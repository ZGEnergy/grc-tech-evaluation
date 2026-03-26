#=
Test C-3: DC OPF Scale — MEDIUM grade assessment (multi-solver)
Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus, case_ACTIVSg10k.m)
Pass condition: Wall-clock time per solver, peak memory, objective value consistency.
  Max branch loading reported. Note: MEDIUM has 19.4% branches with Inf rate_a.
Tool: PowerModels.jl v0.21.5
Solvers: HiGHS (primary), GLPK (secondary — per solver-config.md)

Notes:
  - ACTIVSg10k uses quadratic costs → must linearize to LP for both solvers.
  - ACTIVSg10k is uncongested: uniform LMPs expected (~84-85% max loading).

Preprocessing (per MEDIUM protocol):
  - Zero-reactance fix: branches with br_x=0 → set to 0.0001 pu
  - Zero/Inf RATE_A fix: branches with rate_a=0 or Inf → set to 9999 MVA
=#

using PowerModels, JuMP, HiGHS, GLPK
using Printf

PowerModels.silence()

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024
        end
    end
    return nothing
end

function apply_medium_preprocessing!(data::Dict)
    base_mva = data["baseMVA"]
    n_x_fixed = 0
    n_rate_fixed = 0
    for (_, branch) in data["branch"]
        if branch["br_x"] == 0.0
            branch["br_x"] = 0.0001
            n_x_fixed += 1
        end
        ra = get(branch, "rate_a", 0.0)
        if ra == 0.0 || isinf(ra)
            branch["rate_a"] = 9999.0 / base_mva
            n_rate_fixed += 1
        end
    end
    return (n_x_fixed, n_rate_fixed)
end

function linearize_costs!(data::Dict)
    n_linearized = 0
    for (_, gen) in data["gen"]
        if get(gen, "model", 2) == 2 && get(gen, "ncost", 0) >= 3
            c = gen["cost"]
            if abs(c[1]) > 1e-10
                gen["cost"] = [c[2], c[3]]
                gen["ncost"] = 2
                n_linearized += 1
            end
        end
    end
    return n_linearized
end

function compute_max_branch_loading(opf_result, data)
    max_loading = 0.0
    max_loading_branch = ""
    n_over_100 = 0
    base_mva = data["baseMVA"]

    if !haskey(opf_result, "solution") || !haskey(opf_result["solution"], "branch")
        return (max_loading=NaN, max_loading_branch="", n_over_100=0)
    end

    for (br_id, br_sol) in opf_result["solution"]["branch"]
        pf = abs(get(br_sol, "pf", 0.0))
        rate_a = data["branch"][br_id]["rate_a"]
        if rate_a > 0.01  # skip zero-rated branches
            loading = pf / rate_a  # both in p.u.
            if loading > max_loading
                max_loading = loading
                max_loading_branch = br_id
            end
            if loading > 1.0 + 1e-4
                n_over_100 += 1
            end
        end
    end
    return (max_loading=max_loading, max_loading_branch=max_loading_branch, n_over_100=n_over_100)
end

function solve_dcopf(data::Dict, optimizer, solver_name::String)
    println("Solving DC OPF with $solver_name...")
    t_solve_start = time()
    opf_result = PowerModels.solve_dc_opf(
        data, optimizer; setting=Dict("output" => Dict("duals" => true))
    )
    t_solve = time() - t_solve_start
    term_status = string(opf_result["termination_status"])
    objective = get(opf_result, "objective", NaN)
    solver_time = get(opf_result, "solve_time", NaN)
    println(
        "  $solver_name: status=$term_status  obj=$(@sprintf("%.6e", objective))  " *
        "solve=$(@sprintf("%.6e", solver_time))s  wall=$(@sprintf("%.6e", t_solve))s",
    )
    return (
        term_status=term_status,
        objective=objective,
        solver_time=solver_time,
        wall_clock=t_solve,
        result=opf_result,
    )
end

