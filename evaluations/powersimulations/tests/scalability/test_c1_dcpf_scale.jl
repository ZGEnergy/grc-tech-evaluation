#=
Test C-1: DCPF on MEDIUM (ACTIVSg 10k)

Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus, 12706 branches, 2485 generators)
Pass condition: Completes. Wall-clock and peak memory recorded.
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

        # JIT warm-up: first DCPF solve
        println(stderr, "JIT warm-up DCPF solve...")
        t_warmup = time()
        _ = solve_powerflow(DCPowerFlow(), sys)
        elapsed_warmup = time() - t_warmup
        println(stderr, "Warm-up done in $(round(elapsed_warmup, digits=2))s")
        results["details"]["warmup_seconds"] = round(elapsed_warmup; digits=3)

        mem_after_warmup = peak_rss_mb()
        results["details"]["peak_memory_after_warmup_mb"] = mem_after_warmup

        # Timed DCPF solve (second invocation — JIT cached)
        println(stderr, "Timed DCPF solve...")
        t0 = time()
        pf_result = solve_powerflow(DCPowerFlow(), sys)
        elapsed = time() - t0
        println(stderr, "DCPF solved in $(round(elapsed, digits=3))s")

        results["wall_clock_seconds"] = round(elapsed; digits=3)
        results["details"]["peak_memory_mb"] = peak_rss_mb()

        if pf_result === nothing || isempty(pf_result)
            push!(results["errors"], "DCPF returned nothing or empty result")
            return results
        end

        # Extract results — DCPF returns nested Dict with period key "1"
        result_key = first(keys(pf_result))
        inner = pf_result[result_key]
        bus_df = inner["bus_results"]
        flow_df = inner["flow_results"]

        # Bus angle statistics
        angles = bus_df[!, "θ"]
        angles_deg = rad2deg.(angles)
        results["details"]["bus_count_solved"] = nrow(bus_df)
        results["details"]["voltage_angles"] = Dict(
            "min_deg" => round(minimum(angles_deg); digits=2),
            "max_deg" => round(maximum(angles_deg); digits=2),
            "mean_deg" => round(sum(angles_deg) / length(angles_deg); digits=2),
            "nonzero_count" => count(x -> abs(x) > 1e-10, angles),
        )

        # Nodal injection statistics
        p_net = bus_df[!, "P_net"]
        p_gen = bus_df[!, "P_gen"]
        p_load = bus_df[!, "P_load"]
        results["details"]["nodal_injections"] = Dict(
            "P_gen_sum_mw" => round(sum(p_gen) * base_power; digits=1),
            "P_load_sum_mw" => round(sum(p_load) * base_power; digits=1),
            "P_net_sum_pu" => round(sum(p_net); digits=6),
        )

        # Branch flow statistics
        p_from = flow_df[!, "P_from_to"]
        results["details"]["branch_count_solved"] = nrow(flow_df)
        results["details"]["line_flows"] = Dict(
            "min_mw" => round(minimum(p_from) * base_power; digits=1),
            "max_mw" => round(maximum(p_from) * base_power; digits=1),
            "nonzero_count" => count(x -> abs(x) > 1e-6, p_from),
        )

        # Branch loading analysis
        max_loading_pct = 0.0
        n_above_90 = 0
        n_above_99 = 0
        for line in get_components(Line, sys)
            ln = get_name(line)
            if ln in flow_df[!, "line_name"]
                idx = findfirst(==(ln), flow_df[!, "line_name"])
                if idx !== nothing
                    flow_pu = abs(flow_df[idx, "P_from_to"])
                    rating_pu = get_rating(line)
                    if rating_pu > 0
                        loading = flow_pu / rating_pu * 100.0
                        max_loading_pct = max(max_loading_pct, loading)
                        if loading > 90.0
                            n_above_90 += 1
                        end
                        if loading > 99.0
                            n_above_99 += 1
                        end
                    end
                end
            end
        end
        results["details"]["branch_loading"] = Dict(
            "max_loading_pct" => round(max_loading_pct; digits=1),
            "n_above_90pct" => n_above_90,
            "n_above_99pct" => n_above_99,
        )

        # Pass checks
        has_angles = count(x -> abs(x) > 1e-10, angles) > 0
        has_flows = count(x -> abs(x) > 1e-6, p_from) > 0
        results["details"]["pass_checks"] = Dict(
            "completed" => true,
            "has_nonzero_angles" => has_angles,
            "has_nonzero_flows" => has_flows,
            "bus_count_matches" => nrow(bus_df) == n_buses,
        )

        if has_angles && has_flows
            results["status"] = "pass"
        else
            push!(results["errors"], "DCPF produced zero angles or flows")
        end

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
