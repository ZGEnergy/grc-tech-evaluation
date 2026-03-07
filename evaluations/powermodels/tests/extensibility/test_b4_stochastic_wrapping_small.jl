#=
Test B-4: Stochastic Wrapping -- 20 scenarios of 12hr multi-period DCOPF
Dimension: extensibility
Network: SMALL (ACTIVSg 2000-bus)
Pass condition: Tool accepts timeseries inputs programmatically. Scenario loop
    expressible without excessive overhead. Results collectable.
Tool: PowerModels.jl v0.21.5
Solver: HiGHS
=#

using PowerModels, JuMP, HiGHS, JSON
using Random

function run(
    network_file::String=joinpath(
        @__DIR__, "..", "..", "..", "..", "data", "networks", "case_ACTIVSg2000.m"
    ),
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

        # Fix generators with empty cost arrays
        for (id, gen) in data["gen"]
            if gen["model"] == 2 && (gen["ncost"] == 0 || isempty(gen["cost"]))
                gen["cost"] = [0.0, 0.0, 0.0]
                gen["ncost"] = 3
            end
        end

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
        T = 12  # hours
        N_scenarios = 20
        rng = MersenneTwister(42)

        # Base hourly load profile (fraction of peak)
        base_profile = [0.80, 0.75, 0.72, 0.70, 0.75, 0.85, 0.95, 1.00, 0.98, 0.95, 0.90, 0.85]

        load_ids = collect(keys(data["load"]))
        gen_ids = sort(parse.(Int, collect(keys(data["gen"]))))

        # Classify generators: first 80% thermal, last 20% renewable-like
        n_thermal = Int(floor(0.8 * length(gen_ids)))
        thermal_gens = [string(g) for g in gen_ids[1:n_thermal]]
        renewable_gens = [string(g) for g in gen_ids[(n_thermal + 1):end]]

        scenarios = []
        for s in 1:N_scenarios
            load_common_factor = 1.0 + 0.03 * randn(rng)
            bus_noise = Dict(lid => 1.0 + 0.005 * randn(rng) for lid in load_ids)
            hourly_load = [base_profile[t] * load_common_factor for t in 1:T]

            thermal_avail = Dict(
                g => max(0.8, min(1.0, 1.0 + 0.03 * randn(rng))) for g in thermal_gens
            )
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

        # ---- Warm-up solve ----
        try
            _d = deepcopy(data)
            _mn = PowerModels.replicate(_d, 2)
            PowerModels.solve_mn_opf(_mn, DCPPowerModel, optimizer)
        catch
            ;
        end

        # ---- Solve each scenario ----
        scenario_results = Dict{Int,Dict}()
        solve_times = Float64[]
        all_objectives = Float64[]

        t_loop = time()
        for s in 1:N_scenarios
            sc = scenarios[s]

            sc_data = deepcopy(data)

            for (g, avail) in sc["thermal_avail"]
                sc_data["gen"][g]["pmax"] *= avail
            end
            for (g, avail) in sc["renewable_avail"]
                sc_data["gen"][g]["pmax"] *= avail
            end

            mn_data = PowerModels.replicate(sc_data, T)

            for t in 1:T
                nw = mn_data["nw"][string(t)]
                for (lid, load) in nw["load"]
                    load["pd"] *= sc["hourly_load"][t] * get(sc["bus_noise"], lid, 1.0)
                    load["qd"] *= sc["hourly_load"][t] * get(sc["bus_noise"], lid, 1.0)
                end
            end

            t_solve = time()
            mn_result = PowerModels.solve_mn_opf(mn_data, DCPPowerModel, optimizer)
            dt_solve = time() - t_solve
            push!(solve_times, dt_solve)

            term = string(mn_result["termination_status"])

            if term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"]
                push!(all_objectives, mn_result["objective"])
                scenario_results[s] = Dict(
                    "termination" => term,
                    "objective" => mn_result["objective"],
                    "solve_time" => dt_solve,
                )
            else
                scenario_results[s] = Dict(
                    "termination" => term, "objective" => nothing, "solve_time" => dt_solve
                )
            end

            println("Scenario $s: $term ($(round(dt_solve, digits=2))s)")
        end
        loop_time = time() - t_loop

        # ---- Collect aggregate results ----
        n_optimal = count(
            s -> scenario_results[s]["termination"] in ["OPTIMAL", "LOCALLY_SOLVED"], 1:N_scenarios
        )

        results["details"]["scenarios_optimal"] = n_optimal
        results["details"]["scenarios_failed"] = N_scenarios - n_optimal
        results["details"]["total_solve_time"] = round(sum(solve_times); digits=2)
        results["details"]["loop_wall_clock"] = round(loop_time; digits=2)
        results["details"]["mean_solve_time"] = round(sum(solve_times) / N_scenarios; digits=2)
        results["details"]["min_solve_time"] = round(minimum(solve_times); digits=2)
        results["details"]["max_solve_time"] = round(maximum(solve_times); digits=2)

        if !isempty(all_objectives)
            results["details"]["mean_objective"] = round(
                sum(all_objectives) / length(all_objectives); digits=2
            )
            results["details"]["min_objective"] = round(minimum(all_objectives); digits=2)
            results["details"]["max_objective"] = round(maximum(all_objectives); digits=2)
            results["details"]["objective_range"] = round(
                maximum(all_objectives) - minimum(all_objectives); digits=2
            )
        end

        results["details"]["scenario_1"] = scenario_results[1]
        results["details"]["scenario_20"] = scenario_results[N_scenarios]

        results["details"]["accepts_timeseries_programmatically"] = true
        results["details"]["scenario_loop_method"] = "deepcopy(data) + replicate() + modify loads/gens + solve_mn_opf()"
        results["details"]["per_scenario_overhead"] = "deepcopy + replicate (data dict operations, no file I/O)"
        results["details"]["results_collectable"] = true

        if n_optimal >= 16  # at least 80% should solve for SMALL (more likely to have infeasible)
            results["status"] = "pass"
        else
            push!(results["errors"], "Only $n_optimal of $N_scenarios scenarios solved optimally")
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        push!(results["errors"], sprint(showerror, e, catch_backtrace()))
    finally
        results["wall_clock_seconds"] = round(time() - t0; digits=2)
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end
