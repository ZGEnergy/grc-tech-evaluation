#=
Supplemental MEDIUM tests:
1. Ipopt DC OPF — extract LMP/dispatch details (we already know it converges)
2. GLPK DC OPF — fully linearize all costs (ncost=2 linear form)
3. ACPF — try with Ipopt-based AC OPF as feasibility check
=#

using PowerModels, JuMP, HiGHS, Ipopt, GLPK, JSON

const _Memento = Base.require(PowerModels, :Memento)
_Memento.setlevel!(_Memento.getlogger(PowerModels), "error")

const BASE_DIR = joinpath(@__DIR__, "..", "..", "..")
const NETWORK_FILE = joinpath(BASE_DIR, "data", "networks", "case_ACTIVSg10k.m")
const WARMUP_FILE = joinpath(BASE_DIR, "data", "networks", "case39.m")

results = Dict{String,Any}()

# Warm-up
println("=== Warm-up ===")
_d = PowerModels.parse_file(WARMUP_FILE)
PowerModels.compute_dc_pf(_d)
_opt = JuMP.optimizer_with_attributes(Ipopt.Optimizer, "print_level" => 0)
PowerModels.solve_dc_opf(_d, _opt)
println("Done.\n")

# ─── 1. Ipopt DC OPF with full details ───
println("=== Ipopt DC OPF (details extraction) ===")
data1 = PowerModels.parse_file(NETWORK_FILE)
n_fixed = let cnt = 0
    for (id, gen) in data1["gen"]
        if gen["model"] == 2 && (gen["ncost"] == 0 || isempty(gen["cost"]))
            gen["cost"] = [0.0, 0.0, 0.0]
            gen["ncost"] = 3
            cnt += 1
        end
    end
    cnt
end
zero_rate = count(br -> get(br, "rate_a", 0.0) == 0.0, values(data1["branch"]))

optimizer_ipopt = JuMP.optimizer_with_attributes(
    Ipopt.Optimizer, "max_iter" => 10000, "tol" => 1e-6, "print_level" => 3
)

GC.gc()
mem_before = Base.gc_live_bytes()
t0 = time()
opf = PowerModels.solve_dc_opf(
    data1, optimizer_ipopt; setting=Dict("output" => Dict("duals" => true))
)
ipopt_time = time() - t0
mem_after = Base.gc_live_bytes()

term = string(opf["termination_status"])
println("Termination: $term")
println("Time: $(round(ipopt_time, digits=3))s")
println("Objective: $(opf["objective"])")

if term in ["OPTIMAL", "LOCALLY_SOLVED", "ALMOST_LOCALLY_SOLVED"]
    # Dispatch
    total_gen = sum(gen["pg"] for (_, gen) in opf["solution"]["gen"])
    dispatched = count(gen -> gen["pg"] > 1e-6, values(opf["solution"]["gen"]))
    println("Total generation: $(round(total_gen, digits=2)) p.u.")
    println("Generators dispatched (pg > 0): $dispatched / $(length(opf["solution"]["gen"]))")

    # LMPs
    lmps = Float64[]
    for (_, bus) in opf["solution"]["bus"]
        if haskey(bus, "lam_kcl_r")
            push!(lmps, bus["lam_kcl_r"])
        end
    end
    if !isempty(lmps)
        println(
            "LMPs: n=$(length(lmps)), min=$(round(minimum(lmps), digits=2)), max=$(round(maximum(lmps), digits=2)), mean=$(round(sum(lmps)/length(lmps), digits=2))",
        )
        println(
            "LMP std: $(round(sqrt(sum((l - sum(lmps)/length(lmps))^2 for l in lmps) / length(lmps)), digits=2))",
        )
    end

    # Branch flows
    println("Branch flows: $(length(opf["solution"]["branch"]))")

    results["ipopt"] = Dict(
        "status" => "pass",
        "termination" => term,
        "solve_time" => round(ipopt_time; digits=3),
        "objective" => round(opf["objective"]; digits=2),
        "total_generation_pu" => round(total_gen; digits=2),
        "num_gen_dispatched" => dispatched,
        "num_gen_total" => length(opf["solution"]["gen"]),
        "num_lmps" => length(lmps),
        "lmp_min" => isempty(lmps) ? nothing : round(minimum(lmps); digits=2),
        "lmp_max" => isempty(lmps) ? nothing : round(maximum(lmps); digits=2),
        "lmp_mean" => isempty(lmps) ? nothing : round(sum(lmps)/length(lmps); digits=2),
        "lmp_range" => isempty(lmps) ? nothing : round(maximum(lmps) - minimum(lmps); digits=2),
        "num_branch_flows" => length(opf["solution"]["branch"]),
        "generators_cost_fixed" => n_fixed,
        "branches_zero_rate_a" => zero_rate,
        "peak_memory_mb" => round(mem_after / 1e6; digits=1),
        "memory_delta_mb" => round((mem_after - mem_before) / 1e6; digits=1),
    )
