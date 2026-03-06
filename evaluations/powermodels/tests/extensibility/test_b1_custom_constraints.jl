#= Test B-1: Add a flow gate limit to DC OPF from A-3
   A flow gate is a constraint on the sum of flows on a group of branches.
   Use instantiate_model + add JuMP constraint to pm.model.
=#
using PowerModels, JuMP, HiGHS, JSON
PowerModels.silence()

function run(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "test_id" => "B-1",
        "test_name" => "custom_constraints",
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

        # --- Step 1: Baseline DC OPF (reproduce A-3) ---
        result_base = solve_dc_opf(
            data, HiGHS.Optimizer; setting=Dict("output" => Dict("duals" => true))
        )
        @assert result_base["termination_status"] == OPTIMAL
        results["details"]["baseline_objective"] = result_base["objective"]

        baseline_flows = Dict{String,Float64}()
        for (br_id, br) in result_base["solution"]["branch"]
            baseline_flows[br_id] = get(br, "pf", 0.0)
        end

        # --- Step 2: DC OPF with flow gate constraint ---
        data2 = PowerModels.parse_file(network_file)

        # Define a flow gate: sum of flows on branches 1, 2, 3 (arbitrary group)
        # Choose branches that have significant flow in the baseline
        gate_branches = ["1", "2", "3"]
        gate_baseline_flow = sum(get(baseline_flows, br, 0.0) for br in gate_branches)
        results["details"]["gate_branches"] = gate_branches
        results["details"]["gate_baseline_flow_pu"] = round(gate_baseline_flow; digits=4)

        # Set gate limit to 80% of baseline flow (force the constraint to bind)
        gate_limit = abs(gate_baseline_flow) * 0.8
        if gate_limit < 0.01
            # If baseline flow is too small, pick branches with more flow
            sorted_branches = sort(collect(baseline_flows); by=x->abs(x[2]), rev=true)
            gate_branches = [sorted_branches[i][1] for i in 1:min(3, length(sorted_branches))]
            gate_baseline_flow = sum(baseline_flows[br] for br in gate_branches)
            gate_limit = abs(gate_baseline_flow) * 0.8
            results["details"]["gate_branches_adjusted"] = gate_branches
            results["details"]["gate_baseline_flow_adjusted_pu"] = round(
                gate_baseline_flow; digits=4
            )
        end
        results["details"]["gate_limit_pu"] = round(gate_limit; digits=4)

        # Two-stage approach: instantiate model, then add custom constraint
        pm = PowerModels.instantiate_model(
            data2,
            DCPPowerModel,
            PowerModels.build_opf;
            setting=Dict("output" => Dict("duals" => true)),
        )

        # Access branch flow variables
        # In DC OPF, branch power flow variable is :p, indexed by (branch_id, from_bus, to_bus)
        # We need to find the correct variable references
        gate_flow_vars = []
        for br_str in gate_branches
            br_id = parse(Int, br_str)
            try
                pf_var = PowerModels.var(
                    pm,
                    :p,
                    (br_id, data2["branch"][br_str]["f_bus"], data2["branch"][br_str]["t_bus"]),
                )
                push!(gate_flow_vars, pf_var)
            catch e
                push!(
                    results["errors"],
                    "Could not access flow var for branch $br_id: $(sprint(showerror, e))",
                )
            end
        end

        results["details"]["gate_flow_vars_found"] = length(gate_flow_vars)

        if length(gate_flow_vars) == length(gate_branches)
            # Add flow gate constraint: sum of flows <= gate_limit
            JuMP.@constraint(pm.model, flowgate_upper, sum(gate_flow_vars) <= gate_limit)
            JuMP.@constraint(pm.model, flowgate_lower, sum(gate_flow_vars) >= -gate_limit)

            results["details"]["constraint_added"] = true
            results["details"]["constraint_type"] = "flow gate: sum(pf[branches]) bounded by +/- gate_limit"
            results["details"]["method"] = "instantiate_model + JuMP.@constraint on pm.model"
            results["details"]["source_patching_required"] = false

            # Solve
            result_gated = PowerModels.optimize_model!(pm; optimizer=HiGHS.Optimizer)

            gate_status = result_gated["termination_status"]
            results["details"]["gated_termination_status"] = string(gate_status)

            if gate_status == OPTIMAL || gate_status == LOCALLY_SOLVED
                results["details"]["gated_objective"] = result_gated["objective"]
                results["details"]["objective_increase"] = round(
                    result_gated["objective"] - result_base["objective"]; digits=4
                )

                # Check if gate constraint is binding (objective increased)
                obj_increased = result_gated["objective"] > result_base["objective"] + 1e-4
                results["details"]["gate_constraint_binding"] = obj_increased

                # Extract constrained flows
                gated_flows = Dict{String,Float64}()
                for (br_id, br) in result_gated["solution"]["branch"]
                    gated_flows[br_id] = get(br, "pf", 0.0)
                end

                gate_constrained_flow = sum(get(gated_flows, br, 0.0) for br in gate_branches)
                results["details"]["gate_constrained_flow_pu"] = round(
                    gate_constrained_flow; digits=4
                )
                results["details"]["gate_limit_respected"] =
                    abs(gate_constrained_flow) <= gate_limit + 1e-4

                # Compare dispatch
                gated_dispatch = Dict{String,Float64}()
                for (gid, gen) in result_gated["solution"]["gen"]
                    gated_dispatch[gid] = gen["pg"]
                end
                results["details"]["gated_dispatch_pu"] = gated_dispatch

                # LMPs
                gated_lmps = Dict{String,Float64}()
                for (bid, bus) in result_gated["solution"]["bus"]
                    gated_lmps[bid] = get(bus, "lam_kcl_r", NaN)
                end
                results["details"]["gated_lmps"] = gated_lmps

                results["status"] = "pass"
            else
                push!(results["errors"], "Gated DC OPF did not converge: $gate_status")
            end
        else
            push!(results["errors"], "Could not access all gate branch flow variables")
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
