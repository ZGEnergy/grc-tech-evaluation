#=
Test G-FNM-3: DCPF Verification Against Reference Solution

Dimension: fnm_ingestion
Network: LARGE (FNM main island via MATPOWER fallback, 28000 buses)
Pass condition: All aggregate thresholds met per pass_conditions.json dcpf section.
  - Bus angle: >=95% of non-excluded buses within 1.0 deg
  - Branch flow: >=90% of in-service branches within 10% (floor 1.0 MW)
  - No hard-fail conditions triggered
Tool: PowerSimulations.jl v0.30.2 (PowerSystems.jl v4.6.2, PowerFlows.jl v0.9.0)

Note: PowerFlows.jl DCPowerFlow returns bus angles in radians and branch flows
in per-unit (system base), despite the @info message claiming MW/MVAr. This is
a known documentation inconsistency in PowerFlows.jl v0.9.0 for the DC path.
The AC path correctly exports in MW. We convert: angles via rad2deg, flows via
multiplication by baseMVA (100).
=#

using Logging
using PowerSystems: PowerSystems
using PowerFlows: PowerFlows
using CSV: CSV
using DataFrames: DataFrames
using JSON: JSON

const PS = PowerSystems
const PF = PowerFlows

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024  # kB to MB
        end
    end
    return nothing
end

function load_excluded_buses(path::String)
    data = JSON.parsefile(path)
    excluded = Set{Int}()
    for entry in data["excluded_buses"]
        push!(excluded, entry["bus_number"])
    end
    return excluded
end

