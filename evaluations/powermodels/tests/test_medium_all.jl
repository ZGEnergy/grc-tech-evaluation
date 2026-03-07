#=
Batch MEDIUM test runner: A-1/C-1 (DCPF), A-2/C-2 (ACPF), A-3/C-3 (DCOPF)
on ACTIVSg 10000-bus network.
Suppresses PowerModels Memento warnings to avoid output overflow.
Writes results to JSON file for post-processing.
=#

using PowerModels, JuMP, HiGHS, Ipopt, GLPK, JSON

# Suppress PowerModels' Memento-based warnings (not Julia Logging)
# Memento is a dependency of PowerModels, access via PowerModels
const _Memento = Base.require(PowerModels, :Memento)
_Memento.setlevel!(_Memento.getlogger(PowerModels), "error")

const BASE_DIR = joinpath(@__DIR__, "..", "..", "..")
const NETWORK_FILE = joinpath(BASE_DIR, "data", "networks", "case_ACTIVSg10k.m")
const WARMUP_FILE = joinpath(BASE_DIR, "data", "networks", "case39.m")
const OUTPUT_FILE = joinpath(@__DIR__, "medium_results.json")

all_results = Dict{String,Any}()

# ─── Warm-up on tiny network ───
println("=== Warming up Julia JIT on case39 ===")
_d = PowerModels.parse_file(WARMUP_FILE)
PowerModels.compute_dc_pf(_d)
PowerModels.compute_ac_pf(_d)
_opt = JuMP.optimizer_with_attributes(Ipopt.Optimizer, "print_level" => 0)
PowerModels.solve_dc_opf(_d, _opt)
println("Warm-up complete.\n")

# ═══════════════════════════════════════════════════════════════
# A-1 / C-1: DCPF on MEDIUM (10000-bus)
# ═══════════════════════════════════════════════════════════════
println("=== A-1 / C-1: DCPF on MEDIUM ===")

mem_before = Base.gc_live_bytes()
t_parse = time()
data_dc = PowerModels.parse_file(NETWORK_FILE)
parse_time_dc = time() - t_parse
println("Parse time: $(round(parse_time_dc, digits=2))s")
println(
    "Buses: $(length(data_dc["bus"])), Branches: $(length(data_dc["branch"])), Gens: $(length(data_dc["gen"]))",
)

t_dcpf = time()
pf_result = PowerModels.compute_dc_pf(data_dc)
dcpf_time = time() - t_dcpf
dcpf_converged = pf_result["termination_status"]
println("DCPF converged: $dcpf_converged")
println("DCPF solve time: $(round(dcpf_time, digits=4))s")

sol_dc = pf_result["solution"]
PowerModels.update_data!(data_dc, sol_dc)
branch_flows_dc = PowerModels.calc_branch_flow_dc(data_dc)

# Sample angles
bus_ids_sorted = sort(collect(keys(sol_dc["bus"])); by=x->parse(Int, x))
println(
    "Sample angles: ",
    join(
        [
            "bus $(k): $(round(sol_dc["bus"][k]["va"], digits=4))" for
            k in bus_ids_sorted[1:min(5, length(bus_ids_sorted))]
        ],
        ", ",
    ),
)

mem_after_dcpf = Base.gc_live_bytes()
dcpf_mem_mb = round((mem_after_dcpf - mem_before) / 1e6; digits=1)
total_mem_dcpf = round(mem_after_dcpf / 1e6; digits=1)
println("DCPF memory (delta): $(dcpf_mem_mb) MB, total live: $(total_mem_dcpf) MB")

all_results["a1_dcpf"] = Dict(
    "status" => dcpf_converged ? "pass" : "fail",
    "parse_time" => round(parse_time_dc; digits=3),
    "solve_time" => round(dcpf_time; digits=4),
    "wall_clock" => round(parse_time_dc + dcpf_time; digits=3),
    "num_buses" => length(data_dc["bus"]),
    "num_branches" => length(data_dc["branch"]),
    "num_generators" => length(data_dc["gen"]),
    "num_loads" => length(data_dc["load"]),
    "num_bus_angles" => length(sol_dc["bus"]),
    "num_branch_flows" => length(branch_flows_dc["branch"]),
    "peak_memory_mb" => total_mem_dcpf,
    "memory_delta_mb" => dcpf_mem_mb,
)

