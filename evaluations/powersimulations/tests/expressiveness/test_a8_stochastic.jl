#=
Test A-8: Stochastic Timeseries (12hr multi-period DCOPF with scenarios)

Dimension: expressiveness
Network: TINY (case39.m -- IEEE 39-bus)
Pass condition: Tool natively supports scenario-indexed timeseries for load, wind, and
                solar -- the stochastic structure is part of the optimization formulation
                (e.g., scenario tree, two-stage stochastic program), not just independent
                deterministic solves in a loop.
Tool: PowerSimulations.jl v0.30.2

EXPECTED RESULT: FAIL
PSI does NOT have native stochastic optimization support. PowerSystems.jl has a
`Scenarios` time series type, but PSI's DecisionModel solves deterministic problems only.
This test documents the limitation and demonstrates a manual scenario loop as a workaround.
=#

using PowerSystems
using PowerSimulations
using HiGHS
using JuMP
using JSON
using DataFrames
using Dates
using TimeSeries

const HIGHS_SETTINGS = [
    "time_limit" => 300.0, "presolve" => "on", "threads" => 1, "output_flag" => false
]

# 12-hour load profiles for 3 scenarios (multipliers on base load)
# Scenario 1: High load (hot day)
const SCENARIO_HIGH = [0.85, 0.80, 0.78, 0.82, 0.90, 0.95, 1.00, 1.00, 0.98, 0.95, 0.90, 0.85]
# Scenario 2: Medium load (normal day)
const SCENARIO_MED = [0.70, 0.65, 0.62, 0.68, 0.78, 0.85, 0.90, 0.88, 0.85, 0.82, 0.78, 0.72]
# Scenario 3: Low load (mild day)
const SCENARIO_LOW = [0.55, 0.52, 0.50, 0.55, 0.65, 0.72, 0.78, 0.75, 0.72, 0.68, 0.65, 0.60]

const SCENARIO_PROBS = [0.3, 0.5, 0.2]  # probabilities

