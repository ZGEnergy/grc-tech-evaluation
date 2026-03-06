
#= Test C-6: 50-scenario stochastic DCPF at SMALL (2000 buses) =#

using PowerModels, JuMP, HiGHS, JSON, Random
PowerModels.silence()

function preprocess_data!(data)
    for (i, gen) in data["gen"]
        if !haskey(gen, "cost") || isempty(get(gen, "cost", []))
            gen["model"] = 2
            gen["ncost"] = 2
            gen["cost"] = [20.0, 0.0]
        end
    end
    for (i, br) in data["branch"]
        if get(br, "rate_a", 0.0) == 0.0
            br["rate_a"] = 9999.0
        end
    end
end

function run(network_file::String="/workspace/data/networks/case_ACTIVSg2000.m")
    results = Dict{String,Any}(
        "test_id" => "C-6",
        "test_name" => "stochastic_dcpf_scale",
        "network" => "SMALL",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        data = PowerModels.parse_file(network_file)
        preprocess_data!(data)

        nbus = length(data["bus"])
        nbranch = length(data["branch"])
        ngen = length(data["gen"])
        results["details"]["num_buses"] = nbus
        results["details"]["num_branches"] = nbranch
        results["details"]["num_generators"] = ngen

        n_scenarios = 50
        n_hours = 24

        # Create multi-period network
        mn_data = PowerModels.replicate(data, n_hours)

        base_loads = Dict{String,Float64}()
        for (i, load) in data["load"]
            base_loads[i] = load["pd"]
        end
        n_loads = length(base_loads)

        Random.seed!(42)
        common_factor_weight = 0.6

        scenario_costs = Float64[]
        scenario_solve_times = Float64[]

        GC.gc()
        mem_before = Base.gc_live_bytes() / 1024^2

        for s in 1:n_scenarios
            sc_data = deepcopy(mn_data)
            common_factors = randn(n_hours) * 0.1

            for t in 1:n_hours
                nw = sc_data["nw"]["$t"]
                idio_noise = randn(n_loads) * 0.05
                for (j, (load_id, base_pd)) in enumerate(base_loads)
                    perturbation =
                        common_factor_weight * common_factors[t] +
                        (1 - common_factor_weight) * idio_noise[j]
                    nw["load"][load_id]["pd"] = base_pd * (1.0 + perturbation)
                end
            end

            st = time()
            result = PowerModels.solve_mn_opf(sc_data, DCPPowerModel, HiGHS.Optimizer)
            solve_t = time() - st
            push!(scenario_solve_times, solve_t)

            if result["termination_status"] == OPTIMAL ||
                result["termination_status"] == LOCALLY_SOLVED
                push!(scenario_costs, result["objective"])
            else
                push!(scenario_costs, NaN)
            end

            # Progress reporting
            if s % 10 == 0
                println(
                    "Scenario $s/$(n_scenarios) done ($(round(time() - t0; digits=1))s elapsed)"
                )
            end
        end

        GC.gc()
        mem_after = Base.gc_live_bytes() / 1024^2

        valid_costs = filter(!isnan, scenario_costs)

        results["details"]["n_scenarios"] = n_scenarios
        results["details"]["n_hours"] = n_hours
        results["details"]["n_loads_perturbed"] = n_loads
        results["details"]["scenarios_solved"] = length(valid_costs)
        results["details"]["scenarios_failed"] = n_scenarios - length(valid_costs)
        results["details"]["mean_cost"] =
            isempty(valid_costs) ? NaN : round(sum(valid_costs) / length(valid_costs); digits=2)
        results["details"]["std_cost"] = if isempty(valid_costs)
            NaN
        else
            round(
                sqrt(
                    sum((c - sum(valid_costs) / length(valid_costs))^2 for c in valid_costs) /
                    length(valid_costs),
                );
                digits=2,
            )
        end
        results["details"]["min_cost"] =
            isempty(valid_costs) ? NaN : round(minimum(valid_costs); digits=2)
        results["details"]["max_cost"] =
            isempty(valid_costs) ? NaN : round(maximum(valid_costs); digits=2)
        results["details"]["total_solve_time_seconds"] = round(sum(scenario_solve_times); digits=2)
        results["details"]["per_scenario_average_seconds"] = round(
            sum(scenario_solve_times) / length(scenario_solve_times); digits=4
        )
        results["details"]["peak_memory_mb"] = round(mem_after - mem_before; digits=2)
        results["details"]["approach"] = "replicate() for multi-period + deepcopy + modify loads per scenario + solve_mn_opf with HiGHS"

        if length(valid_costs) == n_scenarios
            results["status"] = "pass"
        elseif length(valid_costs) > 0
            results["status"] = "qualified_pass"
            push!(
                results["errors"], "$(n_scenarios - length(valid_costs)) scenarios failed to solve"
            )
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
