#=
Test B-2: BFS graph traversal to depth 3 from a chosen bus
Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: Works via native graph primitives or clean documented export to Graphs.jl.
Tool: PowerModels.jl v0.21.5
Solver: N/A

Approach: PowerModels has no native Graphs.jl integration. Build adjacency from
branch f_bus/t_bus data and perform BFS manually. Return all buses and branches
within depth-3 subgraph.
=#

using PowerModels, JSON

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
        PowerModels.parse_file(network_file)
    catch
        ;
    end

    t0 = time()
    try
        data = PowerModels.parse_file(network_file)

        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_branches"] = length(data["branch"])

        # ---- Step 1: Build adjacency from branch data ----
        bus_ids = sort(parse.(Int, collect(keys(data["bus"]))))
        branch_ids = sort(parse.(Int, collect(keys(data["branch"]))))

        # adjacency: bus_id -> [(neighbor_bus, branch_id), ...]
        adjacency = Dict{Int,Vector{Tuple{Int,Int}}}()
        for b in bus_ids
            adjacency[b] = Tuple{Int,Int}[]
        end

        branch_endpoints = Dict{Int,Tuple{Int,Int}}()
        for br_id in branch_ids
            br = data["branch"][string(br_id)]
            f = br["f_bus"]
            t = br["t_bus"]
            branch_endpoints[br_id] = (f, t)
            push!(adjacency[f], (t, br_id))
            push!(adjacency[t], (f, br_id))
        end

        results["details"]["adjacency_source"] = "branch f_bus/t_bus (manual construction)"
        results["details"]["native_graph_api"] = false

        # ---- Step 2: Choose a seed bus and run BFS to depth 3 ----
        # Choose bus 16 (interior bus with good connectivity)
        seed_bus = 16
        max_depth = 3

        # Verify seed bus exists
        if !haskey(adjacency, seed_bus)
            push!(results["errors"], "Seed bus $seed_bus not found in network")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        results["details"]["seed_bus"] = seed_bus
        results["details"]["bfs_max_depth"] = max_depth
        results["details"]["seed_bus_degree"] = length(adjacency[seed_bus])

        # BFS
        visited = Dict{Int,Int}()  # bus_id -> depth
        visited[seed_bus] = 0
        queue = [seed_bus]
        buses_by_depth = Dict{Int,Vector{Int}}()
        buses_by_depth[0] = [seed_bus]

        while !isempty(queue)
            current = popfirst!(queue)
            d = visited[current]
            if d >= max_depth
                continue
            end
            for (neighbor, _) in adjacency[current]
                if !haskey(visited, neighbor)
                    visited[neighbor] = d + 1
                    push!(queue, neighbor)
                    if !haskey(buses_by_depth, d + 1)
                        buses_by_depth[d + 1] = Int[]
                    end
                    push!(buses_by_depth[d + 1], neighbor)
                end
            end
        end

        # Collect all buses in subgraph
        subgraph_buses = sort(collect(keys(visited)))
        results["details"]["subgraph_buses"] = subgraph_buses
        results["details"]["subgraph_bus_count"] = length(subgraph_buses)

        # Report buses by depth
        for depth in 0:max_depth
            if haskey(buses_by_depth, depth)
                results["details"]["buses_at_depth_$depth"] = sort(buses_by_depth[depth])
            end
        end

        # ---- Step 3: Collect branches within subgraph ----
        # A branch is in the subgraph if BOTH endpoints are visited buses
        subgraph_bus_set = Set(subgraph_buses)
        subgraph_branches = Int[]
        subgraph_branch_details = Dict{String,Dict{String,Any}}()

        for br_id in branch_ids
            f, t = branch_endpoints[br_id]
            if f in subgraph_bus_set && t in subgraph_bus_set
                push!(subgraph_branches, br_id)
                subgraph_branch_details[string(br_id)] = Dict(
                    "f_bus" => f, "t_bus" => t, "f_depth" => visited[f], "t_depth" => visited[t]
                )
            end
        end
        sort!(subgraph_branches)

        results["details"]["subgraph_branches"] = subgraph_branches
        results["details"]["subgraph_branch_count"] = length(subgraph_branches)
        results["details"]["subgraph_branch_details"] = subgraph_branch_details

        # ---- Step 4: Summary statistics ----
        results["details"]["total_buses_in_network"] = length(bus_ids)
        results["details"]["total_branches_in_network"] = length(branch_ids)
        results["details"]["pct_buses_in_subgraph"] = round(
            100.0 * length(subgraph_buses) / length(bus_ids); digits=1
        )
        results["details"]["pct_branches_in_subgraph"] = round(
            100.0 * length(subgraph_branches) / length(branch_ids); digits=1
        )

        # Verify we got a reasonable subgraph
        if length(subgraph_buses) < 2
            push!(results["errors"], "Subgraph too small: only $(length(subgraph_buses)) bus(es)")
            results["wall_clock_seconds"] = time() - t0
            return results
        end

        push!(
            results["workarounds"],
            "PowerModels has NO native graph API or Graphs.jl integration. " *
            "Adjacency must be built manually from branch f_bus/t_bus data (~15 lines). " *
            "BFS is a standard algorithm easily implemented in Julia. " *
            "PowerModelsAnalytics.jl would provide Graphs.jl bridge but is not installed.",
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
