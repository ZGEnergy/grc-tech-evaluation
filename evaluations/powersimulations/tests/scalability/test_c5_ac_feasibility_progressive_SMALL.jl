#=
Test C-5: AC Feasibility — Progressive Relaxation on SMALL

Dimension: scalability
Network: SMALL (ACTIVSg 2000-bus, 3206 branches, 544 generators)
Pass condition: Diagnostic finding. Record relaxation level (0%, 10%, 20%, or infeasible).
  Wall-clock per attempt.
Tool: PowerSimulations.jl v0.30.2 (PowerFlows.jl v0.9.0)
=#

using PowerSystems
using PowerFlows
using HiGHS
using Ipopt
using JuMP
using JSON
using Logging
using DataFrames
using Dates
using TimeSeries: TimeArray

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

function load_system(network_file::String)
    sys = System(network_file)
    return sys
end

function attempt_acpf(sys; label::String="")
    println(stderr, "  Attempting ACPF ($label)...")
    t0 = time()
    pf_result = nothing
    converged = false
    err_msg = nothing

    try
        pf_result = solve_powerflow(ACPowerFlow(), sys)
        converged = pf_result !== nothing
    catch e
        err_msg = string(typeof(e), ": ", sprint(showerror, e))
    end

    elapsed = time() - t0
    mem = peak_rss_mb()

    result = Dict{String,Any}(
        "label" => label,
        "converged" => converged,
        "wall_clock_seconds" => round(elapsed; digits=3),
        "peak_memory_mb" => mem,
    )

    if err_msg !== nothing
        result["error"] = err_msg
    end

    if converged && pf_result !== nothing
        # Extract voltage statistics
        bus_df = pf_result["bus_results"]
        vm_vals = bus_df[:, :Vm]
        va_vals = bus_df[:, :θ]

        result["voltage_summary"] = Dict(
            "min_vm_pu" => round(minimum(vm_vals); digits=4),
            "max_vm_pu" => round(maximum(vm_vals); digits=4),
            "mean_vm_pu" => round(sum(vm_vals) / length(vm_vals); digits=4),
            "n_buses" => length(vm_vals),
            "n_vm_nonflat" => count(v -> abs(v - 1.0) > 1e-4, vm_vals),
        )

        # Voltage violations
        n_under = count(v -> v < 0.95, vm_vals)
        n_over = count(v -> v > 1.05, vm_vals)
        result["voltage_violations"] = Dict(
            "n_under_0.95" => n_under, "n_over_1.05" => n_over, "total" => n_under + n_over
        )

        # Check flow results
        flow_df = pf_result["flow_results"]
        result["n_branches_solved"] = nrow(flow_df)
    end

    println(stderr, "  ACPF ($label): converged=$converged, $(round(elapsed, digits=1))s")
    return result
end

function apply_thermal_relaxation!(sys, factor::Float64)
    # Multiply all branch ratings by (1 + factor)
    # factor = 0.0 -> nominal, 0.10 -> +10%, 0.20 -> +20%
    multiplier = 1.0 + factor
    for line in get_components(Line, sys)
        base_rating = get_rating(line)
        set_rating!(line, base_rating * multiplier)
    end
    for xfmr in get_components(Transformer2W, sys)
        base_rating = get_rating(xfmr)
        set_rating!(xfmr, base_rating * multiplier)
    end
    for xfmr in get_components(TapTransformer, sys)
        base_rating = get_rating(xfmr)
        set_rating!(xfmr, base_rating * multiplier)
    end
end