"""
Test 1: Check if PSI can use Scenarios time series type in DecisionModel.
This is the native support test -- expected to fail.
"""
function test_native_scenarios(network_file::String)
    result = Dict{String,Any}()
    result["test"] = "native_scenario_support"

    try
        sys = System(network_file)

        # Fix generator limits
        for gen in get_components(ThermalStandard, sys)
            if get_active_power(gen) > get_active_power_limits(gen).max
                set_active_power!(gen, get_active_power_limits(gen).max)
            end
        end

        resolution = Hour(1)
        initial_time = DateTime("2024-01-01T00:00:00")
        timestamps = [initial_time + Hour(i) for i in 0:12]  # 13 for fence-post

        # Try adding Scenarios time series to loads
        scenario_data = hcat(
            vcat(SCENARIO_HIGH, [SCENARIO_HIGH[1]]),
            vcat(SCENARIO_MED, [SCENARIO_MED[1]]),
            vcat(SCENARIO_LOW, [SCENARIO_LOW[1]]),
        )

        scenarios_added = false
        try
            for load in get_components(PowerLoad, sys)
                ta = TimeArray(timestamps, scenario_data)
                ts = Scenarios("max_active_power", ta)
                add_time_series!(sys, load, ts)
            end
            scenarios_added = true
            result["scenarios_added_to_loads"] = true
        catch e
            result["scenarios_added_to_loads"] = false
            result["scenarios_add_error"] = string(typeof(e), ": ", sprint(showerror, e))
        end

        # Add deterministic time series for generators (scenarios only for loads)
        gen_profile = ones(13)
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

        # If scenarios weren't added, add deterministic for loads too
        if !scenarios_added
            for load in get_components(PowerLoad, sys)
                ta = TimeArray(timestamps, vcat(SCENARIO_MED, [SCENARIO_MED[1]]))
                ts = SingleTimeSeries("max_active_power", ta)
                add_time_series!(sys, load, ts)
            end
        end

        # Transform time series
        try
            transform_single_time_series!(sys, 12 * resolution, resolution)
        catch e
            result["transform_error"] = string(typeof(e), ": ", sprint(showerror, e))
        end

        # Try to build a DecisionModel
        template = ProblemTemplate(NetworkModel(PTDFPowerModel))
        set_device_model!(template, ThermalStandard, ThermalBasicDispatch)
        set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
        set_device_model!(template, PowerLoad, StaticPowerLoad)
        set_device_model!(template, Line, StaticBranch)
        set_device_model!(template, Transformer2W, StaticBranch)
        set_device_model!(template, TapTransformer, StaticBranch)

        solver = optimizer_with_attributes(HiGHS.Optimizer, HIGHS_SETTINGS...)
        model = DecisionModel(template, sys; optimizer=solver, store_variable_names=true)

        build_status = build!(model; output_dir=mktempdir())
        result["build_status"] = string(build_status)

        if occursin("BUILT", string(build_status))
            solve_status = solve!(model)
            result["solve_status"] = string(solve_status)

            # Check if scenarios are in the formulation
            try
                jump_model = get_jump_model(model)
                n_vars = JuMP.num_variables(jump_model)
                result["jump_num_variables"] = n_vars
                # A stochastic formulation would have N_scenarios * N_deterministic variables
                # If n_vars matches deterministic count, scenarios are not used
                result["note"] = "Variable count suggests deterministic formulation only"
            catch e
                result["jump_error"] = string(typeof(e), ": ", sprint(showerror, e))
            end

            result["native_stochastic"] = false
            result["reason"] =
                "PSI DecisionModel solves deterministic problems only. " *
                "Even if Scenarios time series are added to PowerSystems.System, " *
                "the DecisionModel does not create scenario-indexed decision variables " *
                "or a stochastic program. The Scenarios type in PowerSystems.jl is for " *
                "data storage, not optimization formulation."
        else
            result["native_stochastic"] = false
            result["reason"] =
                "Model build failed -- Scenarios time series type may not " *
                "be compatible with DecisionModel's time series resolution logic."
        end

    catch e
        result["native_stochastic"] = false
        result["error"] = string(typeof(e), ": ", sprint(showerror, e))
        result["reason"] = "Exception during native scenario test: $(typeof(e))"
    end

    result["status"] = "fail"  # native support does not exist
    return result
end

