#=
Batch MEDIUM test runner: A-1 (DCPF), A-2 (ACPF), A-3 (DCOPF) on ACTIVSg 10000-bus
Runs all three in a single Julia session to avoid repeated startup overhead.
Also covers C-1, C-2, C-3 scalability measurements.
=#

using PowerModels, JuMP, HiGHS, Ipopt, JSON
using LinearAlgebra

const NETWORK_FILE = joinpath(@__DIR__, "..", "..", "..", "data", "networks", "case_ACTIVSg10k.m")
const NETWORK_SMALL = joinpath(@__DIR__, "..", "..", "..", "data", "networks", "case_ACTIVSg2000.m")

# Warm up on small network
println("=== Warming up on case39 ===")
_d = PowerModels.parse_file(joinpath(@__DIR__, "..", "..", "..", "data", "networks", "case39.m"))
PowerModels.compute_dc_pf(_d)
PowerModels.compute_ac_pf(_d)
PowerModels.solve_dc_opf(_d, Ipopt.Optimizer)

println("\n=== A-1 / C-1: DCPF on MEDIUM (10000-bus) ===")
t_parse = time()
data = PowerModels.parse_file(NETWORK_FILE)
parse_time = time() - t_parse
println("Parse time: $(round(parse_time, digits=2))s")
println(
    "Buses: $(length(data["bus"])), Branches: $(length(data["branch"])), Gens: $(length(data["gen"]))",
)

t_dcpf = time()
pf_result = PowerModels.compute_dc_pf(data)
dcpf_time = time() - t_dcpf
dcpf_converged = pf_result["termination_status"]
println("DCPF converged: $dcpf_converged")
println("DCPF solve time: $(round(dcpf_time, digits=4))s")

sol = pf_result["solution"]
PowerModels.update_data!(data, sol)
branch_flows_dc = PowerModels.calc_branch_flow_dc(data)

# Sample angles
bus_ids_sorted = sort(collect(keys(sol["bus"])); by=x->parse(Int, x))
println(
    "Sample angles: ",
    join(["bus $(k): $(round(sol["bus"][k]["va"], digits=4))" for k in bus_ids_sorted[1:5]], ", "),
)
println("Num bus angles: $(length(sol["bus"]))")
println("Num branch flows: $(length(branch_flows_dc["branch"]))")

mem_after_dcpf = round(Base.gc_live_bytes() / 1e6; digits=1)
println("Memory after DCPF: $(mem_after_dcpf) MB")

a1_results = Dict(
    "status" => dcpf_converged ? "pass" : "fail",
    "parse_time" => round(parse_time; digits=3),
    "solve_time" => round(dcpf_time; digits=4),
    "num_buses" => length(data["bus"]),
    "num_branches" => length(data["branch"]),
    "num_generators" => length(data["gen"]),
    "memory_mb" => mem_after_dcpf,
)

println("\n=== A-2 / C-2: ACPF on MEDIUM (10000-bus) ===")
data2 = PowerModels.parse_file(NETWORK_FILE)

t_acpf = time()
ac_result = PowerModels.compute_ac_pf(data2)
acpf_time = time() - t_acpf
ac_converged = ac_result["termination_status"]
println("ACPF converged: $ac_converged")
println("ACPF solve time: $(round(acpf_time, digits=4))s")

a2_results = Dict{String,Any}(
    "converged" => string(ac_converged), "solve_time" => round(acpf_time; digits=4)
)

if if ac_converged isa Bool
    ac_converged
else
    string(ac_converged) in ("LOCALLY_SOLVED", "OPTIMAL", "true")
