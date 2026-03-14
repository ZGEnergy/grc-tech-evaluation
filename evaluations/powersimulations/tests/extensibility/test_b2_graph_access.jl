#=
Test B-2: Graph Access (BFS to depth 3 from chosen bus)

Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: Works via native graph primitives or clean export to Graphs.jl.
Tool: PowerSimulations.jl v0.30.2 (PowerNetworkMatrices.jl v0.12.1)
=#

using PowerSystems
using PowerNetworkMatrices
using JSON
using Logging

# Suppress verbose logging
global_logger(ConsoleLogger(stderr, Logging.Error))

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024  # kB to MB
        end
    end
    return nothing
end

"""
BFS from a start bus to a given depth, using an adjacency structure.
Returns Dict mapping depth => list of bus numbers at that depth.
"""
function bfs_from_bus(adj::Dict{Int,Vector{Int}}, start_bus::Int, max_depth::Int)
    visited = Set{Int}([start_bus])
    current_level = Set{Int}([start_bus])
    depth_map = Dict{Int,Vector{Int}}()
    depth_map[0] = [start_bus]

    for d in 1:max_depth
        next_level = Set{Int}()
        for bus in current_level
            for neighbor in get(adj, bus, Int[])
                if !(neighbor in visited)
                    push!(next_level, neighbor)
                    push!(visited, neighbor)
                end
            end
        end
        depth_map[d] = sort(collect(next_level))
        current_level = next_level
        if isempty(next_level)
            break
        end
    end

    return depth_map, visited
end

function run(
    network_file::String="/workspace/data/networks/case39.m";
    timeseries_dir::Union{String,Nothing}=nothing,
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    try
        # 1. Load system
        sys = System(network_file)

        # Warm-up: construct adjacency matrix once to trigger JIT
        _ = AdjacencyMatrix(sys)

        # 2. Timed run
        t0 = time()

        # Get AdjacencyMatrix from PowerNetworkMatrices
        adj_matrix = AdjacencyMatrix(sys)

        # Inspect type and axes
        results["details"]["adj_matrix_type"] = string(typeof(adj_matrix))
        adj_ax = axes(adj_matrix)
        bus_ids = collect(adj_ax[1])  # These are Int bus numbers
        results["details"]["bus_ids_sample"] = bus_ids[1:min(5, length(bus_ids))]
        results["details"]["num_buses"] = length(bus_ids)
        results["details"]["axes_types"] = [string(typeof(adj_ax[1])), string(typeof(adj_ax[2]))]

        # Build adjacency dict from the matrix
        # The AdjacencyMatrix A[i,j] is nonzero if buses i and j are connected
        adj_dict = Dict{Int,Vector{Int}}()
        for bus1 in bus_ids
            neighbors = Int[]
            for bus2 in bus_ids
                if bus1 == bus2
                    ;
                    continue;
                end
                val = adj_matrix[bus1, bus2]
                if abs(val) > 1e-10
                    push!(neighbors, bus2)
                end
            end
            adj_dict[bus1] = sort(neighbors)
        end

        # Count edges
        total_edges = sum(length(v) for v in values(adj_dict)) / 2
        results["details"]["total_edges"] = Int(total_edges)

        # Also get IncidenceMatrix for documentation
        inc_matrix = IncidenceMatrix(sys)
        results["details"]["incidence_matrix_type"] = string(typeof(inc_matrix))
        inc_ax = axes(inc_matrix)
        results["details"]["incidence_axes"] = [length(inc_ax[1]), length(inc_ax[2])]

        # 3. BFS from bus 16 (center of network, well-connected)
        start_bus = 16
        max_depth = 3

        # Verify start bus exists
        if !haskey(adj_dict, start_bus)
            start_bus = first(keys(adj_dict))
            results["details"]["start_bus_fallback"] = true
        end

        depth_map, visited = bfs_from_bus(adj_dict, start_bus, max_depth)

        elapsed = time() - t0

        results["wall_clock_seconds"] = elapsed
        results["details"]["peak_memory_mb"] = peak_rss_mb()

        # Record BFS results
        bfs_results = Dict{String,Any}()
        for d in 0:max_depth
            buses = get(depth_map, d, Int[])
            bfs_results["depth_$(d)"] = Dict("count" => length(buses), "buses" => buses)
        end
        results["details"]["bfs_start_bus"] = start_bus
        results["details"]["bfs_max_depth"] = max_depth
        results["details"]["bfs_results"] = bfs_results
        results["details"]["total_reachable"] = length(visited)

        # Neighbors of start bus (depth 1)
        neighbors = get(adj_dict, start_bus, Int[])
        results["details"]["start_bus_neighbors"] = neighbors
        results["details"]["start_bus_degree"] = length(neighbors)

        # Also document available PowerSystems topology access
        # (PowerSystems has get_components which can enumerate branches and their endpoints)
        n_lines = length(collect(get_components(Line, sys)))
        n_xfmr2w = length(collect(get_components(Transformer2W, sys)))
        n_taptx = length(collect(get_components(TapTransformer, sys)))
        results["details"]["topology_via_powersystems"] = Dict(
            "n_lines" => n_lines,
            "n_transformer2w" => n_xfmr2w,
            "n_tap_transformer" => n_taptx,
            "total_branches" => n_lines + n_xfmr2w + n_taptx,
        )

        # Validate results
        has_neighbors = length(neighbors) > 0
        reached_depth_3 = haskey(depth_map, 3) && !isempty(depth_map[3])
        nontrivial_bfs = length(visited) > 1
        adj_matrix_obtained = length(bus_ids) > 0

        results["details"]["pass_checks"] = Dict(
            "adj_matrix_obtained" => adj_matrix_obtained,
            "has_neighbors" => has_neighbors,
            "reached_depth_3" => reached_depth_3,
            "nontrivial_bfs" => nontrivial_bfs,
            "total_reachable_from_bfs" => length(visited),
        )

        # Document workaround: no native graph primitives, manual BFS required
        push!(
            results["workarounds"],
            "PowerNetworkMatrices.jl provides AdjacencyMatrix and IncidenceMatrix as " *
            "KeyedArray-like sparse structures indexed by bus number, but no graph traversal " *
            "primitives (no BFS, DFS, shortest_path). Manual BFS implemented by iterating " *
            "the adjacency matrix entries. No Graphs.jl dependency in the PSI ecosystem. " *
            "Constructing a Graphs.jl SimpleGraph from the adjacency matrix would be " *
            "straightforward (~5 lines) but requires adding Graphs.jl as an external dependency.",
        )

        if adj_matrix_obtained && has_neighbors && nontrivial_bfs
            results["status"] = "qualified_pass"
        else
            push!(results["errors"], "BFS from adjacency matrix failed or produced trivial results")
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end
