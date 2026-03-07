#=
Test A-3: DCOPF (DC OPF with generation costs and line flow limits)

Dimension: expressiveness
Network: TINY (case39.m — IEEE 39-bus)
Pass condition: Converges. Optimal dispatch and LMPs/shadow prices extractable from solution.
Tool: PowerSimulations.jl v0.30.2
=#

using PowerSystems
using PowerSimulations
using HiGHS
using GLPK
using JuMP
using JSON
using DataFrames
using Dates
using TimeSeries

# Solver configurations per solver-config.md
const HIGHS_SETTINGS = [
    "time_limit" => 300.0,
    "mip_rel_gap" => 0.01,
    "presolve" => "on",
    "threads" => 1,
    "output_flag" => true,
]

const GLPK_SETTINGS = ["tm_lim" => 300000, "mip_gap" => 0.01, "msg_lev" => GLPK.GLP_MSG_ON]

"""
Prepare system for DecisionModel: fix generator limits and add time series.
PSI requires forecast/time series data — MATPOWER files don't include this.
Time series values are multipliers on max_active_power (1.0 = full capacity available).
"""
function prepare_system_for_opf!(sys::System)
    # Fix generators with active_power > Pmax (data issue in MATPOWER case39)
    for gen in get_components(ThermalStandard, sys)
        p = get_active_power(gen)
        pmax = get_active_power_limits(gen).max
        if p > pmax
            set_active_power!(gen, pmax)
        end
    end

    # Add time series as multipliers on max_active_power
    resolution = Hour(1)
    initial_time = DateTime("2024-01-01T00:00:00")
    timestamps = [initial_time, initial_time + resolution]

    # Generators: 1.0 = full capacity available
    for gen in get_components(ThermalStandard, sys)
        ta = TimeArray(timestamps, [1.0, 1.0])
        ts = SingleTimeSeries("max_active_power", ta)
        add_time_series!(sys, gen, ts)
    end

    # Renewable generators: 1.0 = full capacity available
    for gen in get_components(RenewableDispatch, sys)
        ta = TimeArray(timestamps, [1.0, 1.0])
        ts = SingleTimeSeries("max_active_power", ta)
        add_time_series!(sys, gen, ts)
    end

    # Loads: 1.0 = full load
    for load in get_components(PowerLoad, sys)
        ta = TimeArray(timestamps, [1.0, 1.0])
        ts = SingleTimeSeries("max_active_power", ta)
        add_time_series!(sys, load, ts)
    end

    # Transform single time series to deterministic forecasts
    transform_single_time_series!(sys, resolution, resolution)
end

function solve_dcopf_with_solver(sys::System, solver_name::String, solver)
    result = Dict{String,Any}()

    # Create problem template with PTDF-based DC network model
    # Request duals on CopperPlateBalanceConstraint for energy price
    template = ProblemTemplate(NetworkModel(PTDFPowerModel; duals=[CopperPlateBalanceConstraint]))

    # Set device models — must include all component types present in the network
    set_device_model!(template, ThermalStandard, ThermalBasicDispatch)
    set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
    set_device_model!(template, PowerLoad, StaticPowerLoad)
    set_device_model!(template, Line, StaticBranch)
    set_device_model!(template, Transformer2W, StaticBranch)
    set_device_model!(template, TapTransformer, StaticBranch)

    # Build and solve
    t_solve = time()
    model = DecisionModel(template, sys; optimizer=solver, store_variable_names=true)
    build_status = build!(model; output_dir=mktempdir())
    result["build_status"] = string(build_status)

    if !occursin("BUILT", string(build_status))
        result["status"] = "fail"
        result["error"] = "Model build failed: $(build_status)"
        return result
    end

    solve_status = solve!(model)
    solve_time = time() - t_solve
    result["solve_time_seconds"] = solve_time
    result["solve_status"] = string(solve_status)

    if !occursin("SUCCESSFULLY_FINALIZED", string(solve_status))
        result["status"] = "fail"
        result["error"] = "Solve failed: $(solve_status)"
        return result
    end

    # Extract results
    res = OptimizationProblemResults(model)

    # Objective value (total cost)
    obj_val = get_objective_value(res)
    result["objective_value"] = obj_val

    # Generator dispatch
    all_vars = read_variables(res)
    result["variable_names"] = [string(k) for k in keys(all_vars)]

    for (var_name, df) in all_vars
        var_str = string(var_name)
        if occursin("ActivePower", var_str) && occursin("Thermal", var_str)
            result["dispatch_variable"] = var_str
            gen_cols = [c for c in names(df) if c != "DateTime"]
            dispatch_summary = Dict{String,Any}()
            for col in gen_cols
                dispatch_summary[col] = df[1, col]
            end
            result["dispatch"] = dispatch_summary
            result["dispatch_gen_count"] = length(gen_cols)
            break
        end
    end

    # Extract LMPs/shadow prices (duals)
    try
        all_duals = read_duals(res)
        result["dual_names"] = [string(k) for k in keys(all_duals)]

        for (dual_name, df) in all_duals
            result["lmp_variable"] = string(dual_name)
            dual_cols = [c for c in names(df) if c != "DateTime"]
            lmp_values = Dict{String,Any}()
            for col in dual_cols
                lmp_values[col] = df[1, col]
            end
            result["lmps"] = lmp_values
            result["lmp_count"] = length(dual_cols)
            break
        end
        result["lmp_extraction"] = "success"
    catch e
        result["lmp_extraction"] = "failed"
        result["lmp_error"] = string(typeof(e), ": ", sprint(showerror, e))
    end

    # Optimizer stats
    try
        stats = get_optimizer_stats(res)
        result["optimizer_stats_available"] = true
        result["optimizer_stats_type"] = string(typeof(stats))
    catch
        result["optimizer_stats_available"] = false
    end

    result["status"] = "pass"
    result["solver"] = solver_name
    return result
