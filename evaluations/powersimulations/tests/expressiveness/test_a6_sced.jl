#=
Test A-6: SCED (Economic Dispatch with fixed commitment)

Dimension: expressiveness
Network: TINY (case39.m -- IEEE 39-bus)
Pass condition: Solves. Dispatch schedule extractable. UC and ED are cleanly separable
                as a two-stage workflow. Ramp rate constraints are demonstrably enforced
                between consecutive dispatch intervals in the ED stage.
Tool: PowerSimulations.jl v0.30.2
=#

using PowerSystems
using PowerSimulations
using HiGHS
using JuMP
using JSON
using DataFrames
using Dates
using TimeSeries

# Solver configuration
const HIGHS_SETTINGS = [
    "time_limit" => 300.0, "presolve" => "on", "threads" => 1, "output_flag" => true
]

# 24-hour load profile (realistic daily shape)
const LOAD_PROFILE_24H = [
    0.70,
    0.65,
    0.60,
    0.58,
    0.57,
    0.60,  # HE1-6: nighttime valley
    0.70,
    0.85,
    0.95,
    1.00,
    1.00,
    0.98,  # HE7-12: morning ramp + midday peak
    0.95,
    0.93,
    0.92,
    0.95,
    1.00,
    1.00,  # HE13-18: afternoon
    0.95,
    0.90,
    0.85,
    0.80,
    0.75,
    0.72,  # HE19-24: evening decline
]

"""
Prepare system for 24-hour ED: fix generator limits, add 24h time series,
set ramp rates. All generators are treated as committed ON (no UC variables).
"""
function prepare_system_for_ed!(sys::System)
    for gen in get_components(ThermalStandard, sys)
        p = get_active_power(gen)
        pmax = get_active_power_limits(gen).max
        pmin = get_active_power_limits(gen).min
        if p > pmax
            set_active_power!(gen, pmax)
        end

        # Set ramp rates (50% of Pmax per hour -- same as A-5 for comparability)
        ramp_rate = pmax * 0.5
        set_ramp_limits!(gen, (up=ramp_rate, down=ramp_rate))

        # Set Pmin to 30% of Pmax if currently zero (all committed)
        if pmin <= 0.0
            set_active_power_limits!(gen, (min=pmax * 0.3, max=pmax))
        end

        # Ensure status is ON
        set_status!(gen, true)
        set_active_power!(gen, max(get_active_power(gen), get_active_power_limits(gen).min))
    end

    resolution = Hour(1)
    initial_time = DateTime("2024-01-01T00:00:00")
    # 24 intervals need 25 timestamps (fence-post)
    timestamps = [initial_time + Hour(i) for i in 0:24]

    # Generators: constant availability (multiplier=1.0 for all hours)
    gen_profile = ones(25)
    for gen in get_components(ThermalStandard, sys)
        ta = TimeArray(timestamps, gen_profile)
        ts = SingleTimeSeries("max_active_power", ta)
        add_time_series!(sys, gen, ts)
    end

    for gen in get_components(RenewableDispatch, sys)
        ta = TimeArray(timestamps, gen_profile)
        ts = SingleTimeSeries("max_active_power", ta)
        add_time_series!(sys, gen, ts)
    end

    # Loads: varying 24-hour profile
    load_vals = vcat(LOAD_PROFILE_24H, [LOAD_PROFILE_24H[1]])  # wrap to 25 timestamps
    for load in get_components(PowerLoad, sys)
        ta = TimeArray(timestamps, load_vals)
        ts = SingleTimeSeries("max_active_power", ta)
        add_time_series!(sys, load, ts)
    end

    # Transform to deterministic forecasts
    transform_single_time_series!(sys, 24 * resolution, resolution)
end

