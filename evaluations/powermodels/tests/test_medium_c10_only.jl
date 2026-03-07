#=
C-10: Distributed Slack OPF on MEDIUM (10k-bus) - standalone run
=#

using PowerModels, JuMP, Ipopt, JSON
using LinearAlgebra

const NETWORK_FILE = "/workspace/.claude/worktrees/eval/powermodels-v4/data/networks/case_ACTIVSg10k.m"

println("=== Warming up ===")
_d = PowerModels.parse_file(
    "/workspace/.claude/worktrees/eval/powermodels-v4/data/networks/case39.m"
)
PowerModels.solve_dc_opf(_d, Ipopt.Optimizer)

function fix_costs!(data)
    for (id, gen) in data["gen"]
        if gen["model"] == 2 && (gen["ncost"] == 0 || isempty(gen["cost"]))
            gen["cost"] = [0.0, 0.0, 0.0]
            gen["ncost"] = 3
        end
    end
end

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
        println("PTDF memory: $(round(sizeof(H) / 1e6, digits=1)) MB")

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

        t_dist = time()
        Hw = H * w
        H_dist = H .- Hw
        dist_time = time() - t_dist
        println("H_dist construction: $(round(dist_time, digits=3))s")

        max_diff = maximum(abs.(H_dist .- H))
        println("Max |H_dist - H| = $(round(max_diff, digits=6))")

        results["status"] =
            ss_term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"] ? "pass" : "fail"
        results["single_slack_term"] = ss_term
        results["single_slack_objective"] = round(ss_result["objective"]; digits=2)
        results["single_slack_time"] = round(ss_time; digits=2)
        results["ptdf_time"] = round(ptdf_time; digits=2)
        results["ptdf_dims"] = "$(nbr) x $(nb)"
        results["n_nonzero_weights"] = n_nonzero_w
        results["H_dist_max_diff_from_H"] = round(max_diff; digits=6)
        results["ptdf_mem_mb"] = round(sizeof(H) / 1e6; digits=1)
        results["dist_construction_time"] = round(dist_time; digits=3)
        println("C-10: DONE")
    catch e
        results["status"] = "fail"
        results["error"] = string(typeof(e), ": ", sprint(showerror, e))
        println("C-10 ERROR: $(results["error"])")
    end

    results["wall_clock"] = round(time() - t_c10; digits=2)
    println("C-10 total wall clock: $(results["wall_clock"])s")
    println("\n" * JSON.json(results, 2))
    return results
end

run_c10()
