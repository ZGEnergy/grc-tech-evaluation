#= Test A-8: Multi-period 24hr DC OPF with stochastic load and renewable scenarios on TINY (case39)
   NOTE: PowerModels has multi-network (replicate) but no native stochastic structure.
   Two approaches are tested:
   1. Multi-network with scenario x period flattening (single optimization)
   2. Loop over deterministic solves per scenario (comparison baseline)
=#
using PowerModels, HiGHS, Ipopt, JuMP, JSON

function run(network_file::String="/workspace/data/networks/case39.m")
    results = Dict{String,Any}(
        "test_id" => "A-8",
        "test_name" => "stochastic_timeseries",
        "network" => "case39",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        data = PowerModels.parse_file(network_file)
        nperiods = 24
        nscenarios = 3
        ngens = length(data["gen"])
        results["details"]["num_periods"] = nperiods
        results["details"]["num_scenarios"] = nscenarios
        results["details"]["num_generators"] = ngens

        base_profile = [
            0.60,
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
        scenario_multipliers = [1.0, 1.05, 0.95]
        scenario_probs = [0.5, 0.3, 0.2]

        results["details"]["scenario_probabilities"] = scenario_probs
        results["details"]["scenario_multipliers"] = scenario_multipliers

        # Use Ipopt for the large multi-network problem (handles quadratic objectives well)
        solver = optimizer_with_attributes(
            Ipopt.Optimizer, "max_iter" => 10000, "print_level" => 0, "tol" => 1e-6
        )

        # Also prepare HiGHS for deterministic solves (smaller problems)
        solver_det = optimizer_with_attributes(
            HiGHS.Optimizer, "time_limit" => 300.0, "threads" => 1, "output_flag" => false
        )

        # --- Approach 1: Multi-network OPF (all scenarios x periods in single optimization) ---
        # Each scenario-period is an independent sub-network within the single JuMP model.
        # For DC OPF without commitment, all dispatch is recourse (second-stage),
        # so each scenario-period solves independently but within a single JuMP model.
        total_nw = nscenarios * nperiods
        mn_data = PowerModels.replicate(data, total_nw)

        for s in 1:nscenarios
            for t in 1:nperiods
                nw_idx = (s - 1) * nperiods + t
                for (lid, load) in mn_data["nw"]["$nw_idx"]["load"]
                    base_pd = data["load"][lid]["pd"]
                    base_qd = data["load"][lid]["qd"]
                    mn_data["nw"]["$nw_idx"]["load"][lid]["pd"] =
                        base_pd * base_profile[t] * scenario_multipliers[s]
                    mn_data["nw"]["$nw_idx"]["load"][lid]["qd"] =
                        base_qd * base_profile[t] * scenario_multipliers[s]
                end
            end
        end

        mn_result = solve_mn_opf(mn_data, DCPPowerModel, solver)
        results["details"]["mn_termination_status"] = string(mn_result["termination_status"])
        results["details"]["mn_objective"] = mn_result["objective"]

        if mn_result["termination_status"] == OPTIMAL ||
            mn_result["termination_status"] == LOCALLY_SOLVED
            # Extract per-scenario costs from multi-network solution
            scenario_dispatches = Dict{String,Any}()
            for s in 1:nscenarios
                peak_nw = (s - 1) * nperiods + 10  # period 10 = peak
                gen_dispatch = Dict{String,Float64}()
                for (gid, gen) in mn_result["solution"]["nw"]["$peak_nw"]["gen"]
                    gen_dispatch[gid] = gen["pg"]
                end
                scenario_dispatches["scenario_$(s)_peak"] = gen_dispatch
            end
            results["details"]["scenario_peak_dispatches"] = scenario_dispatches

            # --- Approach 2: Loop over deterministic solves (comparison) ---
            det_objectives = Float64[]
            for s in 1:nscenarios
                det_data = PowerModels.replicate(data, nperiods)
                for t in 1:nperiods
                    for (lid, load) in det_data["nw"]["$t"]["load"]
                        base_pd = data["load"][lid]["pd"]
                        base_qd = data["load"][lid]["qd"]
                        det_data["nw"]["$t"]["load"][lid]["pd"] =
                            base_pd * base_profile[t] * scenario_multipliers[s]
                        det_data["nw"]["$t"]["load"][lid]["qd"] =
                            base_qd * base_profile[t] * scenario_multipliers[s]
                    end
                end
                det_result = solve_mn_opf(det_data, DCPPowerModel, solver)
                if det_result["termination_status"] == OPTIMAL ||
                    det_result["termination_status"] == LOCALLY_SOLVED
                    push!(det_objectives, det_result["objective"])
                else
                    push!(det_objectives, NaN)
                end
            end
            results["details"]["deterministic_objectives_per_scenario"] = det_objectives

            # Expected cost from deterministic solves
            valid_det = [i for i in 1:length(det_objectives) if !isnan(det_objectives[i])]
            if length(valid_det) == nscenarios
                expected_det = sum(scenario_probs .* det_objectives)
                results["details"]["expected_cost_deterministic"] = expected_det

                # Multi-network sum should equal sum of deterministic solves (no coupling)
                results["details"]["mn_vs_det_diff"] = mn_result["objective"] - sum(det_objectives)
            end

            results["details"]["approach"] = "Multi-network flattening via replicate() with scenario x period indexing. For DC OPF without commitment, each scenario-period is independent within the single optimization. PowerModels multi-network provides the infrastructure but not native probability weighting or scenario tree structure."
            results["details"]["native_stochastic_support"] = false
            results["details"]["qualification"] = "Qualified pass: multi-network infrastructure enables scenario-indexed formulations, but probability weighting, scenario trees, and non-anticipativity for commitment variables require manual JuMP-level construction. No native stochastic programming support."

            results["status"] = "pass"
            push!(
                results["workarounds"],
                "PowerModels has NO native stochastic programming support (no probability weights, scenario trees, or non-anticipativity). The multi-network infrastructure (replicate + solve_mn_opf) provides scenario indexing, but stochastic structure must be built manually via JuMP. For dispatch-only problems, this reduces to independent scenario solves. For SCUC with commitment, non-anticipativity constraints on binary variables would need manual implementation.",
            )
        else
            push!(
                results["errors"], "Multi-network solve failed: $(mn_result["termination_status"])"
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
