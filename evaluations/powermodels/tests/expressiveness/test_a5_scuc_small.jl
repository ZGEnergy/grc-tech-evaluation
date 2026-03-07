#=
Test A-5: 24-hour SCUC (Unit Commitment) as MILP on SMALL (ACTIVSg 2000-bus)
Dimension: expressiveness
Network: SMALL (ACTIVSg 2000-bus, 544 generators, 3206 branches)
Pass condition: Solves to feasibility (MIP gap <= 10%). Commitment schedule extractable
               as time-indexed binary matrix.
Tool: PowerModels.jl v0.21.5
Solver: HiGHS

NOTE: Same approach as TINY but with relaxed MIP gap (10%) and 300s timeout.
The 2000-bus network has 544 generators which creates a very large MILP.
=#

using PowerModels, JuMP, HiGHS, JSON

function run(network_file::String)
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
        results["details"]["num_periods"] = 24
        results["details"]["built_in_scuc"] = false
        results["details"]["approach"] = "User-assembled MILP via JuMP; PowerModels used only for data parsing"

        # Vary load across 24 hours (typical daily profile)
        load_profile = [
            0.65,
            0.60,
            0.58,
            0.56,
            0.56,
            0.60,
            0.70,
            0.80,
            0.90,
            0.95,
            1.00,
            1.00,
            0.98,
            0.96,
            0.95,
            0.93,
            0.95,
            1.00,
            0.98,
            0.96,
            0.90,
            0.85,
            0.78,
            0.70,
        ]

        T = 1:24
        gen_ids = sort(parse.(Int, collect(keys(data["gen"]))))
        bus_ids = sort(parse.(Int, collect(keys(data["bus"]))))
        branch_ids = sort(parse.(Int, collect(keys(data["branch"]))))

        # Find reference bus
        ref_bus = nothing
        for (id, bus) in data["bus"]
            if bus["bus_type"] == 3
                ref_bus = parse(Int, id)
                break
            end
        end

        # Extract generator parameters
        gen_bus = Dict(g => data["gen"][string(g)]["gen_bus"] for g in gen_ids)
        pmin = Dict(g => data["gen"][string(g)]["pmin"] for g in gen_ids)
        pmax = Dict(g => data["gen"][string(g)]["pmax"] for g in gen_ids)

        # Linearize costs - handle empty cost arrays
        marginal_cost = Dict{Int,Float64}()
        for g in gen_ids
            gd = data["gen"][string(g)]
            if gd["model"] == 2 && !isempty(gd["cost"]) && gd["ncost"] >= 2
                marginal_cost[g] = gd["cost"][end - 1]  # linear term
            elseif gd["model"] == 2 && !isempty(gd["cost"]) && gd["ncost"] == 1
                marginal_cost[g] = 0.0
            else
                marginal_cost[g] = 0.0  # free generation for empty/missing costs
            end
        end

        # Compute base load at each bus
        base_bus_load = Dict(b => 0.0 for b in bus_ids)
        for (_, load) in data["load"]
            bid = load["load_bus"]
            base_bus_load[bid] += load["pd"]
        end

        println(
            "Building SCUC model: $(length(gen_ids)) generators, $(length(bus_ids)) buses, $(length(branch_ids)) branches, 24 periods",
        )
        println("Estimated binary variables: $(length(gen_ids) * 24 * 3) (u, v_start, v_shut)")

        model = Model(
            optimizer_with_attributes(
                HiGHS.Optimizer,
                "time_limit" => 300.0,
                "mip_rel_gap" => 0.10,
                "presolve" => "on",
                "threads" => 1,
                "output_flag" => true,
            ),
        )

        # Decision variables
        @variable(model, pg[g in gen_ids, t in T] >= 0)
        @variable(model, u[g in gen_ids, t in T], Bin)
        @variable(model, v_start[g in gen_ids, t in T], Bin)
        @variable(model, v_shut[g in gen_ids, t in T], Bin)
        @variable(model, theta[b in bus_ids, t in T])

        # Fix reference bus angle
        for t in T
            fix(theta[ref_bus, t], 0.0; force=true)
        end

        # Generation limits linked to commitment
        for g in gen_ids, t in T
            @constraint(model, pg[g, t] <= pmax[g] * u[g, t])
            @constraint(model, pg[g, t] >= pmin[g] * u[g, t])
        end

        # Power balance at each bus (DC power flow)
        for t in T
            for b in bus_ids
                gen_at_bus = [g for g in gen_ids if gen_bus[g] == b]
                load_t = base_bus_load[b] * load_profile[t]

                flow_out = AffExpr(0.0)
                for br_id in branch_ids
                    br = data["branch"][string(br_id)]
                    if br["br_status"] == 0
                        continue
                    end
                    f = br["f_bus"]
                    t_bus = br["t_bus"]
                    x = br["br_x"]
                    if abs(x) < 1e-10
                        continue
                    end
                    susceptance = 1.0 / x

                    if f == b
                        add_to_expression!(flow_out, susceptance, theta[f, t])
                        add_to_expression!(flow_out, -susceptance, theta[t_bus, t])
                    elseif t_bus == b
                        add_to_expression!(flow_out, -susceptance, theta[f, t])
                        add_to_expression!(flow_out, susceptance, theta[t_bus, t])
                    end
                end

                @constraint(model, sum(pg[g, t] for g in gen_at_bus; init=0.0) - load_t == flow_out)
            end
        end

        # Branch flow limits
        for br_id in branch_ids, t in T
            br = data["branch"][string(br_id)]
            if br["br_status"] == 0
                continue
            end
            rate = br["rate_a"]
            if rate > 0 && rate < 1e10
                f = br["f_bus"]
                t_bus = br["t_bus"]
                x = br["br_x"]
                if abs(x) < 1e-10
                    continue
                end
                susceptance = 1.0 / x
                @constraint(model, susceptance * (theta[f, t] - theta[t_bus, t]) <= rate)
                @constraint(model, susceptance * (theta[f, t] - theta[t_bus, t]) >= -rate)
            end
        end

        # Startup/shutdown variable linking
        for g in gen_ids, t in T
            if t > 1
                @constraint(model, v_start[g, t] >= u[g, t] - u[g, t - 1])
                @constraint(model, v_shut[g, t] >= u[g, t - 1] - u[g, t])
                @constraint(model, v_start[g, t] + v_shut[g, t] <= 1)
            else
                @constraint(model, v_start[g, t] >= u[g, t] - 1)
                @constraint(model, v_shut[g, t] >= 1 - u[g, t])
            end
        end

        # Minimum up-time (3 hours)
        min_up = 3
        for g in gen_ids, t in T
            if t >= min_up
                @constraint(model, sum(v_start[g, tau] for tau in (t - min_up + 1):t) <= u[g, t])
            end
        end

        # Minimum down-time (2 hours)
        min_down = 2
        for g in gen_ids, t in T
            if t >= min_down
                @constraint(
                    model, sum(v_shut[g, tau] for tau in (t - min_down + 1):t) <= 1 - u[g, t]
                )
            end
        end

        # Ramp rate constraints (50% of Pmax per hour)
        for g in gen_ids, t in T
            ramp_limit = 0.5 * pmax[g]
            if t > 1
                @constraint(model, pg[g, t] - pg[g, t - 1] <= ramp_limit)
                @constraint(model, pg[g, t - 1] - pg[g, t] <= ramp_limit)
            end
        end

        # Reserve requirement (10% of total load per period)
        for t in T
            total_load = sum(base_bus_load[b] * load_profile[t] for b in bus_ids)
            @constraint(model, sum(pmax[g] * u[g, t] for g in gen_ids) >= total_load * 1.10)
        end

        # Objective: minimize linearized generation cost + startup costs
        startup_cost = Dict(g => 0.1 * pmax[g] * abs(marginal_cost[g]) for g in gen_ids)

        @objective(
            model,
            Min,
            sum(marginal_cost[g] * pg[g, t] for g in gen_ids, t in T) +
                sum(startup_cost[g] * v_start[g, t] for g in gen_ids, t in T)
        )

        println("Model built. Solving...")
        optimize!(model)

        term_status = string(termination_status(model))
        results["details"]["termination_status"] = term_status
        results["details"]["solve_time"] = solve_time(model)

        if term_status in ("OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED", "TIME_LIMIT")
            # Check if we have a feasible solution (TIME_LIMIT may or may not)
            if has_values(model)
                results["details"]["objective"] = objective_value(model)

                try
                    results["details"]["mip_gap"] = relative_gap(model)
                catch
                    results["details"]["mip_gap"] = "not available"
                end

                # Commitment schedule summary (too large to dump full matrix)
                committed_per_period = [sum(round(Int, value(u[g, t])) for g in gen_ids) for t in T]
                results["details"]["committed_units_per_period"] = committed_per_period
                results["details"]["min_committed"] = minimum(committed_per_period)
                results["details"]["max_committed"] = maximum(committed_per_period)

                # Total startups
                results["details"]["total_startups"] = sum(
                    round(Int, value(v_start[g, t])) for g in gen_ids, t in T
                )

                # Sample dispatch (first 5 generators)
                dispatch_sample = Dict{String,Vector{Float64}}()
                for g in gen_ids[1:min(5, length(gen_ids))]
                    dispatch_sample[string(g)] = [round(value(pg[g, t]); digits=2) for t in T]
                end
                results["details"]["dispatch_schedule_sample"] = dispatch_sample

                # Check MIP gap against 10% threshold
                gap = results["details"]["mip_gap"]
                if isa(gap, Number) && gap <= 0.10
                    results["status"] = "pass"
                elseif term_status == "OPTIMAL"
                    results["status"] = "pass"
                else
                    push!(results["errors"], "MIP gap $gap exceeds 10% threshold")
                end

                push!(
                    results["workarounds"],
                    "PowerModels has NO built-in SCUC. Entire formulation user-assembled: " *
                    "PowerModels used only for MATPOWER parsing. " *
                    "All UC constraints built manually in JuMP. " *
                    "Generator costs linearized because HiGHS cannot solve MIQP.",
                )
            else
                push!(results["errors"], "Solver hit time limit with no feasible solution found")
            end
        else
            push!(results["errors"], "SCUC did not solve: $term_status")
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
    nf = get(
        ARGS,
        1,
        joinpath(@__DIR__, "..", "..", "..", "..", "data", "networks", "case_ACTIVSg2000.m"),
    )
    result = run(nf)
    println(JSON.json(result, 2))
end
