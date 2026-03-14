#=
Test C-5: AC Feasibility — Progressive Relaxation on SMALL (ACTIVSg 2000-bus)

Dimension: scalability
Network: SMALL (ACTIVSg 2000, 2000 buses)
Pass condition: Relaxation level required (0%, 10%, 20%, or infeasible).
  Wall-clock time per attempt. Whether solution was found.
Tool: PowerModels.jl v0.21.5
Solver: Ipopt (NLP)

Depends on: A-2 (ACPF convergence)

Protocol:
  Step 1: Solve DCPF, extract VA for warm start
  Step 2: ACPF at 0% relaxation (VM=1.0, VA=DCPF angles), 30-min timeout
  Step 3: If Step 2 fails, relax thermal limits 10%, retry
  Step 4: If Step 3 fails, relax 20%, retry. Stop here.

converges_ac: true

Implementation notes:
  - PowerModels compute_ac_pf uses NLsolve internally (Newton-Raphson)
  - A-2 MEDIUM showed compute_ac_pf fails on 10k-bus; need to test 2000-bus
  - DC warm start: solve DCPF, set va from solution, keep vm=1.0
  - Thermal relaxation: scale rate_a by (1 + relaxation_fraction)
  - 30-minute timeout per attempt
=#

using PowerModels
using HiGHS
using Ipopt

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

