#=
Test A-7: N-M Contingency Sweep on TINY (IEEE 39-bus)
Dimension: expressiveness
Network: TINY (IEEE 39-bus)
Pass condition: Completes without full model reconstruction per contingency.
               Load loss collected. Pruning logic expressible.
               Graph-distance scoping achievable.
Tool: PowerModels.jl v0.21.5
Solver: N/A (direct solve via compute_dc_pf)

Parameters: x=3 (graph distance), m=3 (max simultaneous outages)

Approach: PowerModels has NO native graph library. BFS must be implemented
manually using branch f_bus/t_bus pairs. Contingency DCPF is performed by
setting branch br_status=0 and re-running compute_dc_pf. No model
reconstruction from file is needed.
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
        data = PowerModels.parse_file(network_file)

        results["details"]["num_buses"] = length(data["bus"])
        results["details"]["num_branches"] = length(data["branch"])
        results["details"]["graph_distance_x"] = 3
        results["details"]["max_outage_order_m"] = 3

        # ---- Step 1: Build adjacency graph from branch data ----
        # PowerModels has no native graph library; build manually
        bus_ids = sort(parse.(Int, collect(keys(data["bus"]))))
        branch_ids = sort(parse.(Int, collect(keys(data["branch"]))))

        # Build adjacency list: bus -> set of (neighbor_bus, branch_id)
        adjacency = Dict{Int,Vector{Tuple{Int,Int}}}()
        for b in bus_ids
            adjacency[b] = Tuple{Int,Int}[]
        end
        # Also build branch -> (f_bus, t_bus) mapping
        branch_endpoints = Dict{Int,Tuple{Int,Int}}()
        for br_id in branch_ids
            br = data["branch"][string(br_id)]
            f = br["f_bus"]
            t = br["t_bus"]
            branch_endpoints[br_id] = (f, t)
            push!(adjacency[f], (t, br_id))
            push!(adjacency[t], (f, br_id))
        end

        results["details"]["adjacency_built_manually"] = true

        # ---- Step 2: BFS to find branches within graph distance x=3 of chosen bus ----
        # Choose bus 16 (interior bus with reasonable connectivity)
        seed_bus = 16
        x = 3

        # BFS from seed_bus, collecting all buses within distance x
        visited = Dict{Int,Int}()  # bus -> distance
        visited[seed_bus] = 0
        queue = [seed_bus]
        while !isempty(queue)
            current = popfirst!(queue)
            d = visited[current]
            if d >= x
                continue
            end
            for (neighbor, _) in adjacency[current]
                if !haskey(visited, neighbor)
                    visited[neighbor] = d + 1
                    push!(queue, neighbor)
                end
            end
        end

        # Collect branches that have BOTH endpoints within the BFS scope
        # (i.e., branches whose removal could affect flow in the neighborhood)
        scoped_branches = Int[]
        for br_id in branch_ids
            f, t = branch_endpoints[br_id]
            if haskey(visited, f) && haskey(visited, t)
                push!(scoped_branches, br_id)
            end
        end

        results["details"]["seed_bus"] = seed_bus
        results["details"]["buses_in_scope"] = length(visited)
        results["details"]["branches_in_scope"] = length(scoped_branches)
        results["details"]["scoped_branch_ids"] = scoped_branches

        # ---- Step 3: Compute base case total load ----
        base_total_load = sum(load["pd"] for (_, load) in data["load"])
        results["details"]["base_total_load_pu"] = round(base_total_load; digits=4)

        # Helper: compute load loss for a given set of outaged branches
        function compute_load_loss(outaged_branch_ids::Vector{Int})
            # Clone data dict (deep copy to avoid mutation)
            d = deepcopy(data)

            # Set outaged branches to inactive
            for br_id in outaged_branch_ids
                d["branch"][string(br_id)]["br_status"] = 0
            end

            # First check connectivity -- if network splits, compute_dc_pf
            # will throw SingularException on the admittance matrix
            components = PowerModels.calc_connected_components(d)

            # Find which component has the reference bus
            ref_bus_id = nothing
            for (id, bus) in d["bus"]
                if bus["bus_type"] == 3
                    ref_bus_id = parse(Int, id)
                    break
                end
            end

            # Identify the main island (containing reference bus)
            main_component = Set{Int}()
            for comp in components
                if ref_bus_id in comp
                    main_component = comp
                    break
                end
            end

            # Load on buses NOT in main component is lost
            lost_load = 0.0
            for (_, load) in d["load"]
                if !(load["load_bus"] in main_component) && load["status"] == 1
                    lost_load += load["pd"]
                end
            end

            # If network is connected (single component), try DC PF to verify
            if length(components) == 1
                try
                    pf_result = PowerModels.compute_dc_pf(d)
                    if !pf_result["termination_status"]
                        return base_total_load, false
                    end
                catch e
                    if isa(e, LinearAlgebra.SingularException)
                        # Singular matrix despite single component -- treat as total loss
                        return base_total_load, false
                    end
                    rethrow(e)
                end
            end

            return lost_load, length(components) == 1
        end

        # ---- Step 4: N-1 sweep ----
        n1_results = Dict{Int,Dict{String,Any}}()
        pruned_branches = Set{Int}()  # branches causing total load loss at seed bus
        solve_count = 0

        for br_id in scoped_branches
            loss, converged = compute_load_loss([br_id])
            solve_count += 1
            n1_results[br_id] = Dict(
                "load_loss_pu" => round(loss; digits=6),
                "converged" => converged,
                "total_loss" => loss >= base_total_load - 1e-6,
            )
            # Prune if total load loss
            if loss >= base_total_load - 1e-6
                push!(pruned_branches, br_id)
            end
        end

        results["details"]["n1_cases"] = length(scoped_branches)
        results["details"]["n1_total_loss_count"] = length(pruned_branches)
        results["details"]["n1_pruned_branches"] = sort(collect(pruned_branches))

        # Summary of N-1 results
        n1_with_loss = [(br_id, r) for (br_id, r) in n1_results if r["load_loss_pu"] > 1e-6]
        results["details"]["n1_cases_with_load_loss"] = length(n1_with_loss)
        results["details"]["n1_results_sample"] = Dict(
            string(k) => v for (k, v) in Iterators.take(sort(collect(n1_results); by=x->x[1]), 10)
        )

        # ---- Step 5: N-2 sweep (pruning branches that caused total loss at N-1) ----
        surviving_branches = [br for br in scoped_branches if !(br in pruned_branches)]
        results["details"]["n2_surviving_branches"] = length(surviving_branches)

        n2_results = Dict{String,Dict{String,Any}}()
        n2_pruned = Set{Tuple{Int,Int}}()

        for i in 1:length(surviving_branches)
            for j in (i + 1):length(surviving_branches)
                br1 = surviving_branches[i]
                br2 = surviving_branches[j]
                loss, converged = compute_load_loss([br1, br2])
                solve_count += 1
                key = "$(br1)_$(br2)"
                n2_results[key] = Dict(
                    "branches" => [br1, br2],
                    "load_loss_pu" => round(loss; digits=6),
                    "converged" => converged,
                    "total_loss" => loss >= base_total_load - 1e-6,
                )
                if loss >= base_total_load - 1e-6
                    push!(n2_pruned, (br1, br2))
                end
            end
        end

        results["details"]["n2_cases"] = length(n2_results)
        results["details"]["n2_total_loss_count"] = length(n2_pruned)

        n2_with_loss = [(k, r) for (k, r) in n2_results if r["load_loss_pu"] > 1e-6]
        results["details"]["n2_cases_with_load_loss"] = length(n2_with_loss)
        # Show first few N-2 results with load loss
        results["details"]["n2_results_with_loss_sample"] = Dict(
            k => v for (k, v) in
            Iterators.take(sort(collect(n2_with_loss); by=x->x[2]["load_loss_pu"], rev=true), 5)
        )

        # ---- Step 6: N-3 sweep (pruning branches from N-2 total loss) ----
        # For N-3, we need to prune individual branches that appeared in ALL
        # N-2 total-loss pairs. But the protocol says: prune branches whose
        # removal at order n-1 already produced total load loss.
        # At N-2, the "unit" is a pair. We prune pairs, not individual branches.
        # Actually, re-reading: prune branches that at lower orders caused total loss.
        # So branches pruned at N-1 stay pruned. From surviving branches, enumerate N-3.

        n3_results = Dict{String,Dict{String,Any}}()
        # Use surviving branches (same as N-2 set, since N-2 pruning removes pairs not branches)
        n_surviving = length(surviving_branches)
        n3_count = 0

        for i in 1:n_surviving
            for j in (i + 1):n_surviving
                for k in (j + 1):n_surviving
                    br1 = surviving_branches[i]
                    br2 = surviving_branches[j]
                    br3 = surviving_branches[k]

                    # Skip if any N-2 subset was already total loss (pruning)
                    skip = false
                    for (p1, p2) in n2_pruned
                        subset = Set([p1, p2])
                        if issubset(subset, Set([br1, br2, br3]))
                            skip = true
                            break
                        end
                    end
                    if skip
                        continue
                    end

                    loss, converged = compute_load_loss([br1, br2, br3])
                    solve_count += 1
                    n3_count += 1
                    key = "$(br1)_$(br2)_$(br3)"
                    n3_results[key] = Dict(
                        "branches" => [br1, br2, br3],
                        "load_loss_pu" => round(loss; digits=6),
                        "converged" => converged,
                    )
                end
            end
        end

        results["details"]["n3_cases_evaluated"] = n3_count
        results["details"]["n3_cases_pruned"] = binomial(n_surviving, 3) - n3_count

        n3_with_loss = [(k, r) for (k, r) in n3_results if r["load_loss_pu"] > 1e-6]
        results["details"]["n3_cases_with_load_loss"] = length(n3_with_loss)
        results["details"]["n3_results_with_loss_sample"] = Dict(
            k => v for (k, v) in
            Iterators.take(sort(collect(n3_with_loss); by=x->x[2]["load_loss_pu"], rev=true), 5)
        )

        results["details"]["total_solves"] = solve_count
        results["details"]["time_per_solve"] = round((time() - t0) / solve_count; digits=6)

        push!(
            results["workarounds"],
            "PowerModels has NO native graph library. BFS adjacency graph built " *
            "manually from branch f_bus/t_bus data (~20 lines). Graph-distance " *
            "scoping and pruning logic expressed in plain Julia loops. " *
            "Contingency re-solve uses deepcopy(data) + br_status=0 + compute_dc_pf " *
            "-- no model reconstruction from file. PowerModels' " *
            "calc_connected_components used for island detection and load loss " *
            "calculation.",
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

# Binomial helper
function binomial(n, k)
    k < 0 && return 0
    k > n && return 0
    k == 0 && return 1
    k == 1 && return n
    result = 1
    for i in 1:k
        result = result * (n - k + i) / i
    end
    return round(Int, result)
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end