# ═══════════════════════════════════════════════════════════════
# A-2 / C-2: ACPF on MEDIUM (10000-bus)
# ═══════════════════════════════════════════════════════════════
println("\n=== A-2 / C-2: ACPF on MEDIUM ===")

GC.gc()
mem_before_ac = Base.gc_live_bytes()
data_ac = PowerModels.parse_file(NETWORK_FILE)

# Attempt 1: flat start (default)
println("Solving ACPF (flat start)...")
t_acpf = time()
ac_result = PowerModels.compute_ac_pf(data_ac)
acpf_time = time() - t_acpf
ac_converged = ac_result["termination_status"]
println("ACPF converged: $ac_converged, time: $(round(acpf_time, digits=4))s")

convergence_attempt = 1
if !(
    if ac_converged isa Bool
        ac_converged
    else
        string(ac_converged) in ("LOCALLY_SOLVED", "OPTIMAL", "true")
    end
)
    println("Flat start failed. Trying DC warm start...")
    # DC warm start: solve DC first, use angles as initialization
    data_ac2 = PowerModels.parse_file(NETWORK_FILE)
    dc_init = PowerModels.compute_dc_pf(data_ac2)
    if dc_init["termination_status"] == true
        PowerModels.update_data!(data_ac2, dc_init["solution"])
    end
    t_acpf2 = time()
    ac_result = PowerModels.compute_ac_pf(data_ac2)
    acpf_time = time() - t_acpf2
    ac_converged = ac_result["termination_status"]
    convergence_attempt = 2
    println("DC warm start ACPF converged: $ac_converged, time: $(round(acpf_time, digits=4))s")
end

a2_results = Dict{String,Any}(
    "convergence_attempt" => convergence_attempt,
    "solve_time" => round(acpf_time; digits=4),
    "converged" => string(ac_converged),
)

is_conv = if ac_converged isa Bool
    ac_converged
else
    string(ac_converged) in ("LOCALLY_SOLVED", "OPTIMAL", "true")
end
if is_conv
    ac_sol = ac_result["solution"]
    vm_vals = [bus["vm"] for (_, bus) in ac_sol["bus"]]
    va_vals = [bus["va"] for (_, bus) in ac_sol["bus"]]
    println(
        "Vm range: $(round(minimum(vm_vals), digits=4)) to $(round(maximum(vm_vals), digits=4))"
    )
    println("Vm mean: $(round(sum(vm_vals)/length(vm_vals), digits=4))")

    data_ac_flows = convergence_attempt == 1 ? data_ac : data_ac2
    PowerModels.update_data!(data_ac_flows, ac_sol)
    ac_flows = PowerModels.calc_branch_flow_ac(data_ac_flows)
    total_p_loss = sum(br["pf"] + br["pt"] for (_, br) in ac_flows["branch"])
    total_q_loss = sum(br["qf"] + br["qt"] for (_, br) in ac_flows["branch"])
    println("Total P loss: $(round(total_p_loss, digits=4)) p.u.")
    println("Total Q loss: $(round(total_q_loss, digits=4)) p.u.")

    a2_results["status"] = "pass"
    a2_results["vm_min"] = round(minimum(vm_vals); digits=4)
    a2_results["vm_max"] = round(maximum(vm_vals); digits=4)
    a2_results["vm_mean"] = round(sum(vm_vals)/length(vm_vals); digits=4)
    a2_results["va_min"] = round(minimum(va_vals); digits=4)
    a2_results["va_max"] = round(maximum(va_vals); digits=4)
    a2_results["total_p_loss_pu"] = round(total_p_loss; digits=4)
    a2_results["total_q_loss_pu"] = round(total_q_loss; digits=4)
    a2_results["num_bus_voltages"] = length(vm_vals)
    a2_results["num_branch_flows"] = length(ac_flows["branch"])
else
    a2_results["status"] = "fail"
    println("ACPF FAILED to converge after 2 attempts")
end

mem_after_ac = Base.gc_live_bytes()
a2_results["peak_memory_mb"] = round(mem_after_ac / 1e6; digits=1)
a2_results["memory_delta_mb"] = round((mem_after_ac - mem_before_ac) / 1e6; digits=1)

all_results["a2_acpf"] = a2_results

# ═══════════════════════════════════════════════════════════════
# A-3 / C-3: DC OPF on MEDIUM (10000-bus)
# ═══════════════════════════════════════════════════════════════
println("\n=== A-3 / C-3: DC OPF on MEDIUM ===")

