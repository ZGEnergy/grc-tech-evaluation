
#= Test B-8: Reference Bus Configuration — DC OPF with 3 slack configs =#

using PowerModels, JuMP, HiGHS, JSON
PowerModels.silence()

const DUAL_SETTING = Dict("output" => Dict("duals" => true))

function run_test(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        # --- Config 1: Default reference bus ---
        data1 = PowerModels.parse_file(network_file)

        # Find default ref bus
        default_ref_bus = -1
        for (i, bus) in data1["bus"]
            if bus["bus_type"] == 3
                default_ref_bus = bus["index"]
            end
        end

        result1 = PowerModels.solve_dc_opf(data1, HiGHS.Optimizer; setting=DUAL_SETTING)
        @assert result1["termination_status"] == OPTIMAL ||
            result1["termination_status"] == LOCALLY_SOLVED

        lmps1 = Dict{Int,Float64}()
        for (i, bus_sol) in result1["solution"]["bus"]
            if haskey(bus_sol, "lam_kcl_r")
                lmps1[parse(Int, i)] = bus_sol["lam_kcl_r"]
            end
        end

        # --- Config 2: Different single slack bus ---
        data2 = PowerModels.parse_file(network_file)

        old_ref = -1
        new_ref = -1
        gen_buses = Set{Int}()
        for (i, gen) in data2["gen"]
            if gen["gen_status"] != 0
                push!(gen_buses, gen["gen_bus"])
            end
        end

        for (i, bus) in data2["bus"]
            if bus["bus_type"] == 3
                old_ref = bus["index"]
            end
        end

        # Pick a different gen bus as the new reference
        for gb in sort(collect(gen_buses))
            if gb != old_ref
                new_ref = gb
                break
            end
        end

        # Swap bus types
        for (i, bus) in data2["bus"]
            if bus["index"] == old_ref
                bus["bus_type"] = 2  # demote to PV
            elseif bus["index"] == new_ref
                bus["bus_type"] = 3  # promote to ref
            end
        end

        result2 = PowerModels.solve_dc_opf(data2, HiGHS.Optimizer; setting=DUAL_SETTING)
        @assert result2["termination_status"] == OPTIMAL ||
            result2["termination_status"] == LOCALLY_SOLVED

        lmps2 = Dict{Int,Float64}()
        for (i, bus_sol) in result2["solution"]["bus"]
            if haskey(bus_sol, "lam_kcl_r")
                lmps2[parse(Int, i)] = bus_sol["lam_kcl_r"]
            end
        end

        # --- Config 3: Distributed slack (workaround with custom constraints) ---
        data3 = PowerModels.parse_file(network_file)

        # Distributed slack requires a custom formulation.
        # PowerModels does NOT support it natively.
        # Workaround: custom build function replacing constraint_theta_ref
        # with a sum-of-angles constraint (uniform distributed slack).
        #
        # In lossless DC OPF, the angle reference only sets the "zero point"
        # for angles. Dispatch and LMPs are independent of which bus is reference.
        # Distributed slack distributes the angle reference uniformly.

        function build_distributed_slack_opf(pm::PowerModels.AbstractPowerModel)
            PowerModels.variable_bus_voltage(pm)
            PowerModels.variable_gen_power(pm)
            PowerModels.variable_branch_power(pm)
            PowerModels.variable_dcline_power(pm)

            PowerModels.objective_min_fuel_and_flow_cost(pm)

            PowerModels.constraint_model_voltage(pm)

            # Replace constraint_theta_ref with distributed slack:
            # Fix sum of all bus angles to zero (uniform participation)
            bus_ids = collect(PowerModels.ids(pm, :bus))
            va_vars = [PowerModels.var(pm, :va, i) for i in bus_ids]
            JuMP.@constraint(pm.model, sum(va_vars) == 0.0)

            for i in PowerModels.ids(pm, :bus)
                PowerModels.constraint_power_balance(pm, i)
            end

            for i in PowerModels.ids(pm, :branch)
                PowerModels.constraint_ohms_yt_from(pm, i)
                PowerModels.constraint_ohms_yt_to(pm, i)
                PowerModels.constraint_voltage_angle_difference(pm, i)
                PowerModels.constraint_thermal_limit_from(pm, i)
                PowerModels.constraint_thermal_limit_to(pm, i)
            end

            for i in PowerModels.ids(pm, :dcline)
                PowerModels.constraint_dcline_power_losses(pm, i)
            end
        end

        result3 = PowerModels.solve_model(
            data3, DCPPowerModel, HiGHS.Optimizer, build_distributed_slack_opf; setting=DUAL_SETTING
        )

        config3_status = string(result3["termination_status"])
        distributed_slack_lmps = Dict{Int,Float64}()
        if result3["termination_status"] == OPTIMAL ||
            result3["termination_status"] == LOCALLY_SOLVED
            for (i, bus_sol) in result3["solution"]["bus"]
                if haskey(bus_sol, "lam_kcl_r")
                    distributed_slack_lmps[parse(Int, i)] = bus_sol["lam_kcl_r"]
                end
            end
        end

        # Compare LMPs across configs
        common_buses_12 = intersect(keys(lmps1), keys(lmps2))
        lmp_diffs_1_vs_2 = Float64[]
        for bus in common_buses_12
            push!(lmp_diffs_1_vs_2, abs(lmps1[bus] - lmps2[bus]))
        end
        max_lmp_diff_1v2 = isempty(lmp_diffs_1_vs_2) ? NaN : maximum(lmp_diffs_1_vs_2)

        common_buses_13 = intersect(keys(lmps1), keys(distributed_slack_lmps))
        lmp_diffs_1_vs_3 = Float64[]
        for bus in common_buses_13
            push!(lmp_diffs_1_vs_3, abs(lmps1[bus] - distributed_slack_lmps[bus]))
        end
        max_lmp_diff_1v3 = isempty(lmp_diffs_1_vs_3) ? NaN : maximum(lmp_diffs_1_vs_3)

        # Sample LMPs for reporting
        all_common = sort(collect(union(common_buses_12, common_buses_13)))
        sample_buses = all_common[1:min(5, length(all_common))]
        sample_lmps = Dict(
            string(bus) => Dict(
                "config1_default" => round(get(lmps1, bus, NaN); digits=4),
                "config2_alt_ref" => round(get(lmps2, bus, NaN); digits=4),
                "config3_distributed" => round(get(distributed_slack_lmps, bus, NaN); digits=4),
            ) for bus in sample_buses
        )

        results["details"] = Dict(
            "default_ref_bus" => default_ref_bus,
            "alt_ref_bus" => new_ref,
            "config1_objective" => round(result1["objective"]; digits=2),
            "config2_objective" => round(result2["objective"]; digits=2),
            "config3_objective" => round(get(result3, "objective", NaN); digits=2),
            "config3_status" => config3_status,
            "max_lmp_diff_config1_vs_config2" =>
                isnan(max_lmp_diff_1v2) ? "N/A" : round(max_lmp_diff_1v2; digits=6),
            "max_lmp_diff_config1_vs_config3" =>
                isnan(max_lmp_diff_1v3) ? "N/A" : round(max_lmp_diff_1v3; digits=6),
            "n_buses_with_lmps_config1" => length(lmps1),
            "n_buses_with_lmps_config2" => length(lmps2),
            "n_buses_with_lmps_config3" => length(distributed_slack_lmps),
            "sample_lmps" => sample_lmps,
            "ref_bus_configurable" => true,
            "ref_bus_mechanism" => "Set bus[\"bus_type\"]=3 for desired ref bus, set old ref to bus_type=2",
            "distributed_slack_native" => false,
            "distributed_slack_workaround" => "Custom build function: replace constraint_theta_ref with sum(va)==0 using PowerModels.var(pm,:va,i)",
        )
        push!(
            results["workarounds"],
            "Distributed slack requires custom build function; not built into PowerModels",
        )

        results["status"] = "pass"
    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
    finally
        results["wall_clock_seconds"] = time() - t0
    end
    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run_test()
    println(JSON.json(result, 2))
end
