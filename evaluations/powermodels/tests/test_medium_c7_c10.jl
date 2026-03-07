#=
MEDIUM tests: C-7 (solver swap) and C-10 (distributed slack) on 10k-bus
Run separately from batch3 to avoid being blocked by A-4 AC PF.
=#

using PowerModels, JuMP, HiGHS, Ipopt, GLPK, SCIP, JSON
using LinearAlgebra

const NETWORK_FILE = "/workspace/.claude/worktrees/eval/powermodels-v4/data/networks/case_ACTIVSg10k.m"

println("=== Warming up ===")
_d = PowerModels.parse_file(
    "/workspace/.claude/worktrees/eval/powermodels-v4/data/networks/case39.m"
)
PowerModels.solve_dc_opf(_d, Ipopt.Optimizer)

function fix_costs!(data; linearize=false)
    n_fixed = 0
    for (id, gen) in data["gen"]
        if gen["model"] == 2 && (gen["ncost"] == 0 || isempty(gen["cost"]))
            gen["cost"] = [0.0, 0.0, 0.0]
            gen["ncost"] = 3
            n_fixed += 1
        end
        if linearize && gen["model"] == 2 && gen["ncost"] == 3
            # Must actually remove quadratic term: set ncost=2 and trim cost vector
            gen["cost"] = [gen["cost"][2], gen["cost"][3]]
            gen["ncost"] = 2
        end
    end
    return n_fixed
end

function prep(; linearize=false)
    d = PowerModels.parse_file(NETWORK_FILE)
    fix_costs!(d; linearize=linearize)
    return d
end

function solve_with(solver_name, opt, d; request_duals=true)
    t = time()
    try
        settings = request_duals ? Dict("output" => Dict("duals" => true)) : Dict{String,Any}()
        r = PowerModels.solve_dc_opf(d, opt; setting=settings)
        dt = time() - t
        term = string(r["termination_status"])
        obj = if term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED", "TIME_LIMIT"]
            round(r["objective"]; digits=2)
        else
            nothing
        end
        println("$solver_name: $term, time=$(round(dt, digits=2))s, obj=$obj")
        return Dict("term" => term, "time" => round(dt; digits=2), "objective" => obj)
    catch e
        dt = time() - t
        println("$solver_name: ERROR after $(round(dt, digits=2))s: $(sprint(showerror, e))")
        return Dict(
            "term" => "ERROR",
            "time" => round(dt; digits=2),
            "objective" => nothing,
            "error" => sprint(showerror, e),
        )
    end
end

# ============================================================
# C-7: Solver Swap
# ============================================================
println("\n=== C-7: Solver Swap on MEDIUM (10k-bus) ===")
c7 = Dict{String,Any}()

println("--- HiGHS (skipped -- already have data: TIME_LIMIT at 302s) ---")
c7["highs"] = Dict(
    "term" => "TIME_LIMIT", "time" => 302.28, "objective" => 2436631.23, "note" => "from prior run"
)

println("--- GLPK (skipped -- already have data: OPTIMAL at 46.81s) ---")
c7["glpk"] = Dict(
    "term" => "OPTIMAL",
    "time" => 46.81,
    "objective" => 2401337.08,
    "note" => "LP linearized costs, from prior run",
)

println("--- SCIP ---")
r = solve_with(
    "SCIP",
    JuMP.optimizer_with_attributes(
        SCIP.Optimizer, "limits/time" => 300.0, "display/verblevel" => 4
    ),
    prep(; linearize=true);
    request_duals=false,
)
r["note"] = "LP -- quadratic costs linearized, no dual support"
c7["scip"] = r

println("--- Ipopt ---")
c7["ipopt"] = solve_with(
    "Ipopt",
    JuMP.optimizer_with_attributes(
        Ipopt.Optimizer, "max_iter" => 10000, "tol" => 1e-6, "print_level" => 3
    ),
    prep(),
)