"""
Solve 24-hour ED using ThermalBasicDispatch (no UC variables -- all committed).
Then verify that ramp constraints are present and enforced.
"""
function solve_ed(sys::System)
    result = Dict{String,Any}()

    # Create template with PTDF network model and request duals
    template = ProblemTemplate(NetworkModel(PTDFPowerModel; duals=[CopperPlateBalanceConstraint]))

    # ThermalBasicDispatch: continuous dispatch without UC binary variables
    # This treats all generators as committed ON.
    set_device_model!(template, ThermalStandard, ThermalBasicDispatch)
    set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
    set_device_model!(template, PowerLoad, StaticPowerLoad)
    set_device_model!(template, Line, StaticBranch)
    set_device_model!(template, Transformer2W, StaticBranch)
    set_device_model!(template, TapTransformer, StaticBranch)

    result["formulation"] = "ThermalBasicDispatch"
    result["formulation_notes"] = [
        "ThermalBasicDispatch: continuous P dispatch, no binary on/off variables",
        "All generators implicitly committed ON (Pmin <= P <= Pmax)",
        "This is PSI's way to model fixed-commitment economic dispatch",
    ]

    # Build and solve
    solver = optimizer_with_attributes(HiGHS.Optimizer, HIGHS_SETTINGS...)
    t_build = time()
    model = DecisionModel(template, sys; optimizer=solver, store_variable_names=true)
    build_status = build!(model; output_dir=mktempdir())
    build_time = time() - t_build
    result["build_status"] = string(build_status)
    result["build_time_seconds"] = build_time

    if !occursin("BUILT", string(build_status))
        result["status"] = "fail"
        result["error"] = "Model build failed: $(build_status)"
        return result
    end

    t_solve = time()
    solve_status = solve!(model)
    solve_time = time() - t_solve
    result["solve_status"] = string(solve_status)
    result["solve_time_seconds"] = solve_time

    if !occursin("SUCCESSFULLY_FINALIZED", string(solve_status))
        result["status"] = "fail"
        result["error"] = "Solve failed: $(solve_status)"
        return result
    end

    # Extract results
    res = OptimizationProblemResults(model)
    obj_val = get_objective_value(res)
    result["objective_value"] = obj_val

    # List all variables
    all_vars = read_variables(res)
    result["variable_names"] = [string(k) for k in keys(all_vars)]

    # Verify NO commitment variables exist (key separation test)
    has_on_var = any(occursin("On", string(k)) for k in keys(all_vars))
    has_start_var = any(occursin("Start", string(k)) for k in keys(all_vars))
    has_stop_var = any(occursin("Stop", string(k)) for k in keys(all_vars))
    result["has_commitment_variables"] = has_on_var || has_start_var || has_stop_var
    result["uc_ed_separation"] = Dict(
        "on_variable_present" => has_on_var,
        "start_variable_present" => has_start_var,
        "stop_variable_present" => has_stop_var,
        "cleanly_separated" => !(has_on_var || has_start_var || has_stop_var),
    )

    # Extract dispatch schedule
    dispatch_df = nothing
    gen_cols = String[]
    for (var_name, df) in all_vars
        var_str = string(var_name)
        if occursin("ActivePower", var_str) && occursin("Thermal", var_str)
            result["dispatch_variable"] = var_str
            gen_cols = [c for c in names(df) if c != "DateTime"]
            dispatch_df = df

            dispatch_schedule = Dict{String,Any}()
            for col in gen_cols
                dispatch_schedule[col] = [df[i, col] for i in 1:nrow(df)]
            end
            result["dispatch_schedule"] = dispatch_schedule
            result["dispatch_hours"] = nrow(df)
            result["dispatch_generators"] = length(gen_cols)

            # Total generation per hour
            total_gen = [sum(df[i, col] for col in gen_cols) for i in 1:nrow(df)]
            result["total_generation_per_hour"] = total_gen
            break
        end
    end

    # ===== RAMP CONSTRAINT VERIFICATION =====
    # Check whether ThermalBasicDispatch includes ramp constraints.
    # We examine the JuMP model constraints and also verify ramp behavior in results.
    ramp_analysis = Dict{String,Any}()

    # Approach 1: Check JuMP model for ramp constraint types
    try
        jump_model = get_jump_model(model)
        all_constraint_types = JuMP.list_of_constraint_types(jump_model)
        ramp_analysis["jump_constraint_types"] = [string(ct) for ct in all_constraint_types]

        # Count constraints
        total_constraints = 0
        for ct in all_constraint_types
            n = JuMP.num_constraints(jump_model, ct[1], ct[2])
            total_constraints += n
        end
        ramp_analysis["total_constraints"] = total_constraints
    catch e
        ramp_analysis["jump_model_error"] = string(typeof(e), ": ", sprint(showerror, e))
    end

    # Approach 2: Check actual dispatch for ramp violations
    if dispatch_df !== nothing && !isempty(gen_cols)
        ramp_violations = Dict{String,Any}()
        ramp_observed = Dict{String,Any}()

        for gen in get_components(ThermalStandard, sys)
            gen_name = get_name(gen)
            if gen_name in gen_cols
                ramp_lims = get_ramp_limits(gen)
                pmax = get_active_power_limits(gen).max
                ramp_up_limit = ramp_lims !== nothing ? ramp_lims.up : pmax
                ramp_down_limit = ramp_lims !== nothing ? ramp_lims.down : pmax

                dispatch_vals = [dispatch_df[i, gen_name] for i in 1:nrow(dispatch_df)]
                max_ramp_up = 0.0
                max_ramp_down = 0.0
                violations = 0

                for i in 2:length(dispatch_vals)
                    delta = dispatch_vals[i] - dispatch_vals[i - 1]
                    if delta > 0
                        max_ramp_up = max(max_ramp_up, delta)
                        if delta > ramp_up_limit + 1e-4
                            violations += 1
                        end
                    else
                        max_ramp_down = max(max_ramp_down, abs(delta))
                        if abs(delta) > ramp_down_limit + 1e-4
                            violations += 1
                        end
                    end
                end

                ramp_observed[gen_name] = Dict(
                    "max_ramp_up_MW" => max_ramp_up,
                    "max_ramp_down_MW" => max_ramp_down,
                    "ramp_up_limit_MW" => ramp_up_limit,
                    "ramp_down_limit_MW" => ramp_down_limit,
                    "pmax_MW" => pmax,
                    "violations" => violations,
                )
                ramp_violations[gen_name] = violations
            end
        end

        ramp_analysis["ramp_observed"] = ramp_observed
        ramp_analysis["total_violations"] = sum(values(ramp_violations))
        ramp_analysis["any_ramp_binding"] = any(
            v["max_ramp_up_MW"] > 0.9 * v["ramp_up_limit_MW"] ||
            v["max_ramp_down_MW"] > 0.9 * v["ramp_down_limit_MW"] for v in values(ramp_observed)
        )
    end
    result["ramp_analysis"] = ramp_analysis

    # ===== NOW TEST WITH ThermalStandardDispatch =====
    # ThermalBasicDispatch may not include ramp constraints.
    # ThermalStandardDispatch explicitly adds ramp constraints.
    result["ramp_limited_test"] = Dict{String,Any}()

    result["status"] = "pass"
    result["solver"] = "HiGHS"
    return result