end

# ─── 2. GLPK DC OPF (fully linearized) ───
println("\n=== GLPK DC OPF (fully linearized) ===")
data2 = PowerModels.parse_file(NETWORK_FILE)
for (id, gen) in data2["gen"]
    if gen["model"] == 2 && (gen["ncost"] == 0 || isempty(gen["cost"]))
        gen["cost"] = [0.0, 0.0]
        gen["ncost"] = 2
    elseif gen["model"] == 2
        # Convert any polynomial cost to linear: keep only linear and constant terms
        if gen["ncost"] >= 3
            # cost = [a2, a1, a0] for quadratic => linearize to [a1, a0]
            linear_coeff = gen["cost"][end - 1]
            const_coeff = gen["cost"][end]
            gen["cost"] = [linear_coeff, const_coeff]
            gen["ncost"] = 2
        end
    end
end

optimizer_glpk = JuMP.optimizer_with_attributes(
    GLPK.Optimizer, "tm_lim" => 300000, "msg_lev" => GLPK.GLP_MSG_ON
)

t_glpk = time()
try
    opf_glpk = PowerModels.solve_dc_opf(
        data2, optimizer_glpk; setting=Dict("output" => Dict("duals" => true))
    )
    glpk_time = time() - t_glpk
    glpk_term = string(opf_glpk["termination_status"])
    println("GLPK termination: $glpk_term, time: $(round(glpk_time, digits=2))s")

    results["glpk"] = Dict(
        "termination" => glpk_term,
        "solve_time" => round(glpk_time; digits=3),
        "note" => "Fully linearized costs (ncost=2) to make LP-compatible",
    )

    if glpk_term in ["OPTIMAL", "LOCALLY_SOLVED"]
        println("GLPK objective: $(round(opf_glpk["objective"], digits=2))")
        results["glpk"]["objective"] = round(opf_glpk["objective"]; digits=2)

        glmps = Float64[]
        for (_, bus) in opf_glpk["solution"]["bus"]
            if haskey(bus, "lam_kcl_r")
                push!(glmps, bus["lam_kcl_r"])
            end
        end
        if !isempty(glmps)
            results["glpk"]["num_lmps"] = length(glmps)
            results["glpk"]["lmp_min"] = round(minimum(glmps); digits=2)
            results["glpk"]["lmp_max"] = round(maximum(glmps); digits=2)
        end

        total_gen_glpk = sum(gen["pg"] for (_, gen) in opf_glpk["solution"]["gen"])
        results["glpk"]["total_generation_pu"] = round(total_gen_glpk; digits=2)
    end
catch e
    glpk_time = time() - t_glpk
    println("GLPK failed: $e")
    results["glpk"] = Dict(
        "status" => "fail",
        "error" => string(typeof(e), ": ", sprint(showerror, e)),
        "solve_time" => round(glpk_time; digits=3),
    )
end

# ─── Summary ───
println("\n=== SUMMARY ===")
println(JSON.json(results, 2))

open(joinpath(@__DIR__, "medium_supplemental_results.json"), "w") do f
    JSON.print(f, results, 2)
end
println("\nResults saved.")