function prepare_opf_data(file; linearize=false)
    d = PowerModels.parse_file(file)
    n_fixed = 0
    for (id, gen) in d["gen"]
        if gen["model"] == 2 && (gen["ncost"] == 0 || isempty(gen["cost"]))
            gen["cost"] = [0.0, 0.0, 0.0]
            gen["ncost"] = 3
            n_fixed += 1
        end
        if linearize && gen["model"] == 2 && gen["ncost"] == 3
            gen["cost"][1] = 0.0  # remove quadratic term for LP solvers
        end
    end
    zero_rate = count(br -> get(br, "rate_a", 0.0) == 0.0, values(d["branch"]))
    return d, n_fixed, zero_rate
end

# --- Ipopt (primary, handles QP) ---
data_opf, n_fixed, zero_rate = prepare_opf_data(NETWORK_FILE)
println("Fixed $n_fixed generators with empty costs")
println("Branches with zero rate_a: $zero_rate / $(length(data_opf["branch"]))")

GC.gc()
mem_before_opf = Base.gc_live_bytes()

optimizer_ipopt = JuMP.optimizer_with_attributes(
    Ipopt.Optimizer, "max_iter" => 10000, "tol" => 1e-6, "print_level" => 3
)

println("Solving DC OPF with Ipopt...")
t_ipopt = time()
opf_ipopt = PowerModels.solve_dc_opf(
    data_opf, optimizer_ipopt; setting=Dict("output" => Dict("duals" => true))
)
ipopt_time = time() - t_ipopt
ipopt_term = string(opf_ipopt["termination_status"])
println("Ipopt termination: $ipopt_term, time: $(round(ipopt_time, digits=2))s")
println("Ipopt objective: $(round(opf_ipopt["objective"], digits=2))")

a3_results = Dict{String,Any}(
    "generators_cost_fixed" => n_fixed,
    "branches_zero_rate_a" => zero_rate,
    "num_buses" => length(data_opf["bus"]),
    "num_branches" => length(data_opf["branch"]),
    "num_generators" => length(data_opf["gen"]),
)

if ipopt_term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"]
    a3_results["status"] = "pass"
    a3_results["solver"] = "Ipopt"
    a3_results["termination"] = ipopt_term
    a3_results["solve_time"] = round(ipopt_time; digits=3)
    a3_results["objective"] = round(opf_ipopt["objective"]; digits=2)

    total_gen = sum(gen["pg"] for (_, gen) in opf_ipopt["solution"]["gen"])
    a3_results["total_generation_pu"] = round(total_gen; digits=2)
    a3_results["num_gen_dispatched"] = length(opf_ipopt["solution"]["gen"])

    # LMPs
    lmp_vals = Float64[]
    for (_, bus) in opf_ipopt["solution"]["bus"]
        if haskey(bus, "lam_kcl_r")
            push!(lmp_vals, bus["lam_kcl_r"])
        end
    end
    if !isempty(lmp_vals)
        a3_results["num_lmps"] = length(lmp_vals)
        a3_results["lmp_min"] = round(minimum(lmp_vals); digits=2)
        a3_results["lmp_max"] = round(maximum(lmp_vals); digits=2)
        a3_results["lmp_mean"] = round(sum(lmp_vals)/length(lmp_vals); digits=2)
        a3_results["lmp_range"] = round(maximum(lmp_vals) - minimum(lmp_vals); digits=2)
    end
    a3_results["num_branch_flows"] = length(opf_ipopt["solution"]["branch"])
else
    a3_results["status"] = "fail"
    a3_results["error"] = "Ipopt did not converge: $ipopt_term"
end

mem_after_ipopt = Base.gc_live_bytes()
a3_results["peak_memory_mb"] = round(mem_after_ipopt / 1e6; digits=1)

# --- HiGHS (for C-3 comparison) ---
println("\nSolving DC OPF with HiGHS...")
data_highs, _, _ = prepare_opf_data(NETWORK_FILE)

optimizer_highs = JuMP.optimizer_with_attributes(
    HiGHS.Optimizer,
    "time_limit" => 300.0,
    "presolve" => "on",
    "threads" => 1,
    "output_flag" => true,
)