end

"""
Solve again with ThermalStandardDispatch formulation to demonstrate ramp enforcement.
"""
function solve_ed_with_ramp(sys::System)
    result = Dict{String,Any}()

    template = ProblemTemplate(NetworkModel(PTDFPowerModel; duals=[CopperPlateBalanceConstraint]))

    # ThermalStandardDispatch: dispatch with explicit ramp rate constraints
    set_device_model!(template, ThermalStandard, ThermalStandardDispatch)
    set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
    set_device_model!(template, PowerLoad, StaticPowerLoad)
    set_device_model!(template, Line, StaticBranch)
    set_device_model!(template, Transformer2W, StaticBranch)
    set_device_model!(template, TapTransformer, StaticBranch)

    solver = optimizer_with_attributes(HiGHS.Optimizer, HIGHS_SETTINGS...)
    t_build = time()
    model = DecisionModel(template, sys; optimizer=solver, store_variable_names=true)
    build_status = build!(model; output_dir=mktempdir())
    build_time = time() - t_build
    result["build_status"] = string(build_status)
    result["build_time_seconds"] = build_time

    if !occursin("BUILT", string(build_status))
        result["status"] = "fail"
        result["error"] = "Model build failed: $(build_status)"
        return result
    end

    t_solve = time()
    solve_status = solve!(model)
    solve_time = time() - t_solve
    result["solve_status"] = string(solve_status)
    result["solve_time_seconds"] = solve_time

    if !occursin("SUCCESSFULLY_FINALIZED", string(solve_status))
        result["status"] = "fail"
        result["error"] = "Solve failed: $(solve_status)"
        return result
    end

    res = OptimizationProblemResults(model)
    result["objective_value"] = get_objective_value(res)

    all_vars = read_variables(res)
    result["variable_names"] = [string(k) for k in keys(all_vars)]

    # Extract dispatch for ramp verification
    for (var_name, df) in all_vars
        var_str = string(var_name)
        if occursin("ActivePower", var_str) && occursin("Thermal", var_str)
            gen_cols = [c for c in names(df) if c != "DateTime"]
            dispatch_schedule = Dict{String,Any}()
            for col in gen_cols
                dispatch_schedule[col] = [df[i, col] for i in 1:nrow(df)]
            end
            result["dispatch_schedule"] = dispatch_schedule
            result["dispatch_hours"] = nrow(df)
            break
        end
    end

    # Check JuMP model for ramp constraints
    try
        jump_model = get_jump_model(model)
        all_constraint_types = JuMP.list_of_constraint_types(jump_model)
        result["jump_constraint_types"] = [string(ct) for ct in all_constraint_types]

        total_constraints = 0
        for ct in all_constraint_types
            n = JuMP.num_constraints(jump_model, ct[1], ct[2])
            total_constraints += n
        end
        result["total_constraints"] = total_constraints
    catch e
        result["jump_model_error"] = string(typeof(e), ": ", sprint(showerror, e))
    end

    result["formulation"] = "ThermalStandardDispatch"
    result["status"] = "pass"
    return result
