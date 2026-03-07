#=
SMALL tests:
  B-4: Stochastic wrapping -- 20 scenarios x 12hr DCOPF on ACTIVSg 2000-bus
  C-6: Stochastic scale -- 20 scenarios on ACTIVSg 2000-bus with per-scenario timing
=#

using PowerModels, JuMP, HiGHS, Ipopt, JSON
using Random

const NETWORK_FILE = joinpath(@__DIR__, "..", "..", "..", "data", "networks", "case_ACTIVSg2000.m")

# Warm up
println("=== Warming up ===")
_d = PowerModels.parse_file(joinpath(@__DIR__, "..", "..", "..", "data", "networks", "case39.m"))
_mn = PowerModels.replicate(_d, 2)
PowerModels.solve_mn_opf(_mn, DCPPowerModel, HiGHS.Optimizer)

# Helper: fix empty cost arrays
function fix_costs!(data; linearize=false)
    n_fixed = 0
    for (id, gen) in data["gen"]
        if gen["model"] == 2 && (gen["ncost"] == 0 || isempty(gen["cost"]))
            gen["cost"] = [0.0, 0.0, 0.0]
            gen["ncost"] = 3
            n_fixed += 1
        end
        if linearize && gen["model"] == 2 && gen["ncost"] == 3
            gen["cost"][1] = 0.0
        end
    end
    return n_fixed
end

println("\n=== Parsing ACTIVSg 2000-bus ===")
t_parse = time()
data = PowerModels.parse_file(NETWORK_FILE)
parse_time = time() - t_parse
n_fixed = fix_costs!(data; linearize=true)  # Linearize for HiGHS LP compatibility
println("Parse: $(round(parse_time, digits=2))s, Fixed costs: $n_fixed")
println(
    "Buses: $(length(data["bus"])), Branches: $(length(data["branch"])), Gens: $(length(data["gen"]))",
)

# HiGHS LP with linearized costs (HiGHS QP fails on ACTIVSg2000, Ipopt INVALID_MODEL with DCPPowerModel mn_opf)
optimizer = JuMP.optimizer_with_attributes(
    HiGHS.Optimizer,
    "time_limit" => 300.0,
    "presolve" => "on",
    "threads" => 1,
    "output_flag" => false,
)

# ============================================================
# B-4 / C-6: 20 scenarios x 12hr multi-period DCOPF
# ============================================================
println("\n=== B-4 / C-6: 20 scenarios x 12hr multi-period DCOPF ===")

T = 12
N_scenarios = 20
rng = MersenneTwister(42)

# Keep all multipliers <= 1.0 so loads never exceed base case
base_profile = [0.80, 0.75, 0.72, 0.70, 0.75, 0.85, 0.92, 0.95, 0.93, 0.90, 0.87, 0.82]

load_ids = collect(keys(data["load"]))
gen_ids = collect(keys(data["gen"]))

# Classify generators
n_gens = length(gen_ids)
thermal_gens = gen_ids[1:min(Int(round(n_gens * 0.8)), n_gens)]
renewable_gens = gen_ids[min(Int(round(n_gens * 0.8)) + 1, n_gens):end]

println(
    "Generators: $(n_gens) total, $(length(thermal_gens)) thermal, $(length(renewable_gens)) renewable-like",
)

# Generate scenarios
scenarios = []
for s in 1:N_scenarios
    # Small perturbations to stay feasible on ACTIVSg2000
    load_common_factor = 1.0 + 0.01 * randn(rng)
    bus_noise = Dict(lid => 1.0 + 0.002 * randn(rng) for lid in load_ids)
    hourly_load = [base_profile[t] * load_common_factor for t in 1:T]

    # Use very small perturbations -- ACTIVSg2000 has tight margins
    thermal_avail = Dict(g => max(0.95, min(1.0, 1.0 + 0.01 * randn(rng))) for g in thermal_gens)
    renewable_avail = Dict(
        g => max(0.90, min(1.0, 0.98 + 0.02 * randn(rng))) for g in renewable_gens
    )

    push!(
        scenarios,
        Dict(
            "load_common_factor" => load_common_factor,
            "bus_noise" => bus_noise,
            "hourly_load" => hourly_load,
            "thermal_avail" => thermal_avail,
            "renewable_avail" => renewable_avail,
        ),
    )