t_highs = time()
opf_highs = PowerModels.solve_dc_opf(
    data_highs, optimizer_highs; setting=Dict("output" => Dict("duals" => true))
)
highs_time = time() - t_highs
highs_term = string(opf_highs["termination_status"])
println("HiGHS termination: $highs_term, time: $(round(highs_time, digits=2))s")
if highs_term in ["OPTIMAL", "LOCALLY_SOLVED"]
    println("HiGHS objective: $(round(opf_highs["objective"], digits=2))")
end

c3_highs = Dict{String,Any}(
    "solver" => "HiGHS", "termination" => highs_term, "solve_time" => round(highs_time; digits=3)
)
if highs_term in ["OPTIMAL", "LOCALLY_SOLVED"]
    c3_highs["objective"] = round(opf_highs["objective"]; digits=2)
    # HiGHS LMPs
    hlmp = Float64[]
    for (_, bus) in opf_highs["solution"]["bus"]
        if haskey(bus, "lam_kcl_r")
            push!(hlmp, bus["lam_kcl_r"])
        end
    end
    if !isempty(hlmp)
        c3_highs["num_lmps"] = length(hlmp)
        c3_highs["lmp_min"] = round(minimum(hlmp); digits=2)
        c3_highs["lmp_max"] = round(maximum(hlmp); digits=2)
    end
end

# --- GLPK (for C-3 comparison, LP only) ---
println("\nSolving DC OPF with GLPK (linearized costs)...")
data_glpk, _, _ = prepare_opf_data(NETWORK_FILE; linearize=true)

optimizer_glpk = JuMP.optimizer_with_attributes(
    GLPK.Optimizer, "tm_lim" => 300000, "msg_lev" => GLPK.GLP_MSG_ON
)

t_glpk = time()
opf_glpk = PowerModels.solve_dc_opf(
    data_glpk, optimizer_glpk; setting=Dict("output" => Dict("duals" => true))
)
glpk_time = time() - t_glpk
glpk_term = string(opf_glpk["termination_status"])
println("GLPK termination: $glpk_term, time: $(round(glpk_time, digits=2))s")
if glpk_term in ["OPTIMAL", "LOCALLY_SOLVED"]
    println("GLPK objective: $(round(opf_glpk["objective"], digits=2))")
end

c3_glpk = Dict{String,Any}(
    "solver" => "GLPK",
    "termination" => glpk_term,
    "solve_time" => round(glpk_time; digits=3),
    "note" => "Linearized costs (quadratic terms zeroed) since GLPK is LP-only",
)
if glpk_term in ["OPTIMAL", "LOCALLY_SOLVED"]
    c3_glpk["objective"] = round(opf_glpk["objective"]; digits=2)
    glmp = Float64[]
    for (_, bus) in opf_glpk["solution"]["bus"]
        if haskey(bus, "lam_kcl_r")
            push!(glmp, bus["lam_kcl_r"])
        end
    end
    if !isempty(glmp)
        c3_glpk["num_lmps"] = length(glmp)
        c3_glpk["lmp_min"] = round(minimum(glmp); digits=2)
        c3_glpk["lmp_max"] = round(maximum(glmp); digits=2)
    end
end

a3_results["highs"] = c3_highs
a3_results["glpk"] = c3_glpk

all_results["a3_dcopf"] = a3_results

# ═══════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════
println("\n========== SUMMARY ==========")
println(
    "A-1 DCPF: $(all_results["a1_dcpf"]["status"]), solve=$(all_results["a1_dcpf"]["solve_time"])s, mem=$(all_results["a1_dcpf"]["peak_memory_mb"])MB",
)
println(
    "A-2 ACPF: $(all_results["a2_acpf"]["status"]), solve=$(all_results["a2_acpf"]["solve_time"])s, mem=$(all_results["a2_acpf"]["peak_memory_mb"])MB",
)
println(
    "A-3 DCOPF (Ipopt): $(a3_results["status"]), solve=$(a3_results["solve_time"])s, obj=$(a3_results["objective"])",
)
println("A-3 DCOPF (HiGHS): $(c3_highs["termination"]), solve=$(c3_highs["solve_time"])s")
println("A-3 DCOPF (GLPK):  $(c3_glpk["termination"]), solve=$(c3_glpk["solve_time"])s")

# Write results to file
open(OUTPUT_FILE, "w") do f
    JSON.print(f, all_results, 2)
end
println("\nResults written to: $OUTPUT_FILE")
println("=============================")