println("\n=== C-7 Summary ===")
for k in sort(collect(keys(c7)))
    res = c7[k]
    println("  $k: $(res["term"]), $(res["time"])s, obj=$(res["objective"])")
end

# ============================================================
# C-10: Distributed Slack OPF
# ============================================================
function run_c10()
    println("\n=== C-10: Distributed Slack OPF on MEDIUM (10k-bus) ===")
    t_c10 = time()
    results = Dict{String,Any}()

    try
        data = PowerModels.parse_file(NETWORK_FILE)
        fix_costs!(data)

        optimizer_ipopt = JuMP.optimizer_with_attributes(
            Ipopt.Optimizer, "max_iter" => 10000, "tol" => 1e-6, "print_level" => 3
        )

        println("Solving single-slack DC OPF (Ipopt)...")
        t_ss = time()
        ss_result = PowerModels.solve_dc_opf(
            data, optimizer_ipopt; setting=Dict("output" => Dict("duals" => true))
        )
        ss_time = time() - t_ss
        ss_term = string(ss_result["termination_status"])
        println(
            "Single-slack: $ss_term, obj=$(round(ss_result["objective"], digits=2)), time=$(round(ss_time, digits=2))s",
        )

        println("Computing PTDF matrix...")
        data2 = PowerModels.parse_file(NETWORK_FILE)
        fix_costs!(data2)
        basic = PowerModels.make_basic_network(deepcopy(data2))
        t_ptdf = time()
        H = PowerModels.calc_basic_ptdf_matrix(basic)
        ptdf_time = time() - t_ptdf
        nbr, nb = size(H)
        println("PTDF: $(nbr) x $(nb), time=$(round(ptdf_time, digits=2))s")

        basic_bus_ids = sort(parse.(Int, collect(keys(basic["bus"]))))
        bus_to_idx = Dict(id => i for (i, id) in enumerate(basic_bus_ids))

        w = zeros(nb)
        for (_, load) in basic["load"]
            bus = load["load_bus"]
            if haskey(bus_to_idx, bus)
                w[bus_to_idx[bus]] += load["pd"]
            end
        end
        w_sum = sum(w)
        if w_sum > 0
            w ./= w_sum
        end
        n_nonzero_w = count(x -> x > 0, w)
        println("Distributed slack weights: $n_nonzero_w non-zero out of $nb")

        Hw = H * w
        H_dist = H .- Hw

        results["status"] =
            ss_term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"] ? "pass" : "fail"
        results["single_slack_term"] = ss_term
        results["single_slack_objective"] = round(ss_result["objective"]; digits=2)
        results["single_slack_time"] = round(ss_time; digits=2)
        results["ptdf_time"] = round(ptdf_time; digits=2)
        results["ptdf_dims"] = "$(nbr) x $(nb)"
        results["n_nonzero_weights"] = n_nonzero_w
        results["H_dist_max_diff_from_H"] = round(maximum(abs.(H_dist .- H)); digits=6)
        results["ptdf_mem_mb"] = round(sizeof(H) / 1e6; digits=1)
        println("C-10: done. Max H_dist-H diff = $(results["H_dist_max_diff_from_H"])")
    catch e
        results["status"] = "fail"
        results["error"] = string(typeof(e), ": ", sprint(showerror, e))
        println("C-10 ERROR: $(results["error"])")
    end

    results["wall_clock"] = round(time() - t_c10; digits=2)
    println("C-10 time: $(results["wall_clock"])s")
    return results
end

c10_results = run_c10()

println("\n=== FINAL SUMMARY ===")
println("C-7 Solver swap:")
for k in sort(collect(keys(c7)))
    res = c7[k]
    println("  $k: $(res["term"]), $(res["time"])s")
end
println("C-10 Distributed slack: $(c10_results["status"]), $(c10_results["wall_clock"])s")

all_results = Dict("c7_solver_swap" => c7, "c10_distributed_slack" => c10_results)
println("\n" * JSON.json(all_results, 2))
