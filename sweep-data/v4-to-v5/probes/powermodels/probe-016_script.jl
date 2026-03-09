#=
Probe-016: Verify projected infeasibility claims for C-5 and C-8 on ACTIVSg 10k-bus

Claims:
- C-5: BFS depth-5 scope yields 500-2000 branches; DCPF per solve ~0.2-0.5s; N-2+ infeasible
- C-8: SCOPF with 500 contingencies on 10k-bus exceeds practical limits

This probe:
1. Loads ACTIVSg 10k and counts buses/branches
2. Performs BFS depth-5 from a chosen bus to measure actual scope
3. Runs 10 N-1 DCPF contingencies to measure per-solve time
4. Attempts to build a small SCOPF (5 contingencies) to check feasibility
=#

using PowerModels, JuMP, HiGHS, JSON, LinearAlgebra

const NETWORK_FILE = joinpath(
    @__DIR__, "..", "..", "..", "..", "data", "networks", "case_ACTIVSg10k.m"
)

println("=" ^ 70)
println("PROBE-016: Verifying C-5/C-8 infeasibility projections")
println("=" ^ 70)

# ---- Step 1: Load network and report size ----
println("\n--- Step 1: Loading ACTIVSg 10k network ---")
t_parse = time()
data = PowerModels.parse_file(NETWORK_FILE)
parse_time = time() - t_parse
println("Parse time: $(round(parse_time; digits=2))s")

num_buses = length(data["bus"])
num_branches = length(data["branch"])
num_gens = length(data["gen"])
println("Buses: $num_buses")
println("Branches: $num_branches")
println("Generators: $num_gens")

bus_ids = sort(parse.(Int, collect(keys(data["bus"]))))
branch_ids = sort(parse.(Int, collect(keys(data["branch"]))))

# ---- Step 2: BFS depth-5 scope enumeration ----
println("\n--- Step 2: BFS depth-5 scope enumeration ---")

# Build adjacency list
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

# Try a few seed buses to get a range of scope sizes
# Pick buses with varying connectivity
seed_buses = Int[]
# Pick bus with median degree, high degree, and a random interior bus
degrees = [(b, length(adjacency[b])) for b in bus_ids]
sort!(degrees; by=x->x[2], rev=true)
push!(seed_buses, degrees[1][1])  # highest degree
push!(seed_buses, degrees[div(end, 2)][1])  # median degree
push!(seed_buses, degrees[div(end, 4)][1])  # 25th percentile degree
# Also try bus 5000 as a generic interior bus
if haskey(adjacency, 5000)
    push!(seed_buses, 5000)
end

println("Testing BFS depth=5 from seed buses: $seed_buses")
println(
    "Degree distribution: max=$(degrees[1][2]), median=$(degrees[div(end,2)][2]), min=$(degrees[end][2])",
)

bfs_results = Dict{Int,Dict{String,Any}}()
for seed in seed_buses
    visited = Dict{Int,Int}()
    visited[seed] = 0
    queue = [seed]
    while !isempty(queue)
        current = popfirst!(queue)
        d = visited[current]
        if d >= 5
            continue
        end
        for (neighbor, _) in adjacency[current]
            if !haskey(visited, neighbor)
                visited[neighbor] = d + 1
                push!(queue, neighbor)
            end
        end
    end

    # Count branches with both endpoints in scope
    scoped_branches = Int[]
    for br_id in branch_ids
        f, t = branch_endpoints[br_id]
        if haskey(visited, f) && haskey(visited, t)
            push!(scoped_branches, br_id)
        end
    end

    bfs_results[seed] = Dict(
        "buses_in_scope" => length(visited),
        "branches_in_scope" => length(scoped_branches),
        "degree" => length(adjacency[seed]),
    )
    println(
        "  Seed bus $seed (degree=$(length(adjacency[seed]))): " *
        "$(length(visited)) buses, $(length(scoped_branches)) branches in scope",
    )
end

# ---- Step 3: Warm-up DCPF on 10k ----
println("\n--- Step 3: Warm-up DCPF solve ---")
t_warmup = time()
try
    warmup_data = deepcopy(data)
    warmup_result = PowerModels.compute_dc_pf(warmup_data)
    println("Warm-up DCPF converged: $(warmup_result["termination_status"])")
catch e
    println("Warm-up DCPF failed: $e")
end
warmup_time = time() - t_warmup
println("Warm-up time (includes JIT): $(round(warmup_time; digits=3))s")

# ---- Step 4: Time 10 N-1 DCPF contingencies ----
println("\n--- Step 4: Timing 10 N-1 DCPF contingencies ---")
# Pick 10 branches spread across the network
test_branches = branch_ids[round.(Int, range(1, length(branch_ids); length=10))]

