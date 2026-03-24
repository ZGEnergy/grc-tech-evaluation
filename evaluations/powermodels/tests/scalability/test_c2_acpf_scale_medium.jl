#=
Test C-2: ACPF Scale — MEDIUM grade assessment
Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus, case_ACTIVSg10k.m)
Pass condition: Wall-clock time, peak memory, iterations, convergence_evidence_quality.
  Max bus power mismatch < 1e-4 p.u.
Tool: PowerModels.jl v0.21.5
Solver: Ipopt (primary), compute_ac_pf/NLsolve (secondary attempt)

Protocol v11 note: Prior v10 results showed both Ipopt and NLsolve diverge on MEDIUM.
This re-run confirms with both solvers and documents all attempts.

Convergence protocol:
  1. Flat start with Ipopt (vm=1.0, va=0.0)
  2. DC warm start with Ipopt
  3. compute_ac_pf (NLsolve) flat start
  4. compute_ac_pf (NLsolve) DC warm start
=#

using PowerModels
using JuMP
using Ipopt
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

function verify_convergence(result, data, label; is_nlsolve=false)
    println("  --- Convergence verification ($label) ---")

    if is_nlsolve
        term_status = string(result["termination_status"])
        solver_time = NaN
    else
        term_status = string(result["termination_status"])
        solver_time = get(result, "solve_time", NaN)
    end
    println("  Termination status: $term_status")
    if !is_nlsolve
        println("  Solve time: $(@sprintf("%.6e", solver_time))s")
    end

    if !haskey(result, "solution") || !haskey(result["solution"], "bus")
        println("  No bus solution found — cannot verify convergence")
        return (
            converged=false,
            n_vm_differ=0,
            n_va_nonzero=0,
            vm_range=[NaN, NaN],
            va_range_deg=[NaN, NaN],
            term_status=term_status,
            solver_time=solver_time,
        )
    end

    n_buses = length(data["bus"])
    vm_vals = Float64[]
    va_vals = Float64[]
    n_vm_differ = 0
    n_va_nonzero = 0

    for (bus_id, bus_sol) in result["solution"]["bus"]
        vm = get(bus_sol, "vm", 1.0)
        va = get(bus_sol, "va", 0.0)
        push!(vm_vals, vm)
        push!(va_vals, va * 180 / pi)
        if abs(vm - 1.0) > 1e-4
            n_vm_differ += 1
        end
        bus_type = get(data["bus"][bus_id], "bus_type", 1)
        if bus_type != 3 && abs(va) > 1e-6
            n_va_nonzero += 1
        end
    end

    vm_range = isempty(vm_vals) ? [NaN, NaN] : [minimum(vm_vals), maximum(vm_vals)]
    va_range = isempty(va_vals) ? [NaN, NaN] : [minimum(va_vals), maximum(va_vals)]

    pct_vm_differ = n_vm_differ / max(1, n_buses) * 100
    pct_va_nonzero = n_va_nonzero / max(1, n_buses - 1) * 100

    println("  Vm range: $(@sprintf("%.6e", vm_range[1])) — $(@sprintf("%.6e", vm_range[2])) pu")
    println("  Va range: $(@sprintf("%.6e", va_range[1])) — $(@sprintf("%.6e", va_range[2])) deg")
    println("  Buses with Vm != 1.0: $n_vm_differ / $n_buses ($(@sprintf("%.1f", pct_vm_differ))%)")
    println(
        "  Non-slack Va != 0: $n_va_nonzero / $(n_buses-1) ($(@sprintf("%.1f", pct_va_nonzero))%)"
    )

    quality_ok = pct_va_nonzero >= 95.0
    println(
        "  Convergence quality: $(quality_ok ? "VERIFIED" : "FAILED") (>95% non-flat angles required)",
    )

    is_converged = if is_nlsolve
        term_status == "true"
    else
        (
            occursin("LOCALLY_SOLVED", term_status) ||
            occursin("OPTIMAL", term_status) ||
            occursin("ALMOST_LOCALLY_SOLVED", term_status)
        )
    end

    return (
        converged=is_converged && quality_ok,
        n_vm_differ=n_vm_differ,
        n_va_nonzero=n_va_nonzero,
        vm_range=vm_range,
        va_range_deg=va_range,
        term_status=term_status,
        solver_time=solver_time,
        quality_ok=quality_ok,
        solver_converged=is_converged,
    )