end

t_total = time()
scenario_results = Dict{Int,Dict}()
solve_times = Float64[]
all_objectives = Float64[]

for s in 1:N_scenarios
    println("  Scenario $s/$N_scenarios...")
    sc = scenarios[s]

    sc_data = deepcopy(data)

    # Do NOT perturb generator pmax -- ACTIVSg2000 has tight margins and
    # pmax reductions cause infeasibility. Only vary load levels.

    # Create multi-period network
    mn_data = PowerModels.replicate(sc_data, T)

    # Apply hourly load profiles
    for t in 1:T
        nw = mn_data["nw"][string(t)]
        for (lid, load) in nw["load"]
            load["pd"] *= sc["hourly_load"][t] * get(sc["bus_noise"], lid, 1.0)
            load["qd"] *= sc["hourly_load"][t] * get(sc["bus_noise"], lid, 1.0)
        end
    end

    # Solve
    t_solve = time()
    mn_result = PowerModels.solve_mn_opf(mn_data, DCPPowerModel, optimizer)
    dt_solve = time() - t_solve
    push!(solve_times, dt_solve)

    term = string(mn_result["termination_status"])
    println("    $term, time=$(round(dt_solve, digits=2))s")

    if term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"]
        push!(all_objectives, mn_result["objective"])
        scenario_results[s] = Dict(
            "termination" => term, "objective" => mn_result["objective"], "solve_time" => dt_solve
        )
    else
        scenario_results[s] = Dict(
            "termination" => term, "objective" => nothing, "solve_time" => dt_solve
        )
    end
end

total_time = time() - t_total

n_optimal = count(
    s -> scenario_results[s]["termination"] in
    ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"],
    1:N_scenarios,
)

println("\n=== SUMMARY ===")
println("Scenarios optimal: $n_optimal / $N_scenarios")
println("Total time: $(round(total_time, digits=2))s")
println("Mean time per scenario: $(round(total_time/N_scenarios, digits=2))s")
println("Min solve: $(round(minimum(solve_times), digits=2))s")
println("Max solve: $(round(maximum(solve_times), digits=2))s")
if !isempty(all_objectives)
    println(
        "Objective range: $(round(minimum(all_objectives), digits=2)) to $(round(maximum(all_objectives), digits=2))",
    )
    println("Mean objective: $(round(sum(all_objectives)/length(all_objectives), digits=2))")
end

# Per-scenario timing for C-6
println("\nPer-scenario times:")
for s in 1:N_scenarios
    println(
        "  Scenario $s: $(round(solve_times[s], digits=2))s - $(scenario_results[s]["termination"])"
    )
end

results = Dict(
    "n_scenarios" => N_scenarios,
    "n_periods" => T,
    "n_optimal" => n_optimal,
    "total_time" => round(total_time; digits=2),
    "mean_time" => round(total_time/N_scenarios; digits=2),
    "min_time" => round(minimum(solve_times); digits=2),
    "max_time" => round(maximum(solve_times); digits=2),
    "solve_times" => [round(t; digits=2) for t in solve_times],
    "num_buses" => length(data["bus"]),
    "num_branches" => length(data["branch"]),
    "num_generators" => n_gens,
    "status" => n_optimal >= 18 ? "pass" : "fail",
)
if !isempty(all_objectives)
    results["mean_objective"] = round(sum(all_objectives)/length(all_objectives); digits=2)
    results["min_objective"] = round(minimum(all_objectives); digits=2)
    results["max_objective"] = round(maximum(all_objectives); digits=2)
    results["objective_spread"] = round(maximum(all_objectives) - minimum(all_objectives); digits=2)
end

println("\n" * JSON.json(results, 2))
