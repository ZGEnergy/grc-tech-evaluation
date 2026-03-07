#=
Test A-4: AC Feasibility Check (DC OPF dispatch -> ACPF validation)

Dimension: expressiveness
Network: TINY (case39.m -- IEEE 39-bus)
Pass condition: Achievable within the same model context (no export to file and reimport).
                Voltage violations and thermal limit violations identifiable from results.
Tool: PowerSimulations.jl v0.30.2 (via PowerFlows.jl v0.9.0)
=#

using PowerSystems
using PowerSimulations
using PowerFlows
using HiGHS
using JuMP
using JSON
using DataFrames
using Dates
using TimeSeries

const HIGHS_SETTINGS = [
    "time_limit" => 300.0,
    "mip_rel_gap" => 0.01,
    "presolve" => "on",
    "threads" => 1,
    "output_flag" => false,
]

function run_test(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    try
        # ===== STEP 1: Load system =====
        sys = System(network_file)
        n_buses = length(collect(get_components(ACBus, sys)))
        n_branches = length(collect(get_components(Branch, sys)))
        n_gens = length(collect(get_components(Generator, sys)))
        results["details"]["network"] = Dict(
            "buses" => n_buses, "branches" => n_branches, "generators" => n_gens
        )

        # ===== STEP 2: Solve DC OPF to get dispatch =====
        for gen in get_components(ThermalStandard, sys)
            p = get_active_power(gen)
            pmax = get_active_power_limits(gen).max
            if p > pmax
                set_active_power!(gen, pmax)
            end
        end

        resolution = Hour(1)
        initial_time = DateTime("2024-01-01T00:00:00")
        timestamps = [initial_time, initial_time + resolution]

        for gen in get_components(ThermalStandard, sys)
            ta = TimeArray(timestamps, [1.0, 1.0])
            ts = SingleTimeSeries("max_active_power", ta)
            add_time_series!(sys, gen, ts)
        end
        for gen in get_components(RenewableDispatch, sys)
            ta = TimeArray(timestamps, [1.0, 1.0])
            ts = SingleTimeSeries("max_active_power", ta)
            add_time_series!(sys, gen, ts)
        end
        for load in get_components(PowerLoad, sys)
            ta = TimeArray(timestamps, [1.0, 1.0])
            ts = SingleTimeSeries("max_active_power", ta)
            add_time_series!(sys, load, ts)
        end
        transform_single_time_series!(sys, resolution, resolution)

        template = ProblemTemplate(
            NetworkModel(PTDFPowerModel; duals=[CopperPlateBalanceConstraint])
        )
        set_device_model!(template, ThermalStandard, ThermalBasicDispatch)
        set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
        set_device_model!(template, PowerLoad, StaticPowerLoad)
        set_device_model!(template, Line, StaticBranch)
        set_device_model!(template, Transformer2W, StaticBranch)
        set_device_model!(template, TapTransformer, StaticBranch)

        highs_solver = optimizer_with_attributes(HiGHS.Optimizer, HIGHS_SETTINGS...)
        model = DecisionModel(template, sys; optimizer=highs_solver, store_variable_names=true)
        build_status = build!(model; output_dir=mktempdir())
        results["details"]["dcopf_build_status"] = string(build_status)

        if !occursin("BUILT", string(build_status))
            push!(results["errors"], "DC OPF build failed: $(build_status)")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        t_dcopf = time()
        solve_status = solve!(model)
        dcopf_time = time() - t_dcopf
        results["details"]["dcopf_solve_status"] = string(solve_status)
        results["details"]["dcopf_solve_time"] = dcopf_time

        if !occursin("SUCCESSFULLY", string(solve_status))
            push!(results["errors"], "DC OPF solve failed: $(solve_status)")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        res = OptimizationProblemResults(model)
        results["details"]["dcopf_objective"] = get_objective_value(res)

        all_vars = read_variables(res)
        dispatch_values = Dict{String,Float64}()
        for (var_name, df) in all_vars
            var_str = string(var_name)
            if occursin("ActivePower", var_str) && occursin("Thermal", var_str)
                gen_cols = [c for c in names(df) if c != "DateTime"]
                for col in gen_cols
                    dispatch_values[col] = df[1, col]
                end
                break
            end
        end
        results["details"]["dispatch_gen_count"] = length(dispatch_values)
        base_power = get_base_power(sys)
        results["details"]["base_power_mva"] = base_power

        # ===== STEP 3: Apply dispatch to SAME system and run ACPF =====
        dispatch_applied = Dict{String,Any}()
        for gen in get_components(ThermalStandard, sys)
            gen_name = get_name(gen)
            if haskey(dispatch_values, gen_name)
                new_p = dispatch_values[gen_name]
                set_active_power!(gen, new_p)
                dispatch_applied[gen_name] = Dict(
                    "dispatch_pu" => new_p, "dispatch_mw" => new_p * base_power
                )
            end
        end
        results["details"]["dispatch_applied"] = dispatch_applied
        results["details"]["same_model_context"] = true

        push!(
            results["workarounds"],
            "Time series boilerplate required for PSI DecisionModel (same as A-3). " *
            "Dispatch transfer from PSI to PowerFlows via shared System object — no file I/O.",
        )

        # ===== STEP 4: Run ACPF =====
        t_acpf = time()
        pf_result = solve_powerflow(ACPowerFlow(), sys)
        acpf_time = time() - t_acpf
        results["details"]["acpf_solve_time"] = acpf_time

        if ismissing(pf_result) || pf_result === nothing
            results["details"]["flat_start_converged"] = false
            solve_powerflow(DCPowerFlow(), sys)
            t_acpf2 = time()
            pf_result = solve_powerflow(ACPowerFlow(), sys)
            acpf_time = time() - t_acpf2
            if ismissing(pf_result) || pf_result === nothing
                push!(results["errors"], "ACPF did not converge even with DC warm start")
                results["wall_clock_seconds"] = time() - t0
                return results
            end
            results["details"]["dc_warmstart_needed"] = true
        else
            results["details"]["flat_start_converged"] = true
        end

        # ===== STEP 5: Voltage violations =====
        bus_df = pf_result["bus_results"]
        results["details"]["bus_results_columns"] = string.(names(bus_df))

        voltage_violations = Dict{String,Any}[]
        if "Vm" in names(bus_df)
            for i in 1:DataFrames.nrow(bus_df)
                v = bus_df[i, "Vm"]
                if v < 0.95 || v > 1.05
                    bus_id =
                        "bus_number" in names(bus_df) ? string(bus_df[i, "bus_number"]) : string(i)
                    push!(voltage_violations, Dict("bus" => bus_id, "vm_pu" => v))
                end
            end
            vm_vals = bus_df[!, "Vm"]
            results["details"]["voltage_stats"] = Dict(
                "min_vm" => minimum(vm_vals), "max_vm" => maximum(vm_vals)
            )
        end
        results["details"]["voltage_violations"] = voltage_violations
        results["details"]["voltage_violation_count"] = length(voltage_violations)

        # ===== STEP 6: Thermal violations =====
        flow_df = pf_result["flow_results"]
        results["details"]["flow_results_columns"] = string.(names(flow_df))

        thermal_violations = Dict{String,Any}[]
        branch_ratings = Dict{String,Float64}()
        for br in get_components(Branch, sys)
            branch_ratings[get_name(br)] = get_rating(br)
        end

        if "line_name" in names(flow_df) && "P_from_to" in names(flow_df)
            for i in 1:DataFrames.nrow(flow_df)
                line_name = string(flow_df[i, "line_name"])
                p_from = abs(flow_df[i, "P_from_to"])
                p_to = "P_to_from" in names(flow_df) ? abs(flow_df[i, "P_to_from"]) : p_from
                max_flow = max(p_from, p_to)
                if haskey(branch_ratings, line_name)
                    rating = branch_ratings[line_name]
                    if rating > 0 && max_flow > rating
                        push!(
                            thermal_violations,
                            Dict(
                                "branch" => line_name,
                                "flow_pu" => max_flow,
                                "rating_pu" => rating,
                                "overload_pct" => (max_flow / rating - 1.0) * 100,
                            ),
                        )
                    end
                end
            end
        end
        results["details"]["thermal_violations"] = thermal_violations
        results["details"]["thermal_violation_count"] = length(thermal_violations)

        # ===== STEP 7: Per-gen reactive power via mutating solve =====
        reactive_violations = Dict{String,Any}[]
        try
            pf_converged = solve_powerflow!(ACPowerFlow(), sys)
            results["details"]["mutating_pf_converged"] = pf_converged
            if pf_converged
                for gen in get_components(ThermalStandard, sys)
                    q = get_reactive_power(gen)
                    q_limits = get_reactive_power_limits(gen)
                    if q < q_limits.min || q > q_limits.max
                        push!(
                            reactive_violations,
                            Dict(
                                "generator" => get_name(gen),
                                "q_pu" => q,
                                "q_min" => q_limits.min,
                                "q_max" => q_limits.max,
                            ),
                        )
                    end
                end
            end
        catch e
            results["details"]["mutating_pf_error"] = string(e)
        end
        results["details"]["reactive_violations"] = reactive_violations
        results["details"]["reactive_violation_count"] = length(reactive_violations)

        results["details"]["summary"] = Dict(
            "dcopf_solved" => true,
            "acpf_converged" => true,
            "same_model_context" => true,
            "voltage_violations" => length(voltage_violations),
            "thermal_violations" => length(thermal_violations),
            "reactive_violations" => length(reactive_violations),
        )
        results["status"] = "pass"

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

result = run_test()
println(JSON.json(result, 2))
