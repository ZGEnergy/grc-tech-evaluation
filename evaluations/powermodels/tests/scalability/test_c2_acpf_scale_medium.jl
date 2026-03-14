#=
Test C-2: ACPF Scale — MEDIUM grade assessment
Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus, case_ACTIVSg10k.m)
Pass condition: Wall-clock time, peak memory, iterations
Tool: PowerModels.jl v0.21.5
Solver: Ipopt (per v10 protocol)

Protocol v10 note: Prior v9 results showed NLsolve (compute_ac_pf) failed on 10k buses.
This version uses solve_ac_pf with Ipopt and applies convergence protocol:
  1. Flat start (vm=1.0, va=0.0)
  2. If flat start fails: DC warm start fallback (DCPF angles + vm=1.0)

converges_ac: true — apply convergence verification
=#

using PowerModels
using JuMP
using Ipopt
using HiGHS

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

function verify_convergence(result, data, label)
    println("  --- Convergence verification ($label) ---")
    term_status = string(result["termination_status"])
    println("  Termination status: $term_status")

    solver_time = get(result, "solve_time", NaN)
    println("  Solve time: $(round(solver_time, digits=3))s")

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

    println("  Vm range: $(round(vm_range[1], digits=5)) — $(round(vm_range[2], digits=5)) pu")
    println("  Va range: $(round(va_range[1], digits=2)) — $(round(va_range[2], digits=2)) deg")
    println("  Buses with Vm != 1.0: $n_vm_differ / $n_buses ($(round(pct_vm_differ, digits=1))%)")
    println(
        "  Non-slack Va != 0: $n_va_nonzero / $(n_buses-1) ($(round(pct_va_nonzero, digits=1))%)"
    )

    quality_ok = pct_va_nonzero >= 95.0
    println(
        "  Convergence quality: $(quality_ok ? "VERIFIED" : "FAILED") (>95% non-flat angles required)",
    )

    is_converged = (
        occursin("LOCALLY_SOLVED", term_status) ||
        occursin("OPTIMAL", term_status) ||
        occursin("ALMOST_LOCALLY_SOLVED", term_status)
    )

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

    # Warm-up on case39 to eliminate JIT compilation
    println("Warming up JIT on case39...")
    try
        tiny_file = joinpath(dirname(network_file), "case39.m")
        _data = PowerModels.parse_file(tiny_file)
        _r1 = PowerModels.solve_ac_pf(_data, Ipopt.Optimizer)
        _data2 = PowerModels.parse_file(tiny_file)
        _r2 = PowerModels.compute_dc_pf(_data2)
    catch e
        println("Warm-up warning: $e")
    end
    println("JIT warm-up complete.")

    rss_before = peak_rss_mb()
    t0 = time()
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
        # Step 1: Flat start (vm=1.0, va=0.0)
        # ================================================================
        println("\n=== Step 1: ACPF Flat Start with Ipopt ===")
        data_flat = deepcopy(data)
        for (_, bus) in data_flat["bus"]
            bus["vm"] = 1.0
            bus["va"] = 0.0
        end

        t_flat_start = time()
        result_flat = PowerModels.solve_ac_pf(data_flat, ipopt_opt)
        t_flat = time() - t_flat_start
        println("Flat start wall-clock: $(round(t_flat, digits=2))s")

        flat_cv = verify_convergence(result_flat, data_flat, "flat start")

        # ================================================================
        # Step 2: DC warm start fallback (if flat start failed)
        # ================================================================
        dc_warmstart_used = false
        dc_cv = nothing
        t_dc_warmstart = 0.0
        t_dcpf = 0.0

        if !flat_cv.converged
            println("\n=== Step 2: DC Warm Start Fallback ===")
            dc_warmstart_used = true

            # Solve DCPF for angles
            data_dc = deepcopy(data)
            t_dcpf_start = time()
            dc_result = PowerModels.compute_dc_pf(data_dc)
            t_dcpf = time() - t_dcpf_start
            println("DCPF solve time: $(round(t_dcpf, digits=2))s")

            dc_converged = dc_result["termination_status"] == true
            println("DCPF converged: $dc_converged")

            if dc_converged && haskey(dc_result, "solution") && haskey(dc_result["solution"], "bus")
                # Set warm start angles from DCPF, vm=1.0
                data_warm = deepcopy(data)
                dc_sol = dc_result["solution"]["bus"]
                for (bus_id, bus) in data_warm["bus"]
                    bus["vm"] = 1.0
                    bus["va"] = get(get(dc_sol, bus_id, Dict()), "va", 0.0)
                end

                # Ipopt with warm start hints
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
                println("DC warm-start ACPF wall-clock: $(round(t_dc_warmstart, digits=2))s")

                dc_cv = verify_convergence(result_warm, data_warm, "DC warm start")
            else
                println("DCPF failed — cannot provide DC warm start")
                push!(results["errors"], "DCPF failed, DC warm start not available")
            end
        end

        rss_after = peak_rss_mb()

        # ================================================================
        # Determine final status
        # ================================================================
        final_converged = flat_cv.converged || (dc_cv !== nothing && dc_cv.converged)
        winning_method = if flat_cv.converged
            "flat_start"
        elseif dc_cv !== nothing && dc_cv.converged
            "dc_warm_start"
        else
            "none"
        end

        if flat_cv.converged
            results["status"] = "pass"
        elseif dc_cv !== nothing && dc_cv.converged
            results["status"] = "qualified_pass"
            push!(
                results["workarounds"],
                "DC warm start required for convergence on 10k-bus ACPF. " *
                "Flat start did not converge.",
            )
        else
            results["status"] = "fail"
            push!(
                results["errors"],
                "ACPF did not converge at MEDIUM scale with either flat start or DC warm start using Ipopt.",
            )
        end

        # Use the winning convergence result for details
        best_cv = flat_cv.converged ? flat_cv : (dc_cv !== nothing ? dc_cv : flat_cv)
        best_time = flat_cv.converged ? t_flat : t_dc_warmstart

        results["details"] = Dict(
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens" => n_gens,
            "base_mva" => base_mva,
            "n_x_fixed" => n_x_fixed,
            "n_rate_fixed" => n_rate_fixed,
            "solver" => "Ipopt",
            "flat_start_converged" => flat_cv.converged,
            "flat_start_term_status" => flat_cv.term_status,
            "flat_start_solver_time_s" => flat_cv.solver_time,
            "flat_start_wall_clock_s" => t_flat,
            "flat_start_vm_range" => flat_cv.vm_range,
            "flat_start_va_range_deg" => flat_cv.va_range_deg,
            "flat_start_n_vm_differ" => flat_cv.n_vm_differ,
            "flat_start_n_va_nonzero" => flat_cv.n_va_nonzero,
            "dc_warmstart_used" => dc_warmstart_used,
            "dc_warmstart_converged" => dc_cv !== nothing ? dc_cv.converged : nothing,
            "dc_warmstart_term_status" => dc_cv !== nothing ? dc_cv.term_status : nothing,
            "dc_warmstart_solver_time_s" => dc_cv !== nothing ? dc_cv.solver_time : nothing,
            "dc_warmstart_wall_clock_s" => t_dc_warmstart,
            "dcpf_time_s" => t_dcpf,
            "winning_method" => winning_method,
            "peak_rss_mb_before" => rss_before,
            "peak_rss_mb_after" => rss_after,
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
    println("Wall clock: $(round(results["wall_clock_seconds"], digits=3))s")
    println("Peak RSS: $(peak_rss_mb()) MB")
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
    for (k, v) in result["details"]
        println("  $k: $v")
    end
end
