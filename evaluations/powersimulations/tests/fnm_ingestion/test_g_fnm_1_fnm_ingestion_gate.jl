#=
Test G-FNM-1: Intermediate format ingestion — two-check gate (PSS/E compat + record counts)

Dimension: fnm_ingestion
Network: LARGE (FNM Annual S01, ~30K buses)
Pass condition: (a) PSS/E compatibility: tool parses .RAW file without error.
                (b) Record count fidelity: all counts match manifest exactly.
Tool: PowerSimulations.jl (via PowerSystems.jl v4.6.2)
=#

using Logging
using PowerSystems: PowerSystems
const PS = PowerSystems

function peak_rss_mb()
    for line in eachline("/proc/self/status")
        if startswith(line, "VmHWM:")
            return parse(Float64, split(line)[2]) / 1024  # kB to MB
        end
    end
    return nothing
end

function run_test(;
    raw_file::String="/data/fnm-source/AUC_AN_2026_2026_S01_ON_NETWORK_MODEL.RAW",
    matpower_fallback::String="/workspace/data/fnm/reference/cleaned/fnm_main_island.m",
)
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    # Suppress verbose PowerSystems logging
    logger = ConsoleLogger(stderr, Logging.Error)
    global_logger(logger)

    # --- Expected counts from intermediate_manifest.json ---
    manifest = Dict(
        "bus" => 30307,
        "load" => 15062,
        "generator" => 5768,
        "branch" => 24117,
        "transformer" => 9723,
        "area" => 49,
        "zone" => 90,
        "switched_shunt" => 3114,
    )

    t0 = time()

    # ===== Sub-check (a): PSS/E RAW parsing =====
    psse_success = false
    psse_error_msg = nothing

    try
        println("Sub-check (a): Attempting PSS/E RAW parse...")
        println("  File: $raw_file")
        println("  File exists: $(isfile(raw_file))")
        println("  File size: $(isfile(raw_file) ? filesize(raw_file) : 0) bytes")

        sys = PS.System(raw_file; runchecks=false)
        psse_success = true
        println("  PSS/E parse: SUCCESS")
    catch e
        psse_error_msg = string(typeof(e), ": ", e)
        println("  PSS/E parse: FAILED")
        println("  Error: $psse_error_msg")
    end

    results["details"]["psse_parse_success"] = psse_success
    results["details"]["psse_error"] = psse_error_msg

    if psse_success
        # ===== Sub-check (b): Record count fidelity =====
        println("\nSub-check (b): Checking record counts...")
        # (Would proceed to count components against manifest)
        # This branch is not reached in this evaluation.
    else
        # PSS/E failed — record failure and try MATPOWER fallback
        results["status"] = "fail"
        results["details"]["failure_reason"] = "psse_parse_error"
        results["details"]["input_path"] = "matpower"
        push!(results["errors"], "PSS/E RAW parsing failed: $psse_error_msg")

        # Load MATPOWER fallback to verify it works for downstream tests
        println("\n--- MATPOWER fallback ---")
        println("  Loading: $matpower_fallback")

        try
            t_mat = time()
            sys = PS.System(matpower_fallback; runchecks=false)
            mat_elapsed = time() - t_mat
            println("  MATPOWER load: SUCCESS in $(round(mat_elapsed, digits=2))s")

            # Collect component counts from MATPOWER fallback
            bus_count = length(collect(PS.get_components(PS.ACBus, sys)))
            gen_count = length(collect(PS.get_components(PS.Generator, sys)))
            line_count = length(collect(PS.get_components(PS.Line, sys)))
            t2w_count = length(collect(PS.get_components(PS.Transformer2W, sys)))
            tap_count = length(collect(PS.get_components(PS.TapTransformer, sys)))
            pst_count = length(collect(PS.get_components(PS.PhaseShiftingTransformer, sys)))
            load_count = length(collect(PS.get_components(PS.ElectricLoad, sys)))
            shunt_count = length(collect(PS.get_components(PS.FixedAdmittance, sys)))
            area_count = length(collect(PS.get_components(PS.Area, sys)))

            matpower_counts = Dict(
                "bus" => bus_count,
                "generator" => gen_count,
                "line" => line_count,
                "transformer_2w" => t2w_count,
                "tap_transformer" => tap_count,
                "phase_shifting_transformer" => pst_count,
                "line_plus_transformers" => line_count + t2w_count + tap_count + pst_count,
                "load" => load_count,
                "fixed_admittance" => shunt_count,
                "area" => area_count,
            )

            results["details"]["matpower_fallback_success"] = true
            results["details"]["matpower_fallback_seconds"] = mat_elapsed
            results["details"]["matpower_counts"] = matpower_counts
            results["details"]["matpower_note"] = "Loaded pre-cleaned main island (27,862 buses). Not the full 30,307-bus FNM."
            results["details"]["peak_rss_mb"] = peak_rss_mb()

            println("\n  Component counts (MATPOWER fallback):")
            for (k, v) in sort(collect(matpower_counts))
                println("    $k: $v")
            end
        catch e
            results["details"]["matpower_fallback_success"] = false
            push!(results["errors"], "MATPOWER fallback also failed: $(typeof(e)): $e")
        end
    end

    results["wall_clock_seconds"] = time() - t0
    return results
end

# Run and print when executed directly
if abspath(PROGRAM_FILE) == @__FILE__
    using JSON
    result = run_test()
    println("\n" * JSON.json(result, 2))
end
