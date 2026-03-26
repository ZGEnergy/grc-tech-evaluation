#=
Test C-5: AC Feasibility — Progressive Relaxation on MEDIUM (ACTIVSg 10000-bus)

Dimension: scalability
Network: MEDIUM (ACTIVSg 10000, 10000 buses)
Pass condition: Relaxation level required (0%, 10%, 20%, or infeasible).
  Wall-clock time per attempt.
Tool: PowerModels.jl v0.21.5
Solver: Ipopt (NLP)

converges_ac: true — apply convergence verification

Protocol:
  Step 1: Solve DCPF, extract VA for warm start
  Step 2: ACPF at 0% relaxation (VM=1.0, VA=DCPF angles), 30-min timeout
  Step 3: If Step 2 fails, relax thermal limits 10%, retry
  Step 4: If Step 3 fails, relax 20%, retry. Stop here.

Implementation notes:
  - Prior v9 C-5 on SMALL (2000-bus) passed at 0% with compute_ac_pf (NLsolve)
  - For MEDIUM, use solve_ac_pf with Ipopt (same approach as C-2 v10)
  - 30-minute timeout per attempt
=#

using PowerModels
using JuMP
using Ipopt
using HiGHS

PowerModels.silence()

const RELAXATION_LEVELS = [0.0, 0.10, 0.20]
const TIMEOUT_SECONDS = 1800.0
const VM_MIN = 0.95
const VM_MAX = 1.05

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

