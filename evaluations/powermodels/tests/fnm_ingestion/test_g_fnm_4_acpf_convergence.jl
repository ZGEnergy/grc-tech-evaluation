#=
Test G-FNM-4: ACPF Convergence on Cleaned FNM Case

Dimension: fnm_ingestion
Network: LARGE (FNM 28000-bus main island)
Pass condition: Informational (all outcomes recorded, no gate consequence)
Tool: PowerModels.jl
Solver: Ipopt
Ingestion path: matpower_raw (MATPOWER .mat fallback)
Test hash: 44405f4b

Steps:
  1. Solve DCPF fresh, extract VA angles, record dcpf_init_mean_deg and dcpf_init_max_abs_deg
  2. ACPF at 0% thermal relaxation with DCPF warm start (VM=1.0, VA=DCPF angles), 30-min timeout
  3. If Step 2 fails, relax thermal limits x1.10, retry
  4. If Step 3 fails, relax x1.20, retry
=#

using PowerModels
using HiGHS
using Ipopt
using JSON
using Printf

PowerModels.silence()

function apply_preprocessing!(data::Dict)
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

function apply_dcpf_warm_start!(data::Dict, dcpf_result::Dict)
    bus_sol = dcpf_result["solution"]["bus"]
    for (bus_id_str, bus_entry) in data["bus"]
        bus_entry["vm"] = 1.0
        va = get(get(bus_sol, bus_id_str, Dict()), "va", 0.0)
        bus_entry["va"] = va
    end
end

function relax_thermal_limits!(data::Dict, relax_fraction::Float64)
    for (_, branch) in data["branch"]
        for key in ["rate_a", "rate_b", "rate_c"]
            if haskey(branch, key) && branch[key] > 0.0
                branch[key] *= (1.0 + relax_fraction)
            end
        end
    end
end

function attempt_acpf(data::Dict, label::String)
    println("  Attempting ACPF ($label)...")
    t_start = time()
    try
        result = PowerModels.solve_ac_pf(
            data, Ipopt.Optimizer; setting=Dict("output" => Dict("duals" => false))
        )
        solve_time = time() - t_start
        term_status = string(result["termination_status"])
        println("    Termination: $term_status")
        println("    Solve time: $(@sprintf("%.2f", solve_time))s")

        converged = term_status in ["LOCALLY_SOLVED", "OPTIMAL"]

        # Check voltage profile quality
        n_flat = 0
        n_total = 0
        vm_values = Float64[]
        if converged && haskey(result, "solution") && haskey(result["solution"], "bus")
            for (_, bus_sol) in result["solution"]["bus"]
                n_total += 1
                vm = get(bus_sol, "vm", 1.0)
                push!(vm_values, vm)
                if abs(vm - 1.0) < 1e-6
                    n_flat += 1
                end
            end
            flat_pct = n_total > 0 ? round(100.0 * n_flat / n_total; digits=1) : 0.0
            println("    Flat VM (=1.0): $n_flat / $n_total ($flat_pct%)")
            if flat_pct > 95.0
                println("    WARNING: >95% flat VM — solver did not converge meaningfully")
                converged = false
            end
        end

        return Dict(
            "converged" => converged,
            "termination_status" => term_status,
            "solve_time_seconds" => round(solve_time; digits=2),
            "objective" => get(result, "objective", nothing),
            "flat_vm_count" => n_flat,
            "total_buses" => n_total,
            "flat_vm_pct" => n_total > 0 ? round(100.0 * n_flat / n_total; digits=1) : nothing,
        )
    catch e
        solve_time = time() - t_start
        err_msg = sprint(showerror, e)
        println("    ERROR: $err_msg")
        println("    Elapsed: $(@sprintf("%.2f", solve_time))s")
        return Dict(
            "converged" => false,
            "termination_status" => "ERROR",
            "solve_time_seconds" => round(solve_time; digits=2),
            "error" => err_msg,
        )
    end
end

