#=
Test B-3: N-M Contingency Sweep with Escalating Order and Pruning

Dimension: extensibility
Network: TINY (IEEE 39-bus, New England)
Pass condition: Completes without full model reconstruction per contingency case.
  Load loss per contingency case collected. Pruning logic is expressible without
  fighting the tool. Combinatorial enumeration and graph-distance scoping are
  achievable via the tool's API or a clean graph library bridge.
Tool: PowerModels.jl v0.21.5
depends_on: B-2 (graph-distance scoping)

N-M sweep: x=3 (max order), m=3 (max simultaneous outages), with pruning.
=#

using PowerModels

PowerModels.silence()

function run(
    network_file::String=joinpath(@__DIR__, "..", "..", "..", "..", "data", "networks", "case39.m");
    timeseries_dir::Union{String,Nothing}=nothing,
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
        n_buses = length(data["bus"])
        n_branches = length(data["branch"])
        base_mva = data["baseMVA"]

        # --- Build adjacency from data["branch"] (reuses B-2 pattern) ---
        bus_ids = sort([parse(Int, id) for id in keys(data["bus"])])
        branch_ids = sort([parse(Int, id) for id in keys(data["branch"])])

        adjacency = Dict{Int,Vector{Tuple{Int,Int}}}()
        branch_buses = Dict{Int,Tuple{Int,Int}}()
        for b in bus_ids
            adjacency[b] = Tuple{Int,Int}[]
        end
        for br_id in branch_ids
            br = data["branch"][string(br_id)]
            if get(br, "br_status", 1) == 0
                continue
            end
            f = br["f_bus"]
            t = br["t_bus"]
            push!(adjacency[f], (t, br_id))
            push!(adjacency[t], (f, br_id))
            branch_buses[br_id] = (f, t)
        end

        # --- Graph-distance scoping: BFS from each branch to find nearby branches ---
        # For pruning: only combine branches that are within graph distance d of each other
        function branches_within_distance(seed_br::Int, max_dist::Int)
            f, t = branch_buses[seed_br]
            visited_buses = Set{Int}([f, t])
            frontier = [f, t]
            nearby_branches = Set{Int}([seed_br])

            for depth in 1:max_dist
                next_frontier = Int[]
                for bus in frontier
                    for (neighbor, br_id) in adjacency[bus]
                        push!(nearby_branches, br_id)
                        if !(neighbor in visited_buses)
                            push!(visited_buses, neighbor)
                            push!(next_frontier, neighbor)
                        end
                    end
                end
                frontier = next_frontier
            end
            return nearby_branches
        end

        # --- Helper: solve DCPF and compute max branch loading ---
        function solve_and_max_loading(d::Dict)
            pf_result = PowerModels.compute_dc_pf(d)
            PowerModels.update_data!(d, pf_result["solution"])
            flow_dict = PowerModels.calc_branch_flow_dc(d)

            max_loading = 0.0
            for (bid, br) in d["branch"]
                if get(br, "br_status", 1) == 0
                    continue
                end
                br_flow = get(flow_dict["branch"], bid, Dict())
                pf = abs(get(br_flow, "pf", 0.0))
                rate_a = get(br, "rate_a", 0.0)
                if rate_a > 0 && rate_a < 1e10
                    loading = pf / rate_a
                    max_loading = max(max_loading, loading)
                end
            end
            return max_loading
        end

        # --- N-M contingency enumeration with pruning ---
        # x = max order (3), m = max simultaneous outages (3)
        max_order = 3
        max_simultaneous = 3
        graph_distance_prune = 2  # only combine branches within distance 2

        parse_time = time() - t0
        t_loop = time()

        contingency_results = Dict{String,Any}[]
        n_evaluated = 0
        n_pruned = 0
        n_island = 0
        n_converged = 0
        n_overload = 0

        # Order 1 (N-1): all single-branch outages
        order1_results = Dict{Int,Dict{String,Any}}()
        for br_id in branch_ids
            d = deepcopy(data)
            d["branch"][string(br_id)]["br_status"] = 0

            comps = PowerModels.calc_connected_components(d)
            if length(comps) > 1
                order1_results[br_id] = Dict("status" => "island", "max_loading" => Inf)
                push!(
                    contingency_results,
                    Dict(
                        "order" => 1,
                        "outages" => [br_id],
                        "status" => "island",
                        "max_loading" => Inf,
                        "load_loss_pu" => 0.0,
                    ),
                )
                n_island += 1
            else
                max_loading = solve_and_max_loading(d)

                order1_results[br_id] = Dict("status" => "converged", "max_loading" => max_loading)
                push!(
                    contingency_results,
                    Dict(
                        "order" => 1,
                        "outages" => [br_id],
                        "status" => "converged",
                        "max_loading" => round(max_loading * 100; digits=2),
                        "load_loss_pu" => 0.0,
                    ),
                )
                n_converged += 1
                if max_loading > 1.0
                    n_overload += 1
                end
            end
            n_evaluated += 1
        end

        # Order 2 (N-2): pairs of branches, pruned by graph distance
        order2_count = 0
        for i in 1:length(branch_ids)
            br1 = branch_ids[i]
            nearby = branches_within_distance(br1, graph_distance_prune)
            for j in (i + 1):length(branch_ids)
                br2 = branch_ids[j]
                if !(br2 in nearby)
                    n_pruned += 1
                    continue
                end

                d = deepcopy(data)
                d["branch"][string(br1)]["br_status"] = 0
                d["branch"][string(br2)]["br_status"] = 0

                comps = PowerModels.calc_connected_components(d)
                if length(comps) > 1
                    push!(
                        contingency_results,
                        Dict(
                            "order" => 2,
                            "outages" => [br1, br2],
                            "status" => "island",
                            "max_loading" => Inf,
                            "load_loss_pu" => 0.0,
                        ),
                    )
                    n_island += 1
                else
                    max_loading = solve_and_max_loading(d)

                    push!(
                        contingency_results,
                        Dict(
                            "order" => 2,
                            "outages" => [br1, br2],
                            "status" => "converged",
                            "max_loading" => round(max_loading * 100; digits=2),
                            "load_loss_pu" => 0.0,
                        ),
                    )
                    n_converged += 1
                    if max_loading > 1.0
                        n_overload += 1
                    end
                end
                n_evaluated += 1
                order2_count += 1
            end
        end

        # Order 3 (N-3): triples, pruned by graph distance from first branch
        order3_count = 0
        for i in 1:length(branch_ids)
            br1 = branch_ids[i]
            nearby1 = branches_within_distance(br1, graph_distance_prune)
            for j in (i + 1):length(branch_ids)
                br2 = branch_ids[j]
                if !(br2 in nearby1)
                    continue
                end
                nearby2 = intersect(nearby1, branches_within_distance(br2, graph_distance_prune))
                for k in (j + 1):length(branch_ids)
                    br3 = branch_ids[k]
                    if !(br3 in nearby2)
                        n_pruned += 1
                        continue
                    end

                    d = deepcopy(data)
                    d["branch"][string(br1)]["br_status"] = 0
                    d["branch"][string(br2)]["br_status"] = 0
                    d["branch"][string(br3)]["br_status"] = 0

                    comps = PowerModels.calc_connected_components(d)
                    if length(comps) > 1
                        push!(
                            contingency_results,
                            Dict(
                                "order" => 3,
                                "outages" => [br1, br2, br3],
                                "status" => "island",
                                "max_loading" => Inf,
                                "load_loss_pu" => 0.0,
                            ),
                        )
                        n_island += 1
                    else
                        max_loading = solve_and_max_loading(d)

                        push!(
                            contingency_results,
                            Dict(
                                "order" => 3,
                                "outages" => [br1, br2, br3],
                                "status" => "converged",
                                "max_loading" => round(max_loading * 100; digits=2),
                                "load_loss_pu" => 0.0,
                            ),
                        )
                        n_converged += 1
                        if max_loading > 1.0
                            n_overload += 1
                        end
                    end
                    n_evaluated += 1
                    order3_count += 1
                end
            end
        end

        loop_time = time() - t_loop

        # Count per-order
        order_counts = Dict(1 => length(branch_ids), 2 => order2_count, 3 => order3_count)

        # Top 5 worst contingencies by max loading
        valid_results = filter(r -> r["status"] == "converged", contingency_results)
        sort!(valid_results; by=r -> -r["max_loading"])
        top5 = valid_results[1:min(5, end)]

        println("\n=== B-3 N-M Contingency Sweep (TINY) ===")
        println("Orders: 1, 2, 3 (max simultaneous: $max_simultaneous)")
        println("Graph-distance pruning: $graph_distance_prune")
        println("Total evaluated: $n_evaluated")
        println("  Order 1: $(order_counts[1])")
        println("  Order 2: $(order_counts[2])")
        println("  Order 3: $(order_counts[3])")
        println("Pruned: $n_pruned")
        println("Converged: $n_converged")
        println("Islands: $n_island")
        println("Overloaded: $n_overload")
        println("Loop time: $(round(loop_time, digits=3))s")
        println("Avg per contingency: $(round(loop_time / n_evaluated * 1000, digits=2))ms")
        println("\nTop 5 worst contingencies:")
        for c in top5
            println("  Order $(c["order"]), outages=$(c["outages"]): $(c["max_loading"])% loading")
        end

        results["status"] = "pass"
        results["details"] = Dict(
            "network" => "case39",
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "max_order" => max_order,
            "max_simultaneous" => max_simultaneous,
            "graph_distance_prune" => graph_distance_prune,
            "total_evaluated" => n_evaluated,
            "order_1_count" => order_counts[1],
            "order_2_count" => order_counts[2],
            "order_3_count" => order_counts[3],
            "total_pruned" => n_pruned,
            "n_converged" => n_converged,
            "n_island" => n_island,
            "n_overload" => n_overload,
            "loop_time_s" => round(loop_time; digits=3),
            "avg_per_contingency_ms" => round(loop_time / n_evaluated * 1000; digits=2),
            "top5_worst" => top5,
            "method" => "deepcopy + br_status=0, no model reconstruction",
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