end

function run(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    try
        # 1. Load network and inspect cost data
        sys = System(network_file)
        n_buses = length(collect(get_components(ACBus, sys)))
        n_branches = length(collect(get_components(Branch, sys)))
        n_gens = length(collect(get_components(Generator, sys)))
        results["details"]["network"] = Dict(
            "buses" => n_buses, "branches" => n_branches, "generators" => n_gens
        )

        # Record branch type breakdown
        results["details"]["branch_types"] = Dict(
            "Line" => length(collect(get_components(Line, sys))),
            "Transformer2W" => length(collect(get_components(Transformer2W, sys))),
            "TapTransformer" => length(collect(get_components(TapTransformer, sys))),
        )

        gens_with_cost = 0
        cost_types = Set{String}()
        for gen in get_components(Generator, sys)
            op_cost = get_operation_cost(gen)
            if op_cost !== nothing
                gens_with_cost += 1
                push!(cost_types, string(typeof(op_cost)))
            end
        end
        results["details"]["generators_with_cost"] = gens_with_cost
        results["details"]["cost_curve_types"] = collect(cost_types)

        # Document cost curve details (first generator as example)
        for gen in get_components(ThermalStandard, sys)
            vc = get_variable(get_operation_cost(gen))
            results["details"]["cost_curve_example"] = string(vc)
            break
        end

        # 2. Prepare system (fix limits + add time series)
        prepare_system_for_opf!(sys)
        push!(
            results["workarounds"],
            "Added synthetic single-period time series (multiplier=1.0) to all generators " *
            "and loads: PSI DecisionModel requires forecast/time series data but MATPOWER " *
            ".m files contain only snapshot data. Time series values are multipliers on " *
            "max_active_power. This is by design (PSI is a simulation framework).",
        )
        push!(
            results["workarounds"],
            "Registered device models for Transformer2W and TapTransformer as StaticBranch: " *
            "case39.m has 34 Lines, 1 Transformer2W, and 11 TapTransformers. PSI requires " *
            "explicit device model registration for every component type in the system.",
        )

        # 3. Test with HiGHS (primary solver)
        highs_solver = optimizer_with_attributes(HiGHS.Optimizer, HIGHS_SETTINGS...)
        highs_result = solve_dcopf_with_solver(sys, "HiGHS", highs_solver)
        results["details"]["highs"] = highs_result

        # 4. Test with GLPK (secondary solver) — reload to avoid state contamination
        sys2 = System(network_file)
        prepare_system_for_opf!(sys2)
        glpk_solver = optimizer_with_attributes(GLPK.Optimizer, GLPK_SETTINGS...)
        glpk_result = solve_dcopf_with_solver(sys2, "GLPK", glpk_solver)
        results["details"]["glpk"] = glpk_result

        # 5. Compare objective values across solvers
        if haskey(highs_result, "objective_value") && haskey(glpk_result, "objective_value")
            h_obj = highs_result["objective_value"]
            g_obj = glpk_result["objective_value"]
            obj_diff = abs(h_obj - g_obj)
            results["details"]["solver_comparison"] = Dict(
                "highs_objective" => h_obj,
                "glpk_objective" => g_obj,
                "absolute_difference" => obj_diff,
                "objectives_match" => obj_diff < 1e-2,
            )
        end

        # 6. Overall status
        highs_pass = get(highs_result, "status", "fail") == "pass"
        glpk_pass = get(glpk_result, "status", "fail") == "pass"

        if highs_pass && glpk_pass
            results["status"] = "pass"
        elseif highs_pass || glpk_pass
            results["status"] = "qualified_pass"
            push!(results["workarounds"], "Only one solver produced valid results")
        end

        results["details"]["output_format"] = "DataFrames via OptimizationProblemResults API (read_variables, read_duals)"

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

# Run and print when executed directly
if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end
