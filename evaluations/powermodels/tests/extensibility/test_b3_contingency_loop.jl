#=
Test B-3: N-1 DCPF contingency loop
Dimension: extensibility
Network: TINY (IEEE 39-bus, 46 branches)
Pass condition: Runs in a loop without re-parsing or re-instantiating the base model
               from file each iteration. Base model modified in-place or cloned efficiently.
Tool: PowerModels.jl v0.21.5
Solver: N/A (direct solve via compute_dc_pf)

Approach: Parse network once. For each branch, deepcopy the data dict, set
br_status=0 for that branch, run compute_dc_pf, collect line loading.
=#

using PowerModels, JSON, LinearAlgebra

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

    # Warm-up
    try
        _data = PowerModels.parse_file(network_file)
        PowerModels.compute_dc_pf(_data)
    catch
        ;
    end

    t0 = time()
    try
        # ---- Step 1: Parse network ONCE ----
        t_parse = time()
        data = PowerModels.parse_file(network_file)
        parse_time = time() - t_parse

        branch_ids = sort(parse.(Int, collect(keys(data["branch"]))))
        num_branches = length(branch_ids)

        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_branches"] = num_branches
        results["details"]["parse_time_s"] = round(parse_time; digits=6)
        results["details"]["reparse_per_contingency"] = false

        # Get branch ratings for computing loading percentages
        branch_ratings = Dict{Int,Float64}()
        for br_id in branch_ids
            br = data["branch"][string(br_id)]
            rate_a = get(br, "rate_a", 0.0)
            branch_ratings[br_id] = rate_a > 0 ? rate_a : Inf
        end

        # ---- Step 2: Solve base case ----
        t_base = time()
        base_result = PowerModels.compute_dc_pf(data)
        base_time = time() - t_base

        if !base_result["termination_status"]
            push!(results["errors"], "Base case DCPF did not converge")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        # Get base case flows
        PowerModels.update_data!(data, base_result["solution"])
        base_flows_data = PowerModels.calc_branch_flow_dc(data)
        base_flows = Dict{Int,Float64}()
        for (id, br) in base_flows_data["branch"]
            base_flows[parse(Int, id)] = abs(br["pf"])
        end
        results["details"]["base_solve_time_s"] = round(base_time; digits=6)

        # Re-parse to get clean data for contingency loop (update_data! modified it)
        data = PowerModels.parse_file(network_file)

        # ---- Step 3: N-1 contingency loop ----
        contingency_results = Dict{Int,Dict{String,Any}}()
        per_contingency_times = Float64[]
        max_loading_across_all = 0.0
        max_loading_branch = -1
        max_loading_contingency = -1
        island_count = 0
        diverged_count = 0

        t_loop = time()
        for outage_br_id in branch_ids
            t_case = time()

            # Deep copy -- do NOT re-parse from file
            d = deepcopy(data)
            d["branch"][string(outage_br_id)]["br_status"] = 0

            # Check connectivity
            components = PowerModels.calc_connected_components(d)
            is_connected = length(components) == 1

            case_result = Dict{String,Any}(
                "outaged_branch" => outage_br_id, "is_connected" => is_connected
            )

            if !is_connected
                island_count += 1
                case_result["status"] = "island"
                case_result["num_islands"] = length(components)
                case_result["max_loading_pct"] = NaN
            else
                # Solve DCPF
                try
                    pf_result = PowerModels.compute_dc_pf(d)
                    converged = pf_result["termination_status"]

                    if converged
                        # Calculate branch flows
                        PowerModels.update_data!(d, pf_result["solution"])
                        flows_data = PowerModels.calc_branch_flow_dc(d)

                        # Compute loading for each non-outaged branch
                        max_loading_this_case = 0.0
                        max_loading_br_this = -1
                        for br_id in branch_ids
                            if br_id == outage_br_id
                                continue
                            end
                            flow = abs(flows_data["branch"][string(br_id)]["pf"])
                            rating = branch_ratings[br_id]
                            loading = rating == Inf ? 0.0 : (flow / rating) * 100.0
                            if loading > max_loading_this_case
                                max_loading_this_case = loading
                                max_loading_br_this = br_id
                            end
                        end

                        case_result["status"] = "converged"
                        case_result["max_loading_pct"] = round(max_loading_this_case; digits=2)
                        case_result["max_loading_branch"] = max_loading_br_this

                        if max_loading_this_case > max_loading_across_all
                            max_loading_across_all = max_loading_this_case
                            max_loading_branch = max_loading_br_this
                            max_loading_contingency = outage_br_id
                        end
                    else
                        case_result["status"] = "diverged"
                        case_result["max_loading_pct"] = NaN
                        diverged_count += 1
                    end
                catch e
                    if isa(e, LinearAlgebra.SingularException)
                        case_result["status"] = "singular"
                        case_result["max_loading_pct"] = NaN
                        diverged_count += 1
                    else
                        rethrow(e)
                    end
                end
            end

            elapsed_case = time() - t_case
            case_result["solve_time_s"] = round(elapsed_case; digits=6)
            push!(per_contingency_times, elapsed_case)
            contingency_results[outage_br_id] = case_result
        end
        loop_time = time() - t_loop

        # ---- Step 4: Summary ----
        results["details"]["total_contingencies"] = num_branches
        results["details"]["converged_count"] = count(
            r -> get(r, "status", "") == "converged", values(contingency_results)
        )
        results["details"]["island_count"] = island_count
        results["details"]["diverged_count"] = diverged_count

        results["details"]["max_loading_pct"] = round(max_loading_across_all; digits=2)
        results["details"]["max_loading_branch"] = max_loading_branch
        results["details"]["max_loading_contingency"] = max_loading_contingency

        results["details"]["loop_wall_clock_s"] = round(loop_time; digits=4)
        results["details"]["avg_time_per_contingency_s"] = round(loop_time / num_branches; digits=6)
        results["details"]["min_contingency_time_s"] = round(
            minimum(per_contingency_times); digits=6
        )
        results["details"]["max_contingency_time_s"] = round(
            maximum(per_contingency_times); digits=6
        )
        results["details"]["median_contingency_time_s"] = round(
            sort(per_contingency_times)[div(length(per_contingency_times)+1, 2)]; digits=6
        )

        # Per-contingency timing breakdown
        results["details"]["per_contingency_times"] = [
            round(t; digits=6) for t in per_contingency_times
        ]

        # Top 5 most loaded contingencies
        converged_cases = [
            (br_id, r) for (br_id, r) in contingency_results if get(r, "status", "") == "converged"
        ]
        sort!(converged_cases; by=x -> x[2]["max_loading_pct"], rev=true)
        top5 = Dict{String,Any}()
        for (br_id, r) in Iterators.take(converged_cases, 5)
            top5[string(br_id)] = Dict(
                "max_loading_pct" => r["max_loading_pct"],
                "max_loading_branch" => r["max_loading_branch"],
            )
        end
        results["details"]["top5_contingencies"] = top5

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
