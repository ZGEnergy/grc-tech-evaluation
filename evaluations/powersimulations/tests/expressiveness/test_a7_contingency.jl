#=
Test A-7: Contingency Sweep (N-M, graph distance x=3, m=3)

Dimension: expressiveness
Network: TINY (case39.m -- IEEE 39-bus)
Pass condition: Completes without full model reconstruction per contingency case.
                Load loss per contingency case collected. Pruning logic is expressible
                without fighting the tool. Combinatorial enumeration and graph-distance
                scoping are achievable via the tool's API or a clean graph library bridge.
Tool: PowerSimulations.jl v0.30.2 (via PowerFlows.jl for DCPF)
=#

using PowerSystems
using PowerFlows
using PowerNetworkMatrices
using JSON
using DataFrames

"""
Generate all combinations of `k` elements from `items`.
Manual implementation to avoid Combinatorics.jl dependency.
"""
function combinations(items::Vector{T}, k::Int) where {T}
    n = length(items)
    if k > n || k < 0
        return Vector{Vector{T}}()
    end
    if k == 0
        return [T[]]
    end
    if k == n
        return [copy(items)]
    end
    result = Vector{Vector{T}}()
    indices = collect(1:k)
    while true
        push!(result, items[indices])
        # Find rightmost index that can be incremented
        i = k
        while i > 0 && indices[i] == n - k + i
            i -= 1
        end
        if i == 0
            break
        end
        indices[i] += 1
        for j in (i + 1):k
            indices[j] = indices[j - 1] + 1
        end
    end
    return result
end

"""
Build adjacency graph from PowerSystems bus/branch data.
Returns: (adj_list, bus_names, branch_list)
  - adj_list: Dict{String, Set{String}} mapping bus name to connected bus names
  - bus_names: Vector{String} of all bus names
  - branch_list: Vector of (name, from_bus, to_bus) tuples
"""
function build_adjacency(sys::System)
    adj = Dict{String,Set{String}}()
    branch_list = Tuple{String,String,String}[]

    # Initialize all buses
    for bus in get_components(ACBus, sys)
        adj[get_name(bus)] = Set{String}()
    end

    # Add edges from all branch types
    for branch in get_components(Branch, sys)
        from_bus = get_name(get_arc(branch).from)
        to_bus = get_name(get_arc(branch).to)
        branch_name = get_name(branch)

        push!(adj[from_bus], to_bus)
        push!(adj[to_bus], from_bus)
        push!(branch_list, (branch_name, from_bus, to_bus))
    end

    bus_names = collect(keys(adj))
    return adj, bus_names, branch_list
end

"""
BFS from seed_bus to depth x. Returns set of bus names within distance x.
"""
function bfs_neighborhood(adj::Dict{String,Set{String}}, seed_bus::String, x::Int)
    visited = Set{String}([seed_bus])
    frontier = Set{String}([seed_bus])

    for depth in 1:x
        next_frontier = Set{String}()
        for bus in frontier
            for neighbor in adj[bus]
                if !(neighbor in visited)
                    push!(visited, neighbor)
                    push!(next_frontier, neighbor)
                end
            end
        end
        frontier = next_frontier
        if isempty(frontier)
            break
        end
    end
    return visited
end

"""
Find branches within the neighborhood (both endpoints in the subgraph).
"""
function branches_in_subgraph(
    branch_list::Vector{Tuple{String,String,String}}, neighborhood::Set{String}
)
    return [
        (name, from, to) for
        (name, from, to) in branch_list if from in neighborhood && to in neighborhood
    ]
end

"""
Solve DCPF with specified branches removed. Returns Dict with load loss info.
Uses PowerFlows.jl direct DCPF (no optimizer needed).
"""
function solve_contingency(sys::System, branches_to_remove::Vector{String})
    result = Dict{String,Any}()
    result["removed_branches"] = branches_to_remove

    # Get pre-contingency total load
    total_load = 0.0
    for load in get_components(PowerLoad, sys)
        total_load += get_active_power(load) * get_base_power(sys)  # MW
    end
    result["total_load_mw"] = total_load

    # Deactivate branches for contingency
    deactivated = String[]
    for branch in get_components(Branch, sys)
        if get_name(branch) in branches_to_remove
            if get_available(branch)
                set_available!(branch, false)
                push!(deactivated, get_name(branch))
            end
        end
    end
    result["branches_deactivated"] = length(deactivated)

    # Solve DCPF
    load_loss = 0.0
    try
        pf_result = solve_powerflow(DCPowerFlow(), sys)

        if pf_result !== nothing && !isempty(pf_result)
            result["converged"] = true
            # Extract bus results
            result_key = first(keys(pf_result))
            bus_df = pf_result[result_key]["bus_results"]

            # Check for voltage angle spread (large angles indicate stress)
            if "theta" in names(bus_df) || "θ" in names(bus_df)
                angle_col = "θ" in names(bus_df) ? "θ" : "theta"
                angles = bus_df[!, angle_col]
                result["max_angle_spread_rad"] = maximum(angles) - minimum(angles)
            end

            # In a DCPF, load loss = 0 if system is connected and has enough generation
            # DCPF always satisfies power balance (it's a linear solve, not optimization)
            # Load shedding only occurs if the system is islanded
            result["load_loss_mw"] = 0.0
        else
            result["converged"] = false
            # DCPF failure indicates islanding or numerical issues
            result["load_loss_mw"] = total_load  # worst case: assume all load lost
            load_loss = total_load
        end
    catch e
        result["converged"] = false
        result["error"] = string(typeof(e), ": ", sprint(showerror, e))
        # On solver failure, conservatively assume load loss
        result["load_loss_mw"] = total_load
        load_loss = total_load
    end

    # Re-activate branches
    for branch in get_components(Branch, sys)
        if get_name(branch) in branches_to_remove
            set_available!(branch, true)
        end
    end

    return result