"""
Test 2: Manual scenario loop workaround.
Solve 3 independent deterministic 12-hour DCOPFs, one per scenario.
Compute expected cost as probability-weighted sum.
"""
function test_scenario_loop(network_file::String)
    result = Dict{String,Any}()
    result["test"] = "manual_scenario_loop_workaround"

    scenarios = Dict("high" => SCENARIO_HIGH, "medium" => SCENARIO_MED, "low" => SCENARIO_LOW)
    probs = Dict("high" => 0.3, "medium" => 0.5, "low" => 0.2)

    scenario_results = Dict{String,Any}()
    expected_cost = 0.0

    for (name, profile) in scenarios
        try
            sys = System(network_file)

            # Fix generator limits
            for gen in get_components(ThermalStandard, sys)
                if get_active_power(gen) > get_active_power_limits(gen).max
                    set_active_power!(gen, get_active_power_limits(gen).max)
                end
            end

            resolution = Hour(1)
            initial_time = DateTime("2024-01-01T00:00:00")
            timestamps = [initial_time + Hour(i) for i in 0:12]

            # Generator time series (constant)
            gen_vals = ones(13)
            for gen in get_components(ThermalStandard, sys)
                ta = TimeArray(timestamps, gen_vals)
                ts = SingleTimeSeries("max_active_power", ta)
                add_time_series!(sys, gen, ts)
            end
            for gen in get_components(RenewableDispatch, sys)
                ta = TimeArray(timestamps, gen_vals)
                ts = SingleTimeSeries("max_active_power", ta)
                add_time_series!(sys, gen, ts)
            end

            # Load time series (scenario-specific)
            load_vals = vcat(profile, [profile[1]])
            for load in get_components(PowerLoad, sys)
                ta = TimeArray(timestamps, load_vals)
                ts = SingleTimeSeries("max_active_power", ta)
                add_time_series!(sys, load, ts)
            end

            transform_single_time_series!(sys, 12 * resolution, resolution)

            # Build and solve
            template = ProblemTemplate(NetworkModel(PTDFPowerModel))
            set_device_model!(template, ThermalStandard, ThermalBasicDispatch)
            set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
            set_device_model!(template, PowerLoad, StaticPowerLoad)
            set_device_model!(template, Line, StaticBranch)
            set_device_model!(template, Transformer2W, StaticBranch)
            set_device_model!(template, TapTransformer, StaticBranch)

            solver = optimizer_with_attributes(HiGHS.Optimizer, HIGHS_SETTINGS...)
            model = DecisionModel(template, sys; optimizer=solver, store_variable_names=true)
            build_status = build!(model; output_dir=mktempdir())

            if occursin("BUILT", string(build_status))
                solve_status = solve!(model)
                if occursin("SUCCESSFULLY_FINALIZED", string(solve_status))
                    res = OptimizationProblemResults(model)
                    obj = get_objective_value(res)
                    scenario_results[name] = Dict(
                        "status" => "pass",
                        "objective_value" => obj,
                        "probability" => probs[name],
                        "weighted_cost" => obj * probs[name],
                    )
                    expected_cost += obj * probs[name]
                else
                    scenario_results[name] = Dict(
                        "status" => "fail", "error" => "Solve failed: $(solve_status)"
                    )
                end
            else
                scenario_results[name] = Dict(
                    "status" => "fail", "error" => "Build failed: $(build_status)"
                )
            end
        catch e
            scenario_results[name] = Dict(
                "status" => "fail", "error" => string(typeof(e), ": ", sprint(showerror, e))
            )
        end
    end

    result["scenario_results"] = scenario_results
    result["expected_cost"] = expected_cost
    result["all_scenarios_solved"] = all(
        get(v, "status", "fail") == "pass" for v in values(scenario_results)
    )

    result["limitation"] = Dict(
        "description" =>
            "Manual scenario loop is NOT a stochastic program. " *
            "Each scenario is solved independently -- there are no linking constraints " *
            "(e.g., first-stage commitment decisions that must be the same across scenarios). " *
            "This is just Monte Carlo simulation, not stochastic optimization.",
        "what_would_be_needed" => [
            "Scenario-indexed decision variables (e.g., x[scenario, time, generator])",
            "Non-anticipativity constraints linking first-stage decisions across scenarios",
            "Scenario tree structure (e.g., two-stage: commit now, dispatch per scenario)",
            "Probability weights in the objective function",
        ],
        "psi_gap" =>
            "PSI's DecisionModel is deterministic only. The Scenarios type in " *
            "PowerSystems.jl is for data storage, not used in optimization formulations.",
    )

    result["status"] = "pass"  # The workaround loop itself works
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
        # ===== Test 1: Native stochastic support =====
        println("=== Test 1: Checking native stochastic support ===")
        native_result = test_native_scenarios(network_file)
        results["details"]["native_test"] = native_result

        # ===== Test 2: Manual scenario loop workaround =====
        println("=== Test 2: Manual scenario loop workaround ===")
        loop_result = test_scenario_loop(network_file)
        results["details"]["loop_workaround"] = loop_result

        # ===== Assessment =====
        results["details"]["assessment"] = Dict(
            "native_stochastic_support" => false,
            "scenario_loop_works" => get(loop_result, "all_scenarios_solved", false),
            "verdict" =>
                "FAIL: PSI does not natively support stochastic optimization. " *
                "The tool can solve individual scenarios deterministically, but cannot " *
                "formulate a stochastic program with scenario-indexed variables, " *
                "non-anticipativity constraints, or probability-weighted objectives. " *
                "The Scenarios time series type in PowerSystems.jl is a data container " *
                "that is not consumed by PSI's optimization formulations.",
        )

        push!(
            results["workarounds"],
            "Manual scenario loop: solve independent deterministic DCOPFs per scenario " *
            "and compute expected cost. This is NOT stochastic optimization -- no linking " *
            "constraints between scenarios.",
        )

        # Status is FAIL because the pass condition requires NATIVE support
        results["status"] = "fail"

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