function run_test(;
    matpower_file::String="/workspace/data/fnm/reference/cleaned/fnm_main_island.m",
    ref_bus_file::String="/workspace/data/fnm/reference/dcpf/buses_dcpf.csv",
    ref_branch_file::String="/workspace/data/fnm/reference/dcpf/branches_dcpf.csv",
    excluded_buses_file::String="/workspace/data/fnm/reference/excluded_buses.json",
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    # Suppress verbose logging
    logger = ConsoleLogger(stderr, Logging.Error)
    global_logger(logger)

    t0 = time()
    try
        # --- 1. Load network ---
        println("Loading MATPOWER network: $matpower_file")
        t_load = time()
        sys = PS.System(matpower_file; runchecks=false)
        load_elapsed = time() - t_load
        baseMVA = PS.get_base_power(sys)
        println("  Network loaded in $(round(load_elapsed, digits=2))s, baseMVA=$baseMVA")
        results["details"]["load_seconds"] = load_elapsed
        results["details"]["baseMVA"] = baseMVA

        bus_count = length(collect(PS.get_components(PS.ACBus, sys)))
        println("  Bus count: $bus_count")

        # --- 2. Solve DCPF ---
        println("\nSolving DCPF via PowerFlows.DCPowerFlow()...")
        t_solve = time()
        dc_result = PF.solve_powerflow(PF.DCPowerFlow(), sys)
        solve_elapsed = time() - t_solve
        println("  DCPF solved in $(round(solve_elapsed, digits=2))s")
        results["details"]["solve_seconds"] = solve_elapsed

        # Extract results — Dict(timestep => Dict("bus_results" => df, "flow_results" => df))
        timestep_key = first(keys(dc_result))
        bus_df = dc_result[timestep_key]["bus_results"]
        flow_df = dc_result[timestep_key]["flow_results"]

        println("  Bus results rows: $(DataFrames.nrow(bus_df))")
        println("  Flow results rows: $(DataFrames.nrow(flow_df))")

        # Verify non-trivial solution
        nonzero_angles = count(x -> abs(x) > 1e-10, bus_df.θ)
        println("  Non-zero bus angles: $nonzero_angles / $(DataFrames.nrow(bus_df))")
        if nonzero_angles == 0
            push!(results["errors"], "Trivial solution: all bus angles are zero")
            results["details"]["trivial_solution"] = true
            results["wall_clock_seconds"] = time() - t0
            return results
        end
        results["details"]["trivial_solution"] = false

        # --- 3. Load reference solution ---
        println("\nLoading reference DCPF solution...")
        ref_buses = CSV.read(ref_bus_file, DataFrames.DataFrame)
        ref_branches = CSV.read(ref_branch_file, DataFrames.DataFrame)
        println(
            "  Reference buses: $(DataFrames.nrow(ref_buses)), branches: $(DataFrames.nrow(ref_branches))",
        )

        excluded = load_excluded_buses(excluded_buses_file)
        println("  Excluded buses: $(length(excluded))")

        # --- 4. Bus angle comparison ---
        # Tool angles in radians -> convert to degrees
        tool_bus_map = Dict{Int,Float64}()
        for row in DataFrames.eachrow(bus_df)
            tool_bus_map[row.bus_number] = rad2deg(row.θ)
        end

        bus_passing = 0
        bus_failing = 0
        bus_total = 0
        max_va_dev = 0.0
        max_va_bus = 0
        bus_deviations = Float64[]
        failing_buses = Tuple{Int,Float64,Float64,Float64}[]  # (bus, tool, ref, dev)

        for row in DataFrames.eachrow(ref_buses)
            bus_num = row.bus_number
            bus_num in excluded && continue
            !haskey(tool_bus_map, bus_num) && continue
            bus_total += 1

            tool_va = tool_bus_map[bus_num]
            ref_va = row.va_deg
            dev = abs(tool_va - ref_va)
            push!(bus_deviations, dev)

            if dev > max_va_dev
                max_va_dev = dev
                max_va_bus = bus_num
            end

            if dev < 1.0  # va_tolerance_deg = 1.0
                bus_passing += 1
            else
                bus_failing += 1
                if length(failing_buses) < 20
                    push!(failing_buses, (bus_num, tool_va, ref_va, dev))
                end
            end
        end

        bus_passing_frac = bus_total > 0 ? bus_passing / bus_total : 0.0
        bus_failing_frac = bus_total > 0 ? bus_failing / bus_total : 1.0
        mean_va_dev =
            length(bus_deviations) > 0 ? sum(bus_deviations) / length(bus_deviations) : 0.0
        sorted_devs = sort(bus_deviations)
        median_va_dev = length(sorted_devs) > 0 ? sorted_devs[div(length(sorted_devs), 2) + 1] : 0.0
        p95_va_dev = if length(sorted_devs) > 0
            sorted_devs[min(length(sorted_devs), Int(ceil(0.95 * length(sorted_devs))))]
        else
            0.0
        end

        println("\n=== Bus Angle Results ===")
        println("  Total non-excluded buses compared: $bus_total")
        println("  Passing (< 1.0 deg): $bus_passing ($(round(bus_passing_frac * 100, digits=2))%)")
        println("  Failing: $bus_failing ($(round(bus_failing_frac * 100, digits=2))%)")
        println("  Max VA deviation: $(round(max_va_dev, digits=4)) deg at bus $max_va_bus")
        println("  Mean VA deviation: $(round(mean_va_dev, digits=4)) deg")
        println("  Median VA deviation: $(round(median_va_dev, digits=4)) deg")
        println("  P95 VA deviation: $(round(p95_va_dev, digits=4)) deg")

        if !isempty(failing_buses)
            println("\n  Sample failing buses (first 10):")
            for (b, tv, rv, d) in failing_buses[1:min(10, length(failing_buses))]
                println(
                    "    Bus $b: tool=$(round(tv, digits=4)) deg, ref=$(round(rv, digits=4)) deg, dev=$(round(d, digits=4))",
                )
            end
        end

        results["details"]["bus_angle"] = Dict(
            "total_compared" => bus_total,
            "passing" => bus_passing,
            "failing" => bus_failing,
            "passing_fraction" => bus_passing_frac,
            "max_deviation_deg" => max_va_dev,
            "max_deviation_bus" => max_va_bus,
            "mean_deviation_deg" => mean_va_dev,
            "median_deviation_deg" => median_va_dev,
            "p95_deviation_deg" => p95_va_dev,
        )

        # --- 5. Branch flow comparison ---
        # Tool flows are in per-unit -> multiply by baseMVA to get MW
        # Aggregate by (from_bus, to_bus) pair to handle parallel branches correctly
        tool_branch_agg = Dict{Tuple{Int,Int},Float64}()
        for row in DataFrames.eachrow(flow_df)
            key = (row.bus_from, row.bus_to)
            tool_branch_agg[key] = get(tool_branch_agg, key, 0.0) + row.P_from_to * baseMVA
        end

        # Aggregate reference flows by (from_bus, to_bus) for in-service branches
        ref_branch_agg = Dict{Tuple{Int,Int},Float64}()
        ref_branch_count = Dict{Tuple{Int,Int},Int}()
        total_inservice = 0
        for row in DataFrames.eachrow(ref_branches)
            row.status != 1 && continue
            total_inservice += 1
            key = (row.from_bus, row.to_bus)
            ref_branch_agg[key] = get(ref_branch_agg, key, 0.0) + row.pf_mw
            ref_branch_count[key] = get(ref_branch_count, key, 0) + 1
        end

        branch_passing = 0
        branch_failing = 0
        branch_total = length(ref_branch_agg)  # unique pairs
        branch_unmatched = 0
        max_branch_dev_pct = 0.0
        max_branch_dev_key = (0, 0)
        branch_deviations_pct = Float64[]
        failing_branches = Tuple{Int,Int,Float64,Float64,Float64}[]

        for (key, ref_flow) in ref_branch_agg
            from_bus, to_bus = key

            tool_flow = nothing
            if haskey(tool_branch_agg, (from_bus, to_bus))
                tool_flow = tool_branch_agg[(from_bus, to_bus)]
            elseif haskey(tool_branch_agg, (to_bus, from_bus))
                tool_flow = -tool_branch_agg[(to_bus, from_bus)]
            end

            if tool_flow === nothing
                branch_unmatched += 1
                branch_failing += 1
                continue
            end

            base = max(abs(ref_flow), 1.0)  # p_base_floor_mw
            dev_pct = abs(tool_flow - ref_flow) / base * 100.0
            push!(branch_deviations_pct, dev_pct)

            if dev_pct > max_branch_dev_pct
                max_branch_dev_pct = dev_pct
                max_branch_dev_key = (from_bus, to_bus)
            end

            if dev_pct < 10.0  # p_tolerance_pct
                branch_passing += 1
            else
                branch_failing += 1
                if length(failing_branches) < 20
                    push!(failing_branches, (from_bus, to_bus, tool_flow, ref_flow, dev_pct))
                end
            end
        end

        branch_passing_frac = branch_total > 0 ? branch_passing / branch_total : 0.0
        branch_failing_frac = branch_total > 0 ? branch_failing / branch_total : 1.0
        mean_branch_dev = if length(branch_deviations_pct) > 0
            sum(branch_deviations_pct) / length(branch_deviations_pct)
        else
            0.0
        end
        sorted_br = sort(branch_deviations_pct)
        median_branch_dev = length(sorted_br) > 0 ? sorted_br[div(length(sorted_br), 2) + 1] : 0.0

        println("\n=== Branch Flow Results ===")
        println("  Total in-service branches (rows): $total_inservice")
        println("  Unique (from,to) pairs: $branch_total")
        println("  Matched: $(branch_total - branch_unmatched)")
        println("  Unmatched: $branch_unmatched")
        println(
            "  Passing (< 10%): $branch_passing ($(round(branch_passing_frac * 100, digits=2))%)"
        )
        println("  Failing: $branch_failing ($(round(branch_failing_frac * 100, digits=2))%)")
        println(
            "  Max branch dev: $(round(max_branch_dev_pct, digits=2))% at $(max_branch_dev_key)"
        )
        println("  Mean branch dev: $(round(mean_branch_dev, digits=2))%")
        println("  Median branch dev: $(round(median_branch_dev, digits=2))%")

        if !isempty(failing_branches)
            println("\n  Sample failing branches (first 10):")
            for (fb, tb, tv, rv, d) in failing_branches[1:min(10, length(failing_branches))]
                println(
                    "    $(fb)->$(tb): tool=$(round(tv, digits=2)) MW, ref=$(round(rv, digits=2)) MW, dev=$(round(d, digits=1))%",
                )
            end
        end

        results["details"]["branch_flow"] = Dict(
            "total_compared" => branch_total,
            "matched" => branch_total - branch_unmatched,
            "unmatched" => branch_unmatched,
            "passing" => branch_passing,
            "failing" => branch_failing,
            "passing_fraction" => branch_passing_frac,
            "max_deviation_pct" => max_branch_dev_pct,
            "max_deviation_branch" => string(max_branch_dev_key),
            "mean_deviation_pct" => mean_branch_dev,
            "median_deviation_pct" => median_branch_dev,
        )

        # --- 6. Hard-fail checks ---
        hard_fail = false
        hard_fail_reasons = String[]

        if bus_failing_frac > 0.2
            hard_fail = true
            push!(
                hard_fail_reasons,
                "Excessive bus failing: $(round(bus_failing_frac*100, digits=1))% > 20%",
            )
        end
        if branch_failing_frac > 0.2
            hard_fail = true
            push!(
                hard_fail_reasons,
                "Excessive branch failing: $(round(branch_failing_frac*100, digits=1))% > 20%",
            )
        end
        if max_branch_dev_pct > 50.0
            hard_fail = true
            push!(
                hard_fail_reasons,
                "Extreme branch deviation: $(round(max_branch_dev_pct, digits=1))% > 50%",
            )
        end

        results["details"]["hard_fail"] = hard_fail
        results["details"]["hard_fail_reasons"] = hard_fail_reasons

        if hard_fail
            println("\n*** HARD FAIL ***")
            for r in hard_fail_reasons
                ;
                println("  $r");
            end
        end

        # --- 7. Pass/fail ---
        bus_gate = bus_passing_frac >= 0.95
        branch_gate = branch_passing_frac >= 0.90

        println("\n=== Pass Condition ===")
        println("  Bus angle gate (>=95%): $bus_gate ($(round(bus_passing_frac*100, digits=2))%)")
        println(
            "  Branch flow gate (>=90%): $branch_gate ($(round(branch_passing_frac*100, digits=2))%)",
        )
        println("  Hard fail: $hard_fail")

        if !hard_fail && bus_gate && branch_gate
            results["status"] = "pass"
        elseif !hard_fail && (bus_gate || branch_gate)
            results["status"] = "qualified_pass"
        else
            results["status"] = "fail"
        end

        results["details"]["peak_rss_mb"] = peak_rss_mb()

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
        println("\n*** ERROR ***")
        println(results["details"]["traceback"])
    end

    results["wall_clock_seconds"] = time() - t0
    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run_test()
    println("\n" * JSON.json(result, 2))
end
