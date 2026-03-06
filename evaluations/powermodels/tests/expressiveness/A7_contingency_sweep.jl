#= Test A-7: N-M contingency sweep with escalating order and pruning on TINY (case39)
   Parameters: x=3 (graph distance), m=3 (max contingency order)
   Use DCPF for contingency cases, remove branches, collect load loss.
=#
using PowerModels, JSON

# Simple combinations generator
function combinations_iter(items::Vector{T}, k::Int) where {T}
    n = length(items)
    if k == 0 || k > n
        return Vector{T}[]
    end
    if k == 1
        return [[item] for item in items]
    end
    result = Vector{T}[]
    for i in 1:(n - k + 1)
        for rest in combinations_iter(items[(i + 1):end], k-1)
            push!(result, vcat([items[i]], rest))
        end
    end
    return result
end

function run(network_file::String="/workspace/data/networks/case39.m")
    results = Dict{String,Any}(
        "test_id" => "A-7",
        "test_name" => "contingency_sweep",
        "network" => "case39",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        data = PowerModels.parse_file(network_file)
        nbus = length(data["bus"])
        nbranch = length(data["branch"])
        results["details"]["num_buses"] = nbus
        results["details"]["num_branches"] = nbranch

        x = 3  # graph distance for pruning
        m = 3  # max contingency order

        # Build adjacency from branches
        bus_ids = sort(parse.(Int, collect(keys(data["bus"]))))
        adj = Dict{Int,Set{Int}}()
        for bid in bus_ids
            adj[bid] = Set{Int}()
        end
        for (br_id, br) in data["branch"]
            if br["br_status"] == 1
                push!(adj[br["f_bus"]], br["t_bus"])
                push!(adj[br["t_bus"]], br["f_bus"])
            end
        end

        # Choose focus bus with most connections
        focus_bus = bus_ids[1]
        max_conn = 0
        for bid in bus_ids
            c = length(adj[bid])
            if c > max_conn
                max_conn = c
                focus_bus = bid
            end
        end
        results["details"]["focus_bus"] = focus_bus

        # BFS to find buses within distance x
        visited = Dict{Int,Int}()
        queue = [(focus_bus, 0)]
        visited[focus_bus] = 0
        while !isempty(queue)
            (node, d) = popfirst!(queue)
            if d < x
                for neighbor in adj[node]
                    if !haskey(visited, neighbor)
                        visited[neighbor] = d + 1
                        push!(queue, (neighbor, d + 1))
                    end
                end
            end
        end
        nearby_buses = Set(keys(visited))
        results["details"]["buses_within_distance"] = length(nearby_buses)

        # Find branches within pruned scope
        candidate_branches = String[]
        for (br_id, br) in data["branch"]
            if br["br_status"] == 1
                if br["f_bus"] in nearby_buses || br["t_bus"] in nearby_buses
                    push!(candidate_branches, br_id)
                end
            end
        end
        sort!(candidate_branches)
        results["details"]["candidate_branches"] = length(candidate_branches)

        # Check network connectivity
        function is_connected(data_mod)
            active_adj = Dict{Int,Set{Int}}()
            for bid in bus_ids
                active_adj[bid] = Set{Int}()
            end
            for (_, br) in data_mod["branch"]
                if br["br_status"] == 1
                    push!(active_adj[br["f_bus"]], br["t_bus"])
                    push!(active_adj[br["t_bus"]], br["f_bus"])
                end
            end
            vis = Set{Int}()
            q = [bus_ids[1]]
            push!(vis, bus_ids[1])
            while !isempty(q)
                nd = popfirst!(q)
                for nb in active_adj[nd]
                    if !(nb in vis)
                        push!(vis, nb)
                        push!(q, nb)
                    end
                end
            end
            return length(vis) == nbus
        end

        # Evaluate a contingency
        function eval_contingency(removed::Vector{String})
            data_mod = deepcopy(data)
            for br_id in removed
                data_mod["branch"][br_id]["br_status"] = 0
            end
            if !is_connected(data_mod)
                return (converged=false, islanded=true)
            end
            try
                PowerModels.compute_dc_pf(data_mod)
                return (converged=true, islanded=false)
            catch
                return (converged=false, islanded=false)
            end
        end

        # Perform N-1, N-2, N-3 sweep
        total_contingencies = 0
        contingency_summary = Dict{String,Any}()

        for order in 1:m
            combos = combinations_iter(candidate_branches, order)
            n_total = length(combos)
            n_converged = 0
            n_islanded = 0
            worst_examples = String[]

            for combo in combos
                total_contingencies += 1
                cr = eval_contingency(combo)
                if cr.converged
                    n_converged += 1
                end
                if cr.islanded
                    n_islanded += 1
                    if length(worst_examples) < 3
                        push!(worst_examples, join(combo, ","))
                    end
                end
            end

            contingency_summary["N-$(order)"] = Dict{String,Any}(
                "total" => n_total,
                "converged" => n_converged,
                "islanded" => n_islanded,
                "example_failures" => worst_examples,
            )
        end

        results["details"]["contingency_results"] = contingency_summary
        results["details"]["total_contingencies_evaluated"] = total_contingencies
        results["details"]["graph_distance_x"] = x
        results["details"]["max_contingency_order_m"] = m
        results["details"]["method"] = "Manual branch removal + compute_dc_pf per contingency (data modification only, no model reconstruction)"

        results["status"] = "pass"
        push!(
            results["workarounds"],
            "PowerModels has no built-in contingency sweep. Required manual implementation: toggle br_status in data dict + recompute DC PF per contingency. The native compute_dc_pf avoids JuMP model reconstruction overhead.",
        )

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