end
    ac_sol = ac_result["solution"]
    vm_vals = [bus["vm"] for (_, bus) in ac_sol["bus"]]
    println(
        "Vm range: $(round(minimum(vm_vals), digits=4)) to $(round(maximum(vm_vals), digits=4))"
    )
    println("Vm mean: $(round(sum(vm_vals)/length(vm_vals), digits=4))")

    PowerModels.update_data!(data2, ac_sol)
    ac_flows = PowerModels.calc_branch_flow_ac(data2)
    total_p_loss = sum(br["pf"] + br["pt"] for (_, br) in ac_flows["branch"])
    total_q_loss = sum(br["qf"] + br["qt"] for (_, br) in ac_flows["branch"])
    println("Total P loss: $(round(total_p_loss, digits=2)) p.u.")
    println("Total Q loss: $(round(total_q_loss, digits=2)) p.u.")

    a2_results["status"] = "pass"
    a2_results["vm_min"] = round(minimum(vm_vals); digits=4)
    a2_results["vm_max"] = round(maximum(vm_vals); digits=4)
    a2_results["vm_mean"] = round(sum(vm_vals)/length(vm_vals); digits=4)
    a2_results["total_p_loss"] = round(total_p_loss; digits=4)
    a2_results["total_q_loss"] = round(total_q_loss; digits=4)
    a2_results["num_branch_flows"] = length(ac_flows["branch"])
else
    a2_results["status"] = "fail"
    println("ACPF failed to converge")
end

mem_after_acpf = round(Base.gc_live_bytes() / 1e6; digits=1)
a2_results["memory_mb"] = mem_after_acpf
println("Memory after ACPF: $(mem_after_acpf) MB")

println("\n=== A-3 / C-3: DC OPF on MEDIUM (10000-bus) ===")
data3 = PowerModels.parse_file(NETWORK_FILE)

# Fix empty cost arrays
n_fixed = let cnt = 0
    for (id, gen) in data3["gen"]
        if gen["model"] == 2 && (gen["ncost"] == 0 || isempty(gen["cost"]))
            gen["cost"] = [0.0, 0.0, 0.0]
            gen["ncost"] = 3
            cnt += 1
        end
    end
    cnt
end
println("Fixed $n_fixed generators with empty costs")

# Count zero rate_a branches
zero_rate = count(br -> get(br, "rate_a", 0.0) == 0.0, values(data3["branch"]))
println("Branches with zero rate_a: $zero_rate / $(length(data3["branch"]))")

# Solve with Ipopt (QP-capable)
optimizer_ipopt = JuMP.optimizer_with_attributes(
    Ipopt.Optimizer, "max_iter" => 10000, "tol" => 1e-6, "print_level" => 3
)

println("Solving DC OPF with Ipopt...")
t_dcopf = time()
opf_result = PowerModels.solve_dc_opf(
    data3, optimizer_ipopt; setting=Dict("output" => Dict("duals" => true))
)
dcopf_time = time() - t_dcopf
opf_term = string(opf_result["termination_status"])
println("DC OPF termination: $opf_term")
println("DC OPF solve time: $(round(dcopf_time, digits=2))s")
println("DC OPF objective: $(round(opf_result["objective"], digits=2))")

a3_results = Dict(
    "termination" => opf_term,
    "solve_time" => round(dcopf_time; digits=3),
    "objective" => round(opf_result["objective"]; digits=2),
    "solver" => "Ipopt",
    "generators_cost_fixed" => n_fixed,
    "branches_zero_rate_a" => zero_rate,
)

if opf_term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"]
    a3_results["status"] = "pass"

    total_gen = sum(gen["pg"] for (_, gen) in opf_result["solution"]["gen"])
    println("Total generation: $(round(total_gen, digits=2)) p.u.")
    a3_results["total_generation_pu"] = round(total_gen; digits=2)

    # LMPs
    lmp_vals = Float64[]
    for (_, bus) in opf_result["solution"]["bus"]
        if haskey(bus, "lam_kcl_r")
            push!(lmp_vals, bus["lam_kcl_r"])
        end
    end
    if !isempty(lmp_vals)
        println(
            "LMP range: $(round(minimum(lmp_vals), digits=2)) to $(round(maximum(lmp_vals), digits=2))",
        )
        a3_results["lmp_min"] = round(minimum(lmp_vals); digits=2)
        a3_results["lmp_max"] = round(maximum(lmp_vals); digits=2)
        a3_results["lmp_range"] = round(maximum(lmp_vals) - minimum(lmp_vals); digits=2)
        a3_results["num_lmps"] = length(lmp_vals)
    end

    a3_results["num_branch_flows"] = length(opf_result["solution"]["branch"])
