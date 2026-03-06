
#= Test A-3: DC OPF with generation costs and line flow limits on TINY (case39) =#

using PowerModels, HiGHS, GLPK, JuMP, JSON

function run(network_file::String="/workspace/data/networks/case39.m")
    results = Dict(
        "test_id" => "A-3",
        "test_name" => "dcopf",
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
        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_generators"] = length(data["gen"])

        # Log cost model info
        cost_info = Dict{String,Any}()
        for (gid, gen) in data["gen"]
            cost_info[gid] = Dict(
                "model" => gen["model"], "ncost" => gen["ncost"], "cost" => gen["cost"]
            )
        end
        results["details"]["generator_costs"] = cost_info

        # Log line limits
        branch_limits = Dict{String,Any}()
        for (bid, br) in data["branch"]
            branch_limits[bid] = Dict(
                "rate_a" => br["rate_a"], "f_bus" => br["f_bus"], "t_bus" => br["t_bus"]
            )
        end
        results["details"]["branch_rate_a_pu"] = branch_limits

        # --- Solve DC OPF with HiGHS, requesting duals ---
        solver = optimizer_with_attributes(
            HiGHS.Optimizer, "time_limit" => 300.0, "threads" => 1, "output_flag" => true
        )
        result_opf = solve_dc_opf(data, solver; setting=Dict("output" => Dict("duals" => true)))

        results["details"]["termination_status"] = string(result_opf["termination_status"])
        results["details"]["objective"] = result_opf["objective"]
        results["details"]["solve_time_seconds"] = result_opf["solve_time"]

        if result_opf["termination_status"] == OPTIMAL ||
            result_opf["primal_status"] == FEASIBLE_POINT
            sol = result_opf["solution"]

            # Optimal dispatch
            gen_dispatch = Dict{String,Float64}()
            for (gid, gen) in sol["gen"]
                gen_dispatch[gid] = gen["pg"]
            end
            results["details"]["optimal_dispatch_pu"] = gen_dispatch

            # LMPs from bus duals
            lmps = Dict{String,Float64}()
            for (bid, bus) in sol["bus"]
                lmps[bid] = get(bus, "lam_kcl_r", NaN)
            end
            results["details"]["lmps_bus_duals"] = lmps

            # Branch duals (congestion shadow prices)
            branch_duals = Dict{String,Dict{String,Any}}()
            for (br_id, br) in sol["branch"]
                branch_duals[br_id] = Dict(
                    "pf" => get(br, "pf", NaN),
                    "mu_sm_fr" => get(br, "mu_sm_fr", NaN),
                    "mu_sm_to" => get(br, "mu_sm_to", NaN),
                )
            end
            results["details"]["branch_flows_and_duals"] = branch_duals

            # Congested lines
            congested = [
                br_id for (br_id, bd) in branch_duals if
                abs(get(bd, "mu_sm_fr", 0.0)) > 1e-4 || abs(get(bd, "mu_sm_to", 0.0)) > 1e-4
            ]
            results["details"]["congested_branches"] = congested

            # Check non-uniform LMPs (indicates congestion)
            lmp_vals = collect(values(lmps))
            lmp_range = maximum(lmp_vals) - minimum(lmp_vals)
            results["details"]["lmp_range"] = lmp_range
            results["details"]["lmp_min"] = minimum(lmp_vals)
            results["details"]["lmp_max"] = maximum(lmp_vals)

            results["status"] = "pass"
            results["details"]["solver"] = "HiGHS"
            results["details"]["api_lines"] = 2  # parse_file + solve_dc_opf
        end

        # --- Also solve with GLPK as secondary ---
        try
            result_glpk = solve_dc_opf(
                data, GLPK.Optimizer; setting=Dict("output" => Dict("duals" => true))
            )
            results["details"]["glpk_termination"] = string(result_glpk["termination_status"])
            results["details"]["glpk_objective"] = result_glpk["objective"]
            obj_diff = abs(result_opf["objective"] - result_glpk["objective"])
            results["details"]["highs_glpk_obj_diff"] = obj_diff
        catch e
            push!(results["errors"], "GLPK secondary solve failed: " * sprint(showerror, e))
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
