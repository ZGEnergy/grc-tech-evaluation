#=
Batch MEDIUM test runner: B-2 (graph access), B-3 (N-1 contingency loop),
B-5 (interoperability), B-9 (PTDF extraction) on ACTIVSg 10000-bus.
Also covers C-9 (PTDF scale).
=#

using PowerModels, JuMP, HiGHS, Ipopt, JSON
using LinearAlgebra

const NETWORK_FILE = joinpath(@__DIR__, "..", "..", "..", "data", "networks", "case_ACTIVSg10k.m")

println("=== Parsing 10k network ===")
t_parse = time()
data = PowerModels.parse_file(NETWORK_FILE)
parse_time = time() - t_parse
println("Parse time: $(round(parse_time, digits=2))s")
println(
    "Buses: $(length(data["bus"])), Branches: $(length(data["branch"])), Gens: $(length(data["gen"]))",
)

# ==== B-2: Graph Access (BFS depth 3) ====
println("\n=== B-2: Graph Access (BFS depth 3) on MEDIUM ===")
t_b2 = time()

# Build adjacency from branch data
adj = Dict{Int,Vector{Tuple{Int,Int}}}()
for (br_id, br) in data["branch"]
    f = br["f_bus"]
    t = br["t_bus"]
    bid = parse(Int, br_id)
    if !haskey(adj, f)
        ;
        adj[f] = Tuple{Int,Int}[];
    end
    if !haskey(adj, t)
        ;
        adj[t] = Tuple{Int,Int}[];
    end
    push!(adj[f], (t, bid))
    push!(adj[t], (f, bid))
end

# BFS from a well-connected bus
all_bus_ids = sort(parse.(Int, collect(keys(data["bus"]))))
# Pick a bus with high degree
degrees = Dict(b => length(get(adj, b, Tuple{Int,Int}[])) for b in all_bus_ids)
seed_bus = sort(collect(degrees); by=x->-x[2])[1][1]  # highest degree bus
println("Seed bus: $seed_bus (degree: $(degrees[seed_bus]))")

visited = Dict{Int,Int}()  # bus -> depth
queue = [(seed_bus, 0)]
visited[seed_bus] = 0
while !isempty(queue)
    (bus, depth) = popfirst!(queue)
    if depth >= 3
        continue
    end
    for (neighbor, _) in get(adj, bus, Tuple{Int,Int}[])
        if !haskey(visited, neighbor)
            visited[neighbor] = depth + 1
            push!(queue, (neighbor, depth + 1))
        end
    end
end

subgraph_buses = sort(collect(keys(visited)))
subgraph_branches = Int[]
for (br_id, br) in data["branch"]
    if br["f_bus"] in subgraph_buses && br["t_bus"] in subgraph_buses
        push!(subgraph_branches, parse(Int, br_id))
    end
end

b2_time = time() - t_b2
println("Subgraph buses: $(length(subgraph_buses)) of $(length(all_bus_ids))")
println("Subgraph branches: $(length(subgraph_branches)) of $(length(data["branch"]))")
println("Depth 0: $(count(v -> v == 0, values(visited)))")
println("Depth 1: $(count(v -> v == 1, values(visited)))")
println("Depth 2: $(count(v -> v == 2, values(visited)))")
println("Depth 3: $(count(v -> v == 3, values(visited)))")
println("BFS time: $(round(b2_time, digits=4))s")

b2_results = Dict(
    "status" => "pass",
    "seed_bus" => seed_bus,
    "seed_degree" => degrees[seed_bus],
    "subgraph_buses" => length(subgraph_buses),
    "subgraph_branches" => length(subgraph_branches),
    "total_buses" => length(all_bus_ids),
    "total_branches" => length(data["branch"]),
    "depth_0" => count(v -> v == 0, values(visited)),
    "depth_1" => count(v -> v == 1, values(visited)),
    "depth_2" => count(v -> v == 2, values(visited)),
    "depth_3" => count(v -> v == 3, values(visited)),
    "wall_clock" => round(b2_time; digits=4),
)

# ==== B-3: N-1 DCPF Contingency Loop (50 contingencies) ====
println("\n=== B-3: N-1 DCPF Contingency Loop (50 contingencies) on MEDIUM ===")

# Warm up compute_dc_pf on this network
try
    _d = deepcopy(data)
    PowerModels.compute_dc_pf(_d)
catch
    ;
end

# Base case
data_base = deepcopy(data)
base_pf = PowerModels.compute_dc_pf(data_base)
base_converged = base_pf["termination_status"]
println("Base case converged: $base_converged")

# Select 50 branches for contingency analysis (first 50)
branch_ids_all = sort(parse.(Int, collect(keys(data["branch"]))))
n_contingencies = min(50, length(branch_ids_all))
ctg_branches = branch_ids_all[1:n_contingencies]

