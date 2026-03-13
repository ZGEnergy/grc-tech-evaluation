---
test_id: G-FNM-5
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v9
skill_version: v1
test_hash: f0d7a20f
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.132
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 306
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# G-FNM-5: Supplemental CSV Representability

## Result: INFORMATIONAL

## Finding

PyPSA achieves 20.5% native (N), 42.5% extension (E), and 37.0% external (X) representability
across 73 actual fields in 7 supplemental CSVs from the FNM source data. The actual CSV schemas
differ substantially from the analytical PSS/E-style field names in supplemental-csvs.md, but the
tier classifications are consistent where cross-referenced (16 of 17 analytical matches confirmed,
1 mismatch on TRADING_HUB.APNode).

PyPSA's extension mechanism (custom DataFrame column assignment) was verified empirically:
`net.lines["custom_field"] = "test_value"` successfully stores and retrieves arbitrary data.

## Evidence

### Actual CSV Discovery

The FNM source directory contains 7 supplemental CSVs (plus 2 RAW files). INTERFACE_ELEMENT.csv
is not present as a separate file; interface element data is merged into INTERFACE.csv
(which contains both interface-level and element-level fields with 17 columns and 4,076 rows).
RESOURCE.csv is present but was not covered in the analytical classification document.

| CSV | Actual Columns | Rows | N | E | X | N% | E% | X% |
|-----|---------------|------|---|---|---|----|----|-----|
| LINE_AND_TRANSFORMER | 19 | 67,612 | 6 | 13 | 0 | 31.6% | 68.4% | 0.0% |
| TRADING_HUB | 4 | 2,215 | 0 | 1 | 3 | 0.0% | 25.0% | 75.0% |
| GEN_DISTRIBUTION_FACTOR | 4 | 392 | 1 | 2 | 1 | 25.0% | 50.0% | 25.0% |
| CONTINGENCY | 9 | 7,218 | 0 | 1 | 8 | 0.0% | 11.1% | 88.9% |
| INTERFACE | 17 | 4,076 | 2 | 8 | 7 | 11.8% | 47.1% | 41.2% |
| OUTAGE | 11 | 612 | 2 | 1 | 8 | 18.2% | 9.1% | 72.7% |
| RESOURCE | 9 | 11,536 | 4 | 5 | 0 | 44.4% | 55.6% | 0.0% |
| **Totals** | **73** | — | **15** | **31** | **27** | **20.5%** | **42.5%** | **37.0%** |

### Schema Divergence from Analytical Spec

The actual CSV column names use ERCOT-specific naming conventions that differ from the PSS/E-style
field names in supplemental-csvs.md. Key differences:

- **LINE_AND_TRANSFORMER.csv** has 19 columns (vs 10 in analytical spec). Additional fields include
  Device Name, EMS Device Name, From/To Bus Name, From/To Bus Substation, From/To Bus Zone,
  Enforcement, Operating Normal/Emergency Rating, and TOU.
- **CONTINGENCY.csv** has 9 columns (vs 6 in analytical). Additional fields: Description, Device Name,
  EMS Device Name, Action, Outage, TOU. Uses device names rather than bus-pair identifiers.
- **INTERFACE.csv** merges interface definitions and interface elements into a single 17-column file
  (vs separate 5-field INTERFACE.csv and 6-field INTERFACE_ELEMENT.csv in analytical spec).
- **OUTAGE.csv** has 11 columns (vs 8 in analytical). Uses OMS Outage ID, Duration In Hour, Action,
  Device Name rather than FROM_BUS/TO_BUS/CKT composite keys.
- **RESOURCE.csv** (9 fields) is not documented in the analytical spec at all.

### Per-CSV Field Classification Details

#### LINE_AND_TRANSFORMER.csv (19 fields)

| Field | Tier | PyPSA Mapping |
|-------|------|---------------|
| Device Name | E | custom column on Lines/Transformers DataFrame |
| EMS Device Name | E | custom column |
| Device Type | E | custom column (LINE/TRANSFORMER distinguishable natively by component type) |
| From Bus Number | **N** | Line.bus0 / Transformer.bus0 |
| From Bus Name | E | custom column (bus names not imported via PPC) |
| From Bus Substation | E | custom column |
| From Bus Zone | **N** | Bus.zone (imported via PPC) |
| To Bus Number | **N** | Line.bus1 / Transformer.bus1 |
| To Bus Name | E | custom column |
| To Bus Substation | E | custom column |
| To Bus Zone | **N** | Bus.zone (via bus1 lookup) |
| Circuit ID | E | custom column (no native CKT field) |
| Status | **N** | Line.active / Transformer.active |
| Enforcement | E | custom column |
| Normal Rating | **N** | Line.s_nom / Transformer.s_nom |
| Emergency Rating | E | custom column (only 1 native rating tier: s_nom) |
| Operating Normal Rating | E | custom column |
| Operating Emergency Rating | E | custom column |
| TOU | E | custom column (time-of-use period) |

#### TRADING_HUB.csv (4 fields)

| Field | Tier | PyPSA Mapping |
|-------|------|---------------|
| Trading Hub | X | no hub model in PyPSA |
| APNode | X | no hub/settlement node model — actual field contains APNode strings, not integer bus numbers |
| Allocation Factor | X | no hub allocation model |
| TOU | E | custom column |

