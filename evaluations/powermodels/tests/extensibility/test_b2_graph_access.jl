
#= Test B-2: Graph Access — BFS to depth 3 from a chosen bus =#

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

        # Build adjacency list from branch data (PowerModels has NO Graphs.jl integration)
        adjacency = Dict{Int,Set{Int}}()
        for (i, bus) in data["bus"]
            adjacency[bus["index"]] = Set{Int}()
        end
        for (i, branch) in data["branch"]
            if branch["br_status"] != 0
                f = branch["f_bus"]
                t = branch["t_bus"]
                push!(adjacency[f], t)
                push!(adjacency[t], f)
            end
        end

        # Also build branch lookup for subgraph extraction
        branch_lookup = Dict{Tuple{Int,Int},Vector{Int}}()
        for (i, branch) in data["branch"]
            if branch["br_status"] != 0
                f = branch["f_bus"]
                t = branch["t_bus"]
                key = (min(f, t), max(f, t))
                if !haskey(branch_lookup, key)
                    branch_lookup[key] = Int[]
                end
                push!(branch_lookup[key], branch["index"])
            end
        end

        # Choose start bus: pick bus 1 (exists in case39)
        start_bus = 1
        max_depth = 3

        # BFS
        visited = Set{Int}([start_bus])
        frontier = Set{Int}([start_bus])
        depth_map = Dict{Int,Int}(start_bus => 0)

        for d in 1:max_depth
            next_frontier = Set{Int}()
            for bus in frontier
                for neighbor in adjacency[bus]
                    if !(neighbor in visited)
                        push!(visited, neighbor)
                        push!(next_frontier, neighbor)
                        depth_map[neighbor] = d
                    end
                end
            end
            frontier = next_frontier
        end

        # Collect branches in subgraph
        subgraph_branches = Set{Int}()
        for bus_a in visited
            for bus_b in adjacency[bus_a]
                if bus_b in visited
                    key = (min(bus_a, bus_b), max(bus_a, bus_b))
                    if haskey(branch_lookup, key)
                        for br_idx in branch_lookup[key]
                            push!(subgraph_branches, br_idx)
                        end
                    end
                end
            end
        end

        results["details"] = Dict(
            "start_bus" => start_bus,
            "max_depth" => max_depth,
            "buses_found" => length(visited),
            "bus_ids" => sort(collect(visited)),
            "branches_found" => length(subgraph_branches),
            "branch_ids" => sort(collect(subgraph_branches)),
            "total_buses" => length(data["bus"]),
            "total_branches" => length(data["branch"]),
            "approach" => "Manual adjacency list from data[\"branch\"], no Graphs.jl integration",
            "loc_for_adjacency_build" => 15,
            "loc_for_bfs" => 15,
            "loc_total" => 30,
        )
        push!(
            results["workarounds"],
            "PowerModels has no Graphs.jl integration; must manually build adjacency from data[\"branch\"]",
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
