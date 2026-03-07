#=
Test B-4: Stochastic Wrapping -- 20 scenarios of 12hr multi-period DCOPF
Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: Tool accepts timeseries inputs programmatically. Scenario loop
    expressible without excessive overhead. Results collectable.
Tool: PowerModels.jl v0.21.5
Solver: HiGHS
=#

using PowerModels, JuMP, HiGHS, JSON
using Random

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

    # Warm-up run
    try
        _data = PowerModels.parse_file(network_file)
        _mn = PowerModels.replicate(_data, 2)
        PowerModels.solve_mn_opf(_mn, DCPPowerModel, HiGHS.Optimizer)
    catch
        ;
    end

    t0 = time()
    try
        data = PowerModels.parse_file(network_file)

        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_branches"] = length(data["branch"])
        results["details"]["num_generators"] = length(data["gen"])

        optimizer = JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => false,
        )

        # ---- Scenario generation ----
        # 20 scenarios with correlated perturbations by resource type.
        # Resource types: thermal (gens 1-8), renewable-like (gens 9-10).
        # Load perturbations correlated across buses within each scenario.
        T = 12  # hours
        N_scenarios = 20
        rng = MersenneTwister(42)

        # Base hourly load profile (fraction of peak)
        base_profile = [0.80, 0.75, 0.72, 0.70, 0.75, 0.85, 0.95, 1.00, 0.98, 0.95, 0.90, 0.85]

        # Generate correlated perturbations by resource type
        # Load perturbation: each scenario has a common load scaling factor + per-bus noise
        # Gen perturbation: thermal gens have small noise, renewable gens have larger noise
        load_ids = collect(keys(data["load"]))
        gen_ids = collect(keys(data["gen"]))

        # Classify generators
        thermal_gens = gen_ids[1:min(8, length(gen_ids))]
        renewable_gens = gen_ids[min(9, length(gen_ids)):end]

        scenarios = []
        for s in 1:N_scenarios
            # Common load scaling factor for this scenario (correlated across buses)
            # Keep perturbations small to avoid infeasibility
            load_common_factor = 1.0 + 0.03 * randn(rng)

            # Per-bus noise (small, uncorrelated)
            bus_noise = Dict(lid => 1.0 + 0.005 * randn(rng) for lid in load_ids)

            # Per-hour load multiplier
            hourly_load = [base_profile[t] * load_common_factor for t in 1:T]

            # Generator availability perturbations
            # Thermal: small variance (high availability)
            thermal_avail = Dict(
                g => max(0.8, min(1.0, 1.0 + 0.03 * randn(rng))) for g in thermal_gens
            )
            # Renewable: moderate variance (weather-dependent) but floor at 0.6
            renewable_avail = Dict(
                g => max(0.6, min(1.0, 0.9 + 0.08 * randn(rng))) for g in renewable_gens
            )

            push!(
                scenarios,
                Dict(
                    "load_common_factor" => load_common_factor,
                    "bus_noise" => bus_noise,
                    "hourly_load" => hourly_load,
                    "thermal_avail" => thermal_avail,
                    "renewable_avail" => renewable_avail,
                ),
            )
        end

        results["details"]["num_scenarios"] = N_scenarios
        results["details"]["num_periods"] = T
        results["details"]["scenario_generation_method"] = "Correlated perturbations by resource type"

        # ---- Solve each scenario ----
        scenario_results = Dict{Int,Dict}()
        solve_times = Float64[]
        all_objectives = Float64[]

        for s in 1:N_scenarios
            sc = scenarios[s]

            # Create multi-network from fresh data copy
            sc_data = deepcopy(data)

            # Apply generator availability perturbations to pmax
            for (g, avail) in sc["thermal_avail"]
                sc_data["gen"][g]["pmax"] *= avail
            end
            for (g, avail) in sc["renewable_avail"]
                sc_data["gen"][g]["pmax"] *= avail
            end

            # Create 12-period multi-network
            mn_data = PowerModels.replicate(sc_data, T)

            # Apply hourly load profiles with scenario-specific perturbations
            for t in 1:T
                nw = mn_data["nw"][string(t)]
                for (lid, load) in nw["load"]
                    load["pd"] *= sc["hourly_load"][t] * get(sc["bus_noise"], lid, 1.0)
                    load["qd"] *= sc["hourly_load"][t] * get(sc["bus_noise"], lid, 1.0)
                end
            end

            # Solve multi-period DCOPF for this scenario
            t_solve = time()
            mn_result = PowerModels.solve_mn_opf(mn_data, DCPPowerModel, optimizer)
            dt_solve = time() - t_solve
            push!(solve_times, dt_solve)

            term = string(mn_result["termination_status"])

            if term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"]
                push!(all_objectives, mn_result["objective"])

                # Collect dispatch and prices for this scenario
                sc_dispatch = Dict{String,Dict{String,Float64}}()
                for t in 1:T
                    nw_sol = mn_result["solution"]["nw"][string(t)]
                    period_dispatch = Dict{String,Float64}()
                    for (gid, gen) in nw_sol["gen"]
                        period_dispatch[gid] = gen["pg"]
                    end
                    sc_dispatch[string(t)] = period_dispatch
                end

                scenario_results[s] = Dict(
                    "termination" => term,
                    "objective" => mn_result["objective"],
                    "solve_time" => dt_solve,
                    "dispatch_period_1" => sc_dispatch["1"],
                    "dispatch_period_12" => sc_dispatch[string(T)],
                )
            else
                scenario_results[s] = Dict(
                    "termination" => term, "objective" => nothing, "solve_time" => dt_solve
                )
            end
        end

        # ---- Collect aggregate results ----
        n_optimal = count(
            s -> scenario_results[s]["termination"] in ["OPTIMAL", "LOCALLY_SOLVED"], 1:N_scenarios
        )

        results["details"]["scenarios_optimal"] = n_optimal
        results["details"]["scenarios_failed"] = N_scenarios - n_optimal
        results["details"]["total_solve_time"] = sum(solve_times)
        results["details"]["mean_solve_time"] = sum(solve_times) / N_scenarios
        results["details"]["min_solve_time"] = minimum(solve_times)
        results["details"]["max_solve_time"] = maximum(solve_times)

        if !isempty(all_objectives)
            results["details"]["mean_objective"] = sum(all_objectives) / length(all_objectives)
            results["details"]["min_objective"] = minimum(all_objectives)
            results["details"]["max_objective"] = maximum(all_objectives)
            results["details"]["objective_range"] =
                maximum(all_objectives) - minimum(all_objectives)
        end

        # Sample scenario details
        results["details"]["scenario_1"] = scenario_results[1]
        results["details"]["scenario_20"] = scenario_results[N_scenarios]

        # API assessment
        results["details"]["accepts_timeseries_programmatically"] = true
        results["details"]["scenario_loop_method"] = "deepcopy(data) + replicate() + modify loads/gens + solve_mn_opf()"
        results["details"]["per_scenario_overhead"] = "deepcopy + replicate (data dict operations, no file I/O)"
        results["details"]["results_collectable"] = true
        results["details"]["results_format"] = "nested Dict from solve_mn_opf result"

        # Pass condition check
        if n_optimal >= 18  # at least 90% of scenarios should solve
            results["status"] = "pass"
        else
            push!(results["errors"], "Only $n_optimal of $N_scenarios scenarios solved optimally")
        end

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