function run_contingency_loop(data, ctg_branches)
    t_b3 = time()
    ctg_results = Dict{Int,Dict}()
    n_converged = 0
    n_islanded = 0
    n_diverged = 0
    ctg_times = Float64[]

    for (i, br_id) in enumerate(ctg_branches)
        t_c = time()
        ctg_data = deepcopy(data)
        ctg_data["branch"][string(br_id)]["br_status"] = 0

        # Check connectivity
        components = PowerModels.calc_connected_components(ctg_data)
        if length(components) > 1
            n_islanded += 1
            dt = time() - t_c
            push!(ctg_times, dt)
            ctg_results[br_id] = Dict("status" => "islanded", "time" => dt)
            continue
        end

        try
            pf = PowerModels.compute_dc_pf(ctg_data)
            if pf["termination_status"]
                n_converged += 1
                PowerModels.update_data!(ctg_data, pf["solution"])
                flows = PowerModels.calc_branch_flow_dc(ctg_data)

                max_loading = 0.0
                max_loading_br = 0
                for (bid, br) in flows["branch"]
                    rate = ctg_data["branch"][bid]["rate_a"]
                    if rate > 0 && rate < 1e10
                        loading = abs(br["pf"]) / rate * 100
                        if loading > max_loading
                            max_loading = loading
                            max_loading_br = parse(Int, bid)
                        end
                    end
                end

                dt = time() - t_c
                push!(ctg_times, dt)
                ctg_results[br_id] = Dict(
                    "status" => "converged",
                    "max_loading" => round(max_loading; digits=2),
                    "max_loading_branch" => max_loading_br,
                    "time" => dt,
                )
            else
                n_diverged += 1
                dt = time() - t_c
                push!(ctg_times, dt)
                ctg_results[br_id] = Dict("status" => "diverged", "time" => dt)
            end
        catch e
            n_diverged += 1
            dt = time() - t_c
            push!(ctg_times, dt)
            ctg_results[br_id] = Dict("status" => "error", "error" => string(e), "time" => dt)
        end
    end
    b3_time = time() - t_b3
    return ctg_results, n_converged, n_islanded, n_diverged, ctg_times, b3_time
end

ctg_results, n_converged, n_islanded, n_diverged, ctg_times, b3_time = run_contingency_loop(
    data, ctg_branches
)

println("Converged: $n_converged, Islanded: $n_islanded, Diverged: $n_diverged")
println("Total time: $(round(b3_time, digits=2))s")
println("Mean per contingency: $(round(b3_time/n_contingencies*1000, digits=1))ms")
if !isempty(ctg_times)
    println(
        "Min: $(round(minimum(ctg_times)*1000, digits=1))ms, Max: $(round(maximum(ctg_times)*1000, digits=1))ms",
    )
end

b3_results = Dict(
    "status" => n_converged > 0 ? "pass" : "fail",
    "n_contingencies" => n_contingencies,
    "n_converged" => n_converged,
    "n_islanded" => n_islanded,
    "n_diverged" => n_diverged,
    "total_time" => round(b3_time; digits=2),
    "mean_time_ms" => round(b3_time/n_contingencies*1000; digits=1),
    "min_time_ms" => isempty(ctg_times) ? 0.0 : round(minimum(ctg_times)*1000; digits=1),
    "max_time_ms" => isempty(ctg_times) ? 0.0 : round(maximum(ctg_times)*1000; digits=1),
)

# ==== B-5: Interoperability (export to DataFrame) ====
println("\n=== B-5: Interoperability on MEDIUM ===")
t_b5 = time()

# Solve DCPF
data_b5 = PowerModels.parse_file(NETWORK_FILE)
pf_b5 = PowerModels.compute_dc_pf(data_b5)
sol_b5 = pf_b5["solution"]
PowerModels.update_data!(data_b5, sol_b5)
flows_b5 = PowerModels.calc_branch_flow_dc(data_b5)

# Export to Dict-of-arrays (DataFrame-like without DataFrames dep)
bus_data_export = Dict(
    "bus_id" => [parse(Int, id) for id in keys(sol_b5["bus"])],
    "va_rad" => [bus["va"] for bus in values(sol_b5["bus"])],
)
branch_data_export = Dict(
    "branch_id" => [parse(Int, id) for id in keys(flows_b5["branch"])],
    "pf" => [br["pf"] for br in values(flows_b5["branch"])],
    "pt" => [br["pt"] for br in values(flows_b5["branch"])],
)
gen_data_export = Dict(
    "gen_id" => [parse(Int, id) for id in keys(data_b5["gen"])],
    "pg" => [g["pg"] for g in values(data_b5["gen"])],
)

b5_time = time() - t_b5
println("Bus rows: $(length(bus_data_export["bus_id"]))")
println("Branch rows: $(length(branch_data_export["branch_id"]))")
println("Gen rows: $(length(gen_data_export["gen_id"]))")
println("Export time: $(round(b5_time, digits=3))s")

b5_results = Dict(
    "status" => "pass",
    "bus_rows" => length(bus_data_export["bus_id"]),
    "branch_rows" => length(branch_data_export["branch_id"]),
    "gen_rows" => length(gen_data_export["gen_id"]),
    "wall_clock" => round(b5_time; digits=3),
    "export_method" => "Dict comprehension from solution Dict (no DataFrames.jl needed)",
    "custom_serialization_needed" => false,
)