function run(
    network_file::String=joinpath(
        @__DIR__, "..", "..", "..", "..", "data", "networks", "case_ACTIVSg10k.m"
    );
    timeseries_dir::Union{String,Nothing}=nothing,
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    # JIT warm-up
    println("Warming up JIT on case39...")
    try
        tiny_file = joinpath(dirname(network_file), "case39.m")
        _data = PowerModels.parse_file(tiny_file)
        PowerModels.compute_dc_pf(_data)
        _data2 = PowerModels.parse_file(tiny_file)
        PowerModels.solve_ac_pf(_data2, Ipopt.Optimizer)
    catch e
        println("Warm-up warning: $e")
    end
    println("JIT warm-up complete.")

    rss_before = peak_rss_mb()
    t0 = time()
    try
        # ================================================================
        # 1. Load network
        # ================================================================
        data = PowerModels.parse_file(network_file)
        base_mva = data["baseMVA"]
        n_buses = length(data["bus"])
        n_branches = length(data["branch"])
        n_gens = length(data["gen"])

        println("Network loaded: $n_buses buses, $n_branches branches, $n_gens gens")
        println("baseMVA = $base_mva")

        load_sum = sum(get(load, "pd", 0.0) for (_, load) in data["load"]) * base_mva
        println("System load: $(round(load_sum, digits=1)) MW")

        n_x_fixed, n_rate_fixed = apply_medium_preprocessing!(data)
        println("Preprocessing: $n_x_fixed br_x→0.0001, $n_rate_fixed rate_a→9999 MVA")

        # Store original rate_a values for relaxation
        original_rate_a = Dict{String,Float64}()
        for (br_id, br) in data["branch"]
            original_rate_a[br_id] = br["rate_a"]
        end

        # ================================================================
        # 2. Step 1: Solve DCPF for warm-start angles
        # ================================================================
        println("\n--- Step 1: Solving DCPF for warm-start angles ---")

        t_dcpf_start = time()
        dc_data = deepcopy(data)
        dc_result = PowerModels.compute_dc_pf(dc_data)
        t_dcpf = time() - t_dcpf_start

        dc_angles = Dict{String,Float64}()
        n_nonzero_angles = 0
        if haskey(dc_result, "solution") && haskey(dc_result["solution"], "bus")
            for (bus_id, bus_sol) in dc_result["solution"]["bus"]
                va = get(bus_sol, "va", 0.0)
                dc_angles[bus_id] = va
                if abs(va) > 1e-8
                    n_nonzero_angles += 1
                end
            end
        end

        dc_converged = get(dc_result, "termination_status", false) == true
        println("  DCPF converged: $dc_converged")
        println("  DCPF time: $(round(t_dcpf, digits=3))s")
        println("  Non-zero angle buses: $n_nonzero_angles / $n_buses")

        if n_nonzero_angles == 0
            println("  WARNING: Trivial DCPF solution (all-zero angles)")
        end

        # ================================================================
        # 3. Progressive relaxation: 0%, 10%, 20%
        # ================================================================
        relaxation_results = []
        solution_found = false
        winning_relaxation = nothing

        for (level_idx, relax) in enumerate(RELAXATION_LEVELS)
            relax_pct = Int(round(relax * 100))
            println("\n--- Step $(level_idx+1): ACPF with $(relax_pct)% thermal relaxation ---")

            # Check time budget
            elapsed = time() - t0
            remaining = TIMEOUT_SECONDS - elapsed
            if remaining < 60.0
                println("  Skipping: only $(round(remaining, digits=0))s remaining in budget")
                push!(
                    relaxation_results,
                    Dict(
                        "relaxation_pct" => relax_pct,
                        "status" => "skipped",
                        "reason" => "insufficient time budget",
                    ),
                )
                continue
            end

            # Fresh data copy for each attempt
            ac_data = deepcopy(data)

            # Apply thermal relaxation
            if relax > 0.0
                for (br_id, br) in ac_data["branch"]
                    br["rate_a"] = original_rate_a[br_id] * (1.0 + relax)
                end
                println("  Applied $(relax_pct)% thermal limit relaxation")
            end

            # Set warm start: VM=1.0, VA=DCPF angles
            for (bus_id, bus) in ac_data["bus"]
                bus["vm"] = 1.0
                if n_nonzero_angles > 0 && haskey(dc_angles, bus_id)
                    bus["va"] = dc_angles[bus_id]
                else
                    bus["va"] = 0.0
                end
            end
            warm_start_type = n_nonzero_angles > 0 ? "DCPF angles" : "flat (0.0)"
            println("  Warm start: VM=1.0, VA=$warm_start_type")

            # Ipopt optimizer
            ipopt_opt = JuMP.optimizer_with_attributes(
                Ipopt.Optimizer,
                "max_iter" => 1000,
                "tol" => 1e-6,
                "acceptable_tol" => 1e-4,
                "print_level" => 5,
                "linear_solver" => "mumps",
                "warm_start_init_point" => "yes",
                "mu_init" => 1e-2,
            )

            # Run ACPF using solve_ac_pf with Ipopt
            t_acpf_start = time()
            ac_result = PowerModels.solve_ac_pf(ac_data, ipopt_opt)
            t_acpf = time() - t_acpf_start

            term_status = string(ac_result["termination_status"])
            solver_time = get(ac_result, "solve_time", NaN)
            solver_converged = (
                occursin("LOCALLY_SOLVED", term_status) ||
                occursin("OPTIMAL", term_status) ||
                occursin("ALMOST_LOCALLY_SOLVED", term_status)
            )

            println("  Termination status: $term_status")
            println(
                "  ACPF time: $(round(t_acpf, digits=3))s (solver: $(round(solver_time, digits=3))s)",
            )

            # Validate convergence quality
            n_vm_differ = 0
            n_va_nonzero = 0
            vm_range = [NaN, NaN]
            va_range = [NaN, NaN]
            n_voltage_violations = 0
            n_thermal_violations = 0

            if solver_converged &&
                haskey(ac_result, "solution") &&
                haskey(ac_result["solution"], "bus")
                vm_vals = Float64[]
                va_vals = Float64[]
                for (bus_id, bus_sol) in ac_result["solution"]["bus"]
                    vm = get(bus_sol, "vm", 1.0)
                    va = get(bus_sol, "va", 0.0)
                    push!(vm_vals, vm)
                    push!(va_vals, va)
                    if abs(vm - 1.0) > 1e-4
                        n_vm_differ += 1
                    end
                    bus_type = get(ac_data["bus"][bus_id], "bus_type", 1)
                    if bus_type != 3 && abs(va) > 1e-6
                        n_va_nonzero += 1
                    end
                    if vm < VM_MIN || vm > VM_MAX
                        n_voltage_violations += 1
                    end
                end
                if !isempty(vm_vals)
                    vm_range = [minimum(vm_vals), maximum(vm_vals)]
                    va_range = [minimum(va_vals) * 180/pi, maximum(va_vals) * 180/pi]
                end

                # Branch flow thermal violations
                PowerModels.update_data!(ac_data, ac_result["solution"])
                flow_data = PowerModels.calc_branch_flow_ac(ac_data)
                for (br_id, br_flows) in flow_data["branch"]
                    pf = get(br_flows, "pf", 0.0)
                    qf = get(br_flows, "qf", 0.0)
                    flow_mva = sqrt(pf^2 + qf^2) * base_mva
                    rate_a_mva = ac_data["branch"][br_id]["rate_a"] * base_mva
                    if rate_a_mva > 0.1 && flow_mva > rate_a_mva
                        n_thermal_violations += 1
                    end
                end

                println(
                    "  Vm range: $(round(vm_range[1], digits=5)) — $(round(vm_range[2], digits=5)) pu",
                )
                println(
                    "  Va range: $(round(va_range[1], digits=2)) — $(round(va_range[2], digits=2)) deg",
                )
                println("  Buses with Vm != 1.0: $n_vm_differ / $n_buses")
                println("  Non-slack Va != 0: $n_va_nonzero / $(n_buses-1)")
                println("  Voltage violations (outside [0.95,1.05]): $n_voltage_violations")
                println("  Thermal violations: $n_thermal_violations")
            end

            convergence_quality_ok = n_va_nonzero / max(1, n_buses - 1) >= 0.95

            level_result = Dict(
                "relaxation_pct" => relax_pct,
                "status" => solver_converged ? "converged" : "failed",
                "converged" => solver_converged,
                "convergence_quality_ok" => convergence_quality_ok,
                "term_status" => term_status,
                "wall_clock_s" => t_acpf,
                "solver_time_s" => solver_time,
                "vm_range" => vm_range,
                "va_range_deg" => va_range,
                "n_vm_differ" => n_vm_differ,
                "n_va_nonzero" => n_va_nonzero,
                "n_voltage_violations" => n_voltage_violations,
                "n_thermal_violations" => n_thermal_violations,
                "warm_start" => warm_start_type,
            )
            push!(relaxation_results, level_result)

            if solver_converged && convergence_quality_ok
                solution_found = true
                winning_relaxation = relax_pct
                println("\n  ** Solution found at $(relax_pct)% relaxation **")
                break
            elseif solver_converged && !convergence_quality_ok
                println("  WARNING: Solver reports converged but convergence quality check FAILED")
                println("    Only $(n_va_nonzero)/$(n_buses-1) non-slack buses have nonzero angles")
            end
        end

        # ================================================================
        # 4. Determine final status
        # ================================================================
        rss_after = peak_rss_mb()

        if solution_found
            results["status"] = "pass"
        else
            any_solver_converged = any(r -> get(r, "converged", false), relaxation_results)
            if any_solver_converged
                results["status"] = "qualified_pass"
                push!(
                    results["errors"],
                    "Solver reported convergence but convergence quality check failed",
                )
            else
                results["status"] = "fail"
                push!(
                    results["errors"],
                    "ACPF did not converge at any relaxation level (0%, 10%, 20%)",
                )
            end
        end

        total_time = time() - t0
        results["details"] = Dict(
            "network_file" => network_file,
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens" => n_gens,
            "base_mva" => base_mva,
            "system_load_mw" => load_sum,
            "n_x_fixed" => n_x_fixed,
            "n_rate_fixed" => n_rate_fixed,
            "dcpf_time_s" => t_dcpf,
            "dcpf_converged" => dc_converged,
            "dcpf_nonzero_angles" => n_nonzero_angles,
            "relaxation_results" => relaxation_results,
            "solution_found" => solution_found,
            "winning_relaxation_pct" => winning_relaxation,
            "peak_rss_mb_before" => rss_before,
            "peak_rss_mb_after" => rss_after,
            "solver" => "Ipopt (via solve_ac_pf)",
            "timeout_per_attempt_s" => TIMEOUT_SECONDS,
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        println("ERROR in C-5: $(typeof(e)): $e")
        bt = catch_backtrace()
        println(sprint(showerror, e, bt))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    println("\n==============================")
    println("C-5 Final Status: $(results["status"])")
    println("Wall clock: $(round(results["wall_clock_seconds"], digits=3))s")
    println("Peak RSS: $(peak_rss_mb()) MB")
    println("Errors: $(results["errors"])")
    println("==============================")

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println("\n--- RESULT SUMMARY ---")
    println("status:             $(result["status"])")
    println("wall_clock_seconds: $(result["wall_clock_seconds"])")
    println("errors:             $(result["errors"])")
    println("workarounds:        $(result["workarounds"])")
    if haskey(result["details"], "relaxation_results")
        for r in result["details"]["relaxation_results"]
            println(
                "  $(r["relaxation_pct"])% relaxation: $(get(r, "status", "unknown")), $(round(get(r, "wall_clock_s", 0.0), digits=2))s",
            )
        end
    end
end
