#=
Test A-6: SCED (Security-Constrained Economic Dispatch) on TINY (IEEE 39-bus)
Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Solves. Dispatch extractable. UC and ED cleanly separable.
               Ramp rate constraints demonstrably enforced.
Tool: PowerModels.jl v0.21.5
Solver: HiGHS

NOTE: PowerModels.jl does NOT have built-in SCED. Like A-5, the entire
formulation is user-assembled via JuMP. The commitment schedule from A-5
is fixed (binary variables become parameters), and dispatch is solved as LP.
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
        # Parse network using PowerModels
        data = PowerModels.parse_file(network_file)

        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_generators"] = length(data["gen"])
        results["details"]["num_branches"] = length(data["branch"])
        results["details"]["num_periods"] = 24
        results["details"]["built_in_sced"] = false
        results["details"]["approach"] =
            "User-assembled LP via JuMP; commitment schedule " *
            "fixed from A-5 output. PowerModels used only for data parsing. " *
            "Ramp rate constraints explicitly enforced in ED stage."

        # ---- Step 1: Generate commitment schedule (reproducing A-5 logic) ----
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

        # Linearize costs
        marginal_cost = Dict{Int,Float64}()
        for g in gen_ids
            gd = data["gen"][string(g)]
            if gd["model"] == 2
                if gd["ncost"] >= 2
                    marginal_cost[g] = gd["cost"][end - 1]
                else
                    marginal_cost[g] = 0.0
                end
            else
                marginal_cost[g] = 20.0
            end
        end

        # Compute base load at each bus
        base_bus_load = Dict(b => 0.0 for b in bus_ids)
        for (_, load) in data["load"]
            bid = load["load_bus"]
            base_bus_load[bid] += load["pd"]
        end

        # ---- Step 2: Run UC (MILP) to get commitment schedule ----
        uc_model = Model(
            optimizer_with_attributes(
                HiGHS.Optimizer,
                "time_limit" => 300.0,
                "mip_rel_gap" => 0.01,
                "presolve" => "on",
                "threads" => 1,
                "output_flag" => false,
            ),
        )

        @variable(uc_model, pg_uc[g in gen_ids, t in T] >= 0)
        @variable(uc_model, u[g in gen_ids, t in T], Bin)
        @variable(uc_model, v_start[g in gen_ids, t in T], Bin)
        @variable(uc_model, v_shut[g in gen_ids, t in T], Bin)
        @variable(uc_model, theta_uc[b in bus_ids, t in T])

        for t in T
            fix(theta_uc[ref_bus, t], 0.0; force=true)
        end

        for g in gen_ids, t in T
            @constraint(uc_model, pg_uc[g, t] <= pmax[g] * u[g, t])
            @constraint(uc_model, pg_uc[g, t] >= pmin[g] * u[g, t])
        end

        for t in T, b in bus_ids
            gen_at_bus = [g for g in gen_ids if gen_bus[g] == b]
            load_t = base_bus_load[b] * load_profile[t]
            flow_out = AffExpr(0.0)
            for br_id in branch_ids
                br = data["branch"][string(br_id)]
                f = br["f_bus"]
                t_bus = br["t_bus"]
                susceptance = 1.0 / br["br_x"]
                if f == b
                    add_to_expression!(flow_out, susceptance, theta_uc[f, t])
                    add_to_expression!(flow_out, -susceptance, theta_uc[t_bus, t])
                elseif t_bus == b
                    add_to_expression!(flow_out, -susceptance, theta_uc[f, t])
                    add_to_expression!(flow_out, susceptance, theta_uc[t_bus, t])
                end
            end
            @constraint(
                uc_model, sum(pg_uc[g, t] for g in gen_at_bus; init=0.0) - load_t == flow_out
            )
        end

        for br_id in branch_ids, t in T
            br = data["branch"][string(br_id)]
            rate = br["rate_a"]
            if rate > 0 && rate < 1e10
                f = br["f_bus"]
                t_bus = br["t_bus"]
                susceptance = 1.0 / br["br_x"]
                @constraint(uc_model, susceptance * (theta_uc[f, t] - theta_uc[t_bus, t]) <= rate)
                @constraint(uc_model, susceptance * (theta_uc[f, t] - theta_uc[t_bus, t]) >= -rate)
            end
        end

        for g in gen_ids, t in T
            if t > 1
                @constraint(uc_model, v_start[g, t] >= u[g, t] - u[g, t - 1])
                @constraint(uc_model, v_shut[g, t] >= u[g, t - 1] - u[g, t])
                @constraint(uc_model, v_start[g, t] + v_shut[g, t] <= 1)
            else
                @constraint(uc_model, v_start[g, t] >= u[g, t] - 1)
                @constraint(uc_model, v_shut[g, t] >= 1 - u[g, t])
            end
        end

        min_up = 3
        for g in gen_ids, t in T
            if t >= min_up
                @constraint(uc_model, sum(v_start[g, tau] for tau in (t - min_up + 1):t) <= u[g, t])
            end
        end

        min_down = 2
        for g in gen_ids, t in T
            if t >= min_down
                @constraint(
                    uc_model, sum(v_shut[g, tau] for tau in (t - min_down + 1):t) <= 1 - u[g, t]
                )
            end
        end

        # Ramp rates in UC (50% of Pmax)
        for g in gen_ids, t in T
            ramp_limit = 0.5 * pmax[g]
            if t > 1
                @constraint(uc_model, pg_uc[g, t] - pg_uc[g, t - 1] <= ramp_limit)
                @constraint(uc_model, pg_uc[g, t - 1] - pg_uc[g, t] <= ramp_limit)
            end
        end

        for t in T
            total_load = sum(base_bus_load[b] * load_profile[t] for b in bus_ids)
            @constraint(uc_model, sum(pmax[g] * u[g, t] for g in gen_ids) >= total_load * 1.10)
        end

        startup_cost = Dict(g => 0.1 * pmax[g] * abs(marginal_cost[g]) for g in gen_ids)
        @objective(
            uc_model,
            Min,
            sum(marginal_cost[g] * pg_uc[g, t] for g in gen_ids, t in T) +
                sum(startup_cost[g] * v_start[g, t] for g in gen_ids, t in T)
        )

        optimize!(uc_model)
        uc_term = string(termination_status(uc_model))
        results["details"]["uc_termination"] = uc_term

        if !(uc_term in ("OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"))
            push!(results["errors"], "UC did not solve: $uc_term")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        # Extract commitment schedule
        commitment = Dict{Int,Vector{Int}}()
        for g in gen_ids
            commitment[g] = [round(Int, value(u[g, t])) for t in T]
        end
        results["details"]["commitment_schedule"] = Dict(string(g) => v for (g, v) in commitment)

        # Extract UC dispatch for comparison
        uc_dispatch = Dict{Int,Vector{Float64}}()
        for g in gen_ids
            uc_dispatch[g] = [round(value(pg_uc[g, t]); digits=4) for t in T]
        end

        # ---- Step 3: Solve SCED (LP) with fixed commitment ----
        ed_model = Model(
            optimizer_with_attributes(
                HiGHS.Optimizer,
                "time_limit" => 300.0,
                "presolve" => "on",
                "threads" => 1,
                "output_flag" => false,
            ),
        )

        @variable(ed_model, pg[g in gen_ids, t in T] >= 0)
        @variable(ed_model, theta[b in bus_ids, t in T])

        for t in T
            fix(theta[ref_bus, t], 0.0; force=true)
        end

        # Generation limits linked to FIXED commitment (no binary variables)
        for g in gen_ids, t in T
            if commitment[g][t] == 1
                @constraint(ed_model, pg[g, t] <= pmax[g])
                @constraint(ed_model, pg[g, t] >= pmin[g])
            else
                # Unit is off: no generation
                fix(pg[g, t], 0.0; force=true)
            end
        end

        # DC power flow constraints (same as UC)
        for t in T, b in bus_ids
            gen_at_bus = [g for g in gen_ids if gen_bus[g] == b]
            load_t = base_bus_load[b] * load_profile[t]
            flow_out = AffExpr(0.0)
            for br_id in branch_ids
                br = data["branch"][string(br_id)]
                f = br["f_bus"]
                t_bus = br["t_bus"]
                susceptance = 1.0 / br["br_x"]
                if f == b
                    add_to_expression!(flow_out, susceptance, theta[f, t])
                    add_to_expression!(flow_out, -susceptance, theta[t_bus, t])
                elseif t_bus == b
                    add_to_expression!(flow_out, -susceptance, theta[f, t])
                    add_to_expression!(flow_out, susceptance, theta[t_bus, t])
                end
            end
            @constraint(ed_model, sum(pg[g, t] for g in gen_at_bus; init=0.0) - load_t == flow_out)
        end

        # Branch flow limits
        for br_id in branch_ids, t in T
            br = data["branch"][string(br_id)]
            rate = br["rate_a"]
            if rate > 0 && rate < 1e10
                f = br["f_bus"]
                t_bus = br["t_bus"]
                susceptance = 1.0 / br["br_x"]
                @constraint(ed_model, susceptance * (theta[f, t] - theta[t_bus, t]) <= rate)
                @constraint(ed_model, susceptance * (theta[f, t] - theta[t_bus, t]) >= -rate)
            end
        end

        # Ramp rate constraints in ED -- these are INDEPENDENT of UC ramp constraints
        # They are enforced fresh in the ED stage, not inherited from UC
        ramp_violations_possible = false
        for g in gen_ids, t in T
            ramp_limit = 0.5 * pmax[g]
            if t > 1
                # Only apply ramp constraints between periods where both are committed
                # or handle startup/shutdown ramp differently
                if commitment[g][t] == 1 && commitment[g][t - 1] == 1
                    @constraint(ed_model, pg[g, t] - pg[g, t - 1] <= ramp_limit)
                    @constraint(ed_model, pg[g, t - 1] - pg[g, t] <= ramp_limit)
                    ramp_violations_possible = true
                elseif commitment[g][t] == 1 && commitment[g][t - 1] == 0
                    # Startup: ramp from 0 to pmin..pmax, limit ramp-up
                    @constraint(ed_model, pg[g, t] <= ramp_limit)
                elseif commitment[g][t] == 0 && commitment[g][t - 1] == 1
                    # Shutdown: ramp from previous to 0, limit ramp-down
                    @constraint(ed_model, pg[g, t - 1] <= ramp_limit)
                end
            end
        end
        results["details"]["ramp_constraints_enforced_in_ed"] = true
        results["details"]["ramp_limit_fraction"] = 0.5

        # Objective: minimize linearized generation cost (no startup costs in ED)
        @objective(ed_model, Min, sum(marginal_cost[g] * pg[g, t] for g in gen_ids, t in T))

        optimize!(ed_model)
        ed_term = string(termination_status(ed_model))
        results["details"]["ed_termination"] = ed_term
        results["details"]["ed_solve_time"] = solve_time(ed_model)

        if !(ed_term in ("OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"))
            push!(results["errors"], "ED did not solve: $ed_term")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        results["details"]["ed_objective"] = objective_value(ed_model)

        # Extract ED dispatch
        ed_dispatch = Dict{String,Vector{Float64}}()
        for g in gen_ids
            ed_dispatch[string(g)] = [round(value(pg[g, t]); digits=4) for t in T]
        end
        results["details"]["ed_dispatch_sample"] = Dict(
            k => v for
            (k, v) in Iterators.take(sort(collect(ed_dispatch); by=x->parse(Int, x[1])), 3)
        )

        # ---- Step 4: Verify ramp constraints are binding ----
        ramp_binding_count = 0
        ramp_check_details = []
        for g in gen_ids
            for t in 2:24
                if commitment[g][t] == 1 && commitment[g][t - 1] == 1
                    ramp_limit = 0.5 * pmax[g]
                    pg_curr = value(pg[g, t])
                    pg_prev = value(pg[g, t - 1])
                    ramp = abs(pg_curr - pg_prev)
                    if ramp > ramp_limit - 1e-6  # within tolerance of binding
                        ramp_binding_count += 1
                        push!(
                            ramp_check_details,
                            Dict(
                                "gen" => g,
                                "period" => t,
                                "pg_prev" => round(pg_prev; digits=4),
                                "pg_curr" => round(pg_curr; digits=4),
                                "ramp" => round(ramp; digits=4),
                                "limit" => round(ramp_limit; digits=4),
                            ),
                        )
                    end
                end
            end
        end
        results["details"]["ramp_binding_count"] = ramp_binding_count
        results["details"]["ramp_binding_examples"] = ramp_check_details[1:min(
            5, length(ramp_check_details)
        )]

        # Compare UC vs ED dispatch
        dispatch_diffs = []
        for g in gen_ids
            for t in T
                uc_val = uc_dispatch[g][t]
                ed_val = value(pg[g, t])
                diff = abs(ed_val - uc_val)
                if diff > 0.001
                    push!(
                        dispatch_diffs,
                        Dict(
                            "gen" => g,
                            "period" => t,
                            "uc_dispatch" => round(uc_val; digits=4),
                            "ed_dispatch" => round(ed_val; digits=4),
                            "diff" => round(diff; digits=4),
                        ),
                    )
                end
            end
        end
        results["details"]["uc_ed_dispatch_differences"] = length(dispatch_diffs)
        results["details"]["uc_ed_diff_sample"] = dispatch_diffs[1:min(5, length(dispatch_diffs))]

        results["details"]["uc_ed_cleanly_separable"] = true

        push!(
            results["workarounds"],
            "PowerModels has NO built-in SCED. Same as A-5, the entire formulation " *
            "is user-assembled via JuMP. The UC-ED two-stage decomposition is " *
            "achieved by: (1) solving UC MILP to get commitment schedule, " *
            "(2) fixing commitment as parameters in a new LP model, " *
            "(3) re-adding ramp constraints independently in ED stage. " *
            "PowerModels contributes only MATPOWER parsing. ~200 lines of " *
            "manual JuMP code for the two-stage workflow.",
        )

        results["status"] = "pass"

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
