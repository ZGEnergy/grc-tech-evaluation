#=
Test G-FNM-1: Intermediate Format Ingestion (Two-Check Gate)

Dimension: fnm_ingestion
Network: LARGE (FNM)
Pass condition: (a) PSS/E intermediate CSV loads successfully; (b) record counts match manifest
Tool: PowerModels.jl 0.21.5

PowerModels.jl does NOT support CSV ingestion. It supports MATPOWER .m, PSS/E .raw
(v33), and JSON formats only. The intermediate CSV tables cannot be parsed.

Sub-check (a) confirms the PSS/E intermediate CSV format is unsupported (expected fail).
The MATPOWER fallback path is verified to confirm downstream tests (G-FNM-3/4/5) can proceed.
=#

using PowerModels
using JSON

PowerModels.silence()

function run(;
    csv_dir::String="/workspace/data/fnm/intermediate",
    matpower_fallback::String="/workspace/data/fnm/reference/cleaned/fnm_main_island.m",
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    try
        # --- Sub-check (a): Attempt CSV ingestion ---
        # PowerModels supports MATPOWER .m, PSS/E .raw, and JSON — NOT CSV.
        # The intermediate CSVs are tabular extracts from PSS/E, not a format
        # PowerModels can parse. This failure is expected and documented.

        csv_attempted = false
        csv_success = false

        if isdir(csv_dir)
            csv_files = filter(f -> endswith(f, ".csv"), readdir(csv_dir))
            if !isempty(csv_files)
                csv_attempted = true
                try
                    test_file = joinpath(csv_dir, csv_files[1])
                    data = PowerModels.parse_file(test_file)
                    csv_success = true
                catch e
                    push!(
                        results["errors"],
                        "CSV ingestion failed (expected): $(typeof(e)): $(sprint(showerror, e))",
                    )
                end
            else
                push!(
                    results["errors"],
                    "No CSV files in intermediate directory ($csv_dir). " *
                    "Intermediate CSVs are NDA-restricted and not committed to version control.",
                )
            end
        else
            push!(results["errors"], "Intermediate CSV directory not found: $csv_dir")
        end

        results["details"]["csv_attempted"] = csv_attempted
        results["details"]["csv_success"] = csv_success
        results["details"]["csv_format_unsupported"] = true
        results["details"]["failure_reason"] = "psse_parse_error"
        results["details"]["ingestion_path"] = "matpower_fallback"

        # --- MATPOWER fallback verification ---
        # G-FNM-1 fails because CSV is unsupported, but we verify the MATPOWER
        # fallback loads correctly so downstream G-FNM-3/4/5 can proceed.
        matpower_success = false

        if isfile(matpower_fallback)
            println("Verifying MATPOWER fallback: $matpower_fallback")
            t_load = time()
            try
                matpower_data = PowerModels.parse_file(matpower_fallback)
                matpower_success = true
                load_time = time() - t_load

                n_bus = length(matpower_data["bus"])
                n_branch = length(matpower_data["branch"])
                n_gen = length(matpower_data["gen"])
                n_load = length(matpower_data["load"])

                slack_buses = [
                    parse(Int, id) for (id, bus) in matpower_data["bus"] if bus["bus_type"] == 3
                ]

                baseMVA = get(matpower_data, "baseMVA", nothing)

                # Check tap ratio preservation
                tap_zero_count = 0
                tap_unity_count = 0
                for (id, br) in matpower_data["branch"]
                    tap = get(br, "tap", 1.0)
                    if tap == 0.0
                        tap_zero_count += 1
                    elseif tap == 1.0
                        tap_unity_count += 1
                    end
                end

                results["details"]["matpower_fallback"] = Dict(
                    "path" => matpower_fallback,
                    "load_time_seconds" => load_time,
                    "bus_count" => n_bus,
                    "branch_count" => n_branch,
                    "gen_count" => n_gen,
                    "load_count" => n_load,
                    "slack_buses" => slack_buses,
                    "baseMVA" => baseMVA,
                    "tap_zero_count" => tap_zero_count,
                    "tap_unity_count" => tap_unity_count,
                )

                println("  Buses:      $n_bus")
                println("  Branches:   $n_branch")
                println("  Generators: $n_gen")
                println("  Loads:      $n_load")
                println("  Slack buses: $slack_buses")
                println("  baseMVA:    $baseMVA")
                println("  Load time:  $(round(load_time, digits=2))s")
            catch e
                push!(
                    results["errors"],
                    "MATPOWER fallback failed: $(typeof(e)): $(sprint(showerror, e))",
                )
            end
        else
            push!(results["errors"], "MATPOWER fallback file not found: $matpower_fallback")
        end

        results["details"]["matpower_fallback_success"] = matpower_success

        # G-FNM-1 status is always fail: the PSS/E intermediate CSV format is
        # not supported by PowerModels. The MATPOWER fallback verification is
        # informational — it enables G-FNM-3/4/5 but does not change G-FNM-1 outcome.
        results["status"] = "fail"

        push!(
            results["workarounds"],
            "PowerModels cannot ingest PSS/E intermediate CSV format. " *
            "MATPOWER .m fallback required for all FNM analysis.",
        )

    catch e
        push!(results["errors"], "$(typeof(e)): $(sprint(showerror, e))")
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

# Run and print when executed directly
if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println("\n=== RESULTS ===")
    println(JSON.json(result, 2))
end
