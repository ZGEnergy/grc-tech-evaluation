#=
Batch MEDIUM test runner #3:
  B-1 (custom constraints on 10k-bus)
  A-4 (AC feasibility on 10k-bus)
  C-7 (solver swap: HiGHS, GLPK, SCIP, Ipopt on 10k-bus DC OPF)
  C-10 (distributed slack on 10k-bus)
=#

using PowerModels, JuMP, HiGHS, Ipopt, GLPK, SCIP, JSON
using LinearAlgebra

const NETWORK_FILE = joinpath(@__DIR__, "..", "..", "..", "data", "networks", "case_ACTIVSg10k.m")

# Warm up on tiny network
println("=== Warming up ===")
_d = PowerModels.parse_file(joinpath(@__DIR__, "..", "..", "..", "data", "networks", "case39.m"))
PowerModels.solve_dc_opf(_d, Ipopt.Optimizer)
PowerModels.compute_ac_pf(_d)

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

function find_max_flow_branch(base_result)
    max_flow_id = ""
    max_flow_val = 0.0
    for (id, br) in base_result["solution"]["branch"]
        pf = abs(br["pf"])
        if pf > max_flow_val
            max_flow_val = pf
            max_flow_id = id
        end
    end
    return max_flow_id, max_flow_val
end

function run_b1()
    println("\n=== B-1: Custom Constraints on MEDIUM (10k-bus) ===")
    t_b1 = time()

    data_b1 = PowerModels.parse_file(NETWORK_FILE)
    fix_costs!(data_b1)

    optimizer_ipopt = JuMP.optimizer_with_attributes(
        Ipopt.Optimizer, "max_iter" => 10000, "tol" => 1e-6, "print_level" => 3
    )

    println("Solving base DC OPF...")
    t_base = time()
    base_result = PowerModels.solve_dc_opf(
        data_b1, optimizer_ipopt; setting=Dict("output" => Dict("duals" => true))
    )
    base_time = time() - t_base
    base_term = string(base_result["termination_status"])
    println(
        "Base DC OPF: $base_term, objective=$(round(base_result["objective"], digits=2)), time=$(round(base_time, digits=2))s",
    )

    max_flow_id, max_flow_val = find_max_flow_branch(base_result)
    println("Max flow branch: $max_flow_id, flow=$(round(max_flow_val, digits=4)) p.u.")

    data_b1b = PowerModels.parse_file(NETWORK_FILE)
    fix_costs!(data_b1b)

    gate_limit = 0.8 * max_flow_val
    gate_branch_id = max_flow_id
    br_data = data_b1b["branch"][gate_branch_id]
    f_bus = br_data["f_bus"]
    t_bus = br_data["t_bus"]
    br_idx = parse(Int, gate_branch_id)

    pm = PowerModels.instantiate_model(data_b1b, PowerModels.DCPPowerModel, PowerModels.build_opf)
    nw_id = PowerModels.nw_id_default
    p_vars = PowerModels.var(pm, nw_id, :p)
    flow_var = p_vars[(br_idx, f_bus, t_bus)]

    jump_model = pm.model
    gate_con_upper = @constraint(jump_model, flow_var <= gate_limit)
    gate_con_lower = @constraint(jump_model, flow_var >= -gate_limit)

    println("Solving constrained DC OPF...")
    t_constrained = time()
    constrained_result = PowerModels.optimize_model!(pm; optimizer=optimizer_ipopt)
    constrained_time = time() - t_constrained
    constrained_term = string(constrained_result["termination_status"])
    println(
        "Constrained: $constrained_term, objective=$(round(constrained_result["objective"], digits=2)), time=$(round(constrained_time, digits=2))s",
    )

    dual_upper = JuMP.dual(gate_con_upper)
    dual_lower = JuMP.dual(gate_con_lower)
    constrained_flow = JuMP.value(flow_var)

    b1_time = time() - t_b1
    println("B-1 total: $(round(b1_time, digits=2))s")
    println(
        "Flow gate: branch $gate_branch_id, limit=$(round(gate_limit, digits=4)), actual=$(round(constrained_flow, digits=4))",
    )
    println("Duals: upper=$(round(dual_upper, digits=4)), lower=$(round(dual_lower, digits=4))")
    println(
        "Obj increase: $(round(constrained_result["objective"] - base_result["objective"], digits=2))",
    )

    return Dict(
        "status" => if constrained_term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"]
            "pass"
        else
            "fail"
        end,
        "base_term" => base_term,
        "base_objective" => round(base_result["objective"]; digits=2),
        "base_solve_time" => round(base_time; digits=2),
        "constrained_term" => constrained_term,
        "constrained_objective" => round(constrained_result["objective"]; digits=2),
        "constrained_solve_time" => round(constrained_time; digits=2),
        "gate_branch" => gate_branch_id,
        "gate_limit" => round(gate_limit; digits=4),
        "constrained_flow" => round(constrained_flow; digits=4),
        "dual_upper" => round(dual_upper; digits=6),
        "dual_lower" => round(dual_lower; digits=6),
        "objective_increase" =>
            round(constrained_result["objective"] - base_result["objective"]; digits=2),
        "constraint_binding" => abs(abs(constrained_flow) - gate_limit) < 1e-3,
        "wall_clock" => round(b1_time; digits=2),
        "num_buses" => length(data_b1["bus"]),
        "num_branches" => length(data_b1["branch"]),
    )
