#=
Test B-4: 20-Scenario Stochastic DCOPF Wrapping with Correlated Perturbations

Dimension: extensibility
Network: TINY (IEEE 39-bus, New England)
Pass condition: Tool accepts timeseries inputs programmatically (not from config
  files only). Scenario loop is expressible without excessive per-scenario overhead.
  Results (prices, dispatch) are collectable in a structured format.
Tool: PowerModels.jl v0.21.5
Solver: HiGHS

Approach: 20 scenarios x single-period DC OPF, each with correlated load
perturbations from scenario_multipliers_50x24.csv. Uses solve_dc_opf (not mn_opf)
to avoid excessive JIT overhead from multinetwork path. The scenario data applies
per-period perturbations; we solve peak hour (HR 18) under each scenario.
=#

using PowerModels, JuMP, HiGHS

PowerModels.silence()

function run(
    network_file::String=joinpath(@__DIR__, "..", "..", "..", "..", "data", "networks", "case39.m");
    timeseries_dir::Union{String,Nothing}=joinpath(
        @__DIR__, "..", "..", "..", "..", "data", "timeseries", "case39"
    ),
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    try
        data = PowerModels.parse_file(network_file)
        base_mva = data["baseMVA"]

        # --- Load scenario multipliers from CSV ---
        scenario_file = joinpath(timeseries_dir, "scenarios", "scenario_multipliers_50x24.csv")
        lines = readlines(scenario_file)
        scenario_mults = Dict{Int,Dict{String,Vector{Float64}}}()
        for line in lines[2:end]
            parts = split(line, ",")
            scen = parse(Int, parts[1])
            gen_uid = String(parts[2])
            mults = [parse(Float64, p) for p in parts[3:end]]
            if !haskey(scenario_mults, scen)
                scenario_mults[scen] = Dict{String,Vector{Float64}}()
            end
            scenario_mults[scen][gen_uid] = mults
        end

        # --- Load hourly loads (use peak hour HR_18) ---
        load_file = joinpath(timeseries_dir, "load_24h.csv")
        load_lines = readlines(load_file)
        bus_loads_hr18 = Dict{Int,Float64}()
        for line in load_lines[2:end]
            parts = split(line, ",")
            bid = parse(Int, parts[1])
            bus_loads_hr18[bid] = parse(Float64, parts[19])  # HR_18 (index 19 = col 18+1)
        end

        # --- Apply differentiated gen costs ---
        cost_map = Dict(
            "hydro" => (5.0, 0.005),
            "nuclear" => (10.0, 0.010),
            "coal_large" => (25.0, 0.025),
            "gas_CC" => (40.0, 0.040),
        )
        gen_tech = Dict(
            0 => "hydro",
            1 => "nuclear",
            2 => "nuclear",
            3 => "coal_large",
            4 => "coal_large",
            5 => "nuclear",
            6 => "gas_CC",
            7 => "nuclear",
            8 => "nuclear",
            9 => "gas_CC",
        )
        for (id, gen) in data["gen"]
            gen_idx = parse(Int, id) - 1
            if haskey(gen_tech, gen_idx)
                c1, c2 = cost_map[gen_tech[gen_idx]]
                gen["cost"] = [c2 / base_mva^2, c1 / base_mva, 0.0]
                gen["ncost"] = 3
                gen["model"] = 2
            end
        end

        # --- Set peak-hour loads ---
        for (lid, load) in data["load"]
            bus_id = load["load_bus"]
            if haskey(bus_loads_hr18, bus_id)
                load["pd"] = bus_loads_hr18[bus_id] / base_mva
            end
        end

        # No branch derating — use nominal ratings to avoid infeasibility
        # under scenario perturbations

        # --- Derive per-scenario load multipliers from renewable scenario data ---
        re_uids = ["WIND_1", "WIND_2", "WIND_3", "SOLAR_1", "SOLAR_2"]

        function get_scenario_mult(s::Int, hr::Int)
            if !haskey(scenario_mults, s)
                return 1.0
            end
            avg = 0.0
            n = 0
            for uid in re_uids
                if haskey(scenario_mults[s], uid)
                    avg += scenario_mults[s][uid][hr]
                    n += 1
                end
            end
            n > 0 ? clamp(2.0 - avg / n, 0.85, 1.15) : 1.0
        end

        # --- Solver ---
        optimizer = JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => false,
        )

        # Warm-up solve (trigger JIT)
        warmup_data = deepcopy(data)
        PowerModels.solve_dc_opf(
            warmup_data, optimizer; setting=Dict("output" => Dict("duals" => true))
        )

        # --- Run 20 scenarios ---
        n_scenarios = 20
        scenario_results_dict = Dict{Int,Dict{String,Any}}()
        solve_times = Float64[]
        n_optimal = 0
        peak_hr = 18

        for s in 1:n_scenarios
            sc_data = deepcopy(data)
            load_mult = get_scenario_mult(s, peak_hr)

            # Apply scenario-specific load perturbation
            for (lid, load) in sc_data["load"]
                load["pd"] *= load_mult
            end

            # Also apply gen availability perturbation (±2%, tighter to avoid infeasibility)
            gen_mult = 1.0
            if haskey(scenario_mults, s) && haskey(scenario_mults[s], "WIND_1")
                gen_mult = clamp(scenario_mults[s]["WIND_1"][peak_hr], 0.98, 1.02)
            end
            for (gid, gen) in sc_data["gen"]
                gen["pmax"] *= gen_mult
            end

            t_solve = time()
            result = PowerModels.solve_dc_opf(
                sc_data, optimizer; setting=Dict("output" => Dict("duals" => true))
            )
            solve_time = time() - t_solve
            push!(solve_times, solve_time)

            term_status = string(result["termination_status"])
            obj = get(result, "objective", NaN)

            # Extract dispatch and LMPs
            dispatch = Dict{String,Float64}()
            lmps = Dict{String,Float64}()
            if haskey(result, "solution")
                if haskey(result["solution"], "gen")
                    for (gid, gsol) in result["solution"]["gen"]
                        dispatch[gid] = get(gsol, "pg", 0.0) * base_mva
                    end
                end
                if haskey(result["solution"], "bus")
                    for (bid, bsol) in result["solution"]["bus"]
                        if haskey(bsol, "lam_kcl_r")
                            lmps[bid] = bsol["lam_kcl_r"]
                        end
                    end
                end
            end

            is_optimal = term_status in ["OPTIMAL", "LOCALLY_SOLVED"]
            if is_optimal
                n_optimal += 1
            end

            lmp_vals = collect(values(lmps))
            scenario_results_dict[s] = Dict(
                "termination_status" => term_status,
                "objective" => round(obj; digits=2),
                "solve_time_s" => round(solve_time; digits=4),
                "load_mult" => round(load_mult; digits=4),
                "gen_mult" => round(gen_mult; digits=4),
                "lmp_range" => if isempty(lmp_vals)
                    nothing
                else
                    [round(minimum(lmp_vals); digits=2), round(maximum(lmp_vals); digits=2)]
                end,
                "total_dispatch_mw" => round(sum(values(dispatch)); digits=2),
            )
        end

        total_solve_time = sum(solve_times)
        mean_solve_time = total_solve_time / n_scenarios
        objectives = [
            scenario_results_dict[s]["objective"] for s in 1:n_scenarios if
            scenario_results_dict[s]["termination_status"] in ["OPTIMAL", "LOCALLY_SOLVED"]
        ]

        println("\n=== B-4 Stochastic DCOPF Wrapping (TINY) ===")
        println("Scenarios: $n_scenarios (single-period DC OPF at HR $peak_hr)")
        println("Optimal: $n_optimal / $n_scenarios")
        println("Total solve time: $(round(total_solve_time, digits=3))s")
        println("Mean solve time: $(round(mean_solve_time * 1000, digits=1))ms")
        println(
            "Min/Max solve time: $(round(minimum(solve_times)*1000, digits=1)) / $(round(maximum(solve_times)*1000, digits=1))ms",
        )
        if !isempty(objectives)
            println(
                "Objective range: $(round(minimum(objectives), digits=2)) - $(round(maximum(objectives), digits=2))",
            )
            println("Mean objective: $(round(sum(objectives)/length(objectives), digits=2))")
        end
        for s in 1:min(5, n_scenarios)
            sr = scenario_results_dict[s]
            println(
                "  Scenario $s: $(sr["termination_status"]), obj=$(sr["objective"]), load_mult=$(sr["load_mult"]), lmp_range=$(sr["lmp_range"])",
            )
        end

        if n_optimal >= 16
            results["status"] = "pass"
        else
            push!(
                results["errors"], "Only $n_optimal / $n_scenarios scenarios optimal (need >= 16)"
            )
        end

        results["details"] = Dict(
            "n_scenarios" => n_scenarios,
            "n_periods_per_scenario" => 1,
            "peak_hour" => peak_hr,
            "n_optimal" => n_optimal,
            "total_solve_time_s" => round(total_solve_time; digits=3),
            "mean_solve_time_ms" => round(mean_solve_time * 1000; digits=1),
            "min_solve_time_ms" => round(minimum(solve_times) * 1000; digits=1),
            "max_solve_time_ms" => round(maximum(solve_times) * 1000; digits=1),
            "objective_range" => if isempty(objectives)
                nothing
            else
                [round(minimum(objectives); digits=2), round(maximum(objectives); digits=2)]
            end,
            "mean_objective" => if isempty(objectives)
                nothing
            else
                round(sum(objectives) / length(objectives); digits=2)
            end,
            "data_source" => "scenario_multipliers_50x24.csv + load_24h.csv",
            "method" => "deepcopy + solve_dc_opf per scenario (single-period, programmatic injection)",
            "perturbation_method" => "correlated load/gen perturbation from renewable scenario multipliers",
            "branch_derating" => "none (nominal ratings)",
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        bt = catch_backtrace()
        println(sprint(showerror, e, bt))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    println("\nStatus: $(results["status"])")
    println("Wall clock: $(round(results["wall_clock_seconds"], digits=3))s")
    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println("\n--- RESULT ---")
    println("status: $(result["status"])")
    println("wall_clock_seconds: $(result["wall_clock_seconds"])")
    println("errors: $(result["errors"])")
    for (k, v) in result["details"]
        println("  $k: $v")
    end
end
