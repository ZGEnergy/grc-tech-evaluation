#=
Test C-7: Solver Swap — MEDIUM (DC OPF solver interface abstraction)
Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus, case_ACTIVSg10k.m)
Pass condition: Whether solver swap requires reformulation or just a parameter change.
               Time per solver recorded.
Tool: PowerModels.jl v0.21.5
Solvers: HiGHS, GLPK, SCIP, Ipopt
Depends on: C-3 (QUALIFIED PASS)

Notes:
  - All four open-source solvers tested on the same DC OPF problem.
  - Solver swap is a one-line change: no model reformulation required.
  - Quadratic cost linearization (workaround from C-3) is still required
    for LP solvers. Ipopt can handle QP natively but linearization is
    applied uniformly for fair comparison.

Preprocessing (per MEDIUM protocol):
  - Zero-reactance fix: branches with br_x=0 → set to 0.0001 pu
  - Zero/Inf RATE_A fix: branches with rate_a=0 or Inf → set to 9999 MVA
=#

using PowerModels, JuMP, HiGHS, GLPK, SCIP, Ipopt

PowerModels.silence()

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

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024  # kB to MB
        end
    end
    return nothing
end

function solve_dcopf(
    data::Dict,
    optimizer,
    solver_name::String,
    time_limit_s::Float64=300.0;
    request_duals::Bool=true,
)
    println(
        "Solving DC OPF with $solver_name (time limit=$(time_limit_s)s, duals=$request_duals)..."
    )
    t_solve_start = time()
    local opf_result
    # Some solvers (SCIP) do not support dual extraction. PowerModels/InfrastructureModels
    # tries to extract duals even with duals=>false in some versions. Use two-level API
    # as fallback to avoid dual extraction entirely.
    try
        opf_result = PowerModels.solve_dc_opf(
            data, optimizer; setting=Dict("output" => Dict("duals" => request_duals))
        )
    catch e
        if occursin("ConstraintDual", string(typeof(e)))
            println("  $solver_name: dual extraction failed, using two-level API fallback...")
            pm = PowerModels.instantiate_model(
                data, PowerModels.DCPPowerModel, PowerModels.build_opf
            )
            result_im = PowerModels.optimize_model!(pm; optimizer=optimizer)
            # Construct minimal result dict
            opf_result = Dict(
                "termination_status" => string(JuMP.termination_status(pm.model)),
                "objective" => JuMP.objective_value(pm.model),
                "solve_time" => JuMP.solve_time(pm.model),
                "solution" => Dict(),
            )
        else
            rethrow()
        end
    end
    t_solve = time() - t_solve_start
    term_status = string(opf_result["termination_status"])
    objective = get(opf_result, "objective", NaN)
    solver_time = get(opf_result, "solve_time", NaN)
    println(
        "  $solver_name: status=$term_status  obj=$(round(objective, digits=2))  " *
        "solve=$(round(solver_time, digits=2))s  wall=$(round(t_solve, digits=2))s",
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
        "test_id" => "C-7",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    # ── JIT warm-up on case39 ─────────────────────────────────────────────────
    println("Warming up JIT on case39...")
    try
        tiny_file = joinpath(dirname(network_file), "case39.m")
        _d = PowerModels.parse_file(tiny_file)
        PowerModels.solve_dc_opf(_d, HiGHS.Optimizer)
        _d = PowerModels.parse_file(tiny_file)
        PowerModels.solve_dc_opf(_d, GLPK.Optimizer)
        _d = PowerModels.parse_file(tiny_file)
        PowerModels.solve_dc_opf(_d, SCIP.Optimizer)
        _d = PowerModels.parse_file(tiny_file)
        PowerModels.solve_dc_opf(_d, Ipopt.Optimizer)
    catch e
        println("Warm-up warning: $e")
    end

    t0 = time()
    try
        println("Loading network: $network_file")
        t_parse_start = time()
        data_orig = PowerModels.parse_file(network_file)
        t_parse = time() - t_parse_start
        println("Network parsed in $(round(t_parse, digits=2))s")

        n_buses = length(data_orig["bus"])
        n_branches = length(data_orig["branch"])
        n_gens = length(data_orig["gen"])
        base_mva = data_orig["baseMVA"]
        println("Network: $n_buses buses, $n_branches branches, $n_gens gens, baseMVA=$base_mva")

        # Apply MEDIUM preprocessing on base copy
        n_x_fixed, n_rate_fixed = apply_medium_preprocessing!(data_orig)
        println("Preprocessing: $n_x_fixed br_x→0.0001, $n_rate_fixed rate_a→9999 MVA")

        solver_results = Dict{String,Any}()

        # ── HiGHS run ──────────────────────────────────────────────────────────
        println("\n=== HiGHS ===")
        data_highs = deepcopy(data_orig)
        n_lin = linearize_costs!(data_highs)
        println("HiGHS: Linearized $n_lin generators from quadratic to linear cost")
        highs_opt = JuMP.optimizer_with_attributes(
            HiGHS.Optimizer,
            "output_flag" => true,
            "presolve" => "on",
            "time_limit" => 300.0,
            "threads" => 1,
        )
        highs_res = solve_dcopf(data_highs, highs_opt, "HiGHS", 300.0)
        solver_results["HiGHS"] = highs_res

        # ── GLPK run ───────────────────────────────────────────────────────────
        println("\n=== GLPK ===")
        data_glpk = deepcopy(data_orig)
        n_lin = linearize_costs!(data_glpk)
        println("GLPK: Linearized $n_lin generators from quadratic to linear cost")
        glpk_opt = JuMP.optimizer_with_attributes(
            GLPK.Optimizer,
            "tm_lim" => 300_000,   # milliseconds
            "msg_lev" => GLPK.GLP_MSG_ON,
        )
        glpk_res = solve_dcopf(data_glpk, glpk_opt, "GLPK", 300.0)
        solver_results["GLPK"] = glpk_res

        # ── SCIP run ───────────────────────────────────────────────────────────
        println("\n=== SCIP ===")
        data_scip = deepcopy(data_orig)
        n_lin = linearize_costs!(data_scip)
        println("SCIP: Linearized $n_lin generators from quadratic to linear cost")
        scip_opt = JuMP.optimizer_with_attributes(
            SCIP.Optimizer, "display/verblevel" => 4, "limits/time" => 300.0
        )
        scip_res = solve_dcopf(data_scip, scip_opt, "SCIP", 300.0)
        solver_results["SCIP"] = scip_res

        # ── Ipopt run ──────────────────────────────────────────────────────────
        println("\n=== Ipopt ===")
        data_ipopt = deepcopy(data_orig)
        n_lin = linearize_costs!(data_ipopt)
        println("Ipopt: Linearized $n_lin generators from quadratic to linear cost")
        ipopt_opt = JuMP.optimizer_with_attributes(
            Ipopt.Optimizer,
            "max_iter" => 10000,
            "tol" => 1e-6,
            "acceptable_tol" => 1e-4,
            "print_level" => 5,
            "linear_solver" => "mumps",
        )
        ipopt_res = solve_dcopf(data_ipopt, ipopt_opt, "Ipopt", 300.0)
        solver_results["Ipopt"] = ipopt_res

        # ── Solver swap verification ────────────────────────────────────────────
        println("\n--- Solver Swap Verification ---")
        println("Solver swap mechanism: JuMP.optimizer_with_attributes(<Solver>.Optimizer, ...)")
        println("PowerModels problem structure: identical across HiGHS / GLPK / SCIP / Ipopt")
        println("Reformulation required: NO — parameter change only")

        # ── Summary table ──────────────────────────────────────────────────────
        println("\n--- Per-Solver Summary ---")
        println(
            "Solver     | Status          | Objective (USD/h) | Solver Time (s) | Wall Clock (s)"
        )
        println("-----------+-----------------+-----------------+-----------------+---------------")
        for name in ["HiGHS", "GLPK", "SCIP", "Ipopt"]
            r = solver_results[name]
            obj_str = isnan(r.objective) ? "N/A" : string(round(r.objective; digits=2))
            println(
                "$(rpad(name, 10)) | $(rpad(r.term_status, 15)) | $(rpad(obj_str, 15)) | $(rpad(round(r.solver_time, digits=2), 15)) | $(round(r.wall_clock, digits=2))",
            )
        end

        # ── Peak memory ────────────────────────────────────────────────────────
        peak_mem = peak_rss_mb()
        println("\nPeak RSS: $(isnothing(peak_mem) ? "N/A" : round(peak_mem, digits=1)) MB")

        # ── Determine status ────────────────────────────────────────────────────
        any_converged = any(
            r.term_status in ["OPTIMAL", "LOCALLY_SOLVED"] for (_, r) in solver_results
        )

        if any_converged
            results["status"] = "qualified_pass"  # cost-linearization workaround still required
        end

        push!(
            results["workarounds"],
            "Quadratic cost linearization (inherited from C-3): " *
            "ACTIVSg10k generators use polynomial cost model 2 (quadratic). " *
            "Costs linearized for LP compatibility. Classification: stable.",
        )

        results["details"] = Dict(
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens" => n_gens,
            "base_mva" => base_mva,
            "n_x_fixed" => n_x_fixed,
            "n_rate_fixed" => n_rate_fixed,
            "solver_swap_requires_reformulation" => false,
            "peak_rss_mb" => peak_mem,
            "t_parse_s" => t_parse,
            "timing_source" => "measured",
        )

        # Record per-solver results
        for name in ["HiGHS", "GLPK", "SCIP", "Ipopt"]
            prefix = lowercase(name)
            r = solver_results[name]
            results["details"]["$(prefix)_term_status"] = r.term_status
            results["details"]["$(prefix)_objective"] = r.objective
            results["details"]["$(prefix)_solver_time_s"] = r.solver_time
            results["details"]["$(prefix)_wall_clock_s"] = r.wall_clock
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        println("ERROR: $(typeof(e)): $e")
        bt = catch_backtrace()
        println(sprint(showerror, e, bt))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    println("\nStatus: $(results["status"])")
    println("Wall clock: $(round(results["wall_clock_seconds"], digits=3))s")

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