# ==== B-9 / C-9: PTDF Matrix Extraction ====
println("\n=== B-9 / C-9: PTDF Matrix Extraction on MEDIUM ===")
t_b9 = time()

data_b9 = PowerModels.parse_file(NETWORK_FILE)

t_basic = time()
basic_data = PowerModels.make_basic_network(deepcopy(data_b9))
basic_time = time() - t_basic
println("make_basic_network: $(round(basic_time, digits=2))s")

t_ptdf = time()
ptdf = PowerModels.calc_basic_ptdf_matrix(basic_data)
ptdf_time = time() - t_ptdf
nbr, nb = size(ptdf)
println("PTDF dimensions: $nbr x $nb")
println("PTDF compute time: $(round(ptdf_time, digits=2))s")

# Validate against DCPF
data_b9_pf = deepcopy(data_b9)
pf_b9 = PowerModels.compute_dc_pf(data_b9_pf)
PowerModels.update_data!(data_b9_pf, pf_b9["solution"])
flows_b9 = PowerModels.calc_branch_flow_dc(data_b9_pf)

basic_bus_ids = sort(parse.(Int, collect(keys(basic_data["bus"]))))
basic_branch_ids = sort(parse.(Int, collect(keys(basic_data["branch"]))))
bus_to_idx = Dict(id => i for (i, id) in enumerate(basic_bus_ids))

# Compute net injections
p_inj = zeros(nb)
for (_, gen) in basic_data["gen"]
    bus = gen["gen_bus"]
    if haskey(bus_to_idx, bus)
        p_inj[bus_to_idx[bus]] += gen["pg"]
    end
end
for (_, load) in basic_data["load"]
    bus = load["load_bus"]
    if haskey(bus_to_idx, bus)
        p_inj[bus_to_idx[bus]] -= load["pd"]
    end
end

# Verify on basic network DCPF
basic_fresh = PowerModels.make_basic_network(PowerModels.parse_file(NETWORK_FILE))
pf_basic = PowerModels.compute_dc_pf(basic_fresh)
PowerModels.update_data!(basic_fresh, pf_basic["solution"])
basic_flows = PowerModels.calc_branch_flow_dc(basic_fresh)

flow_predicted = ptdf * p_inj
flow_actual = zeros(nbr)
for (l, br_id) in enumerate(basic_branch_ids)
    flow_actual[l] = basic_flows["branch"][string(br_id)]["pf"]
end

flow_diff = abs.(flow_predicted .- flow_actual)
max_diff = maximum(flow_diff)
mean_diff = sum(flow_diff) / nbr

println("Max flow prediction error: $max_diff")
println("Mean flow prediction error: $mean_diff")
println("Flows match (< 1e-6): $(max_diff < 1e-6)")

# PTDF rank
ptdf_rank = rank(ptdf)
println("PTDF rank: $ptdf_rank (expected: $(nb - 1))")

b9_time = time() - t_b9
mem_after_ptdf = round(Base.gc_live_bytes() / 1e6; digits=1)
println("Total B-9 time: $(round(b9_time, digits=2))s")
println("Memory after PTDF: $(mem_after_ptdf) MB")

# Estimate PTDF memory
ptdf_mem_mb = round(sizeof(ptdf) / 1e6; digits=1)
println("PTDF matrix size: $(ptdf_mem_mb) MB ($(nbr) x $(nb) Float64)")

b9_results = Dict(
    "status" => max_diff < 1e-6 ? "pass" : "fail",
    "ptdf_rows" => nbr,
    "ptdf_cols" => nb,
    "ptdf_rank" => ptdf_rank,
    "expected_rank" => nb - 1,
    "max_flow_diff" => max_diff,
    "mean_flow_diff" => mean_diff,
    "flows_match" => max_diff < 1e-6,
    "ptdf_compute_time" => round(ptdf_time; digits=2),
    "basic_network_time" => round(basic_time; digits=2),
    "total_time" => round(b9_time; digits=2),
    "ptdf_memory_mb" => ptdf_mem_mb,
    "process_memory_mb" => mem_after_ptdf,
)

println("\n=== SUMMARY ===")
println("B-2 Graph: $(b2_results["status"]), $(b2_results["subgraph_buses"]) buses in subgraph")
println(
    "B-3 N-1 loop: $(b3_results["status"]), $(b3_results["n_converged"])/$(b3_results["n_contingencies"]) converged, $(round(b3_results["total_time"], digits=2))s",
)
println("B-5 Export: $(b5_results["status"]), $(b5_results["bus_rows"]) bus rows")
println(
    "B-9 PTDF: $(b9_results["status"]), $(b9_results["ptdf_rows"])x$(b9_results["ptdf_cols"]), $(b9_results["ptdf_compute_time"])s",
)

all_results = Dict(
    "b2_graph_access" => b2_results,
    "b3_contingency_loop" => b3_results,
    "b5_interoperability" => b5_results,
    "b9_ptdf_extraction" => b9_results,
)
println("\n" * JSON.json(all_results, 2))