#### GEN_DISTRIBUTION_FACTOR.csv (4 fields)

| Field | Tier | PyPSA Mapping |
|-------|------|---------------|
| Generator Name | **N** | Generator name (index) |
| EMS Name | E | custom column |
| Distribution Factor | X | no generator distribution factor attribute |
| TOU | E | custom column |

#### CONTINGENCY.csv (9 fields)

| Field | Tier | PyPSA Mapping |
|-------|------|---------------|
| Contingency Name | X | no contingency model in PyPSA |
| Description | X | no contingency model |
| Device Name | X | no contingency model |
| EMS Device Name | X | no contingency model |
| Device Type | X | no contingency model |
| Status | X | no contingency model |
| Action | X | no contingency model |
| Outage | X | no contingency model |
| TOU | E | custom column |

#### INTERFACE.csv (17 fields, merged interface + elements)

| Field | Tier | PyPSA Mapping |
|-------|------|---------------|
| Interface Name | X | no interface/flowgate model |
| Positive Limit | X | no interface model |
| Negative Limit | X | no interface model |
| Operating Positive Limit | X | no interface model |
| Operating Negative Limit | X | no interface model |
| Device Name | E | custom column for element identification |
| EMS Device Name | E | custom column |
| Device Type | E | custom column |
| From Bus Name | E | custom column |
| From Bus Substation | E | custom column |
| From Bus Zone | **N** | Bus.zone |
| To Bus Name | E | custom column |
| To Bus Substation | E | custom column |
| To Bus Zone | **N** | Bus.zone |
| Factor | X | no interface direction coefficient model |
| Outage | X | no interface contingency model |
| TOU | E | custom column |

#### OUTAGE.csv (11 fields)

| Field | Tier | PyPSA Mapping |
|-------|------|---------------|
| OMS Outage ID | X | no outage schedule model |
| Duration In Hour | X | no outage schedule model |
| Action | X | no outage schedule model |
| Device Type | X | no outage schedule model |
| Device Name | X | no outage schedule model |
| Device EMS Name | X | no outage schedule model |
| From Bus ID | **N** | Line.bus0 (if bus number) |
| To Bus ID | **N** | Line.bus1 (if bus number) |
| Adjusted Base Limit | X | no outage schedule model |
| Adjusted Emergency Limit | X | no outage schedule model |
| TOU | E | custom column |

#### RESOURCE.csv (9 fields, not in analytical spec)

| Field | Tier | PyPSA Mapping |
|-------|------|---------------|
| Generator Name | **N** | Generator name (index) |
| EMS Gen Name | E | custom column |
| Bus Name | E | custom column |
| EMS Bus Name | E | custom column |
| Zone Name | **N** | Bus.zone (via generator bus) |
| Enforcement | E | custom column |
| Mw | **N** | Generator.p_set or Generator.p_nom |
| TOU | E | custom column |
| PMax | **N** | Generator.p_nom |

### Analytical vs Empirical Comparison

Of the 17 field-level cross-references between the analytical classifications (supplemental-csvs.md)
and the empirical classifications from the actual CSV data:

- **16 matches** — analytical and empirical classifications agree
- **1 mismatch** — TRADING_HUB.APNode: analytical = N (Bus index), empirical = X (no hub/settlement
  node model). The actual APNode field contains aggregate pricing node names (strings like
  "SP15_GEN_HUB_APND"), not integer bus numbers. The analytical spec assumed BUS_NUMBER (integer
  bus IDs), but the actual CSV uses APNode settlement node name strings which have no native
  PyPSA analog.

### Extension Mechanism Verification

PyPSA's extension mechanism (custom DataFrame column assignment) was verified empirically:
assigning `net.lines["custom_field"] = "test_value"` successfully stores and retrieves arbitrary
data on component DataFrames. This confirms all E-classified fields can be carried within
PyPSA's data model without external data structures.

## Implications

PyPSA's supplemental CSV representability profile shows clear domain boundaries:

1. **Physical network fields** (bus numbers, ratings, status) are well-covered as Native (N).
2. **Operational metadata** (device names, circuit IDs, substations) can be carried as Extension (E)
   via custom DataFrame columns — PyPSA's extension mechanism works reliably.
3. **Market-layer concepts** (trading hubs, contingency definitions, interface flowgates, outage
   schedules) are consistently External (X) — these concepts have no structural analog in PyPSA.

The 37.0% external rate reflects PyPSA's positioning as a power system planning/optimization tool
rather than a market operations platform. Contingency analysis (88.9% X) and outage management
(72.7% X) represent the largest gaps. Interface data (41.2% X) is 100% external for the
interface-specific fields (name, limits, direction coefficients) — consistent with the analytical
finding that PyPSA has no native interface/flowgate concept.

The schema divergence between actual ERCOT CSVs and the PSS/E-style analytical spec is significant:
the actual files have nearly twice as many fields (73 vs 44) with ERCOT-specific naming conventions,
additional metadata columns (EMS names, substations, enforcement flags), and structural differences
(merged INTERFACE + INTERFACE_ELEMENT, absent INTERFACE_ELEMENT.csv, additional RESOURCE.csv).

## Timing

- **Wall-clock:** 0.132 s
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/fnm_ingestion/test_g_fnm_5_supplemental_csv_representability.py`
