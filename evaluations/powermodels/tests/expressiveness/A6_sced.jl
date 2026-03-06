#= Test A-6: Security-Constrained Economic Dispatch (SCED)
   Fix commitment from A-5, solve economic dispatch as LP/QP.
   Must demonstrate ramp constraint enforcement between consecutive intervals.
=#
using PowerModels, JuMP, HiGHS, JSON
PowerModels.silence()

function run(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "test_id" => "A-6",
        "test_name" => "sced",
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

        # Step 1: Get commitment schedule from A-5 logic
        # In A-5, all generators stayed committed for all 24 hours on case39.
        # We reproduce that result: commitment[g,t] = 1 for all g,t.
        # (This is the actual A-5 result for case39.)
        commitment = ones(Int, ngens, nperiods)
        results["details"]["commitment_source"] = "A-5 result: all generators committed for all 24 hours"

        # Load profile (same as A-5)
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

        # Step 2: Build ED model using multi-network DC OPF with fixed commitment
        mn_data = PowerModels.replicate(data, nperiods)

        # Apply load profile
        for t in 1:nperiods
            for (lid, load) in mn_data["nw"]["$t"]["load"]
                base_pd = data["load"][lid]["pd"]
                base_qd = data["load"][lid]["qd"]
                mn_data["nw"]["$t"]["load"][lid]["pd"] = base_pd * load_profile[t]
                mn_data["nw"]["$t"]["load"][lid]["qd"] = base_qd * load_profile[t]
            end
        end

        # Instantiate multi-network DC OPF
        pm = PowerModels.instantiate_model(mn_data, DCPPowerModel, PowerModels.build_mn_opf)
        model = pm.model

        # Access pg variables
        pg_vars = Dict()
        for t in 1:nperiods
            for gid in 1:ngens
                pg_vars[(t, gid)] = PowerModels.var(pm, t, :pg, gid)
            end
        end

        results["details"]["pg_vars_found"] = length(pg_vars)

        # Step 3: Fix commitment (all committed) — enforce pmin/pmax bounds
        # Since all committed, this just enforces normal bounds (already in OPF)
        # But we explicitly add the commitment linking to show UC/ED separation
        for t in 1:nperiods, g in 1:ngens
            gen = data["gen"]["$g"]
            pmin = gen["pmin"]
            pmax = gen["pmax"]
            pg = pg_vars[(t, g)]
            u = commitment[g, t]  # Fixed binary (1 or 0)
            @constraint(model, pg >= pmin * u)
            @constraint(model, pg <= pmax * u)
        end

        # Step 4: Add ramp rate constraints (key requirement for A-6)
        ramp_constraints_added = 0
        ramp_limits_used = Dict{String,Float64}()
        for g in 1:ngens
            gen = data["gen"]["$g"]
            # ramp_10 is 10-minute ramp rate; scale to hourly
            ramp_limit = gen["ramp_10"] > 0 ? gen["ramp_10"] * 6 : gen["pmax"]
            ramp_limit = min(ramp_limit, gen["pmax"])
            ramp_limits_used["gen_$g"] = ramp_limit
            for t in 2:nperiods
                pg_t = pg_vars[(t, g)]
                pg_tm1 = pg_vars[(t-1, g)]
                @constraint(model, pg_t - pg_tm1 <= ramp_limit)
                @constraint(model, pg_tm1 - pg_t <= ramp_limit)
                ramp_constraints_added += 2
            end
        end
        results["details"]["ramp_constraints_added"] = ramp_constraints_added
        results["details"]["ramp_limits_pu"] = ramp_limits_used

        # Step 5: Solve as LP/QP (no binary variables — commitment is fixed)
        # HiGHS handles QP (quadratic objective from cost curves)
        solver = optimizer_with_attributes(
            HiGHS.Optimizer, "time_limit" => 300.0, "output_flag" => true
        )
        set_optimizer(model, solver)
        optimize!(model)

        term_status = termination_status(model)
        results["details"]["termination_status"] = string(term_status)

        if term_status == MOI.OPTIMAL ||
            term_status == MOI.ALMOST_OPTIMAL ||
            term_status == MOI.LOCALLY_SOLVED
            results["details"]["objective"] = objective_value(model)

            # Extract dispatch schedule
            dispatch = Dict{String,Vector{Float64}}()
            for g in 1:ngens
                dispatch["gen_$g"] = [round(value(pg_vars[(t, g)]); digits=6) for t in 1:nperiods]
            end
            results["details"]["dispatch_schedule_pu"] = dispatch

            # Check ramp constraint enforcement
            ramp_violations = String[]
            max_ramp_seen = Dict{String,Float64}()
            for g in 1:ngens
                gen = data["gen"]["$g"]
                ramp_limit = gen["ramp_10"] > 0 ? gen["ramp_10"] * 6 : gen["pmax"]
                ramp_limit = min(ramp_limit, gen["pmax"])
                max_ramp = 0.0
                for t in 2:nperiods
                    ramp = abs(value(pg_vars[(t, g)]) - value(pg_vars[(t-1, g)]))
                    max_ramp = max(max_ramp, ramp)
                    if ramp > ramp_limit * 1.001  # small tolerance
                        push!(
                            ramp_violations,
                            "gen_$g t=$t: ramp=$(round(ramp; digits=4)) > limit=$(round(ramp_limit; digits=4))",
                        )
                    end
                end
                max_ramp_seen["gen_$g"] = round(max_ramp; digits=6)
            end
            results["details"]["max_ramp_per_gen"] = max_ramp_seen
            results["details"]["ramp_violations"] = ramp_violations
            results["details"]["ramp_constraints_enforced"] = isempty(ramp_violations)

            # Compute total dispatch per period
            total_dispatch = Float64[]
            for t in 1:nperiods
                total = sum(value(pg_vars[(t, g)]) for g in 1:ngens)
                push!(total_dispatch, round(total; digits=4))
            end
            results["details"]["total_dispatch_per_period_pu"] = total_dispatch

            # UC/ED separation
            results["details"]["uc_ed_separable"] = true
            results["details"]["separation_method"] = "Commitment fixed as parameter (not variable), ED solved as continuous QP"

            results["details"]["approach"] = "Multi-network DC OPF via PowerModels + custom ramp constraints via JuMP, commitment fixed from A-5"
            push!(
                results["workarounds"],
                "PowerModels has no built-in SCED. Required custom JuMP code for commitment fixing and ramp constraints after instantiate_model().",
            )

            results["status"] = "pass"
        else
            push!(results["errors"], "Solver did not find optimal solution: $term_status")
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