else
    a3_results["status"] = "fail"
end

# Also try HiGHS for C-3 comparison
println("\nSolving DC OPF with HiGHS...")
data3b = PowerModels.parse_file(NETWORK_FILE)
for (id, gen) in data3b["gen"]
    if gen["model"] == 2 && (gen["ncost"] == 0 || isempty(gen["cost"]))
        gen["cost"] = [0.0, 0.0, 0.0]
        gen["ncost"] = 3
    end
end

optimizer_highs = JuMP.optimizer_with_attributes(
    HiGHS.Optimizer,
    "time_limit" => 300.0,
    "presolve" => "on",
    "threads" => 1,
    "output_flag" => true,
)

t_highs = time()
opf_highs = PowerModels.solve_dc_opf(
    data3b, optimizer_highs; setting=Dict("output" => Dict("duals" => true))
)
highs_time = time() - t_highs
highs_term = string(opf_highs["termination_status"])
println("HiGHS DC OPF termination: $highs_term")
println("HiGHS DC OPF solve time: $(round(highs_time, digits=2))s")
if highs_term in ["OPTIMAL", "LOCALLY_SOLVED"]
    println("HiGHS objective: $(round(opf_highs["objective"], digits=2))")
end

a3_results["highs_termination"] = highs_term
a3_results["highs_solve_time"] = round(highs_time; digits=3)
if highs_term in ["OPTIMAL", "LOCALLY_SOLVED"]
    a3_results["highs_objective"] = round(opf_highs["objective"]; digits=2)
end

# Also try GLPK for C-3
println("\nSolving DC OPF with GLPK...")
using GLPK
data3c = PowerModels.parse_file(NETWORK_FILE)
for (id, gen) in data3c["gen"]
    if gen["model"] == 2 && (gen["ncost"] == 0 || isempty(gen["cost"]))
        gen["cost"] = [0.0, 0.0, 0.0]
        gen["ncost"] = 3
    end
    # Linearize costs for GLPK (LP solver only)
    if gen["model"] == 2 && gen["ncost"] == 3
        gen["cost"][1] = 0.0  # Remove quadratic term
    end
end

optimizer_glpk = JuMP.optimizer_with_attributes(
    GLPK.Optimizer, "tm_lim" => 300000, "msg_lev" => GLPK.GLP_MSG_ON
)

t_glpk = time()
opf_glpk = PowerModels.solve_dc_opf(
    data3c, optimizer_glpk; setting=Dict("output" => Dict("duals" => true))
)
glpk_time = time() - t_glpk
glpk_term = string(opf_glpk["termination_status"])
println("GLPK DC OPF termination: $glpk_term")
println("GLPK DC OPF solve time: $(round(glpk_time, digits=2))s")
if glpk_term in ["OPTIMAL", "LOCALLY_SOLVED"]
    println("GLPK objective: $(round(opf_glpk["objective"], digits=2))")
end

a3_results["glpk_termination"] = glpk_term
a3_results["glpk_solve_time"] = round(glpk_time; digits=3)
if glpk_term in ["OPTIMAL", "LOCALLY_SOLVED"]
    a3_results["glpk_objective"] = round(opf_glpk["objective"]; digits=2)
end

mem_after_opf = round(Base.gc_live_bytes() / 1e6; digits=1)
a3_results["memory_mb"] = mem_after_opf

println("\n=== SUMMARY ===")
println(
    "A-1 DCPF: $(a1_results["status"]), solve=$(a1_results["solve_time"])s, mem=$(a1_results["memory_mb"])MB",
)
println(
    "A-2 ACPF: $(a2_results["status"]), solve=$(a2_results["solve_time"])s, mem=$(a2_results["memory_mb"])MB",
)
println("A-3 DCOPF: $(a3_results["status"]), solve=$(a3_results["solve_time"])s")

all_results = Dict("a1_dcpf" => a1_results, "a2_acpf" => a2_results, "a3_dcopf" => a3_results)
println("\n" * JSON.json(all_results, 2))