function run(; matpower_file::String="/workspace/data/fnm/reference/cleaned/fnm_main_island.m")
    results = Dict(
        "status" => "informational",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    try
        # 1. Load network
        println("Loading network: $matpower_file")
        data = PowerModels.parse_file(matpower_file)
        base_mva = data["baseMVA"]
        n_bus = length(data["bus"])
        n_branch = length(data["branch"])
        println("  baseMVA: $base_mva, Buses: $n_bus, Branches: $n_branch")

        n_x_fixed, n_rate_fixed = apply_preprocessing!(data)
        println("  Preprocessing: $n_x_fixed zero-reactance, $n_rate_fixed rate fixes")

        # Step 1: Solve DCPF fresh for warm start + init metrics
        println("\nStep 1: DCPF for warm start and initialization metrics...")
        t_dcpf = time()
        dcpf_result = PowerModels.solve_dc_pf(data, HiGHS.Optimizer)
        dcpf_time = time() - t_dcpf
        println("  DCPF solved in $(@sprintf("%.2f", dcpf_time))s")
        println("  DCPF termination: $(dcpf_result["termination_status"])")

        # Extract DCPF angles and compute init metrics
        va_degs = Float64[]
        nonzero_va = 0
        for (_, bus_sol) in dcpf_result["solution"]["bus"]
            va_rad = get(bus_sol, "va", 0.0)
            if abs(va_rad) > 1e-10
                nonzero_va += 1
            end
            push!(va_degs, rad2deg(va_rad))
        end
        println("  Nonzero VA buses: $nonzero_va / $(length(va_degs))")

        dcpf_init_mean_deg = isempty(va_degs) ? 0.0 : sum(abs.(va_degs)) / length(va_degs)
        dcpf_init_max_abs_deg = isempty(va_degs) ? 0.0 : maximum(abs.(va_degs))
        println("  DCPF init mean |VA|: $(@sprintf("%.4f", dcpf_init_mean_deg)) deg")
        println("  DCPF init max |VA|: $(@sprintf("%.4f", dcpf_init_max_abs_deg)) deg")

        results["details"]["dcpf"] = Dict(
            "solve_time_seconds" => round(dcpf_time; digits=2),
            "termination_status" => string(dcpf_result["termination_status"]),
            "nonzero_va_buses" => nonzero_va,
            "dcpf_init_mean_deg" => @sprintf("%.4f", dcpf_init_mean_deg),
            "dcpf_init_max_abs_deg" => @sprintf("%.4f", dcpf_init_max_abs_deg),
        )

        # Step 2: ACPF at 0% relaxation with DCPF warm start
        println("\nStep 2: ACPF at 0% relaxation with DCPF warm start...")
        data_0pct = deepcopy(data)
        apply_dcpf_warm_start!(data_0pct, dcpf_result)
        step2_result = attempt_acpf(data_0pct, "0% relaxation")
        results["details"]["acpf_0pct"] = step2_result

        relaxation_achieved = nothing

        if step2_result["converged"]
            relaxation_achieved = "0%"
            println("  ACPF converged at 0% relaxation!")
        else
            # Step 3: Relax thermal limits by 10%
            println("\nStep 3: ACPF at 10% thermal relaxation...")
            data_10pct = deepcopy(data)
            apply_dcpf_warm_start!(data_10pct, dcpf_result)
            relax_thermal_limits!(data_10pct, 0.10)
            step3_result = attempt_acpf(data_10pct, "10% relaxation")
            results["details"]["acpf_10pct"] = step3_result

            if step3_result["converged"]
                relaxation_achieved = "10%"
                println("  ACPF converged at 10% relaxation!")
            else
                # Step 4: Relax thermal limits by 20%
                println("\nStep 4: ACPF at 20% thermal relaxation...")
                data_20pct = deepcopy(data)
                apply_dcpf_warm_start!(data_20pct, dcpf_result)
                relax_thermal_limits!(data_20pct, 0.20)
                step4_result = attempt_acpf(data_20pct, "20% relaxation")
                results["details"]["acpf_20pct"] = step4_result

                if step4_result["converged"]
                    relaxation_achieved = "20%"
                    println("  ACPF converged at 20% relaxation!")
                else
                    println("  ACPF did not converge at any relaxation level.")
                end
            end
        end

        results["details"]["relaxation_level_achieved"] = relaxation_achieved
        results["status"] = "informational"

        println("\n=== RESULT: informational ===")
        println(
            "  Relaxation achieved: $(relaxation_achieved === nothing ? "none" : relaxation_achieved)",
        )

    catch e
        push!(results["errors"], "$(typeof(e)): $(sprint(showerror, e))")
        results["details"]["traceback"] = sprint(io -> Base.showerror(io, e, catch_backtrace()))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    println("JIT warm-up...")
    warmup_data = PowerModels.parse_file("/workspace/data/networks/case39.m")
    PowerModels.solve_dc_pf(warmup_data, HiGHS.Optimizer)
    PowerModels.solve_ac_pf(warmup_data, Ipopt.Optimizer)
    println("Warm-up complete.\n")

    result = run()
    println("\n=== FINAL RESULTS ===")
    println(JSON.json(result, 2))
end
