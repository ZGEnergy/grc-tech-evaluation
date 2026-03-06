
#= Test B-3: N-1 DCPF Contingency Loop — all 46 branches =#

using PowerModels, JSON
PowerModels.silence()

function run_test(network_file::String="/workspace/data/networks/case39.m")
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

        # Get base case branch count
        active_branches = [br for (i, br) in data["branch"] if br["br_status"] != 0]
        n_branches = length(active_branches)

        # Base case DCPF
        base_result = PowerModels.compute_dc_pf(data)
        @assert base_result["termination_status"] == true "Base DCPF failed"

        # Compute base flows from angles
        base_va = Dict{Int,Float64}()
        for (i, bus_sol) in base_result["solution"]["bus"]
            base_va[parse(Int, i)] = bus_sol["va"]
        end

        # N-1 contingency loop: disable one branch at a time, solve DCPF
        max_loading_per_contingency = Dict{Int,Float64}()
        contingency_results = Dict{String,Any}[]
        failed_contingencies = Int[]

        for (idx, br) in enumerate(active_branches)
            br_idx = br["index"]
            # Clone data dict and disable this branch
            cdata = deepcopy(data)
            for (i, cbr) in cdata["branch"]
                if cbr["index"] == br_idx
                    cbr["br_status"] = 0
                    break
                end
            end

            try
                ct_result = PowerModels.compute_dc_pf(cdata)
                if ct_result["termination_status"] != true
                    push!(failed_contingencies, br_idx)
                    continue
                end

                # Compute branch flows from angles
                ct_va = Dict{Int,Float64}()
                for (i, bus_sol) in ct_result["solution"]["bus"]
                    ct_va[parse(Int, i)] = bus_sol["va"]
                end

                max_loading = 0.0
                for (i, cbr) in cdata["branch"]
                    if cbr["br_status"] != 0 && haskey(cbr, "rate_a") && cbr["rate_a"] > 0
                        f_bus = cbr["f_bus"]
                        t_bus = cbr["t_bus"]
                        if haskey(ct_va, f_bus) && haskey(ct_va, t_bus)
                            b = -1.0 / cbr["br_x"]  # susceptance (ignoring resistance for DC)
                            flow = b * (ct_va[f_bus] - ct_va[t_bus])
                            loading = abs(flow) / cbr["rate_a"]
                            max_loading = max(max_loading, loading)
                        end
                    end
                end
                max_loading_per_contingency[br_idx] = max_loading

                push!(
                    contingency_results,
                    Dict(
                        "removed_branch" => br_idx,
                        "max_loading_pct" => round(max_loading * 100; digits=2),
                    ),
                )
            catch e
                push!(failed_contingencies, br_idx)
            end
        end

        # Find overall worst contingency
        worst_branch = -1
        worst_loading = 0.0
        for (br_idx, loading) in max_loading_per_contingency
            if loading > worst_loading
                worst_loading = loading
                worst_branch = br_idx
            end
        end

        results["details"] = Dict(
            "n_branches" => n_branches,
            "n_contingencies_solved" => length(max_loading_per_contingency),
            "n_contingencies_failed" => length(failed_contingencies),
            "failed_contingencies" => failed_contingencies,
            "worst_branch" => worst_branch,
            "worst_loading_pct" => round(worst_loading * 100; digits=2),
            "approach" => "deepcopy data dict, set br_status=0, call compute_dc_pf per contingency",
            "reparsed_from_file" => false,
            "top_5_contingencies" =>
                sort(contingency_results; by=x -> -x["max_loading_pct"])[1:min(
                    5, length(contingency_results)
                )],
        )

        results["status"] = "pass"
    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
    finally
        results["wall_clock_seconds"] = time() - t0
    end
    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run_test()
    println(JSON.json(result, 2))
end
