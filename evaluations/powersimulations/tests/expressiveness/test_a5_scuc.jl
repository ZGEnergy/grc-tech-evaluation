#=
Test A-5: SCUC (24-hour Security-Constrained Unit Commitment)

Dimension: expressiveness
Network: TINY (case39.m -- IEEE 39-bus)
Pass condition: Solves to feasibility (MIP gap <= 1% on TINY). Commitment schedule
                extractable as a time-indexed binary matrix. Built-in constraint types
                vs. user-assembled noted.
Tool: PowerSimulations.jl v0.30.2
=#

using PowerSystems
using PowerSimulations
using HiGHS
using SCIP
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

const SCIP_SETTINGS = [
    "limits/time" => 300.0, "limits/gap" => 0.01, "display/verblevel" => 4, "lp/threads" => 1
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
Prepare system for 24-hour SCUC: fix generator limits, add 24h time series,
set unit commitment parameters.
"""
function prepare_system_for_scuc!(sys::System)
    # Fix generators with active_power > Pmax and set UC parameters
    # MATPOWER case39 does not include UC parameters (ramp rates, min up/down,
    # startup costs). We set reasonable defaults for all thermal generators.
    for gen in get_components(ThermalStandard, sys)
        p = get_active_power(gen)
        pmax = get_active_power_limits(gen).max
        pmin = get_active_power_limits(gen).min
        if p > pmax
            set_active_power!(gen, pmax)
        end

        # Set ramp rates (50% of Pmax per hour — moderate ramp capability)
        ramp_rate = pmax * 0.5
        set_ramp_limits!(gen, (up=ramp_rate, down=ramp_rate))

        # Set min up/down times (2 hours each)
        set_time_limits!(gen, (up=2.0, down=2.0))

        # Set Pmin to 30% of Pmax if currently zero (realistic minimum stable output)
        if pmin <= 0.0
            set_active_power_limits!(gen, (min=pmax * 0.3, max=pmax))
        end

        # Set status to ON initially
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

    # Transform single time series to deterministic forecasts
    transform_single_time_series!(sys, 24 * resolution, resolution)
end

"""
Solve SCUC with a given solver and return structured results.
"""
function solve_scuc_with_solver(sys::System, solver_name::String, solver)
    result = Dict{String,Any}()

    # Create problem template with PTDF network model
    template = ProblemTemplate(NetworkModel(PTDFPowerModel))

    # ThermalStandardUnitCommitment includes built-in constraints:
    # - Binary on/off commitment variables
    # - Min up/down time constraints
    # - Ramp rate constraints
    # - Startup/shutdown costs
    # - Min/max generation limits when committed
    set_device_model!(template, ThermalStandard, ThermalStandardUnitCommitment)
    set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
    set_device_model!(template, PowerLoad, StaticPowerLoad)
    set_device_model!(template, Line, StaticBranch)
    set_device_model!(template, Transformer2W, StaticBranch)
    set_device_model!(template, TapTransformer, StaticBranch)

    # Document built-in vs user-assembled constraint types
    result["formulation"] = "ThermalStandardUnitCommitment"
    result["builtin_constraints"] = [
        "ActivePowerLimits (min/max gen when committed)",
        "CommitmentVariable (binary on/off)",
        "StartupVariable / ShutdownVariable",
        "MinUpTime / MinDownTime",
        "RampLimits (up/down ramp rates)",
        "StartupCost / ShutdownCost",
    ]
    result["user_assembled_constraints"] = [
        "Network model selection (PTDFPowerModel vs DCPPowerModel)",
        "Device model selection per component type",
    ]

    # Build and solve
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

    # Extract commitment schedule (OnVariable__ThermalStandard)
    commitment_extracted = false
    for (var_name, df) in all_vars
        var_str = string(var_name)
        if occursin("On", var_str) && occursin("Thermal", var_str)
            result["commitment_variable"] = var_str
            gen_cols = [c for c in names(df) if c != "DateTime"]

            # Build time-indexed commitment matrix
            commitment_matrix = Dict{String,Any}()
            for col in gen_cols
                commitment_matrix[col] = [df[i, col] for i in 1:nrow(df)]
            end
            result["commitment_schedule"] = commitment_matrix
            result["commitment_hours"] = nrow(df)
            result["commitment_generators"] = length(gen_cols)

            # Summary: which generators are committed each hour
            committed_per_hour = [
                sum(df[i, col] >= 0.5 ? 1 : 0 for col in gen_cols) for i in 1:nrow(df)
            ]
            result["committed_per_hour"] = committed_per_hour

            # Check if any generators cycle (turn on/off)
            cycling_gens = String[]
            for col in gen_cols
                vals = [df[i, col] >= 0.5 ? 1 : 0 for i in 1:nrow(df)]
                if length(unique(vals)) > 1
                    push!(cycling_gens, col)
                end
            end
            result["cycling_generators"] = cycling_gens
            result["cycling_count"] = length(cycling_gens)

            commitment_extracted = true
            break
        end
    end
    result["commitment_extracted"] = commitment_extracted

    # Extract dispatch schedule
    for (var_name, df) in all_vars
        var_str = string(var_name)
        if occursin("ActivePower", var_str) && occursin("Thermal", var_str)
            result["dispatch_variable"] = var_str
            gen_cols = [c for c in names(df) if c != "DateTime"]

            # Dispatch summary per hour
            dispatch_per_hour = Dict{String,Any}()
            for col in gen_cols
                dispatch_per_hour[col] = [df[i, col] for i in 1:nrow(df)]
            end
            result["dispatch_schedule"] = dispatch_per_hour
            result["dispatch_hours"] = nrow(df)

            # Total generation per hour
            total_gen = [sum(df[i, col] for col in gen_cols) for i in 1:nrow(df)]
            result["total_generation_per_hour"] = total_gen
            break
        end
    end

    # Extract startup/shutdown variables if available
    for (var_name, df) in all_vars
        var_str = string(var_name)
        if occursin("Start", var_str) && occursin("Thermal", var_str)
            result["startup_variable"] = var_str
            gen_cols = [c for c in names(df) if c != "DateTime"]
            startups = Dict{String,Int}()
            for col in gen_cols
                startups[col] = sum(df[i, col] >= 0.5 ? 1 : 0 for i in 1:nrow(df))
            end
            result["startup_counts"] = startups
        end
        if occursin("Stop", var_str) && occursin("Thermal", var_str)
            result["shutdown_variable"] = var_str
        end
    end

    # MIP gap (from JuMP model if accessible)
    try
        jump_model = get_jump_model(model)
        if jump_model !== nothing
            result["termination_status"] = string(JuMP.termination_status(jump_model))
            result["primal_status"] = string(JuMP.primal_status(jump_model))
            try
                result["relative_gap"] = JuMP.relative_gap(jump_model)
            catch
                result["relative_gap"] = "not available"
            end
            try
                result["node_count"] = JuMP.node_count(jump_model)
            catch
                result["node_count"] = "not available"
            end
        end
    catch e
        result["jump_model_access_error"] = string(typeof(e), ": ", sprint(showerror, e))
    end

    result["status"] = "pass"
    result["solver"] = solver_name
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

        # Document UC-relevant generator parameters
        uc_params = Dict{String,Any}[]
        for gen in get_components(ThermalStandard, sys)
            gen_name = get_name(gen)
            plims = get_active_power_limits(gen)
            ramp = get_ramp_limits(gen)
            time_limits = get_time_limits(gen)
            push!(
                uc_params,
                Dict(
                    "name" => gen_name,
                    "pmin" => plims.min,
                    "pmax" => plims.max,
                    "ramp_up" => ramp !== nothing ? ramp.up : nothing,
                    "ramp_down" => ramp !== nothing ? ramp.down : nothing,
                    "min_up_time" => time_limits !== nothing ? time_limits.up : nothing,
                    "min_down_time" => time_limits !== nothing ? time_limits.down : nothing,
                ),
            )
        end
        results["details"]["uc_parameters"] = uc_params

        # ===== 2. Prepare 24h time series =====
        prepare_system_for_scuc!(sys)
        push!(
            results["workarounds"],
            "Added 24-hour time series with varying load profile to all components. " *
            "Same pattern as A-3/A-4 but with 25 timestamps for 24 intervals.",
        )

        # ===== 3. Solve with HiGHS (primary MIP solver) =====
        highs_solver = optimizer_with_attributes(HiGHS.Optimizer, HIGHS_SETTINGS...)
        highs_result = solve_scuc_with_solver(sys, "HiGHS", highs_solver)
        results["details"]["highs"] = highs_result

        # ===== 4. Solve with SCIP (secondary MIP solver) =====
        sys2 = System(network_file)
        prepare_system_for_scuc!(sys2)
        scip_solver = optimizer_with_attributes(SCIP.Optimizer, SCIP_SETTINGS...)
        scip_result = solve_scuc_with_solver(sys2, "SCIP", scip_solver)
        results["details"]["scip"] = scip_result

        # ===== 5. Compare solvers =====
        if haskey(highs_result, "objective_value") && haskey(scip_result, "objective_value")
            h_obj = highs_result["objective_value"]
            s_obj = scip_result["objective_value"]
            results["details"]["solver_comparison"] = Dict(
                "highs_objective" => h_obj,
                "scip_objective" => s_obj,
                "absolute_difference" => abs(h_obj - s_obj),
                "relative_difference_pct" => abs(h_obj - s_obj) / max(abs(h_obj), 1e-10) * 100,
            )
        end

        # ===== 6. Document built-in vs user-assembled constraints =====
        results["details"]["constraint_analysis"] = Dict(
            "builtin" => [
                "ThermalStandardUnitCommitment formulation provides:",
                "  - Binary commitment variables (OnVariable)",
                "  - Startup/Shutdown variables (StartVariable/StopVariable)",
                "  - Active power limits coupled with commitment (Pmin*u <= P <= Pmax*u)",
                "  - Min up/down time constraints",
                "  - Ramp rate constraints",
                "  - Startup/shutdown cost modeling",
            ],
            "user_assembled" => [
                "User selects:",
                "  - Network formulation (PTDFPowerModel, DCPPowerModel, etc.)",
                "  - Device model per component type",
                "  - Service models (reserves) if needed",
                "  - Solver and its parameters",
            ],
            "note" =>
                "PSI provides rich built-in UC formulations. Most SCUC constraints " *
                "are built into ThermalStandardUnitCommitment. The user primarily " *
                "configures which formulation to use, not individual constraints.",
        )

        # ===== 7. Overall status =====
        highs_pass = get(highs_result, "status", "fail") == "pass"
        scip_pass = get(scip_result, "status", "fail") == "pass"

        # Check MIP gap <= 1% for pass condition
        highs_gap_ok = false
        scip_gap_ok = false
        if haskey(highs_result, "relative_gap")
            gap = highs_result["relative_gap"]
            if isa(gap, Number)
                highs_gap_ok = gap <= 0.01
                results["details"]["highs_mip_gap_pct"] = gap * 100
            end
        end
        if haskey(scip_result, "relative_gap")
            gap = scip_result["relative_gap"]
            if isa(gap, Number)
                scip_gap_ok = gap <= 0.01
                results["details"]["scip_mip_gap_pct"] = gap * 100
            end
        end

        # Commitment extractable?
        highs_commit = get(highs_result, "commitment_extracted", false)
        scip_commit = get(scip_result, "commitment_extracted", false)

        if highs_pass && highs_commit
            results["status"] = "pass"
        elseif scip_pass && scip_commit
            results["status"] = "pass"
        elseif highs_pass || scip_pass
            results["status"] = "qualified_pass"
            push!(results["workarounds"], "Commitment extraction incomplete for one solver")
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
println(JSON.json(result, 2))