contingency_times = Float64[]
for (i, br_id) in enumerate(test_branches)
    t_start = time()
    d = deepcopy(data)
    d["branch"][string(br_id)]["br_status"] = 0

    try
        pf_result = PowerModels.compute_dc_pf(d)
        elapsed = time() - t_start
        push!(contingency_times, elapsed)
        status = pf_result["termination_status"] ? "converged" : "diverged"
        println("  Contingency $i (branch $br_id): $(round(elapsed; digits=4))s [$status]")
    catch e
        elapsed = time() - t_start
        push!(contingency_times, elapsed)
        println(
            "  Contingency $i (branch $br_id): $(round(elapsed; digits=4))s [error: $(typeof(e))]"
        )
    end
end

avg_time = sum(contingency_times) / length(contingency_times)
median_time = sort(contingency_times)[div(length(contingency_times)+1, 2)]
println("\nPer-contingency DCPF stats:")
println("  Mean:   $(round(avg_time; digits=4))s")
println("  Median: $(round(median_time; digits=4))s")
println("  Min:    $(round(minimum(contingency_times); digits=4))s")
println("  Max:    $(round(maximum(contingency_times); digits=4))s")

# ---- Step 5: Project total times ----
println("\n--- Step 5: Projections ---")
# Use median scope from BFS results
scope_sizes = [r["branches_in_scope"] for (_, r) in bfs_results]
median_scope = sort(scope_sizes)[div(length(scope_sizes)+1, 2)]
println("Median BFS scope size: $median_scope branches")

# N-1 projection
n1_time = median_scope * median_time
println(
    "N-1 ($median_scope contingencies): $(round(n1_time; digits=1))s ($(round(n1_time/60; digits=1)) min)",
)

# N-2 projection
n2_count = div(median_scope * (median_scope - 1), 2)
n2_time = n2_count * median_time
println(
    "N-2 ($n2_count contingencies): $(round(n2_time; digits=0))s ($(round(n2_time/3600; digits=1)) hours)",
)

# N-3 projection (approximate)
n3_count = div(median_scope * (median_scope - 1) * (median_scope - 2), 6)
n3_time = n3_count * median_time
println(
    "N-3 ($n3_count contingencies): $(round(n3_time; digits=0))s ($(round(n3_time/3600; digits=0)) hours)",
)

# ---- Step 6: Attempt small SCOPF (C-8 check) ----
println("\n--- Step 6: Small SCOPF attempt (5 contingencies) ---")
# Build multi-network data for SCOPF with just 5 contingencies
try
    # Use solve_opf first to confirm base DC OPF works
    t_base_opf = time()
    base_opf_result = PowerModels.solve_dc_opf(data, HiGHS.Optimizer)
    base_opf_time = time() - t_base_opf
    println("Base DC OPF solve time: $(round(base_opf_time; digits=3))s")
    println("Base DC OPF status: $(base_opf_result["termination_status"])")
    if haskey(base_opf_result, "objective")
        println("Base DC OPF objective: $(round(base_opf_result["objective"]; digits=2))")
    end

    # Count variables/constraints in base problem
    # Re-solve with JuMP model access to count
    pm = PowerModels.instantiate_model(data, DCPPowerModel, PowerModels.build_opf)
    base_vars = JuMP.num_variables(pm.model)
    base_constraints = sum(
        JuMP.num_constraints(pm.model, F, S) for (F, S) in JuMP.list_of_constraint_types(pm.model)
    )
    println("Base DC OPF: $base_vars variables, $base_constraints constraints")

    # Project SCOPF size
    println("\nProjected SCOPF with 500 contingencies:")
    println("  Variables: ~$(base_vars + 500 * base_vars)")
    println("  Constraints: ~$(base_constraints + 500 * base_constraints)")

    # Attempt multi-network SCOPF with 5 contingencies
    println("\nAttempting multi-network OPF with 5 contingencies...")
    mn_data = PowerModels.replicate(data, 6)  # 1 base + 5 contingencies

    # Apply contingencies to networks 2-6
    for (i, br_id) in enumerate(test_branches[1:5])
        nw_key = string(i + 1)
        mn_data["nw"][nw_key]["branch"][string(br_id)]["br_status"] = 0
    end

    t_scopf = time()
    mn_result = PowerModels.solve_mn_dc_opf(mn_data, HiGHS.Optimizer)
    scopf_time = time() - t_scopf
    println("Multi-network OPF (5 contingencies) solve time: $(round(scopf_time; digits=3))s")
    println("Status: $(mn_result["termination_status"])")

    # Project to 500 contingencies
    projected_500_time = scopf_time * (501 / 6)
    println(
        "Projected time for 500 contingencies (linear scaling): $(round(projected_500_time; digits=0))s",
    )
    println("  Note: LP solve time scales super-linearly, so actual time would be much higher")

catch e
    println("SCOPF attempt failed: $(typeof(e)): $(sprint(showerror, e))")
end

println("\n" * "=" ^ 70)
println("PROBE-016 COMPLETE")
println("=" ^ 70)