function run(network_file::String="/workspace/data/networks/case_ACTIVSg2000.m")
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    try
        cores = cpu_core_count()
        results["details"]["cpu_threads_available"] = cores
        results["details"]["cpu_threads_used"] = 1  # NR is single-threaded

        t_total_start = time()

        # Step 1: Load system
        println(stderr, "Loading system...")
        sys = load_system(network_file)
        base_power = get_base_power(sys)
        n_buses = length(collect(get_components(Bus, sys)))
        n_branches = length(collect(get_components(Branch, sys)))
        n_gens = length(collect(get_components(Generator, sys)))

        results["details"]["base_power_mva"] = base_power
        results["details"]["n_buses"] = n_buses
        results["details"]["n_branches"] = n_branches
        results["details"]["n_generators"] = n_gens

        # Step 2: Solve DCPF for warm-start angles
        println(stderr, "Solving DCPF for warm-start...")
        t_dc = time()
        dcpf_result = solve_powerflow(DCPowerFlow(), sys)
        elapsed_dc = time() - t_dc
        results["details"]["dcpf_wall_clock_seconds"] = round(elapsed_dc; digits=3)

        if dcpf_result === nothing
            push!(results["errors"], "DCPF did not converge — cannot warm-start ACPF")
            results["wall_clock_seconds"] = time() - t_total_start
            return results
        end
        println(stderr, "DCPF solved in $(round(elapsed_dc, digits=2))s")

        # DCPF returns Dict{Union{Char,String}, Dict{String, DataFrame}} with period key "1"
        # Extract the inner dict for period "1"
        dcpf_inner = dcpf_result["1"]
        dcpf_bus_df = dcpf_inner["bus_results"]

        # Step 3: Set bus voltage angles from DCPF, VM = 1.0 pu
        # PowerFlows updates the System in-place when solving DCPF
        # Set all voltage magnitudes to 1.0 pu (DCPF doesn't produce magnitudes)
        for bus in get_components(Bus, sys)
            set_magnitude!(bus, 1.0)
        end
        println(stderr, "Warm-start initialized (DCPF angles + VM=1.0)")

        # Record DCPF angle statistics
        dc_angles = dcpf_bus_df[:, :θ]
        results["details"]["dcpf_angle_range_deg"] = Dict(
            "min" => round(rad2deg(minimum(dc_angles)); digits=2),
            "max" => round(rad2deg(maximum(dc_angles)); digits=2),
        )

        # Step 3b: JIT warm-up — solve ACPF once to compile, discard timing
        println(stderr, "JIT warm-up for ACPF...")
        try
            sys_warmup = load_system(network_file)
            solve_powerflow(ACPowerFlow(), sys_warmup)
            println(stderr, "JIT warm-up complete.")
        catch e
            println(stderr, "JIT warm-up failed (OK): $(typeof(e))")
        end

        # Step 4: Progressive relaxation attempts
        relaxation_levels = [0.0, 0.10, 0.20]
        relaxation_labels = ["0% (nominal)", "10%", "20%"]
        attempt_results = Dict{String,Any}[]
        achieved_level = nothing

        for (i, (relax, label)) in enumerate(zip(relaxation_levels, relaxation_labels))
            # Reload system fresh for each attempt to avoid cumulative relaxation
            sys_attempt = load_system(network_file)

            # Re-apply DCPF warm-start angles
            for row in eachrow(dcpf_bus_df)
                for bus in get_components(Bus, sys_attempt)
                    if get_number(bus) == row[:bus_number]
                        set_angle!(bus, row[:θ])
                        set_magnitude!(bus, 1.0)
                        break
                    end
                end
            end

            # Apply relaxation
            if relax > 0.0
                apply_thermal_relaxation!(sys_attempt, relax)
            end

            attempt = attempt_acpf(sys_attempt; label="relaxation $label")
            push!(attempt_results, attempt)

            if attempt["converged"]
                achieved_level = label
                # Don't break — run all levels for timing comparison
            end
        end

        results["details"]["relaxation_attempts"] = attempt_results
        results["details"]["relaxation_level_achieved"] = achieved_level

        # Total timing
        results["wall_clock_seconds"] = round(time() - t_total_start; digits=3)
        results["details"]["peak_memory_mb"] = peak_rss_mb()

        # Status determination
        if achieved_level !== nothing
            results["status"] = "pass"
            results["details"]["finding"] = "ACPF converged at relaxation level: $achieved_level"
        else
            results["status"] = "fail"
            results["details"]["finding"] = "ACPF did not converge at any relaxation level (0%, 10%, 20%)"
            push!(
                results["errors"],
                "AC power flow infeasible on SMALL even with 20% thermal relaxation",
            )
        end

        push!(
            results["workarounds"],
            "PowerFlows.jl solve_powerflow(ACPowerFlow(), sys) uses built-in Newton-Raphson. " *
            "No Ipopt needed for ACPF (Ipopt is for ACOPF). " *
            "DCPF warm-start applied via set_angle! on each bus.",
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