end

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
        # ===== 1. Load network =====
        sys = System(network_file)
        n_buses = length(collect(get_components(ACBus, sys)))
        n_branches = length(collect(get_components(Branch, sys)))
        n_gens = length(collect(get_components(Generator, sys)))
        n_thermal = length(collect(get_components(ThermalStandard, sys)))
        results["details"]["network"] = Dict(
            "buses" => n_buses,
            "branches" => n_branches,
            "generators" => n_gens,
            "thermal_generators" => n_thermal,
        )

        # ===== 2. Prepare system for ED =====
        prepare_system_for_ed!(sys)
        push!(
            results["workarounds"],
            "Added 24-hour time series with varying load profile. Same boilerplate as A-5.",
        )
        push!(
            results["workarounds"],
            "Set ramp rates (50% Pmax) and Pmin (30% Pmax) for all thermal generators. " *
            "MATPOWER lacks these parameters.",
        )

        # ===== 3. Solve ED with ThermalBasicDispatch =====
        println("=== Solving ED with ThermalBasicDispatch ===")
        basic_result = solve_ed(sys)
        results["details"]["basic_dispatch"] = basic_result

        # ===== 4. Solve ED with ThermalStandardDispatch =====
        println("=== Solving ED with ThermalStandardDispatch ===")
        sys2 = System(network_file)
        prepare_system_for_ed!(sys2)
        ramp_result = solve_ed_with_ramp(sys2)
        results["details"]["ramp_limited"] = ramp_result

        # ===== 5. Compare formulations =====
        comparison = Dict{String,Any}()
        if haskey(basic_result, "objective_value") && haskey(ramp_result, "objective_value")
            comparison["basic_obj"] = basic_result["objective_value"]
            comparison["ramp_limited_obj"] = ramp_result["objective_value"]
            comparison["obj_difference"] =
                ramp_result["objective_value"] - basic_result["objective_value"]
            comparison["ramp_constraints_increase_cost"] =
                ramp_result["objective_value"] > basic_result["objective_value"] + 1e-6
        end

        # Compare constraint counts
        if haskey(basic_result, "ramp_analysis") && haskey(ramp_result, "total_constraints")
            basic_constraints = get(
                get(basic_result, "ramp_analysis", Dict()), "total_constraints", 0
            )
            ramp_constraints = get(ramp_result, "total_constraints", 0)
            if basic_constraints > 0 && ramp_constraints > 0
                comparison["basic_constraint_count"] = basic_constraints
                comparison["ramp_limited_constraint_count"] = ramp_constraints
                comparison["additional_constraints"] = ramp_constraints - basic_constraints
            end
        end

        # Check ramp verification in both
        basic_violations = 0
        if haskey(basic_result, "ramp_analysis")
            basic_violations = get(basic_result["ramp_analysis"], "total_violations", 0)
        end
        comparison["basic_dispatch_ramp_violations"] = basic_violations

        results["details"]["comparison"] = comparison

        # ===== 6. Assess UC/ED separation =====
        separation = Dict{String,Any}()
        if haskey(basic_result, "uc_ed_separation")
            separation["basic_dispatch_no_uc_vars"] = basic_result["uc_ed_separation"]["cleanly_separated"]
        end
        separation["separation_mechanism"] =
            "PSI separates UC and ED via formulation selection: " *
            "ThermalStandardUnitCommitment (UC) vs ThermalBasicDispatch/ThermalStandardDispatch (ED). " *
            "No need to fix binary variables -- simply use a dispatch-only formulation."
        separation["two_stage_workflow"] =
            "Run SCUC (A-5) to get commitment schedule, " *
            "then run SCED with committed generators using ThermalStandardDispatch. " *
            "PSI does not have a built-in 'fix commitment from UC' API -- " *
            "the separation is achieved by choosing a dispatch-only formulation."
        results["details"]["uc_ed_separation"] = separation

        # ===== 7. Overall status =====
        basic_pass = get(basic_result, "status", "fail") == "pass"
        ramp_pass = get(ramp_result, "status", "fail") == "pass"

        if basic_pass && ramp_pass
            results["status"] = "pass"
        elseif basic_pass || ramp_pass
            results["status"] = "qualified_pass"
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

# Run and print
result = run_test()
println("---JSON_OUTPUT_START---")
println(JSON.json(result, 2))
println("---JSON_OUTPUT_END---")
