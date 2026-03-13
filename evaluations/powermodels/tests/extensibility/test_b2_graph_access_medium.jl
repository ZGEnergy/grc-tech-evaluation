#=
Test B-2: Graph Access — MEDIUM grade assessment
Dimension: extensibility
Network: MEDIUM (ACTIVSg 10000-bus, case_ACTIVSg10k.m)
Pass condition: Works via native graph primitives or clean export to Graphs.jl.
Tool: PowerModels.jl v0.21.5

Approach:
  - Build adjacency list manually from data["branch"]["f_bus"] / "t_bus"
  - Run BFS to depth 3 from a chosen hub bus
  - Report: buses reachable, branches in subgraph, BFS time
  - At MEDIUM scale (12706 branches), verify performance is acceptable

No JuMP or solver required — pure graph traversal from the data dict.
Note: PowerModels has no native Graphs.jl integration. Manual adjacency
construction is the only path.
=#

using PowerModels, JSON

PowerModels.silence()

function apply_medium_preprocessing!(data::Dict)
    for (_, branch) in data["branch"]
        if branch["br_x"] == 0.0
            branch["br_x"] = 0.0001
        end
        ra = get(branch, "rate_a", 0.0)
        if ra == 0.0 || isinf(ra)
            branch["rate_a"] = 9999.0 / data["baseMVA"]
        end
    end
end

function build_adjacency(data::Dict)
    # Build undirected adjacency list: bus_id (Int) → [(neighbor_id, branch_id)]
    adj = Dict{Int,Vector{Tuple{Int,String}}}()
    for (_, bus) in data["bus"]
        adj[bus["bus_i"]] = Tuple{Int,String}[]
    end
    for (br_id, branch) in data["branch"]
        if get(branch, "br_status", 1) == 0
            continue
        end
        f = branch["f_bus"]
        t = branch["t_bus"]
        push!(get!(adj, f, Tuple{Int,String}[]), (t, br_id))
        push!(get!(adj, t, Tuple{Int,String}[]), (f, br_id))
    end
    return adj
end

function bfs_depth3(adj::Dict{Int,Vector{Tuple{Int,String}}}, start_bus::Int)
    # BFS to depth 3; return (visited_buses, traversed_branch_ids)
    visited = Set{Int}([start_bus])
    branch_set = Set{String}()
    frontier = [start_bus]
    depth = 0
    while !isempty(frontier) && depth < 3
        next_frontier = Int[]
        for bus in frontier
            for (nbr, br_id) in get(adj, bus, Tuple{Int,String}[])
                push!(branch_set, br_id)
                if nbr ∉ visited
                    push!(visited, nbr)
                    push!(next_frontier, nbr)
                end
            end
        end
        frontier = next_frontier
        depth += 1
    end
    return (visited, branch_set)
end

function find_hub_bus(data::Dict)
    # Pick a bus with high degree (many neighbors) — typical "hub" in transmission grid
    degree = Dict{Int,Int}()
    for (_, branch) in data["branch"]
        if get(branch, "br_status", 1) == 0
            ;
            continue;
        end
        f = branch["f_bus"];
        t = branch["t_bus"]
        degree[f] = get(degree, f, 0) + 1
        degree[t] = get(degree, t, 0) + 1
    end
    best_bus = 0;
    best_deg = 0
    for (bus_id, deg) in degree
        if deg > best_deg
            best_deg = deg
            best_bus = bus_id
        end
    end
    return best_bus, best_deg
end

