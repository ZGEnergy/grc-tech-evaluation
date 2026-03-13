#=
Test C-1: DCPF Scale — MEDIUM grade assessment
Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus, case_ACTIVSg10k.m)
Pass condition: Wall-clock time and peak memory recorded.
Tool: PowerModels.jl v0.21.5
Solver: N/A (direct linear algebra via compute_dc_pf)

Notes:
  - Timing data sourced from A-1 MEDIUM expressiveness test (measured).
  - This script re-documents and confirms the timing from the A-1 run.
  - compute_dc_pf uses Julia's backslash (direct sparse solve), no JuMP.
  - Branch flows require manual post-processing (workaround from A-1).

Preprocessing (per MEDIUM protocol):
  - Zero-reactance fix: branches with br_x=0 → set to 0.0001 pu
  - Zero/Inf RATE_A fix: branches with rate_a=0 or Inf → set to 9999 MVA
=#

using PowerModels

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

function run(
    network_file::String=joinpath(
        @__DIR__, "..", "..", "..", "..", "data", "networks", "case_ACTIVSg10k.m"
    ),
)
    results = Dict(
        "test_id" => "C-1",
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
    )

    # Warm-up on case39 to eliminate JIT compilation from timing
    try
        tiny_file = joinpath(dirname(network_file), "case39.m")
        _data = PowerModels.parse_file(tiny_file)
        PowerModels.compute_dc_pf(_data)
    catch
        ;
    end

    t0 = time()
    try
        println("Loading network: $network_file")
        t_parse_start = time()
        data = PowerModels.parse_file(network_file)
        t_parse = time() - t_parse_start
        println("Network parsed in $(round(t_parse, digits=2))s")

        n_buses = length(data["bus"])
        n_branches = length(data["branch"])
        n_gens = length(data["gen"])
        base_mva = data["baseMVA"]
        println("Network: $n_buses buses, $n_branches branches, $n_gens gens, baseMVA=$base_mva")

        # Apply MEDIUM preprocessing
        n_x_fixed, n_rate_fixed = apply_medium_preprocessing!(data)
        println("Preprocessing: $n_x_fixed br_x→0.0001, $n_rate_fixed rate_a→9999 MVA")

        # Solve DCPF using direct linear-algebra path (no JuMP, no optimizer)
        println("Solving DCPF via compute_dc_pf (direct sparse solve)...")
        t_solve_start = time()
        result = PowerModels.compute_dc_pf(data)
        t_solve = time() - t_solve_start
        println("DCPF solve time: $(round(t_solve, digits=2))s")

        converged = result["termination_status"] == true
        println("Converged: $converged")

        # Count non-zero bus angles
        n_nonzero_angles = 0
        sol_bus = result["solution"]["bus"]
        for (_, bus_sol) in sol_bus
            va = get(bus_sol, "va", 0.0)
            if abs(va) > 1e-10
                n_nonzero_angles += 1
            end
        end
        println("Non-zero bus angles: $n_nonzero_angles / $n_buses")

        # Compute branch flows from angles (workaround: compute_dc_pf doesn't populate solution["branch"])
        t_post_start = time()
        n_nonzero_flows = 0
        flow_mw_list = Float64[]
        for (_, branch) in data["branch"]
            f_bus = string(branch["f_bus"])
            t_bus = string(branch["t_bus"])
            va_f = get(get(sol_bus, f_bus, Dict()), "va", 0.0)
            va_t = get(get(sol_bus, t_bus, Dict()), "va", 0.0)
            shift = get(branch, "shift", 0.0)
            br_x = branch["br_x"]
            tap = get(branch, "tap", 1.0)
            if tap == 0.0
                ;
                tap = 1.0;
            end
            pf_pu = (va_f - va_t - shift) / (br_x * tap)
            pf_mw = pf_pu * base_mva
            push!(flow_mw_list, pf_mw)
            if abs(pf_mw) > 1e-6
                n_nonzero_flows += 1
            end
        end
        t_post = time() - t_post_start
        println("Branch flow computation: $(round(t_post, digits=2))s")
        println("Non-zero branch flows: $n_nonzero_flows / $n_branches")

        flow_range_min = isempty(flow_mw_list) ? NaN : minimum(flow_mw_list)
        flow_range_max = isempty(flow_mw_list) ? NaN : maximum(flow_mw_list)
        println(
            "Flow range: $(round(flow_range_min,digits=2)) to $(round(flow_range_max,digits=2)) MW"
        )

        t_total = time() - t0

        results["status"] = converged ? "pass" : "fail"
        results["details"] = Dict(
            "n_buses" => n_buses,
            "n_branches" => n_branches,
            "n_gens" => n_gens,
            "base_mva" => base_mva,
            "n_x_fixed" => n_x_fixed,
            "n_rate_fixed" => n_rate_fixed,
            "converged" => converged,
            "n_nonzero_angles" => n_nonzero_angles,
            "n_nonzero_flows" => n_nonzero_flows,
            "flow_min_mw" => flow_range_min,
            "flow_max_mw" => flow_range_max,
            "t_parse_s" => t_parse,
            "t_solve_s" => t_solve,
            "t_post_process_s" => t_post,
            "t_total_s" => t_total,
            "solver" => "N/A (compute_dc_pf, direct sparse linear algebra)",
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
    println("--- details ---")
    for (k, v) in result["details"]
        println("  $k: $v")
    end
end
