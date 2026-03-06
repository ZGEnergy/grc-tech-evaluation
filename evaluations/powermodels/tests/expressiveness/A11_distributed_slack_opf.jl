#= Test A-11: DC OPF with distributed slack (load-proportional)
   Compare LMPs to single-slack from A-3.
   PowerModels has NO native distributed slack -- uses custom build function (as in B-8).
=#
using PowerModels, JuMP, HiGHS, JSON
PowerModels.silence()

function run(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "test_id" => "A-11",
        "test_name" => "distributed_slack_opf",
        "network" => "case39",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        data = PowerModels.parse_file(network_file)

        # --- Step 1: Single-slack DC OPF (reproduce A-3 for comparison) ---
        result_single = solve_dc_opf(
            data, HiGHS.Optimizer; setting=Dict("output" => Dict("duals" => true))
        )

        @assert result_single["termination_status"] == OPTIMAL "Single-slack DC OPF did not converge"

        single_lmps = Dict{String,Float64}()
        for (bid, bus) in result_single["solution"]["bus"]
            single_lmps[bid] = get(bus, "lam_kcl_r", NaN)
        end
        results["details"]["single_slack_objective"] = result_single["objective"]
        results["details"]["single_slack_lmps"] = single_lmps

        # Find reference bus
        ref_bus = ""
        for (bid, bus) in data["bus"]
            if bus["bus_type"] == 3
                ref_bus = bid
            end
        end
        results["details"]["single_slack_ref_bus"] = ref_bus

        # --- Step 2: Distributed slack DC OPF ---
        # Load-proportional distributed slack: weight angles by bus load
        # In lossless DC OPF, this affects only angle reference, not dispatch/LMPs.
        # But we implement it properly to test the mechanism.

        data2 = PowerModels.parse_file(network_file)

        # Compute load-proportional weights
        bus_loads = Dict{Int,Float64}()
        total_load = 0.0
        for (lid, load) in data2["load"]
            bid = load["load_bus"]
            bus_loads[bid] = get(bus_loads, bid, 0.0) + load["pd"]
            total_load += load["pd"]
        end

        function build_distributed_slack_opf(pm::PowerModels.AbstractPowerModel)
            PowerModels.variable_bus_voltage(pm)
            PowerModels.variable_gen_power(pm)
            PowerModels.variable_branch_power(pm)
            PowerModels.variable_dcline_power(pm)

            PowerModels.objective_min_fuel_and_flow_cost(pm)

            PowerModels.constraint_model_voltage(pm)

            # Replace constraint_theta_ref with load-proportional distributed slack:
            # sum(w_i * va_i) = 0 where w_i = load_i / total_load
            bus_ids = collect(PowerModels.ids(pm, :bus))
            va_expr = AffExpr(0.0)
            for i in bus_ids
                va_i = PowerModels.var(pm, :va, i)
                weight = get(bus_loads, i, 0.0) / total_load
                if weight > 0
                    add_to_expression!(va_expr, weight, va_i)
                else
                    # Buses without load get uniform weight
                    add_to_expression!(va_expr, 1.0 / length(bus_ids), va_i)
                end
            end
            JuMP.@constraint(pm.model, va_expr == 0.0)

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

        result_dist = PowerModels.solve_model(
            data2,
            DCPPowerModel,
            HiGHS.Optimizer,
            build_distributed_slack_opf;
            setting=Dict("output" => Dict("duals" => true)),
        )

        dist_status = result_dist["termination_status"]
        results["details"]["distributed_slack_status"] = string(dist_status)

        if dist_status == OPTIMAL || dist_status == LOCALLY_SOLVED
            results["details"]["distributed_slack_objective"] = result_dist["objective"]

            dist_lmps = Dict{String,Float64}()
            for (bid, bus) in result_dist["solution"]["bus"]
                dist_lmps[bid] = get(bus, "lam_kcl_r", NaN)
            end
            results["details"]["distributed_slack_lmps"] = dist_lmps

            # --- Step 3: Compare LMPs ---
            lmp_diffs = Dict{String,Float64}()
            max_diff = 0.0
            for bid in keys(single_lmps)
                if haskey(dist_lmps, bid)
                    diff = abs(single_lmps[bid] - dist_lmps[bid])
                    lmp_diffs[bid] = round(diff; digits=6)
                    max_diff = max(max_diff, diff)
                end
            end
            results["details"]["lmp_differences"] = lmp_diffs
            results["details"]["max_lmp_difference"] = round(max_diff; digits=6)

            # Objective comparison
            obj_diff = abs(result_single["objective"] - result_dist["objective"])
            results["details"]["objective_difference"] = round(obj_diff; digits=6)

            # In lossless DC OPF, objectives and LMPs should be identical
            # regardless of slack distribution
            results["details"]["lmps_match"] = max_diff < 1e-4
            results["details"]["objectives_match"] = obj_diff < 1e-4

            # Dispatch comparison
            single_dispatch = Dict{String,Float64}()
            dist_dispatch = Dict{String,Float64}()
            for (gid, gen) in result_single["solution"]["gen"]
                single_dispatch[gid] = gen["pg"]
            end
            for (gid, gen) in result_dist["solution"]["gen"]
                dist_dispatch[gid] = gen["pg"]
            end
            dispatch_diffs = Dict{String,Float64}()
            for gid in keys(single_dispatch)
                if haskey(dist_dispatch, gid)
                    dispatch_diffs[gid] = round(
                        abs(single_dispatch[gid] - dist_dispatch[gid]); digits=6
                    )
                end
            end
            results["details"]["dispatch_differences"] = dispatch_diffs

            results["details"]["method"] = "Custom build function with load-proportional angle reference (sum(w_i * va_i) = 0)"
            push!(
                results["workarounds"],
                "PowerModels has NO native distributed slack. Required custom build function replacing constraint_theta_ref with weighted angle-sum constraint (~40 LOC).",
            )

            results["status"] = "pass"
        else
            push!(results["errors"], "Distributed slack OPF did not converge: $dist_status")
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
    finally
        results["wall_clock_seconds"] = time() - t0
    end
    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end