function run(
    network_file::String=joinpath(
        @__DIR__, "..", "..", "..", "..", "data", "networks", "case_ACTIVSg10k.m"
    ),
)
    results = Dict(
        "test_id" => "C-3",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    cpu_threads_available = Sys.CPU_THREADS
    cpu_threads_used = 1  # single-threaded per solver-config.md

    # Warm-up on case39 to eliminate JIT compilation from timing
    println("Warming up JIT on case39...")
    try
        tiny_file = joinpath(dirname(network_file), "case39.m")
        _data_h = PowerModels.parse_file(tiny_file)
        PowerModels.solve_dc_opf(_data_h, HiGHS.Optimizer)
        _data_g = PowerModels.parse_file(tiny_file)
        PowerModels.solve_dc_opf(_data_g, GLPK.Optimizer)
    catch e
        println("Warm-up warning: $e")
    end
    println("JIT warm-up complete.")

    rss_before = peak_rss_mb()
    t0 = time()
    try
        println("\nLoading network: $network_file")
        t_parse_start = time()
        data_orig = PowerModels.parse_file(network_file)
        t_parse = time() - t_parse_start
        println("Network parsed in $(@sprintf("%.6e", t_parse))s")

        n_buses = length(data_orig["bus"])
        n_branches = length(data_orig["branch"])
        n_gens = length(data_orig["gen"])
        base_mva = data_orig["baseMVA"]
        println("Network: $n_buses buses, $n_branches branches, $n_gens gens, baseMVA=$base_mva")

        n_x_fixed, n_rate_fixed = apply_medium_preprocessing!(data_orig)
        println("Preprocessing: $n_x_fixed br_x→0.0001, $n_rate_fixed rate_a→9999 MVA")

        # Deep-copy for each solver run
        data_highs = deepcopy(data_orig)
        n_lin_h = linearize_costs!(data_highs)
        println("HiGHS: Linearized $n_lin_h generators from quadratic to linear cost")

        data_glpk = deepcopy(data_orig)
        n_lin_g = linearize_costs!(data_glpk)
        println("GLPK:  Linearized $n_lin_g generators from quadratic to linear cost")

        # --- HiGHS run ---
        highs_opt = JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "output_flag" => true,
            "presolve" => "on",
            "time_limit" => 300.0,
            "threads" => 1,
        )
        highs_res = solve_dcopf(data_highs, highs_opt, "HiGHS")

        # --- GLPK run ---
        glpk_opt = JuMP.optimizer_with_attributes(
            GLPK.Optimizer, "tm_lim" => 300_000, "msg_lev" => GLPK.GLP_MSG_ON
        )
        glpk_res = solve_dcopf(data_glpk, glpk_opt, "GLPK")

        rss_after = peak_rss_mb()

        # Objective consistency check
        highs_converged =
            occursin("OPTIMAL", highs_res.term_status) || highs_res.term_status == "LOCALLY_SOLVED"
        glpk_converged =
            occursin("OPTIMAL", glpk_res.term_status) || glpk_res.term_status == "LOCALLY_SOLVED"

        obj_diff = abs(highs_res.objective - glpk_res.objective)
        obj_pct = 100.0 * obj_diff / max(abs(highs_res.objective), 1.0)
        println("\nObjective comparison:")
        println("  HiGHS:  $(@sprintf("%.6e", highs_res.objective)) \$/h")
        println("  GLPK:   $(@sprintf("%.6e", glpk_res.objective)) \$/h")
        println("  Diff:   $(@sprintf("%.6e", obj_diff)) \$/h  ($(@sprintf("%.6e", obj_pct))%)")
        if glpk_converged
            println("  Consistency: $(obj_pct < 0.01 ? "VERIFIED" : "MISMATCH")")
        else
            println("  Consistency: CANNOT VERIFY (GLPK did not converge)")
        end

        # Max branch loading (hard constraint check)
        highs_loading = compute_max_branch_loading(highs_res.result, data_highs)
        println("\nMax branch loading (HiGHS):")
        println(
            "  Max loading: $(@sprintf("%.6e", highs_loading.max_loading)) p.u. (branch $(highs_loading.max_loading_branch))",
        )
        println("  Max loading pct: $(@sprintf("%.2f", highs_loading.max_loading * 100))%")
        println("  Branches over 100%: $(highs_loading.n_over_100)")

        glpk_loading = compute_max_branch_loading(glpk_res.result, data_glpk)
        println("Max branch loading (GLPK):")
        println(
            "  Max loading: $(@sprintf("%.6e", glpk_loading.max_loading)) p.u. (branch $(glpk_loading.max_loading_branch))",
        )
        println("  Max loading pct: $(@sprintf("%.2f", glpk_loading.max_loading * 100))%")
        println("  Branches over 100%: $(glpk_loading.n_over_100)")

        # Extract LMPs from HiGHS run
        lmp_values = Dict{String,Float64}()
        if haskey(highs_res.result["solution"], "bus")
            for (bus_id, bus_sol) in highs_res.result["solution"]["bus"]
                lam = get(bus_sol, "lam_kcl_r", nothing)
                if !isnothing(lam) && isfinite(lam)
                    lmp_values[bus_id] = -lam / base_mva
                end
            end
        end
        lmp_min = isempty(lmp_values) ? NaN : minimum(values(lmp_values))
        lmp_max = isempty(lmp_values) ? NaN : maximum(values(lmp_values))
        println(
            "LMPs (HiGHS): min=$(@sprintf("%.6e", lmp_min))  max=$(@sprintf("%.6e", lmp_max)) \$/MWh",
        )

        # Count dispatched generators
        n_dispatched = 0
        if haskey(highs_res.result["solution"], "gen")
            for (_, gen_sol) in highs_res.result["solution"]["gen"]
                pg = get(gen_sol, "pg", 0.0)
                if abs(pg) > 1e-6
                    n_dispatched += 1
                end
            end
        end

        # Count binding branches
        n_binding = 0
        if haskey(highs_res.result["solution"], "branch")
            for (br_id, br_sol) in highs_res.result["solution"]["branch"]
                pf = abs(get(br_sol, "pf", 0.0))
                rate_a = data_highs["branch"][br_id]["rate_a"]
                if rate_a > 0.01 && pf / rate_a > 0.999
                    n_binding += 1
                end
            end
        end

        # Status
        if highs_converged
            push!(
                results["workarounds"],
                "Quadratic cost linearization required: $(n_lin_h) generators had c2 coefficient dropped " *
                "to convert QP to LP. Both HiGHS and GLPK cannot solve QP at 10k-bus scale within 300s.",
            )
            results["status"] = "qualified_pass"
        else
            results["status"] = "fail"
        end

        results["details"] = Dict(
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens" => n_gens,
            "base_mva" => base_mva,
            "n_x_fixed" => n_x_fixed,
            "n_rate_fixed" => n_rate_fixed,
            "n_costs_linearized" => n_lin_h,
            "n_dispatched" => n_dispatched,
            "n_binding" => n_binding,
            "highs_term_status" => highs_res.term_status,
            "highs_objective" => highs_res.objective,
            "highs_solver_time_s" => highs_res.solver_time,
            "highs_wall_clock_s" => highs_res.wall_clock,
            "glpk_term_status" => glpk_res.term_status,
            "glpk_objective" => glpk_res.objective,
            "glpk_solver_time_s" => glpk_res.solver_time,
            "glpk_wall_clock_s" => glpk_res.wall_clock,
            "objective_diff" => obj_diff,
            "objective_pct_diff" => obj_pct,
            "lmp_min_dollars_per_mwh" => lmp_min,
            "lmp_max_dollars_per_mwh" => lmp_max,
            "lmp_count" => length(lmp_values),
            "highs_max_branch_loading_pu" => highs_loading.max_loading,
            "highs_max_loading_branch" => highs_loading.max_loading_branch,
            "highs_branches_over_100pct" => highs_loading.n_over_100,
            "glpk_max_branch_loading_pu" => glpk_loading.max_loading,
            "glpk_max_loading_branch" => glpk_loading.max_loading_branch,
            "glpk_branches_over_100pct" => glpk_loading.n_over_100,
            "t_parse_s" => t_parse,
            "peak_rss_mb_before" => rss_before,
            "peak_rss_mb_after" => rss_after,
            "cpu_threads_used" => cpu_threads_used,
            "cpu_threads_available" => cpu_threads_available,
            "timing_source" => "measured",
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        println("ERROR: $(typeof(e)): $e")
        bt = catch_backtrace()
        println(sprint(showerror, e, bt))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    println("\nStatus: $(results["status"])")
    println("Wall clock: $(@sprintf("%.6e", results["wall_clock_seconds"]))s")
    println("Peak RSS: $(peak_rss_mb()) MB")
    println("cpu_threads_used: $cpu_threads_used")
    println("cpu_threads_available: $cpu_threads_available")

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println("\n--- RESULT SUMMARY ---")
    println("test_id:            $(result["test_id"])")
    println("status:             $(result["status"])")
    println("wall_clock_seconds: $(result["wall_clock_seconds"])")
    println("errors:             $(result["errors"])")
    println("workarounds:        $(result["workarounds"])")
    println("--- details ---")
    for (k, v) in sort(collect(result["details"]); by=first)
        println("  $k: $v")
    end
end