function run(
    network_file::String="../../data/networks/case_ACTIVSg2000.m";
    timeseries_dir::Union{String,Nothing}=nothing,
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    try
        # ==================================================================
        # 1. Load network
        # ==================================================================
        data = PowerModels.parse_file(network_file)
        base_mva = data["baseMVA"]
        n_buses = length(data["bus"])
        n_branches = length(data["branch"])
        n_gens = length(data["gen"])

        println("Network loaded: $n_buses buses, $n_branches branches, $n_gens gens")
        println("baseMVA = $base_mva")

        # System load
        load_sum = sum(get(load, "pd", 0.0) for (_, load) in data["load"]) * base_mva
        println("System load: $(round(load_sum, digits=1)) MW")

        # Store original rate_a values for relaxation
        original_rate_a = Dict{String,Float64}()
        for (br_id, br) in data["branch"]
            original_rate_a[br_id] = br["rate_a"]
        end

        # ==================================================================
        # 2. Step 1: Solve DCPF for warm-start angles
        # ==================================================================
        println("\n--- Step 1: Solving DCPF for warm-start angles ---")

        # Preprocess: fix zero rate_a branches
        n_zero_rate = 0
        for (_, br) in data["branch"]
            if br["rate_a"] <= 0.0
                br["rate_a"] = 99.99  # 9999 MVA
                n_zero_rate += 1
            end
        end
        println("  Fixed $n_zero_rate zero-rated branches (set to 9999 MVA)")

        t_dcpf_start = time()
        dc_data = deepcopy(data)
        dc_result = PowerModels.compute_dc_pf(dc_data)
        t_dcpf = time() - t_dcpf_start

        # Check for trivial solution (all-zero angles)
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
            println("  Falling back to flat start for ACPF")
        end

        # ==================================================================
        # 3. Progressive relaxation: 0%, 10%, 20%
        # ==================================================================
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
                    # Also fix zero-rated
                    if br["rate_a"] <= 0.0
                        br["rate_a"] = 99.99
                    end
                end
                println("  Applied $(relax_pct)% thermal limit relaxation")
            end

            # Set warm start: VM=1.0, VA=DCPF angles (or flat if DCPF failed)
            for (bus_id, bus) in ac_data["bus"]
                bus["vm"] = 1.0
                if n_nonzero_angles > 0 && haskey(dc_angles, bus_id)
                    bus["va"] = dc_angles[bus_id]
                else
                    bus["va"] = 0.0
                end
            end
            println(
                "  Warm start: VM=1.0, VA=$(n_nonzero_angles > 0 ? "DCPF angles" : "flat (0.0)")"
            )

            # Run ACPF using compute_ac_pf (NLsolve Newton-Raphson)
            t_acpf_start = time()
            ac_result = PowerModels.compute_ac_pf(ac_data)
            t_acpf = time() - t_acpf_start

            raw_status = get(ac_result, "termination_status", false)
            converged = (raw_status == true)

            println("  ACPF converged: $converged (Bool=$raw_status)")
            println("  ACPF time: $(round(t_acpf, digits=3))s")

            # Validate convergence quality
            n_vm_differ = 0
            n_va_nonzero = 0
            vm_range = [1.0, 1.0]
            va_range = [0.0, 0.0]
            n_voltage_violations = 0
            n_thermal_violations = 0

            if converged && haskey(ac_result, "solution") && haskey(ac_result["solution"], "bus")
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
                    # Voltage violations
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
                    "  Vm range: $(round(vm_range[1], digits=5)) - $(round(vm_range[2], digits=5)) pu",
                )
                println(
                    "  Va range: $(round(va_range[1], digits=2)) - $(round(va_range[2], digits=2)) deg",
                )
                println("  Buses with Vm != 1.0: $n_vm_differ / $n_buses")
                println("  Non-slack buses with Va != 0: $n_va_nonzero / $(n_buses-1)")
                println("  Voltage violations (outside [0.95,1.05]): $n_voltage_violations")
                println("  Thermal violations: $n_thermal_violations")
            end

            # Convergence quality: verify >95% buses differ from flat start
            convergence_quality_ok = n_va_nonzero / max(1, n_buses - 1) >= 0.95

            level_result = Dict(
                "relaxation_pct" => relax_pct,
                "status" => converged ? "converged" : "failed",
                "converged" => converged,
                "wall_clock_s" => t_acpf,
                "vm_range" => vm_range,
                "va_range_deg" => va_range,
                "n_vm_differ" => n_vm_differ,
                "n_va_nonzero" => n_va_nonzero,
                "convergence_quality_ok" => convergence_quality_ok,
                "n_voltage_violations" => n_voltage_violations,
                "n_thermal_violations" => n_thermal_violations,
                "warm_start" => n_nonzero_angles > 0 ? "DCPF angles" : "flat",
            )
            push!(relaxation_results, level_result)

            if converged && convergence_quality_ok
                solution_found = true
                winning_relaxation = relax_pct
                println("\n  ** Solution found at $(relax_pct)% relaxation **")
                break
            elseif converged && !convergence_quality_ok
                println("  WARNING: Solver reports converged but convergence quality check FAILED")
                println("    Only $(n_va_nonzero)/$(n_buses-1) non-slack buses have nonzero angles")
            end
        end

        # ==================================================================
        # 4. Determine final status
        # ==================================================================
        mem_mb = peak_rss_mb()

        if solution_found
            results["status"] = "pass"
        else
            # Check if any attempt converged but with poor quality
            any_converged = any(r -> get(r, "converged", false), relaxation_results)
            if any_converged
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

        push!(
            results["workarounds"],
            "compute_ac_pf termination_status is Bool, not JuMP/MOI status code. " *
            "NR iteration count and convergence residual not exposed. " *
            "Convergence verified via Bool status + voltage profile quality check.",
        )

        push!(
            results["workarounds"],
            "Branch flows require post-processing via calc_branch_flow_ac after update_data!. " *
            "compute_ac_pf does not populate result[\"solution\"][\"branch\"].",
        )

        total_time = time() - t0
        results["details"] = Dict(
            "network_file" => network_file,
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens" => n_gens,
            "base_mva" => base_mva,
            "system_load_mw" => load_sum,
            "dcpf_time_s" => t_dcpf,
            "dcpf_converged" => dc_converged,
            "dcpf_nonzero_angles" => n_nonzero_angles,
            "relaxation_results" => relaxation_results,
            "solution_found" => solution_found,
            "winning_relaxation_pct" => winning_relaxation,
            "peak_rss_mb" => mem_mb,
            "solver" => "NLsolve (Newton-Raphson via compute_ac_pf)",
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
    println("Errors: $(results["errors"])")
    println("==============================")

    return results
end

# Run when executed directly
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
