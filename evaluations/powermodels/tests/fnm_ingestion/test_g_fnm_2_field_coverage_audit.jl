#=
Test G-FNM-2: Field Coverage Audit

Dimension: fnm_ingestion
Network: LARGE (FNM via MATPOWER fallback)
Pass condition: All DCPF-critical fields covered (>=19 of 19). ACPF-critical and Informational coverage computed and reported.
Tool: PowerModels.jl 0.21.5
=#

using PowerModels
using JSON

PowerModels.silence()

function run(; matpower_fallback::String="/workspace/data/fnm/reference/cleaned/fnm_main_island.m")
    results = Dict(
        "status" => "fail",
        "wall_clock_seconds" => 0.0,
        "details" => Dict(),
        "errors" => String[],
        "workarounds" => String[],
    )

    t0 = time()
    try
        # 1. Load the MATPOWER fallback
        println("Loading MATPOWER fallback: $matpower_fallback")
        data = PowerModels.parse_file(matpower_fallback)
        println("Loaded successfully. baseMVA=$(data["baseMVA"])")

        # ---------------------------------------------------------------
        # Field Criticality Matrix: enumerate fields present per table
        # The MATPOWER PPC format maps to PowerModels' internal dict keys.
        # We check which fields exist in the loaded data model.
        # ---------------------------------------------------------------

        # Helper: get all unique keys across all entries in a dict-of-dicts
        function get_all_keys(d::Dict)
            all_keys = Set{String}()
            for (id, entry) in d
                if entry isa Dict
                    for k in keys(entry)
                        push!(all_keys, string(k))
                    end
                end
            end
            return sort(collect(all_keys))
        end

        # --- Bus table ---
        bus_keys = get_all_keys(data["bus"])
        println("\nBus fields ($(length(bus_keys))): $bus_keys")

        # Sample a bus entry for inspection
        sample_bus_id = first(keys(data["bus"]))
        sample_bus = data["bus"][sample_bus_id]
        println("Sample bus ($sample_bus_id): $(JSON.json(sample_bus))")

        # --- Load table ---
        load_keys = get_all_keys(data["load"])
        println("\nLoad fields ($(length(load_keys))): $load_keys")

        sample_load_id = first(keys(data["load"]))
        sample_load = data["load"][sample_load_id]
        println("Sample load ($sample_load_id): $(JSON.json(sample_load))")

        # --- Generator table ---
        gen_keys = get_all_keys(data["gen"])
        println("\nGenerator fields ($(length(gen_keys))): $gen_keys")

        sample_gen_id = first(keys(data["gen"]))
        sample_gen = data["gen"][sample_gen_id]
        println("Sample gen ($sample_gen_id): $(JSON.json(sample_gen))")

        # --- Branch table (includes both branches and transformers in MATPOWER) ---
        branch_keys = get_all_keys(data["branch"])
        println("\nBranch fields ($(length(branch_keys))): $branch_keys")

        sample_branch_id = first(keys(data["branch"]))
        sample_branch = data["branch"][sample_branch_id]
        println("Sample branch ($sample_branch_id): $(JSON.json(sample_branch))")

        # --- Check for other top-level data structures ---
        top_keys = sort(collect(keys(data)))
        println("\nTop-level data keys: $top_keys")

        # Check for area, zone, shunt, dcline, storage, switch
        has_shunt = haskey(data, "shunt") && !isempty(data["shunt"])
        has_dcline = haskey(data, "dcline") && !isempty(data["dcline"])
        has_storage = haskey(data, "storage") && !isempty(data["storage"])
        has_switch = haskey(data, "switch") && !isempty(data["switch"])

        println("\nOptional tables present:")
        println("  shunt: $has_shunt")
        println("  dcline: $has_dcline")
        println("  storage: $has_storage")
        println("  switch: $has_switch")

        if has_shunt
            shunt_keys = get_all_keys(data["shunt"])
            println("\nShunt fields ($(length(shunt_keys))): $shunt_keys")
            sample_shunt_id = first(keys(data["shunt"]))
            println("Sample shunt ($sample_shunt_id): $(JSON.json(data["shunt"][sample_shunt_id]))")
            println("Shunt count: $(length(data["shunt"]))")
        end

        if has_dcline
            dcline_keys = get_all_keys(data["dcline"])
            println("\nDCLine fields ($(length(dcline_keys))): $dcline_keys")
            sample_dc_id = first(keys(data["dcline"]))
            println("Sample dcline ($sample_dc_id): $(JSON.json(data["dcline"][sample_dc_id]))")
            println("DCLine count: $(length(data["dcline"]))")
        end

        # ---------------------------------------------------------------
        # Map PowerModels internal field names to intermediate schema fields
        # and assess coverage per criticality tier
        # ---------------------------------------------------------------

        # DCPF-critical fields (26 total across all tables per matrix, but
        # only 19 are from bus/load/generator/branch/transformer -- the
        # record types that map to MATPOWER PPC).
        #
        # The task says "19 DCPF-critical fields" -- let's enumerate them:
        #
        # Bus (3): I, IDE, VA
        # Load (4): I, STATUS, PL  (and actually the matrix shows 4 for load but
        #           one is I which is the bus reference -- let me recount)
        #
        # From the field criticality matrix summary:
        #   Bus: 3 DCPF-critical (I, IDE, VA)
        #   Load: 4 DCPF-critical (I, STATUS, PL, and... let me check)
        #     Actually: I, ID (info), STATUS, AREA(info), ZONE(info), PL, ...
        #     DCPF: I, STATUS, PL = 3, but matrix says 4
        #     Re-reading: Load I=DCPF, ID=Info, STATUS=DCPF, AREA=Info, ZONE=Info,
        #                  PL=DCPF, QL=ACPF... That's 3.
        #     But matrix header says "4 DCPF-critical" -- need to recheck
        #
        # Actually from the matrix re-read:
        #   Load has 4 DCPF-critical: I, STATUS, PL... and checking once more
        #   Actually the summary says "3 DCPF-critical" for load at line 76
        #   Wait -- summary table at line 27 says Load has 4 DCPF-critical
        #   But detailed table at line 76 says "3 DCPF-critical, 5 ACPF-critical, 5 Informational"
        #   There's a discrepancy. Summary says 4, detail says 3+5+5=13... but that doesn't add up to 13 either.
        #   Actually 3+5+5=13. And the detail text at line 76 says "3 DCPF-critical, 5 ACPF-critical, 5 Informational"
        #   but the summary row says 4. Let me count from the actual field table:
        #   I=DCPF, ID=Info, STATUS=DCPF, AREA=Info, ZONE=Info, PL=DCPF, QL=ACPF,
        #   IP=ACPF, IQ=ACPF, YP=ACPF, YQ=ACPF, OWNER=Info, SCALE=Info
        #   That's 3 DCPF-critical. Summary table has a typo showing 4.
        #   Actually re-reading: the summary says Load: 4 DCPF-Critical. Let me trust the detail table
        #   which explicitly assigns tiers. Counting from detail: I, STATUS, PL = 3 DCPF fields.
        #
        # OK, let me just count from the detailed field tables:
        # Bus DCPF-critical: I, IDE, VA = 3
        # Load DCPF-critical: I, STATUS, PL = 3 (summary says 4 but detail says 3)
        # Fixed Shunt DCPF-critical: 0
        # Generator DCPF-critical: I, PG, STAT = 3 (summary says 4, detail text says 3)
        #   Wait -- detail at line 116 says "3 DCPF-critical" but summary says 4
        #   Let me count: I=DCPF, ID=Info, PG=DCPF, QG=ACPF, QT=ACPF, QB=ACPF, VS=ACPF,
        #   IREG=ACPF, MBASE=Info, ..., STAT=DCPF, ...
        #   That's I, PG, STAT = 3. Summary says 4... I'll trust the detail.
        # Branch DCPF-critical: I, J, X, ST = 4 (summary says 5, detail says 4)
        #   Wait detail line 154 says "4 DCPF-critical"... but summary says 5.
        #   I, J, CKT=Info, R=ACPF, X=DCPF, B=ACPF, ..., ST=DCPF = I,J,X,ST = 4
        # Transformer DCPF-critical: I, J, STAT, X1_2, WINDV1, ANG1 = 6
        #   Summary says 10, detail at line 189 says 6
        #   Wait, the summary at line 32 says Transformer: 10 DCPF-critical
        #   but the detail text at line 189 says "6 DCPF-critical". Hmm.
        #   Let me count from the detail table:
        #   I=DCPF, J=DCPF, K=Info, CKT=Info, CW=ACPF, CZ=ACPF, CM=ACPF, MAG1=ACPF,
        #   MAG2=ACPF, NMETR=Info, NAME=Info, STAT=DCPF, ... R1_2=ACPF, X1_2=DCPF,
        #   ... WINDV1=DCPF, ... ANG1=DCPF
        #   So: I, J, STAT, X1_2, WINDV1, ANG1 = 6 DCPF-critical from transformer
        #
        # Total from detail tables: 3 + 3 + 0 + 3 + 4 + 6 = 19 DCPF-critical
        # This matches the task statement of "19 DCPF-critical fields" even though
        # the summary table adds up to 26. The summary table appears to have
        # different counts. I'll use the field-level detail assignments.

        # Now map PowerModels internal names to intermediate schema fields

        # ---- DCPF-CRITICAL FIELD MAPPING ----
        # Format: (schema_table, schema_field, pm_table, pm_key, description)

        dcpf_critical = [
            # Bus (3)
            ("bus", "I", "bus", "bus_i", "Bus number"),
            ("bus", "IDE", "bus", "bus_type", "Bus type code"),
            ("bus", "VA", "bus", "va", "Voltage angle"),
            # Load (3)
            ("load", "I", "load", "load_bus", "Load bus number"),
            ("load", "STATUS", "load", "status", "Load status"),
            ("load", "PL", "load", "pd", "Active load demand"),
            # Generator (3)
            ("generator", "I", "gen", "gen_bus", "Generator bus number"),
            ("generator", "PG", "gen", "pg", "Active power output"),
            ("generator", "STAT", "gen", "gen_status", "Generator status"),
            # Branch (4)
            ("branch", "I", "branch", "f_bus", "From-bus number"),
            ("branch", "J", "branch", "t_bus", "To-bus number"),
            ("branch", "X", "branch", "br_x", "Series reactance"),
            ("branch", "ST", "branch", "br_status", "Branch status"),
            # Transformer (6) -- in MATPOWER, transformers are merged into branch
            ("transformer", "I", "branch", "f_bus", "Transformer winding 1 bus"),
            ("transformer", "J", "branch", "t_bus", "Transformer winding 2 bus"),
            ("transformer", "STAT", "branch", "br_status", "Transformer status"),
            ("transformer", "X1_2", "branch", "br_x", "Transformer reactance"),
            ("transformer", "WINDV1", "branch", "tap", "Winding 1 tap ratio"),
            ("transformer", "ANG1", "branch", "shift", "Phase shift angle"),
        ]

        # ---- ACPF-CRITICAL FIELD MAPPING ----
        acpf_critical = [
            # Bus (2)
            ("bus", "BASKV", "bus", "base_kv", "Base voltage kV"),
            ("bus", "VM", "bus", "vm", "Voltage magnitude"),
            # Load (5)
            ("load", "QL", "load", "qd", "Reactive load"),
            ("load", "IP", "load", nothing, "Constant-current active component"),
            ("load", "IQ", "load", nothing, "Constant-current reactive component"),
            ("load", "YP", "load", nothing, "Constant-admittance active component"),
            ("load", "YQ", "load", nothing, "Constant-admittance reactive component"),
            # Fixed Shunt (5)
            ("fixed_shunt", "I", "shunt", "shunt_bus", "Shunt bus number"),
            ("fixed_shunt", "ID", "shunt", nothing, "Shunt identifier"),
            ("fixed_shunt", "STATUS", "shunt", "status", "Shunt status"),
            ("fixed_shunt", "GL", "shunt", "gs", "Shunt conductance"),
            ("fixed_shunt", "BL", "shunt", "bs", "Shunt susceptance"),
            # Generator (5)
            ("generator", "QG", "gen", "qg", "Reactive power output"),
            ("generator", "QT", "gen", "qmax", "Max reactive power"),
            ("generator", "QB", "gen", "qmin", "Min reactive power"),
            ("generator", "VS", "gen", "vg", "Voltage setpoint"),
            ("generator", "IREG", "gen", nothing, "Remote regulated bus"),
            # Branch (6)
            ("branch", "R", "branch", "br_r", "Series resistance"),
            ("branch", "B", "branch", "b_fr", "Line charging (from-side)"),
            ("branch", "GI", "branch", "g_fr", "From-bus shunt conductance"),
            ("branch", "BI", "branch", "b_fr", "From-bus shunt susceptance"),
            ("branch", "GJ", "branch", "g_to", "To-bus shunt conductance"),
            ("branch", "BJ", "branch", "b_to", "To-bus shunt susceptance"),
            # Transformer ACPF-critical (44 fields -- too many to enumerate individually,
            # but key ones that map to MATPOWER PPC)
            ("transformer", "CW", "branch", nothing, "Winding I/O code"),
            ("transformer", "CZ", "branch", nothing, "Impedance I/O code"),
            ("transformer", "CM", "branch", nothing, "Magnetizing I/O code"),
            ("transformer", "MAG1", "branch", nothing, "Magnetizing conductance"),
            ("transformer", "MAG2", "branch", nothing, "Magnetizing susceptance"),
            ("transformer", "R1_2", "branch", "br_r", "Transformer resistance"),
            ("transformer", "SBASE1_2", "branch", nothing, "Transformer MVA base"),
            ("transformer", "WINDV2", "branch", nothing, "Winding 2 tap ratio"),
            ("transformer", "ANG2", "branch", nothing, "Winding 2 phase shift"),
            ("transformer", "RATA1", "branch", "rate_a", "Winding 1 normal rating"),
            ("transformer", "COD1", "branch", nothing, "Tap changer control mode"),
            ("transformer", "CONT1", "branch", nothing, "Controlled bus number"),
            ("transformer", "RMA1", "branch", nothing, "Max tap ratio"),
            ("transformer", "RMI1", "branch", nothing, "Min tap ratio"),
            ("transformer", "VMA1", "branch", nothing, "Max voltage target"),
            ("transformer", "VMI1", "branch", nothing, "Min voltage target"),
            ("transformer", "NTP1", "branch", nothing, "Number of tap positions"),
            ("transformer", "NOMV1", "branch", nothing, "Winding 1 nominal voltage"),
            ("transformer", "RATA2", "branch", nothing, "Winding 2 normal rating"),
            ("transformer", "COD2", "branch", nothing, "Winding 2 control mode"),
            ("transformer", "CONT2", "branch", nothing, "Winding 2 controlled bus"),
            ("transformer", "RMA2", "branch", nothing, "Winding 2 max tap"),
            ("transformer", "RMI2", "branch", nothing, "Winding 2 min tap"),
            ("transformer", "VMA2", "branch", nothing, "Winding 2 max voltage"),
            ("transformer", "VMI2", "branch", nothing, "Winding 2 min voltage"),
            ("transformer", "NTP2", "branch", nothing, "Winding 2 tap positions"),
            ("transformer", "NOMV2", "branch", nothing, "Winding 2 nominal voltage"),
            ("transformer", "R2_3", "branch", nothing, "Winding 2-3 resistance"),
            ("transformer", "SBASE2_3", "branch", nothing, "Winding 2-3 MVA base"),
            ("transformer", "R3_1", "branch", nothing, "Winding 3-1 resistance"),
            ("transformer", "SBASE3_1", "branch", nothing, "Winding 3-1 MVA base"),
            ("transformer", "VMSTAR", "branch", nothing, "Star-bus voltage magnitude"),
            ("transformer", "ANSTAR", "branch", nothing, "Star-bus voltage angle"),
            ("transformer", "WINDV3", "branch", nothing, "Winding 3 tap ratio"),
            ("transformer", "NOMV3", "branch", nothing, "Winding 3 nominal voltage"),
            ("transformer", "ANG3", "branch", nothing, "Winding 3 phase shift"),
            ("transformer", "RATA3", "branch", nothing, "Winding 3 normal rating"),
            ("transformer", "COD3", "branch", nothing, "Winding 3 control mode"),
            ("transformer", "CONT3", "branch", nothing, "Winding 3 controlled bus"),
            ("transformer", "RMA3", "branch", nothing, "Winding 3 max tap"),
            ("transformer", "RMI3", "branch", nothing, "Winding 3 min tap"),
            ("transformer", "VMA3", "branch", nothing, "Winding 3 max voltage"),
            ("transformer", "VMI3", "branch", nothing, "Winding 3 min voltage"),
            ("transformer", "NTP3", "branch", nothing, "Winding 3 tap positions"),
            # Area (3 ACPF-critical)
            ("area", "ISW", nothing, nothing, "Area slack bus"),
            ("area", "PDES", nothing, nothing, "Area interchange target"),
            ("area", "PTOL", nothing, nothing, "Area interchange tolerance"),
            # Two-Terminal DC (46 ACPF-critical)
            ("two_terminal_dc", "ALL", "dcline", "various", "HVDC line fields"),
            # VSC DC (41 ACPF-critical)
            ("vsc_dc", "ALL", nothing, nothing, "VSC DC fields"),
            # Impedance Correction (23 ACPF-critical)
            ("impedance_correction", "ALL", nothing, nothing, "Impedance correction fields"),
            # Multi-Terminal DC (8 ACPF-critical)
            ("multi_terminal_dc", "ALL", nothing, nothing, "Multi-terminal DC fields"),
            # Multi-Section Line (12 ACPF-critical)
            ("multi_section_line", "ALL", nothing, nothing, "Multi-section line fields"),
            # FACTS (14 ACPF-critical)
            ("facts", "ALL", nothing, nothing, "FACTS device fields"),
            # Switched Shunt (23 ACPF-critical)
            ("switched_shunt", "ALL", nothing, nothing, "Switched shunt fields"),
        ]

        # ---- Check DCPF-critical coverage ----
        dcpf_present = 0
        dcpf_missing = String[]

        for (schema_table, schema_field, pm_table, pm_key, desc) in dcpf_critical
            if pm_key !== nothing && haskey(data, pm_table) && !isempty(data[pm_table])
                sample_id = first(keys(data[pm_table]))
                sample_entry = data[pm_table][sample_id]
                if haskey(sample_entry, pm_key)
                    dcpf_present += 1
                else
                    push!(dcpf_missing, "$schema_table.$schema_field (expected pm key: $pm_key)")
                end
            elseif pm_key === nothing
                push!(dcpf_missing, "$schema_table.$schema_field (no PM mapping)")
            else
                push!(dcpf_missing, "$schema_table.$schema_field (table $pm_table missing)")
            end
        end

        # Note: transformer fields map to branch in MATPOWER, so I/J/STAT/X1_2/WINDV1/ANG1
        # are present as f_bus/t_bus/br_status/br_x/tap/shift in the branch table.
        # These are already counted above.

        dcpf_total = length(dcpf_critical)
        dcpf_coverage_pct = round(100.0 * dcpf_present / dcpf_total; digits=1)

        println("\n=== DCPF-Critical Coverage ===")
        println("Present: $dcpf_present / $dcpf_total ($dcpf_coverage_pct%)")
        if !isempty(dcpf_missing)
            println("Missing: $dcpf_missing")
        end

        # ---- Check ACPF-critical coverage (field-by-field for mappable fields) ----
        acpf_present = 0
        acpf_missing = String[]
        acpf_total_field_count = 0

        for (schema_table, schema_field, pm_table, pm_key, desc) in acpf_critical
            # Skip aggregate entries (ALL) -- count them separately
            if schema_field == "ALL"
                continue
            end
            acpf_total_field_count += 1

            if pm_key !== nothing &&
                pm_table !== nothing &&
                haskey(data, pm_table) &&
                !isempty(data[pm_table])
                sample_id = first(keys(data[pm_table]))
                sample_entry = data[pm_table][sample_id]
                if haskey(sample_entry, pm_key)
                    acpf_present += 1
                else
                    push!(acpf_missing, "$schema_table.$schema_field (expected pm key: $pm_key)")
                end
            elseif pm_key === nothing || pm_table === nothing
                push!(acpf_missing, "$schema_table.$schema_field (no PM mapping)")
            else
                push!(acpf_missing, "$schema_table.$schema_field (table $pm_table missing)")
            end
        end

        # Count aggregate ACPF-critical fields from record types not in MATPOWER PPC
        # Two-Terminal DC: 46 fields -- PowerModels has dcline with partial mapping
        dcline_acpf_present = 0
        dcline_acpf_total = 46
        if has_dcline
            dcline_keys_set = get_all_keys(data["dcline"])
            # PowerModels dcline model has: f_bus, t_bus, br_status, pf, pt, qf, qt, vf, vt,
            # pmin, pmax, qminf, qmaxf, qmint, qmaxt, loss0, loss1, pmaxf, pmaxt, ...
            # This is a simplified model -- maybe 15-20 fields present
            dcline_acpf_present = length(dcline_keys_set)
            println(
                "\nDCLine model has $(dcline_acpf_present) fields (out of 46 two-terminal DC ACPF-critical)",
            )
        end

        # Other record types completely absent from MATPOWER PPC:
        # VSC DC (41), Impedance Correction (23), Multi-Terminal DC (8),
        # Multi-Section Line (12), FACTS (14), Switched Shunt (23)
        # Area (3 -- partially mapped via PowerModels but MATPOWER area data is very limited)

        # Check if area data is present
        has_area = false
        area_field_count = 0
        if haskey(data, "bus")
            # MATPOWER carries area as a bus field, not a separate table
            sample_bus = data["bus"][first(keys(data["bus"]))]
            if haskey(sample_bus, "area")
                has_area = true
                # Only the area number is preserved, not ISW/PDES/PTOL
                area_field_count = 0  # ISW, PDES, PTOL are lost
            end
        end

        # Total ACPF-critical: 237 per summary
        # Fields individually enumerable from bus/load/gen/branch/xfmr tables in MATPOWER PPC
        # plus aggregate counts for record types outside MATPOWER

        total_acpf = 237
        # Individual field-level check count
        acpf_aggregate_missing = (
            46  # two_terminal_dc (even if dcline exists, mapping is partial)
            + 41  # vsc_dc
            + 23  # impedance_correction
            + 8   # multi_terminal_dc
            + 12  # multi_section_line
            + 14  # facts
            + 23  # switched_shunt
            + 3   # area (ISW, PDES, PTOL)
        )
        # Subtract the dcline fields that ARE present
        acpf_aggregate_missing_adjusted = acpf_aggregate_missing
        if has_dcline
            # PowerModels dcline maps some two-terminal DC fields but not all 46
            # The dcline model has ~20 fields; many ACPF-critical fields are lost
            # Being conservative: count the PM fields as partial coverage
            acpf_aggregate_missing_adjusted = acpf_aggregate_missing - min(dcline_acpf_present, 46)
        end

        total_acpf_present = acpf_present + (has_dcline ? min(dcline_acpf_present, 46) : 0)
        total_acpf_missing = total_acpf - total_acpf_present

        acpf_coverage_pct = round(100.0 * total_acpf_present / total_acpf; digits=1)

        println("\n=== ACPF-Critical Coverage ===")
        println("Individually checked: $acpf_present / $acpf_total_field_count")
        println("Total estimated: $total_acpf_present / $total_acpf ($acpf_coverage_pct%)")
        println("Missing individual fields: $acpf_missing")

        # ---- Informational coverage ----
        total_informational = 87

        # Informational fields present in MATPOWER PPC mapping:
        # Bus: NAME(no), AREA(yes), ZONE(yes), OWNER(no), NVHI(vmax), NVLO(vmin), EVHI(no), EVLO(no)
        # -> area, zone, vmax, vmin = 4 of 8
        info_bus_present = 0
        bus_sample = data["bus"][first(keys(data["bus"]))]
        for (field, pm_key) in
            [("AREA", "area"), ("ZONE", "zone"), ("NVHI", "vmax"), ("NVLO", "vmin")]
            if haskey(bus_sample, pm_key)
                info_bus_present += 1
            end
        end
        # Check for NAME, OWNER, EVHI, EVLO
        for (field, pm_key) in
            [("NAME", "name"), ("OWNER", "source_id"), ("EVHI", "evhi"), ("EVLO", "evlo")]
            if haskey(bus_sample, pm_key)
                info_bus_present += 1
            end
        end

        # Load: ID(no individual), AREA(no), ZONE(no), OWNER(no), SCALE(no)
        # -> 0 of 4 typically (PM aggregates loads by index, not by ID)
        info_load_present = 0
        load_sample = data["load"][first(keys(data["load"]))]
        for (field, pm_key) in [
            ("ID", "load_id"),
            ("AREA", "area"),
            ("ZONE", "zone"),
            ("OWNER", "owner"),
            ("SCALE", "scale"),
        ]
            if haskey(load_sample, pm_key)
                info_load_present += 1
            end
        end

        # Generator informational: ID, MBASE, ZR, ZX, RT, XT, GTAP, RMPCT, PT, PB, O1-O4, F1-F4, WMOD, WPF
        info_gen_present = 0
        gen_sample = data["gen"][first(keys(data["gen"]))]
        for pm_key in [
            "gen_id",
            "mbase",
            "zr",
            "zx",
            "rt",
            "xt",
            "gtap",
            "rmpct",
            "pmax",
            "pmin",
            "model",
            "ncost",
            "cost",
            "source_id",
        ]
            if haskey(gen_sample, pm_key)
                info_gen_present += 1
            end
        end

        # Branch informational: CKT, RATEA, RATEB, RATEC, MET, LEN, O1-O4, F1-F4
        info_branch_present = 0
        br_sample = data["branch"][first(keys(data["branch"]))]
        for pm_key in ["rate_a", "rate_b", "rate_c", "source_id"]
            if haskey(br_sample, pm_key)
                info_branch_present += 1
            end
        end

        # Transformer informational (in branch): K, CKT, NMETR, NAME, various
        # Most transformer-specific informational fields are lost in MATPOWER PPC
        info_xfmr_present = 0

        # Zone, Interarea, Owner tables: not present in MATPOWER PPC
        info_other_present = 0

        total_info_present =
            info_bus_present +
            info_load_present +
            info_gen_present +
            info_branch_present +
            info_xfmr_present +
            info_other_present
        info_coverage_pct = round(100.0 * total_info_present / total_informational; digits=1)

        println("\n=== Informational Coverage ===")
        println(
            "Bus: $info_bus_present, Load: $info_load_present, Gen: $info_gen_present, Branch: $info_branch_present",
        )
        println("Total: $total_info_present / $total_informational ($info_coverage_pct%)")

        # ---- Store all results ----
        results["details"] = Dict(
            "bus_fields" => bus_keys,
            "load_fields" => load_keys,
            "gen_fields" => gen_keys,
            "branch_fields" => branch_keys,
            "shunt_present" => has_shunt,
            "dcline_present" => has_dcline,
            "shunt_fields" => has_shunt ? get_all_keys(data["shunt"]) : String[],
            "dcline_fields" => has_dcline ? get_all_keys(data["dcline"]) : String[],
            "shunt_count" => has_shunt ? length(data["shunt"]) : 0,
            "dcline_count" => has_dcline ? length(data["dcline"]) : 0,
            "top_level_keys" => top_keys,
            "dcpf_critical" => Dict(
                "present" => dcpf_present,
                "total" => dcpf_total,
                "coverage_pct" => dcpf_coverage_pct,
                "missing" => dcpf_missing,
            ),
            "acpf_critical" => Dict(
                "present_individual" => acpf_present,
                "total" => total_acpf,
                "estimated_present" => total_acpf_present,
                "coverage_pct" => acpf_coverage_pct,
                "missing_individual" => acpf_missing,
            ),
            "informational" => Dict(
                "present" => total_info_present,
                "total" => total_informational,
                "coverage_pct" => info_coverage_pct,
            ),
        )

        # ---- Determine pass/fail ----
        if dcpf_present >= 19
            results["status"] = "pass"
            println("\n=== PASS: All $dcpf_present/$dcpf_total DCPF-critical fields covered ===")
        else
            results["status"] = "fail"
            println("\n=== FAIL: Only $dcpf_present/$dcpf_total DCPF-critical fields covered ===")
        end

    catch e
        push!(results["errors"], "$(typeof(e)): $(sprint(showerror, e))")
        results["details"]["traceback"] = sprint(io -> Base.showerror(io, e, catch_backtrace()))
    finally
        results["wall_clock_seconds"] = time() - t0
    end

    return results
end

# Run and print when executed directly
if abspath(PROGRAM_FILE) == @__FILE__
    result = run()
    println("\n=== FINAL RESULTS ===")
    println(JSON.json(result, 2))
end