end

function run_a4()
    println("\n=== A-4: AC Feasibility on MEDIUM (10k-bus) ===")
    t_a4 = time()

    data_a4 = PowerModels.parse_file(NETWORK_FILE)
    fix_costs!(data_a4)

    optimizer_ipopt = JuMP.optimizer_with_attributes(
        Ipopt.Optimizer, "max_iter" => 10000, "tol" => 1e-6, "print_level" => 3
    )

    println("Solving DC OPF (Ipopt)...")
    opf_a4 = PowerModels.solve_dc_opf(data_a4, optimizer_ipopt)
    dc_term = string(opf_a4["termination_status"])
    println("DC OPF: $dc_term, obj=$(round(opf_a4["objective"], digits=2))")

    results = Dict{String,Any}("dcopf_term" => dc_term)

    if !(dc_term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"])
        results["status"] = "fail"
        results["fail_reason"] = "DC OPF did not converge"
        results["wall_clock"] = round(time() - t_a4; digits=2)
        return results
    end

    dc_sol = opf_a4["solution"]
    for (id, gen) in dc_sol["gen"]
        data_a4["gen"][id]["pg"] = gen["pg"]
    end

    println("Running AC PF (flat start)...")
    t_acpf = time()
    ac_result = PowerModels.compute_ac_pf(data_a4)
    acpf_time = time() - t_acpf
    ac_converged = ac_result["termination_status"]
    println("AC PF converged: $ac_converged ($(round(acpf_time, digits=2))s)")
    results["ac_converged_flat"] = ac_converged

    if !(ac_converged isa Bool ? ac_converged : false)
        println("Trying Ipopt-based solve_ac_pf...")
        ipopt_acpf = JuMP.optimizer_with_attributes(
            Ipopt.Optimizer,
            "max_iter" => 10000,
            "tol" => 1e-6,
            "acceptable_tol" => 1e-4,
            "print_level" => 3,
        )
        data_a4b = PowerModels.parse_file(NETWORK_FILE)
        fix_costs!(data_a4b)
        for (id, gen) in dc_sol["gen"]
            data_a4b["gen"][id]["pg"] = gen["pg"]
        end
        ac_result = PowerModels.solve_ac_pf(data_a4b, ipopt_acpf)
        ac_term_str = string(ac_result["termination_status"])
        ac_converged = ac_term_str in ["LOCALLY_SOLVED", "OPTIMAL", "ALMOST_LOCALLY_SOLVED"]
        results["ac_converged_ipopt"] = ac_converged
        data_a4 = data_a4b
    end

    if !(ac_converged isa Bool ? ac_converged : true)
        results["status"] = "fail"
        results["fail_reason"] = "AC PF did not converge"
        results["wall_clock"] = round(time() - t_a4; digits=2)
        return results
    end

    ac_sol = ac_result["solution"]
    PowerModels.update_data!(data_a4, ac_sol)
    ac_flows = PowerModels.calc_branch_flow_ac(data_a4)

    vm_vals = [bus["vm"] for (_, bus) in ac_sol["bus"]]
    n_v_violations = 0
    for (id, bus) in ac_sol["bus"]
        vm = bus["vm"]
        vmin = data_a4["bus"][id]["vmin"]
        vmax = data_a4["bus"][id]["vmax"]
        if vm < vmin - 1e-4 || vm > vmax + 1e-4
            n_v_violations += 1
        end
    end

    n_thermal = 0
    for (id, br) in ac_flows["branch"]
        rate_a = data_a4["branch"][id]["rate_a"]
        if rate_a > 0 && rate_a < 1e10
            pf = abs(br["pf"])
            qf = abs(get(br, "qf", 0.0))
            sf = sqrt(pf^2 + qf^2)
            if sf > rate_a * 1.001
                n_thermal += 1
            end
        end
    end

    total_p_loss = sum(br["pf"] + br["pt"] for (_, br) in ac_flows["branch"])

    results["status"] = "pass"
    results["vm_min"] = round(minimum(vm_vals); digits=4)
    results["vm_max"] = round(maximum(vm_vals); digits=4)
    results["vm_mean"] = round(sum(vm_vals)/length(vm_vals); digits=4)
    results["voltage_violations"] = n_v_violations
    results["thermal_violations"] = n_thermal
    results["total_p_loss_pu"] = round(total_p_loss; digits=4)
    results["wall_clock"] = round(time() - t_a4; digits=2)

    println("Vm range: $(results["vm_min"]) to $(results["vm_max"])")
    println("Voltage violations: $n_v_violations, Thermal: $n_thermal")
    println("P loss: $(round(total_p_loss, digits=2)) p.u.")
    println("A-4 time: $(results["wall_clock"])s")

    return results
end

function run_c7()
    println("\n=== C-7: Solver Swap on MEDIUM (10k-bus) ===")
    c7 = Dict{String,Any}()

    function prep(; linearize=false)
        d = PowerModels.parse_file(NETWORK_FILE)
        fix_costs!(d; linearize=linearize)
        return d
    end

    function solve_with(solver_name, opt, d)
        t = time()
        r = PowerModels.solve_dc_opf(d, opt; setting=Dict("output" => Dict("duals" => true)))
        dt = time() - t
        term = string(r["termination_status"])
        obj = if term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"]
            round(r["objective"]; digits=2)
        else
            nothing
        end
        println("$solver_name: $term, time=$(round(dt, digits=2))s, obj=$obj")
        return Dict("term" => term, "time" => round(dt; digits=2), "objective" => obj)
    end

    println("--- HiGHS ---")
    c7["highs"] = solve_with(
        "HiGHS",
        JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "time_limit" => 300.0,
            "presolve" => "on",
            "threads" => 1,
            "output_flag" => true,
        ),
        prep(),
    )

    println("--- GLPK ---")
    r = solve_with(
        "GLPK",
        JuMP.optimizer_with_attributes(
            GLPK.Optimizer, "tm_lim" => 300000, "msg_lev" => GLPK.GLP_MSG_ON
        ),
        prep(; linearize=true),
    )
    r["note"] = "LP only -- quadratic costs linearized"
    c7["glpk"] = r

    println("--- SCIP ---")
    r = solve_with(
        "SCIP",
        JuMP.optimizer_with_attributes(
            SCIP.Optimizer, "limits/time" => 300.0, "display/verblevel" => 4
        ),
        prep(; linearize=true),
    )
    r["note"] = "LP -- quadratic costs linearized"
    c7["scip"] = r

    println("--- Ipopt ---")
    c7["ipopt"] = solve_with(
        "Ipopt",
        JuMP.optimizer_with_attributes(
            Ipopt.Optimizer, "max_iter" => 10000, "tol" => 1e-6, "print_level" => 3
        ),
        prep(),
    )

    return c7
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

# ============================================================
# Run all tests
# ============================================================
b1_results = run_b1()
a4_results = run_a4()
c7_results = run_c7()
c10_results = run_c10()

println("\n=== FINAL SUMMARY ===")
println("B-1 Custom constraints: $(b1_results["status"]), $(b1_results["wall_clock"])s")
println("A-4 AC feasibility: $(a4_results["status"]), $(a4_results["wall_clock"])s")
println("C-7 Solver swap:")
for (solver, res) in sort(collect(c7_results))
    println("  $solver: $(res["term"]), $(res["time"])s")
end
println("C-10 Distributed slack: $(c10_results["status"]), $(c10_results["wall_clock"])s")

all_results = Dict(
    "b1_custom_constraints" => b1_results,
    "a4_ac_feasibility" => a4_results,
    "c7_solver_swap" => c7_results,
    "c10_distributed_slack" => c10_results,
)
println("\n" * JSON.json(all_results, 2))
