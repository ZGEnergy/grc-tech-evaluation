#=
Test A-8: Stochastic Timeseries DCOPF on TINY (IEEE 39-bus)
Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Tool natively supports scenario-indexed timeseries as part of
               the optimization formulation (not just independent deterministic
               solves in a loop).
Tool: PowerModels.jl v0.21.5
Solver: HiGHS

ASSESSMENT: PowerModels.jl does NOT have native stochastic OPF support.
The multi-network framework (replicate()) supports multi-period but NOT
multi-scenario optimization. StochasticPowerModels.jl is a SEPARATE external
package (not installed, not part of core PowerModels).

The test protocol explicitly states: "A tool that only supports deterministic
solves but can be wrapped in a Monte Carlo loop is tested under Extensibility
(B-4), not here." And: "A passing grade on A-8 requires that the tool's
optimization formulation is aware of multiple scenarios simultaneously."

This test documents the FAILURE and demonstrates what IS possible (multi-period
deterministic DCOPF via replicate/solve_mn_opf) vs. what is NOT possible
(scenario-indexed stochastic formulation).
=#

using PowerModels, JuMP, HiGHS, JSON

function run(
    network_file::String=joinpath(@__DIR__, "..", "..", "..", "..", "data", "networks", "case39.m")
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    try
        data = PowerModels.parse_file(network_file)

        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_generators"] = length(data["gen"])
        results["details"]["num_branches"] = length(data["branch"])

        # ---- Demonstrate what PowerModels CAN do: multi-period DCOPF ----
        # replicate() creates a multi-network data structure for time-coupled OPF
        T = 12  # 12 hours
        mn_data = PowerModels.replicate(data, T)

        # Apply hourly load profile
        load_profile = [0.80, 0.75, 0.72, 0.70, 0.75, 0.85, 0.95, 1.00, 0.98, 0.95, 0.90, 0.85]

        for t in 1:T
            nw = mn_data["nw"][string(t)]
            for (_, load) in nw["load"]
                load["pd"] *= load_profile[t]
                load["qd"] *= load_profile[t]
            end
        end

        optimizer = JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => false,
        )

        # solve_mn_opf: multi-network (multi-period) OPF -- deterministic, one scenario
        mn_result = PowerModels.solve_mn_opf(mn_data, DCPPowerModel, optimizer)

        mn_term = string(mn_result["termination_status"])
        results["details"]["multiperiod_dcopf_termination"] = mn_term
        results["details"]["multiperiod_dcopf_objective"] = mn_result["objective"]
        results["details"]["multiperiod_works"] = mn_term in ["OPTIMAL", "LOCALLY_SOLVED"]

        # ---- Document WHY stochastic OPF fails the test ----
        results["details"]["has_native_stochastic_opf"] = false
        results["details"]["stochastic_package"] = "StochasticPowerModels.jl (external, NOT installed)"
        results["details"]["multi_network_supports_scenarios"] = false

        results["details"]["assessment"] = Dict(
            "multi_period" =>
                "SUPPORTED via replicate() + solve_mn_opf(). " *
                "Each period is a separate network in the multi-network structure. " *
                "Temporal coupling (ramp rates, storage) possible via solve_mn_opf_strg.",
            "multi_scenario" =>
                "NOT SUPPORTED natively. The multi-network framework " *
                "models periods, not scenarios. There is no scenario-indexing, " *
                "probability weighting, recourse structure, or chance constraints " *
                "in core PowerModels.",
            "stochastic_opf" =>
                "Requires StochasticPowerModels.jl (external package " *
                "from KU Leuven/Electa, 24 GitHub stars). This package uses polynomial " *
                "chaos expansion for stochastic AC-OPF. It is NOT part of the core " *
                "PowerModels.jl package and NOT installed in this evaluation environment.",
            "manual_assembly" =>
                "A user COULD manually assemble a two-stage stochastic " *
                "program using JuMP (scenario-indexed variables, non-anticipativity " *
                "constraints, expected-cost objective). But this uses JuMP, not PowerModels. " *
                "The test protocol says this does not count: 'A tool that only supports " *
                "deterministic solves but can be wrapped in a Monte Carlo loop is tested " *
                "under Extensibility (B-4), not here.'",
        )

        # Show that independent deterministic solves ARE possible (but don't pass)
        results["details"]["independent_solves_possible"] = true
        results["details"]["scenario_count_attempted"] = 0
        results["details"]["prices_extractable_from_deterministic"] = true

        push!(
            results["errors"],
            "PowerModels.jl does NOT natively support scenario-indexed stochastic " *
            "optimization. The multi-network framework supports multi-period " *
            "(temporal) but not multi-scenario. StochasticPowerModels.jl is a " *
            "separate external package. Per test protocol, wrapping deterministic " *
            "solves in a loop does not satisfy the pass condition.",
        )

        # Status remains "fail" -- this is the expected outcome
        results["status"] = "fail"

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        push!(results["errors"], sprint(showerror, e, catch_backtrace()))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end
