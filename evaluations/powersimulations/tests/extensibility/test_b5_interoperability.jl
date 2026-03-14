#=
Test B-5: Interoperability (Export DCPF results to DataFrames.jl and CSV)

Dimension: extensibility
Network: TINY (IEEE 39-bus)
Pass condition: Trivial — fewer than 5 LOC beyond the solve. No custom serialization.
Tool: PowerSimulations.jl v0.30.2
=#

using PowerSystems
using PowerFlows
using DataFrames
using CSV
using JSON
using Logging

global_logger(ConsoleLogger(stderr, Logging.Error))

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024
        end
    end
    return nothing
end

function run(
    network_file::String="/workspace/data/networks/case39.m";
    timeseries_dir::Union{String,Nothing}=nothing,
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    try
        # 1. Load network and solve DCPF (reuse A-1 approach)
        sys = System(network_file)

        # Warm-up
        _ = solve_powerflow(DCPowerFlow(), sys)

        # Timed run
        t0 = time()
        pf_result = solve_powerflow(DCPowerFlow(), sys)
        elapsed_pf = time() - t0

        result_key = first(keys(pf_result))
        inner = pf_result[result_key]
        bus_df = inner["bus_results"]    # Already a DataFrame!
        flow_df = inner["flow_results"]  # Already a DataFrame!

        results["details"]["pf_wall_clock_seconds"] = elapsed_pf
        results["details"]["bus_df_type"] = string(typeof(bus_df))
        results["details"]["flow_df_type"] = string(typeof(flow_df))
        results["details"]["bus_rows"] = nrow(bus_df)
        results["details"]["bus_columns"] = names(bus_df)
        results["details"]["flow_rows"] = nrow(flow_df)
        results["details"]["flow_columns"] = names(flow_df)

        # 2. Export to CSV — this is the core of B-5
        # The interoperability test: how many LOC to go from solve to CSV?
        outdir = mktempdir()

        t0_export = time()
        # Line 1: write bus results to CSV
        CSV.write(joinpath(outdir, "bus_results.csv"), bus_df)
        # Line 2: write flow results to CSV
        CSV.write(joinpath(outdir, "flow_results.csv"), flow_df)
        elapsed_export = time() - t0_export

        results["details"]["export_wall_clock_seconds"] = elapsed_export
        results["details"]["export_dir"] = outdir

        # 3. Verify the exported files can be read back
        bus_roundtrip = CSV.read(joinpath(outdir, "bus_results.csv"), DataFrame)
        flow_roundtrip = CSV.read(joinpath(outdir, "flow_results.csv"), DataFrame)

        results["details"]["roundtrip_bus_rows"] = nrow(bus_roundtrip)
        results["details"]["roundtrip_flow_rows"] = nrow(flow_roundtrip)
        results["details"]["roundtrip_bus_cols"] = names(bus_roundtrip)
        results["details"]["roundtrip_flow_cols"] = names(flow_roundtrip)

        # Verify data integrity (compare a sample value)
        bus_match = bus_df[1, "bus_number"] == bus_roundtrip[1, "bus_number"]
        flow_match = isapprox(bus_df[1, "θ"], bus_roundtrip[1, Symbol("θ")]; atol=1e-10)
        results["details"]["roundtrip_integrity"] = Dict(
            "bus_number_match" => bus_match, "theta_match" => flow_match
        )

        # 4. Count LOC for export
        # The export is exactly 2 lines:
        #   CSV.write("bus_results.csv", bus_df)
        #   CSV.write("flow_results.csv", flow_df)
        # No serialization, no type conversion, no manual column extraction.
        results["details"]["export_loc"] = 2
        results["details"]["total_loc_beyond_solve"] = 2

        # 5. Also demonstrate DataFrame manipulation (not required, but shows native interop)
        # Filter to only buses with non-zero generation
        gen_buses = filter(row -> row.P_gen > 0, bus_df)
        results["details"]["gen_bus_count"] = nrow(gen_buses)

        # Summary statistics via DataFrames
        results["details"]["bus_angle_stats"] = Dict(
            "mean_deg" => round(mean(rad2deg.(bus_df[!, "θ"])); digits=4),
            "min_deg" => round(minimum(rad2deg.(bus_df[!, "θ"])); digits=4),
            "max_deg" => round(maximum(rad2deg.(bus_df[!, "θ"])); digits=4),
        )

        results["wall_clock_seconds"] = elapsed_pf + elapsed_export
        results["details"]["peak_memory_mb"] = peak_rss_mb()

        # Pass checks
        is_dataframe = bus_df isa DataFrame && flow_df isa DataFrame
        export_trivial = true  # 2 LOC < 5 LOC threshold
        roundtrip_ok = bus_match && flow_match

        results["details"]["pass_checks"] = Dict(
            "result_is_dataframe" => is_dataframe,
            "export_under_5_loc" => export_trivial,
            "roundtrip_integrity" => roundtrip_ok,
        )

        if is_dataframe && export_trivial && roundtrip_ok
            results["status"] = "pass"
        else
            push!(results["errors"], "Pass condition not met")
        end

    catch e
        push!(results["errors"], string(typeof(e), ": ", sprint(showerror, e)))
        results["details"]["traceback"] = sprint(showerror, e, catch_backtrace())
    end

    return results
end

using Statistics: mean

if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println(JSON.json(result, 2))
end
