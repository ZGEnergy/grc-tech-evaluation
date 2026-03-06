#= Test C-5: N-M contingency sweep (x=5, m=4) at MEDIUM (10000 buses)
   Graph-distance pruning from a chosen bus.
=#
using PowerModels, JSON
PowerModels.silence()

function preprocess_data!(data)
    for (i, gen) in data["gen"]
        if !haskey(gen, "cost") || isempty(get(gen, "cost", []))
            gen["model"] = 2
            gen["ncost"] = 2
            gen["cost"] = [20.0, 0.0]
        end
    end
    for (i, br) in data["branch"]
        if get(br, "rate_a", 0.0) == 0.0
            br["rate_a"] = 9999.0
        end
    end
end

# Combinations generator
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

function run(network_file::String="/workspace/data/networks/case_ACTIVSg10k.m")
    results = Dict{String,Any}(
        "test_id" => "C-5",
        "test_name" => "contingency_sweep_scale",
        "network" => "MEDIUM",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )
    t0 = time()
    try
        data = PowerModels.parse_file(network_file)
        preprocess_data!(data)

        nbus = length(data["bus"])
        nbranch = length(data["branch"])
        results["details"]["num_buses"] = nbus
        results["details"]["num_branches"] = nbranch

        x = 5  # graph distance for pruning
        m = 4  # max contingency order

        # Build adjacency from branches
        bus_ids = sort(parse.(Int, collect(keys(data["bus"]))))
        adj = Dict{Int,Set{Int}}()
        for bid in bus_ids
            adj[bid] = Set{Int}()
        end
        branch_bus_map = Dict{String,Tuple{Int,Int}}()
        for (br_id, br) in data["branch"]
            if br["br_status"] == 1
                push!(adj[br["f_bus"]], br["t_bus"])
                push!(adj[br["t_bus"]], br["f_bus"])
                branch_bus_map[br_id] = (br["f_bus"], br["t_bus"])
            end
        end

        # Choose focus bus with most connections
        focus_bus = bus_ids[1]
        max_conn = 0
        for bid in bus_ids
            c = length(get(adj, bid, Set{Int}()))
            if c > max_conn
                max_conn = c
                focus_bus = bid
            end
        end
        results["details"]["focus_bus"] = focus_bus
        results["details"]["focus_bus_connections"] = max_conn

        # BFS to find buses within distance x
        visited = Dict{Int,Int}()
        queue = [(focus_bus, 0)]
        visited[focus_bus] = 0
        while !isempty(queue)
            (node, d) = popfirst!(queue)
            if d < x
                for neighbor in get(adj, node, Set{Int}())
                    if !haskey(visited, neighbor)
                        visited[neighbor] = d + 1
                        push!(queue, (neighbor, d + 1))
                    end
                end
            end
        end
        nearby_buses = Set(keys(visited))
        results["details"]["buses_within_distance"] = length(nearby_buses)
        results["details"]["graph_distance_x"] = x

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
        results["details"]["total_active_branches"] = count(
            br["br_status"] == 1 for (_, br) in data["branch"]
        )
        results["details"]["pruning_ratio"] = round(
            1.0 -
            length(candidate_branches) / count(br["br_status"] == 1 for (_, br) in data["branch"]);
            digits=4,
        )

        # Evaluate contingencies using DCPF
        total_contingencies = 0
        contingency_summary = Dict{String,Any}()
        per_case_times = Float64[]

        GC.gc()
        mem_before = Base.gc_live_bytes() / 1024^2

        for order in 1:m
            combos = combinations_iter(candidate_branches, order)
            n_total = length(combos)

            # For high-order combos, cap at 500 to avoid combinatorial explosion
            max_eval = min(n_total, 500)
            combos_eval = combos[1:max_eval]

            n_converged = 0
            n_islanded = 0

            for combo in combos_eval
                total_contingencies += 1
                data_mod = deepcopy(data)
                for br_id in combo
                    data_mod["branch"][br_id]["br_status"] = 0
                end

                tc = time()
                try
                    PowerModels.compute_dc_pf(data_mod)
                    n_converged += 1
                catch
                    # Might island
                    n_islanded += 1
                end
                push!(per_case_times, time() - tc)
            end

            contingency_summary["N-$(order)"] = Dict{String,Any}(
                "total_possible" => n_total,
                "evaluated" => max_eval,
                "converged" => n_converged,
                "failed" => max_eval - n_converged,
            )
        end

        GC.gc()
        mem_after = Base.gc_live_bytes() / 1024^2

        results["details"]["contingency_results"] = contingency_summary
        results["details"]["total_contingencies_evaluated"] = total_contingencies
        results["details"]["max_contingency_order_m"] = m
        results["details"]["total_sweep_time_seconds"] = round(sum(per_case_times); digits=3)
        results["details"]["per_case_average_seconds"] = round(
            sum(per_case_times) / length(per_case_times); digits=6
        )
        results["details"]["peak_memory_mb"] = round(mem_after - mem_before; digits=2)
        results["details"]["method"] = "Manual branch removal + compute_dc_pf per contingency with graph-distance pruning"

        results["status"] = "pass"

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