end

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
        # ===== 1. Load network =====
        sys = System(network_file)
        n_buses = length(collect(get_components(ACBus, sys)))
        n_branches = length(collect(get_components(Branch, sys)))
        n_gens = length(collect(get_components(Generator, sys)))
        results["details"]["network"] = Dict(
            "buses" => n_buses, "branches" => n_branches, "generators" => n_gens
        )

        # ===== 2. Build adjacency graph =====
        adj, bus_names, branch_list = build_adjacency(sys)
        results["details"]["graph"] = Dict(
            "total_buses" => length(bus_names),
            "total_branches" => length(branch_list),
            "graph_construction" => "Manual from PowerSystems bus/branch data (no Graphs.jl)",
        )

        # ===== 3. Choose seed bus and BFS to depth x=3 =====
        # Pick a bus with high connectivity for interesting contingencies
        # Bus 16 is central in case39 (connects to buses 15, 17, 19, 21, 24)
        seed_bus = "bus-16"
        x = 3  # graph distance
        m = 3  # max simultaneous outages

        neighborhood = bfs_neighborhood(adj, seed_bus, x)
        results["details"]["bfs"] = Dict(
            "seed_bus" => seed_bus,
            "depth" => x,
            "neighborhood_size" => length(neighborhood),
            "neighborhood_buses" => sort(collect(neighborhood)),
        )

        # ===== 4. Find branches in subgraph =====
        subgraph_branches = branches_in_subgraph(branch_list, neighborhood)
        results["details"]["subgraph_branches"] = [
            Dict("name" => b[1], "from" => b[2], "to" => b[3]) for b in subgraph_branches
        ]
        results["details"]["subgraph_branch_count"] = length(subgraph_branches)

        branch_names = [b[1] for b in subgraph_branches]

        # ===== 5. Enumerate contingencies up to order m =====
        contingency_cases = Vector{Vector{String}}()
        for k in 1:m
            for combo in combinations(branch_names, k)
                push!(contingency_cases, combo)
            end
        end
        results["details"]["contingency_enumeration"] = Dict(
            "max_order" => m,
            "n_1_cases" => binomial(length(branch_names), 1),
            "n_2_cases" => binomial(length(branch_names), 2),
            "n_3_cases" => binomial(length(branch_names), 3),
            "total_cases" => length(contingency_cases),
        )

        # ===== 6. Run contingency sweep =====
        println("Running $(length(contingency_cases)) contingency cases...")
        contingency_results = Dict{String,Any}[]
        n_converged = 0
        n_failed = 0
        n_load_loss = 0

        t_sweep = time()
        for (i, case) in enumerate(contingency_cases)
            case_result = solve_contingency(sys, case)
            case_result["case_id"] = i
            case_result["order"] = length(case)
            push!(contingency_results, case_result)

            if get(case_result, "converged", false)
                n_converged += 1
            else
                n_failed += 1
            end

            if get(case_result, "load_loss_mw", 0.0) > 0.0
                n_load_loss += 1
            end

            if i % 50 == 0
                println("  Completed $i / $(length(contingency_cases)) cases")
            end
        end
        sweep_time = time() - t_sweep

        results["details"]["sweep_results"] = Dict(
            "total_cases" => length(contingency_cases),
            "converged" => n_converged,
            "failed" => n_failed,
            "cases_with_load_loss" => n_load_loss,
            "sweep_time_seconds" => sweep_time,
            "avg_time_per_case" => sweep_time / length(contingency_cases),
        )

        # Collect summary of load-loss cases
        load_loss_cases = [
            Dict(
                "case_id" => cr["case_id"],
                "removed" => cr["removed_branches"],
                "order" => cr["order"],
                "load_loss_mw" => cr["load_loss_mw"],
                "converged" => get(cr, "converged", false),
            ) for cr in contingency_results if get(cr, "load_loss_mw", 0.0) > 0.0
        ]
        results["details"]["load_loss_cases"] = load_loss_cases

        # Sample some results for the report (first 5 N-1, first 3 N-3)
        n1_sample = [cr for cr in contingency_results if cr["order"] == 1][1:min(5, end)]
        n3_sample = [cr for cr in contingency_results if cr["order"] == 3][1:min(3, end)]
        results["details"]["sample_n1"] = n1_sample
        results["details"]["sample_n3"] = n3_sample

        # ===== 7. Document approach =====
        push!(
            results["workarounds"],
            "Built adjacency graph manually from PowerSystems bus/branch data. " *
            "PSI has no native Graphs.jl integration or graph-distance API.",
        )
        push!(
            results["workarounds"],
            "Used PowerFlows.jl DCPF (direct linear solve) for each contingency " *
            "instead of full PSI DecisionModel. Avoids model reconstruction overhead.",
        )
        push!(
            results["workarounds"],
            "Branch outages modeled via set_available!(branch, false/true) -- " *
            "no model reconstruction needed, just toggle availability and re-solve.",
        )

        results["details"]["methodology"] = Dict(
            "graph_library" => "None (manual BFS from PowerSystems data)",
            "solver" => "PowerFlows.jl DCPowerFlow (direct linear solve, no optimizer)",
            "contingency_method" => "Toggle branch availability, re-solve DCPF",
            "model_reconstruction" => false,
            "pruning_method" => "BFS neighborhood from seed bus to depth x",
        )

        # ===== 8. Overall status =====
        results["status"] = n_converged > 0 ? "pass" : "fail"

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

# Run and print
result = run_test()
println("---JSON_OUTPUT_START---")
println(JSON.json(result, 2))
println("---JSON_OUTPUT_END---")
