#=
Test C-2: ACPF on MEDIUM (ACTIVSg 10k)

Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus, 12706 branches, 2485 generators)
Pass condition: Completes. Wall-clock, peak memory, convergence status recorded.
Tool: PowerSimulations.jl v0.30.2 (PowerFlows.jl v0.9.0)
=#

using PowerSystems
using PowerFlows
using JSON
using Logging
using DataFrames

# Suppress verbose logging
global_logger(ConsoleLogger(stderr, Logging.Error))

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024  # kB to MB
        end
    end
    return nothing
end

function cpu_core_count()
    count = 0
    for line in eachline("/proc/cpuinfo")
        if startswith(line, "processor")
            count += 1
        end
    end
    return count
end

function run(network_file::String="/workspace/data/networks/case_ACTIVSg10k.m")
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    try
        cores = cpu_core_count()
        results["details"]["cpu_cores_available"] = cores

        # Load system
        println(stderr, "Loading MEDIUM (10k bus) system...")
        t_load = time()
        sys = System(network_file)
        elapsed_load = time() - t_load
        println(stderr, "System loaded in $(round(elapsed_load, digits=2))s")

        base_power = get_base_power(sys)
        n_buses = length(collect(get_components(Bus, sys)))
        n_branches = length(collect(get_components(Branch, sys)))
        n_gens = length(collect(get_components(Generator, sys)))

        results["details"]["base_power_mva"] = base_power
        results["details"]["n_buses"] = n_buses
        results["details"]["n_branches"] = n_branches
        results["details"]["n_generators"] = n_gens
        results["details"]["load_time_seconds"] = round(elapsed_load; digits=3)

        # Step 1: DCPF warm-start for better initial point
        println(stderr, "Solving DCPF for warm-start angles...")
        t_dc = time()
        dcpf_result = solve_powerflow(DCPowerFlow(), sys)
        elapsed_dc = time() - t_dc
        results["details"]["dcpf_wall_clock_seconds"] = round(elapsed_dc; digits=3)
        println(stderr, "DCPF solved in $(round(elapsed_dc, digits=2))s")

        if dcpf_result === nothing
            push!(results["errors"], "DCPF did not converge — cannot warm-start ACPF")
            return results
        end

        # Extract DCPF bus results and set angles
        dcpf_inner = dcpf_result["1"]
        dcpf_bus_df = dcpf_inner["bus_results"]

        dc_angles = dcpf_bus_df[:, :θ]
        results["details"]["dcpf_angle_range_deg"] = Dict(
            "min" => round(rad2deg(minimum(dc_angles)); digits=2),
            "max" => round(rad2deg(maximum(dc_angles)); digits=2),
        )

        # Set bus magnitudes to 1.0 (DCPF doesn't produce magnitudes)
        for bus in get_components(Bus, sys)
            set_magnitude!(bus, 1.0)
        end
        println(stderr, "Warm-start initialized (DCPF angles + VM=1.0)")

        # JIT warm-up: first ACPF solve
        println(stderr, "JIT warm-up ACPF solve...")
        t_warmup = time()
        warmup_result = nothing
        try
            warmup_result = solve_powerflow(ACPowerFlow(), sys)
        catch e
            println(stderr, "Warm-up ACPF error: $(typeof(e))")
        end
        elapsed_warmup = time() - t_warmup
        println(
            stderr,
            "Warm-up ACPF done in $(round(elapsed_warmup, digits=2))s, converged=$(warmup_result !== nothing)",
        )
        results["details"]["warmup_seconds"] = round(elapsed_warmup; digits=3)
        results["details"]["warmup_converged"] = warmup_result !== nothing

        mem_after_warmup = peak_rss_mb()
        results["details"]["peak_memory_after_warmup_mb"] = mem_after_warmup

        # Re-apply warm-start for timed run (ACPF modifies system in-place)
        for bus in get_components(Bus, sys)
            set_magnitude!(bus, 1.0)
        end
        # Re-apply DCPF angles
        for row in eachrow(dcpf_bus_df)
            for bus in get_components(Bus, sys)
                if get_number(bus) == row[:bus_number]
                    set_angle!(bus, row[:θ])
                    break
                end
            end
        end

        # Timed ACPF solve (second invocation — JIT cached) with log capture
        println(stderr, "Timed ACPF solve...")
        timed_log = IOBuffer()
        t0 = time()
        pf_result = nothing
        converged = false
        acpf_error = nothing
        try
            with_logger(ConsoleLogger(timed_log, Logging.Info)) do
                pf_result = solve_powerflow(ACPowerFlow(), sys)
                converged = pf_result !== nothing
            end
        catch e
            acpf_error = string(typeof(e), ": ", sprint(showerror, e))
        end
        elapsed = time() - t0
        timed_log_str = String(take!(timed_log))
        println(stderr, "ACPF solve: converged=$converged in $(round(elapsed, digits=3))s")
        println(stderr, "Log output: $timed_log_str")

        results["wall_clock_seconds"] = round(elapsed; digits=3)
        results["details"]["peak_memory_mb"] = peak_rss_mb()
        results["details"]["converged"] = converged
        results["details"]["solver_log"] = timed_log_str

        # Extract NR iteration count from log
        nr_iterations = nothing
        m = match(r"converged after (\d+) iterations", timed_log_str)
        if m !== nothing
            nr_iterations = parse(Int, m.captures[1])
        end
        results["details"]["nr_iterations"] = nr_iterations

        if acpf_error !== nothing
            results["details"]["acpf_error"] = acpf_error
        end

        if converged && pf_result !== nothing
            # Extract voltage statistics
            bus_df = pf_result["bus_results"]
            vm_vals = bus_df[:, :Vm]
            va_vals = bus_df[:, :θ]

            results["details"]["voltage_summary"] = Dict(
                "min_vm_pu" => round(minimum(vm_vals); digits=4),
                "max_vm_pu" => round(maximum(vm_vals); digits=4),
                "mean_vm_pu" => round(sum(vm_vals) / length(vm_vals); digits=4),
                "n_buses" => length(vm_vals),
                "n_vm_nonflat" => count(v -> abs(v - 1.0) > 1e-4, vm_vals),
            )

            # Voltage violations
            n_under = count(v -> v < 0.95, vm_vals)
            n_over = count(v -> v > 1.05, vm_vals)
            results["details"]["voltage_violations"] = Dict(
                "n_under_0.95" => n_under, "n_over_1.05" => n_over, "total" => n_under + n_over
            )

            # Angle statistics
            va_deg = rad2deg.(va_vals)
            results["details"]["angle_summary"] = Dict(
                "min_deg" => round(minimum(va_deg); digits=2),
                "max_deg" => round(maximum(va_deg); digits=2),
                "spread_deg" => round(maximum(va_deg) - minimum(va_deg); digits=2),
            )

            # Branch flow results
            flow_df = pf_result["flow_results"]
            results["details"]["n_branches_solved"] = nrow(flow_df)

            # Power balance check
            p_gen = bus_df[:, :P_gen]
            p_load = bus_df[:, :P_load]
            results["details"]["power_balance"] = Dict(
                "total_gen_mw" => round(sum(p_gen) * base_power; digits=1),
                "total_load_mw" => round(sum(p_load) * base_power; digits=1),
                "losses_mw" => round((sum(p_gen) - sum(p_load)) * base_power; digits=1),
            )

            results["status"] = "pass"
        else
            # ACPF did not converge — still report as a finding
            results["status"] = "fail"
            if acpf_error !== nothing
                push!(results["errors"], "ACPF threw exception: $acpf_error")
            else
                push!(results["errors"], "ACPF returned nothing (did not converge)")
            end
        end

        push!(
            results["workarounds"],
            "DCPF warm-start applied via set_angle! on each bus before ACPF. " *
            "PowerFlows.jl uses built-in Newton-Raphson for ACPF (no Ipopt needed).",
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    end

    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end