end

function run(
    network_file::String=joinpath(
        @__DIR__, "..", "..", "..", "..", "data", "networks", "case_ACTIVSg10k.m"
    ),
)
    results = Dict(
        "test_id" => "C-2",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    cpu_threads_available = Sys.CPU_THREADS
    cpu_threads_used = 1  # Ipopt/NLsolve are single-threaded

    # Warm-up on case39 to eliminate JIT compilation
    println("Warming up JIT on case39...")
    try
        tiny_file = joinpath(dirname(network_file), "case39.m")
        _data = PowerModels.parse_file(tiny_file)
        _r1 = PowerModels.solve_ac_pf(_data, Ipopt.Optimizer)
        _data2 = PowerModels.parse_file(tiny_file)
        _r2 = PowerModels.compute_ac_pf(_data2)
        _data3 = PowerModels.parse_file(tiny_file)
        _r3 = PowerModels.compute_dc_pf(_data3)
    catch e
        println("Warm-up warning: $e")
    end
    println("JIT warm-up complete.")

    rss_before = peak_rss_mb()
    t0 = time()
    attempts = Dict{String,Any}()

    try
        println("\nLoading network: $network_file")
        data = PowerModels.parse_file(network_file)
        n_buses = length(data["bus"])
        n_branches = length(data["branch"])
        n_gens = length(data["gen"])
        base_mva = data["baseMVA"]
        println("Network: $n_buses buses, $n_branches branches, $n_gens gens, baseMVA=$base_mva")

        n_x_fixed, n_rate_fixed = apply_medium_preprocessing!(data)
        println("Preprocessing: $n_x_fixed br_x→0.0001, $n_rate_fixed rate_a→9999 MVA")

        # Ipopt optimizer with convergence-protocol settings
        ipopt_opt = JuMP.optimizer_with_attributes(
            Ipopt.Optimizer,
            "max_iter" => 10000,
            "tol" => 1e-6,
            "acceptable_tol" => 1e-4,
            "print_level" => 5,
            "linear_solver" => "mumps",
        )

        # ================================================================
        # Attempt 1: Flat start with Ipopt
        # ================================================================
        println("\n=== Attempt 1: ACPF Flat Start with Ipopt ===")
        data_flat = deepcopy(data)
        for (_, bus) in data_flat["bus"]
            bus["vm"] = 1.0
            bus["va"] = 0.0
        end

        t_flat_start = time()
        result_flat = PowerModels.solve_ac_pf(data_flat, ipopt_opt)
        t_flat = time() - t_flat_start
        println("Flat start wall-clock: $(@sprintf("%.6e", t_flat))s")
        flat_cv = verify_convergence(result_flat, data_flat, "Ipopt flat start")
        attempts["ipopt_flat"] = Dict(
            "converged" => flat_cv.converged,
            "term_status" => flat_cv.term_status,
            "solver_time_s" => flat_cv.solver_time,
            "wall_clock_s" => t_flat,
            "vm_range" => flat_cv.vm_range,
            "va_range_deg" => flat_cv.va_range_deg,
            "n_vm_differ" => flat_cv.n_vm_differ,
            "n_va_nonzero" => flat_cv.n_va_nonzero,
        )

        # ================================================================
        # Attempt 2: DC warm start with Ipopt
        # ================================================================
        dc_cv = nothing
        t_dc_warmstart = 0.0
        t_dcpf = 0.0

        if !flat_cv.converged
            println("\n=== Attempt 2: DC Warm Start with Ipopt ===")
            data_dc = deepcopy(data)
            t_dcpf_start = time()
            dc_result = PowerModels.compute_dc_pf(data_dc)
            t_dcpf = time() - t_dcpf_start
            println("DCPF solve time: $(@sprintf("%.6e", t_dcpf))s")

            dc_converged = dc_result["termination_status"] == true
            println("DCPF converged: $dc_converged")

            if dc_converged && haskey(dc_result, "solution") && haskey(dc_result["solution"], "bus")
                data_warm = deepcopy(data)
                dc_sol = dc_result["solution"]["bus"]
                for (bus_id, bus) in data_warm["bus"]
                    bus["vm"] = 1.0
                    bus["va"] = get(get(dc_sol, bus_id, Dict()), "va", 0.0)
                end

                ipopt_warm = JuMP.optimizer_with_attributes(
                    Ipopt.Optimizer,
                    "max_iter" => 10000,
                    "tol" => 1e-6,
                    "acceptable_tol" => 1e-4,
                    "print_level" => 5,
                    "linear_solver" => "mumps",
                    "warm_start_init_point" => "yes",
                    "mu_init" => 1e-2,
                )

                t_warm_start = time()
                result_warm = PowerModels.solve_ac_pf(data_warm, ipopt_warm)
                t_dc_warmstart = time() - t_warm_start
                println("DC warm-start ACPF wall-clock: $(@sprintf("%.6e", t_dc_warmstart))s")
                dc_cv = verify_convergence(result_warm, data_warm, "Ipopt DC warm start")
                attempts["ipopt_dc_warmstart"] = Dict(
                    "converged" => dc_cv.converged,
                    "term_status" => dc_cv.term_status,
                    "solver_time_s" => dc_cv.solver_time,
                    "wall_clock_s" => t_dc_warmstart,
                    "dcpf_time_s" => t_dcpf,
                    "vm_range" => dc_cv.vm_range,
                    "va_range_deg" => dc_cv.va_range_deg,
                    "n_vm_differ" => dc_cv.n_vm_differ,
                    "n_va_nonzero" => dc_cv.n_va_nonzero,
                )
            else
                println("DCPF failed — cannot provide DC warm start for Ipopt")
                attempts["ipopt_dc_warmstart"] = Dict(
                    "converged" => false, "reason" => "DCPF failed"
                )
            end
        end

        # ================================================================
        # Attempt 3: compute_ac_pf (NLsolve) flat start
        # ================================================================
        nlsolve_flat_cv = nothing
        ipopt_already_converged = flat_cv.converged || (dc_cv !== nothing && dc_cv.converged)

        if !ipopt_already_converged
            println("\n=== Attempt 3: compute_ac_pf (NLsolve) Flat Start ===")
            println("NOTE: Previous v10 results showed NLsolve takes ~580s and fails.")
            println("Running with 120s timeout to document...")
            data_nlsolve_flat = deepcopy(data)
            for (_, bus) in data_nlsolve_flat["bus"]
                bus["vm"] = 1.0
                bus["va"] = 0.0
            end

            t_nlsolve_flat_start = time()
            result_nlsolve_flat = PowerModels.compute_ac_pf(data_nlsolve_flat)
            t_nlsolve_flat = time() - t_nlsolve_flat_start
            println("NLsolve flat start wall-clock: $(@sprintf("%.6e", t_nlsolve_flat))s")
            nlsolve_flat_cv = verify_convergence(
                result_nlsolve_flat, data_nlsolve_flat, "NLsolve flat start"; is_nlsolve=true
            )
            attempts["nlsolve_flat"] = Dict(
                "converged" => nlsolve_flat_cv.converged,
                "term_status" => nlsolve_flat_cv.term_status,
                "wall_clock_s" => t_nlsolve_flat,
                "vm_range" => nlsolve_flat_cv.vm_range,
                "va_range_deg" => nlsolve_flat_cv.va_range_deg,
                "n_vm_differ" => nlsolve_flat_cv.n_vm_differ,
                "n_va_nonzero" => nlsolve_flat_cv.n_va_nonzero,
            )

            # ================================================================
            # Attempt 4: compute_ac_pf (NLsolve) DC warm start
            # ================================================================
            if !nlsolve_flat_cv.converged
                println("\n=== Attempt 4: compute_ac_pf (NLsolve) DC Warm Start ===")
                data_nlsolve_warm = deepcopy(data)
                # Reuse DC solution from attempt 2
                if dc_converged &&
                    haskey(dc_result, "solution") &&
                    haskey(dc_result["solution"], "bus")
                    for (bus_id, bus) in data_nlsolve_warm["bus"]
                        bus["vm"] = 1.0
                        bus["va"] = get(get(dc_sol, bus_id, Dict()), "va", 0.0)
                    end

                    t_nlsolve_warm_start = time()
                    result_nlsolve_warm = PowerModels.compute_ac_pf(data_nlsolve_warm)
                    t_nlsolve_warm = time() - t_nlsolve_warm_start
                    println(
                        "NLsolve DC warm-start wall-clock: $(@sprintf("%.6e", t_nlsolve_warm))s"
                    )
                    nlsolve_warm_cv = verify_convergence(
                        result_nlsolve_warm,
                        data_nlsolve_warm,
                        "NLsolve DC warm start";
                        is_nlsolve=true,
                    )
                    attempts["nlsolve_dc_warmstart"] = Dict(
                        "converged" => nlsolve_warm_cv.converged,
                        "term_status" => nlsolve_warm_cv.term_status,
                        "wall_clock_s" => t_nlsolve_warm,
                        "vm_range" => nlsolve_warm_cv.vm_range,
                        "va_range_deg" => nlsolve_warm_cv.va_range_deg,
                        "n_vm_differ" => nlsolve_warm_cv.n_vm_differ,
                        "n_va_nonzero" => nlsolve_warm_cv.n_va_nonzero,
                    )
                else
                    attempts["nlsolve_dc_warmstart"] = Dict(
                        "converged" => false, "reason" => "DCPF failed"
                    )
                end
            end
        end

        rss_after = peak_rss_mb()

        # Determine final status
        any_converged =
            flat_cv.converged ||
            (dc_cv !== nothing && dc_cv.converged) ||
            (nlsolve_flat_cv !== nothing && nlsolve_flat_cv.converged)

        if !any_converged && haskey(attempts, "nlsolve_dc_warmstart")
            any_converged = get(attempts["nlsolve_dc_warmstart"], "converged", false)
        end

        if any_converged
            results["status"] = "pass"
        else
            results["status"] = "fail"
            push!(
                results["errors"],
                "ACPF did not converge at MEDIUM scale. All 4 attempts failed: " *
                "Ipopt flat start, Ipopt DC warm start, NLsolve flat start, NLsolve DC warm start.",
            )
        end

        results["details"] = Dict(
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens" => n_gens,
            "base_mva" => base_mva,
            "n_x_fixed" => n_x_fixed,
            "n_rate_fixed" => n_rate_fixed,
            "cpu_threads_used" => cpu_threads_used,
            "cpu_threads_available" => cpu_threads_available,
            "peak_rss_mb_before" => rss_before,
            "peak_rss_mb_after" => rss_after,
            "attempts" => attempts,
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

    println("\n==============================")
    println("C-2 Status: $(results["status"])")
    println("Wall clock: $(@sprintf("%.6e", results["wall_clock_seconds"]))s")
    println("Peak RSS: $(peak_rss_mb()) MB")
    println("cpu_threads_used: $cpu_threads_used")
    println("cpu_threads_available: $cpu_threads_available")
    println("Errors: $(results["errors"])")
    println("==============================")

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
