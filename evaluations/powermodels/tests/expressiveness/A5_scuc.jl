#= Test A-5: 24-hour SCUC as MILP on TINY (case39)
   CRITICAL: PowerModels has NO built-in SCUC. This test documents the limitation
   and attempts to use multi-network + JuMP model access to build commitment variables.
=#
using PowerModels, HiGHS, SCIP, JuMP, JSON

function run(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "test_id" => "A-5",
        "test_name" => "scuc",
        "network" => "case39",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        data = PowerModels.parse_file(network_file)
        ngens = length(data["gen"])
        nperiods = 24
        results["details"]["num_generators"] = ngens
        results["details"]["num_periods"] = nperiods

        # Create multi-network data for 24 periods
        mn_data = PowerModels.replicate(data, nperiods)

        # Vary load across periods (simple diurnal pattern)
        load_profile = [
            0.6,
            0.55,
            0.52,
            0.50,
            0.52,
            0.58,
            0.70,
            0.85,
            0.95,
            1.00,
            1.00,
            0.98,
            0.95,
            0.93,
            0.90,
            0.92,
            0.95,
            1.00,
            0.98,
            0.95,
            0.90,
            0.82,
            0.72,
            0.65,
        ]
        for t in 1:nperiods
            for (lid, load) in mn_data["nw"]["$t"]["load"]
                base_pd = data["load"][lid]["pd"]
                base_qd = data["load"][lid]["qd"]
                mn_data["nw"]["$t"]["load"][lid]["pd"] = base_pd * load_profile[t]
                mn_data["nw"]["$t"]["load"][lid]["qd"] = base_qd * load_profile[t]
            end
        end

        results["details"]["load_profile"] = load_profile
        results["details"]["approach"] = "two-stage: instantiate multi-network DC OPF, then add binary commitment variables and UC constraints via JuMP"

        # Use two-stage approach: build multi-network OPF then add UC constraints
        # HiGHS cannot solve MIQP (quadratic obj + binary vars).
        # Use SCIP which handles MINLP/MIQP.
        solver = optimizer_with_attributes(
            SCIP.Optimizer, "limits/gap" => 0.01, "limits/time" => 300.0, "display/verblevel" => 4
        )

        pm = PowerModels.instantiate_model(mn_data, DCPPowerModel, PowerModels.build_mn_opf)
        model = pm.model

        # Access generator power variables from the PowerModels model
        # In multi-network, variables are indexed by (nw_id, gen_id)
        # We need to find the pg variables
        pg_vars = Dict()
        for t in 1:nperiods
            for gid in 1:ngens
                # PowerModels uses var(pm, nw, :pg, gen_id) pattern
                try
                    pg_vars[(t, gid)] = PowerModels.var(pm, t, :pg, gid)
                catch
                    # Try alternate access
                end
            end
        end

        results["details"]["pg_vars_found"] = length(pg_vars)

        if length(pg_vars) == ngens * nperiods
            # Add binary commitment variables
            @variable(model, u[t = 1:nperiods, g = 1:ngens], Bin)

            # Startup variables
            @variable(model, v[t = 1:nperiods, g = 1:ngens], Bin)  # startup
            @variable(model, w[t = 1:nperiods, g = 1:ngens], Bin)  # shutdown

            # Link pg to commitment: pmin*u <= pg <= pmax*u
            for t in 1:nperiods, g in 1:ngens
                gen = data["gen"]["$g"]
                pmin = gen["pmin"]
                pmax = gen["pmax"]
                pg = pg_vars[(t, g)]
                @constraint(model, pg >= pmin * u[t, g])
                @constraint(model, pg <= pmax * u[t, g])
            end

            # Startup/shutdown logic: u[t] - u[t-1] = v[t] - w[t]
            for t in 2:nperiods, g in 1:ngens
                @constraint(model, u[t, g] - u[t - 1, g] == v[t, g] - w[t, g])
            end
            # Period 1: assume all units on at t=0
            for g in 1:ngens
                @constraint(model, u[1, g] - 1 == v[1, g] - w[1, g])
            end

            # Minimum up time (3 hours for all gens as proxy)
            min_up = 3
            for g in 1:ngens
                for t in 1:nperiods
                    window_end = min(t + min_up - 1, nperiods)
                    for s in t:window_end
                        @constraint(model, u[s, g] >= v[t, g])
                    end
                end
            end

            # Minimum down time (2 hours for all gens as proxy)
            min_down = 2
            for g in 1:ngens
                for t in 1:nperiods
                    window_end = min(t + min_down - 1, nperiods)
                    for s in t:window_end
                        @constraint(model, u[s, g] <= 1 - w[t, g])
                    end
                end
            end

            # Ramp rate constraints (use ramp_10 from data, scaled to hourly)
            for t in 2:nperiods, g in 1:ngens
                gen = data["gen"]["$g"]
                ramp_limit = gen["ramp_10"] > 0 ? gen["ramp_10"] * 6 : gen["pmax"]  # ramp_10 is 10-min
                ramp_limit = min(ramp_limit, gen["pmax"])
                pg_t = pg_vars[(t, g)]
                pg_tm1 = pg_vars[(t-1, g)]
                @constraint(model, pg_t - pg_tm1 <= ramp_limit)
                @constraint(model, pg_tm1 - pg_t <= ramp_limit)
            end

            # Add startup costs to objective
            startup_cost_expr = AffExpr(0.0)
            for t in 1:nperiods, g in 1:ngens
                gen = data["gen"]["$g"]
                sc = gen["startup"]
                if sc > 0
                    add_to_expression!(startup_cost_expr, sc, v[t, g])
                end
            end
            # Add to existing objective
            orig_obj = objective_function(model)
            @objective(model, Min, orig_obj + startup_cost_expr)

            results["details"]["custom_constraints_added"] = true
            results["details"]["constraint_types"] = [
                "commitment linking (pmin*u <= pg <= pmax*u)",
                "startup/shutdown logic",
                "minimum up time (3h)",
                "minimum down time (2h)",
                "ramp rate limits",
                "startup costs in objective",
            ]

            # Solve
            set_optimizer(model, solver)
            optimize!(model)

            term_status = termination_status(model)
            results["details"]["termination_status"] = string(term_status)

            if term_status == MOI.OPTIMAL || term_status == MOI.ALMOST_OPTIMAL
                results["details"]["objective"] = objective_value(model)

                # Try to get MIP gap
                try
                    results["details"]["mip_gap"] = relative_gap(model)
                catch
                    results["details"]["mip_gap"] = "not available"
                end

                # Extract commitment schedule
                commitment = Dict{String,Vector{Int}}()
                for g in 1:ngens
                    commitment["gen_$g"] = [Int(round(value(u[t, g]))) for t in 1:nperiods]
                end
                results["details"]["commitment_schedule"] = commitment

                # Count how many gens are decommitted at some point
                decommitted = count(
                    g -> any(commitment["gen_$g"][t] == 0 for t in 1:nperiods), 1:ngens
                )
                results["details"]["generators_with_off_periods"] = decommitted

                # Dispatch values
                dispatch = Dict{String,Vector{Float64}}()
                for g in 1:ngens
                    dispatch["gen_$g"] = [value(pg_vars[(t, g)]) for t in 1:nperiods]
                end
                results["details"]["dispatch_schedule_pu"] = dispatch

                results["status"] = "pass"
                push!(
                    results["workarounds"],
                    "PowerModels has NO built-in SCUC. Required manual construction of binary commitment variables, startup/shutdown logic, min up/down time, ramp constraints, and startup costs via JuMP model access after instantiate_model().",
                )
            else
                push!(results["errors"], "Solver did not find optimal solution: $term_status")
            end
        else
            push!(
                results["errors"],
                "Could not access pg variables from PowerModels multi-network model. Found $(length(pg_vars)) of expected $(ngens * nperiods).",
            )

            # Document what's missing
            results["details"]["limitation"] = "PowerModels has no built-in SCUC formulation. The multi-network framework provides temporal structure, but adding binary commitment variables requires deep knowledge of PowerModels' internal variable naming and JuMP model access patterns."
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
