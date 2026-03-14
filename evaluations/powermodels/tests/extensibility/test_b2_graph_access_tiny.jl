#=
Test B-2: Graph Access — BFS to depth 3 from a chosen bus, return subgraph

Dimension: extensibility
Network: TINY (IEEE 39-bus, New England)
Pass condition: Works via native graph primitives or clean, documented export
  to NetworkX/Graphs.jl.
Tool: PowerModels.jl v0.21.5

PowerModels has no native Graphs.jl integration — use branch f_bus/t_bus topology.
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
        println("Network: $n_buses buses, $n_branches branches")

        # --- Build adjacency from data["branch"] f_bus/t_bus ---
        bus_ids = [parse(Int, id) for id in keys(data["bus"])]
        branch_ids = [parse(Int, id) for id in keys(data["branch"])]

        adjacency = Dict{Int,Vector{Tuple{Int,Int}}}()
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
        end

        # --- BFS from seed bus to depth 3 ---
        seed_bus = 16
        max_depth = 3

        visited = Set{Int}([seed_bus])
        frontier = [seed_bus]
        depth_buses = Dict{Int,Vector{Int}}()
        subgraph_branches = Set{Int}()

        for depth in 1:max_depth
            next_frontier = Int[]
            depth_buses[depth] = Int[]
            for bus in frontier
                for (neighbor, br_id) in adjacency[bus]
                    if !(neighbor in visited)
                        push!(visited, neighbor)
                        push!(next_frontier, neighbor)
                        push!(depth_buses[depth], neighbor)
                    end
                    push!(subgraph_branches, br_id)
                end
            end
            sort!(depth_buses[depth])
            frontier = next_frontier
        end

        # Filter subgraph branches to only those with both endpoints in visited set
        subgraph_br_filtered = Set{Int}()
        for br_id in subgraph_branches
            br = data["branch"][string(br_id)]
            if br["f_bus"] in visited && br["t_bus"] in visited
                push!(subgraph_br_filtered, br_id)
            end
        end

        # Connected components check
        components = PowerModels.calc_connected_components(data)
        n_components = length(components)

        seed_degree = length(adjacency[seed_bus])

        println("\nBFS from bus $seed_bus (degree $seed_degree) to depth $max_depth:")
        for d in 1:max_depth
            println("  Depth $d: $(depth_buses[d])")
        end
        println("  Subgraph: $(length(visited)) buses, $(length(subgraph_br_filtered)) branches")
        println("  Network connected: $(n_components == 1) ($n_components components)")

        results["status"] = "qualified_pass"
        push!(
            results["workarounds"],
            "Manual adjacency construction from data[\"branch\"] f_bus/t_bus fields (~12 LOC). " *
            "PowerModels has no Graphs.jl integration and no native BFS function.",
        )

        results["details"] = Dict(
            "network_file" => network_file,
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "seed_bus" => seed_bus,
            "seed_degree" => seed_degree,
            "bfs_depth" => max_depth,
            "depth_1_buses" => depth_buses[1],
            "depth_2_buses" => depth_buses[2],
            "depth_3_buses" => depth_buses[3],
            "subgraph_buses" => length(visited),
            "subgraph_branches" => length(subgraph_br_filtered),
            "n_components" => n_components,
            "graphs_jl_available" => false,
            "loc" => 12,
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
    println("workarounds: $(result["workarounds"])")
    for (k, v) in result["details"]
        println("  $k: $v")
    end
end
