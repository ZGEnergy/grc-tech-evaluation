#=
Test G-FNM-5: Supplemental CSV Representability Assessment

Dimension: fnm_ingestion
Network: LARGE (FNM Annual S01)
Pass condition: No hard gate. Evidence collection exercise.
  For each of 7 supplemental CSVs, report per-field representability (N/E/X).
Tool: PowerSimulations.jl v0.30.2 (PowerSystems.jl v4.6.2)

This is an analytical assessment, not a code execution test.
The assessment is based on PowerSystems.jl type hierarchy documentation
and the supplemental CSV field definitions from data/fnm/docs/.
=#

# This test is a documentation/analysis exercise.
# The Julia script verifies PowerSystems.jl type structure for evidence.

using Logging
using InteractiveUtils
using PowerSystems: PowerSystems
using JSON: JSON

const PS = PowerSystems

function run_test()
    results = Dict(
        "status" => "informational",
        "wall_clock_seconds" => 0.0,
        "details" => Dict{String,Any}(),
        "errors" => String[],
        "workarounds" => String[],
    )

    logger = ConsoleLogger(stderr, Logging.Error)
    global_logger(logger)

    t0 = time()
    try
        # Verify key PowerSystems.jl types and their fields
        println("=== PowerSystems.jl Type Verification ===\n")

        # 1. Check ext field on component types
        println("1. ext field availability:")
        for T in
            [PS.ACBus, PS.ThermalStandard, PS.Line, PS.TapTransformer, PS.Transformer2W, PS.Area]
            has_ext = :ext in fieldnames(T)
            println("  $T: ext field = $has_ext")
        end

        # 2. Check Contingency type
        println("\n2. Contingency type:")
        if isdefined(PS, :Contingency)
            println("  PS.Contingency exists, abstract=$(isabstracttype(PS.Contingency))")
            if !isabstracttype(PS.Contingency)
                println("  Fields: $(fieldnames(PS.Contingency))")
            else
                for st in InteractiveUtils.subtypes(PS.Contingency)
                    try
                        println("  Subtype: $st, fields=$(fieldnames(st))")
                    catch
                        println("  Subtype: $st (abstract or no fieldnames)")
                        for st2 in InteractiveUtils.subtypes(st)
                            try
                                ;
                                println("    Sub: $st2, fields=$(fieldnames(st2))")
                            catch
                                ;
                                println("    Sub: $st2 (no fieldnames)");
                            end
                        end
                    end
                end
            end
        else
            println("  PS.Contingency NOT defined")
        end

        # 3. Check TransmissionInterface type
        println("\n3. TransmissionInterface type:")
        if isdefined(PS, :TransmissionInterface)
            println(
                "  PS.TransmissionInterface exists, abstract=$(isabstracttype(PS.TransmissionInterface))",
            )
            if !isabstracttype(PS.TransmissionInterface)
                println("  Fields: $(fieldnames(PS.TransmissionInterface))")
            else
                for st in InteractiveUtils.subtypes(PS.TransmissionInterface)
                    try
                        ;
                        println("  Subtype: $st, fields=$(fieldnames(st))")
                    catch
                        ;
                        println("  Subtype: $st (abstract or no fieldnames)");
                    end
                end
            end
        else
            println("  PS.TransmissionInterface NOT defined")
        end

        # 4. Check ThermalStandard fields relevant to ratings
        println("\n4. ThermalStandard fields:")
        println("  Fields: $(fieldnames(PS.ThermalStandard))")

        # 5. Check Line and branch fields for ratings
        println("\n5. Line fields:")
        println("  Fields: $(fieldnames(PS.Line))")

        println("\n6. TapTransformer fields:")
        println("  Fields: $(fieldnames(PS.TapTransformer))")

        # 7. Check ACBus fields
        println("\n7. ACBus fields:")
        println("  Fields: $(fieldnames(PS.ACBus))")

        # 8. Check Area fields
        println("\n8. Area fields:")
        println("  Fields: $(fieldnames(PS.Area))")

        # Build representability summary
        representability = Dict(
            "LINE_AND_TRANSFORMER" => Dict(
                "fields" => 10,
                "native" => 4,   # FROM_BUS (Arc.from), TO_BUS (Arc.to), RATE_A (rating), STATUS (available)
                "extension" => 6, # CKT, ELEMENT_TYPE, RATE_B, RATE_C, RATE_D, EFFECTIVE_DATE
                "external" => 0,
                "native_fields" => ["FROM_BUS", "TO_BUS", "RATE_A", "STATUS"],
                "extension_fields" =>
                    ["CKT", "ELEMENT_TYPE", "RATE_B", "RATE_C", "RATE_D", "EFFECTIVE_DATE"],
                "external_fields" => String[],
            ),
            "TRADING_HUB" => Dict(
                "fields" => 4,
                "native" => 1,   # BUS_NUMBER (ACBus.number)
                "extension" => 0,
                "external" => 3, # HUB_NAME, DISTRIBUTION_FACTOR, HUB_TYPE
                "native_fields" => ["BUS_NUMBER"],
                "extension_fields" => String[],
                "external_fields" => ["HUB_NAME", "DISTRIBUTION_FACTOR", "HUB_TYPE"],
            ),
            "GEN_DISTRIBUTION_FACTOR" => Dict(
                "fields" => 5,
                "native" => 2,   # GEN_BUS (bus), GEN_NAME (name)
                "extension" => 1, # GEN_ID (ext dict)
                "external" => 2, # HUB_NAME, PARTICIPATION_FACTOR
                "native_fields" => ["GEN_BUS", "GEN_NAME"],
                "extension_fields" => ["GEN_ID"],
                "external_fields" => ["HUB_NAME", "PARTICIPATION_FACTOR"],
            ),
            "CONTINGENCY" => Dict(
                "fields" => 6,
                "native" => 5,   # CONTINGENCY_NAME, ELEMENT_TYPE, FROM_BUS, TO_BUS, ELEMENT_BUS
                "extension" => 1, # ELEMENT_CKT
                "external" => 0,
                "native_fields" => [
                    "CONTINGENCY_NAME",
                    "ELEMENT_TYPE",
                    "ELEMENT_FROM_BUS",
                    "ELEMENT_TO_BUS",
                    "ELEMENT_BUS",
                ],
                "extension_fields" => ["ELEMENT_CKT"],
                "external_fields" => String[],
            ),
            "INTERFACE" => Dict(
                "fields" => 5,
                "native" => 3,   # INTERFACE_ID, INTERFACE_NAME, NORMAL_LIMIT_MW
                "extension" => 2, # EMERGENCY_LIMIT_MW, DIRECTION
                "external" => 0,
                "native_fields" => ["INTERFACE_ID", "INTERFACE_NAME", "NORMAL_LIMIT_MW"],
                "extension_fields" => ["EMERGENCY_LIMIT_MW", "DIRECTION"],
                "external_fields" => String[],
            ),
            "INTERFACE_ELEMENT" => Dict(
                "fields" => 6,
                "native" => 4,   # INTERFACE_ID, FROM_BUS, TO_BUS, DIRECTION_COEFF
                "extension" => 2, # CKT, WEIGHT_FACTOR
                "external" => 0,
                "native_fields" => ["INTERFACE_ID", "FROM_BUS", "TO_BUS", "DIRECTION_COEFF"],
                "extension_fields" => ["CKT", "WEIGHT_FACTOR"],
                "external_fields" => String[],
            ),
            "OUTAGE" => Dict(
                "fields" => 8,
                "native" => 3,   # ELEMENT_FROM_BUS, ELEMENT_TO_BUS, ELEMENT_BUS
                "extension" => 1, # ELEMENT_CKT
                "external" => 4, # ELEMENT_TYPE, OUTAGE_START, OUTAGE_END, OUTAGE_TYPE
                "native_fields" => ["ELEMENT_FROM_BUS", "ELEMENT_TO_BUS", "ELEMENT_BUS"],
                "extension_fields" => ["ELEMENT_CKT"],
                "external_fields" =>
                    ["ELEMENT_TYPE", "OUTAGE_START", "OUTAGE_END", "OUTAGE_TYPE"],
            ),
        )

        # Compute totals
        total_fields = sum(d["fields"] for d in values(representability))
        total_native = sum(d["native"] for d in values(representability))
        total_extension = sum(d["extension"] for d in values(representability))
        total_external = sum(d["external"] for d in values(representability))

        println("\n=== Representability Summary ===")
        println("Total fields: $total_fields")
        println("Native (N): $total_native ($(round(total_native/total_fields*100, digits=0))%)")
        println(
            "Extension (E): $total_extension ($(round(total_extension/total_fields*100, digits=0))%)",
        )
        println(
            "External (X): $total_external ($(round(total_external/total_fields*100, digits=0))%)"
        )

        results["details"]["representability"] = representability
        results["details"]["totals"] = Dict(
            "fields" => total_fields,
            "native" => total_native,
            "native_pct" => round(total_native / total_fields * 100; digits=1),
            "extension" => total_extension,
            "extension_pct" => round(total_extension / total_fields * 100; digits=1),
            "external" => total_external,
            "external_pct" => round(total_external / total_fields * 100; digits=1),
        )

    catch e
        push!(results["errors"], string(typeof(e), ": ", e))
    end

    results["wall_clock_seconds"] = time() - t0
    return results
end

if abspath(PROGRAM_FILE) == @__FILE__
    result = run_test()
    println("\n" * JSON.json(result, 2))
end