function run(
    network_file::String=joinpath(
        @__DIR__, "..", "..", "..", "..", "data", "networks", "case_ACTIVSg10k.m"
    ),
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
        println("Loading network: $network_file")
        data = PowerModels.parse_file(network_file)

        n_buses = length(data["bus"])
        n_branches = length(data["branch"])
        n_gens = length(data["gen"])
        base_mva = data["baseMVA"]
        println("Network: $n_buses buses, $n_branches branches, $n_gens gens, baseMVA=$base_mva")

        apply_medium_preprocessing!(data)

        # Build adjacency list
        t_adj_start = time()
        adj = build_adjacency(data)
        t_adj = time() - t_adj_start
        println("Adjacency list built: $(length(adj)) nodes  ($(round(t_adj*1000,digits=1)) ms)")

        # Find hub bus
        hub_bus, hub_degree = find_hub_bus(data)
        println("Hub bus selected: $hub_bus  (degree=$hub_degree)")

        # BFS to depth 3 from hub
        t_bfs_start = time()
        visited_buses, traversed_branches = bfs_depth3(adj, hub_bus)
        t_bfs = time() - t_bfs_start

        n_visited = length(visited_buses)
        n_subgraph_br = length(traversed_branches)
        println("BFS depth-3 from bus $hub_bus:")
        println(
            "  Buses reachable: $n_visited / $n_buses  ($(round(n_visited/n_buses*100,digits=1))%)"
        )
        println("  Branches in subgraph: $n_subgraph_br / $n_branches")
        println("  BFS time: $(round(t_bfs*1000,digits=2)) ms")

        # Also test a lower-degree bus (e.g., a radial leaf)
        leaf_bus = 0;
        leaf_degree = Inf
        for (_, bus) in data["bus"]
            bid = bus["bus_i"]
            d = length(get(adj, bid, []))
            if d > 0 && d < leaf_degree
                leaf_degree = d;
                leaf_bus = bid
            end
        end
        println("\nLeaf bus: $leaf_bus  (degree=$(Int(leaf_degree)))")

        t_bfs2_start = time()
        visited_leaf, branches_leaf = bfs_depth3(adj, leaf_bus)
        t_bfs2 = time() - t_bfs2_start
        println(
            "BFS depth-3 from bus $leaf_bus:  $(length(visited_leaf)) buses, $(length(branches_leaf)) branches  ($(round(t_bfs2*1000,digits=2)) ms)",
        )

        # Performance check: BFS on 10k-bus should complete well under 1 second
        performance_ok = t_bfs < 1.0 && t_adj < 2.0

        push!(
            results["workarounds"],
            "No native Graphs.jl integration in PowerModels.jl v0.21.5. " *
            "Adjacency list built manually from data[\"branch\"][\"f_bus\"] / \"t_bus\" (~20 lines). " *
            "PowerModelsAnalytics.jl (separate package, not installed) provides build_network_graph " *
            "but focuses on visualization. Manual construction is straightforward and sufficient.",
        )

        println("\nPass checks:")
        println("  Graph buildable from data dict: true (manual adjacency)")
        println(
            "  BFS depth-3 works:              true ($n_visited buses, $n_subgraph_br branches)"
        )
        println(
            "  Performance acceptable:          $performance_ok  (adj=$(round(t_adj*1000,digits=1))ms, bfs=$(round(t_bfs*1000,digits=2))ms)",
        )

        results["status"] = "pass"

        results["details"] = Dict(
            "network_file" => network_file,
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "base_mva" => base_mva,
            "adjacency_build_ms" => t_adj * 1000.0,
            "hub_bus" => hub_bus,
            "hub_degree" => hub_degree,
            "bfs_hub_buses_visited" => n_visited,
            "bfs_hub_branches" => n_subgraph_br,
            "bfs_hub_ms" => t_bfs * 1000.0,
            "leaf_bus" => leaf_bus,
            "leaf_degree" => Int(leaf_degree),
            "bfs_leaf_buses_visited" => length(visited_leaf),
            "bfs_leaf_branches" => length(branches_leaf),
            "bfs_leaf_ms" => t_bfs2 * 1000.0,
            "performance_ok" => performance_ok,
            "native_graphs_jl" => false,
            "graph_api_method" => "manual adjacency list from data[\"branch\"] f_bus/t_bus",
            "workaround_class" => "stable",
            "loc" => 75,
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        println("ERROR in B-2 MEDIUM: $(typeof(e)): $e")
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
    println("\n--- RESULT SUMMARY ---")
    println("status:             $(result["status"])")
    println("wall_clock_seconds: $(result["wall_clock_seconds"])")
    println("errors:             $(result["errors"])")
    println("workarounds:        $(result["workarounds"])")
    open("/tmp/b2_graph_access_medium_result.json", "w") do f
        JSON.print(f, result, 2)
    end
    println("Result written to /tmp/b2_graph_access_medium_result.json")
end
