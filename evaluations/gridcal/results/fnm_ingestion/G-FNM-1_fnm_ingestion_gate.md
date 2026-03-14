---
test_id: G-FNM-1
tool: gridcal
dimension: fnm_ingestion
network: LARGE
status: fail
workaround_class: null
blocked_by: null
wall_clock_seconds: 15.32
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 155
solver: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: "v10"
skill_version: v1
test_hash: "7827a912"
input_path: csv
failure_reason: psse_parse_error
---

# G-FNM-1: Intermediate format ingestion gate

## Result: FAIL

GridCal/VeraGrid cannot ingest the intermediate CSV tables. The tool has no native
CSV import for network topology data. Sub-check (a) fails; sub-check (b) is not
applicable.

## Approach

### Sub-check (a): PSS/E CSV format compatibility

Examined GridCal/VeraGrid v5.6.28's file I/O capabilities to determine whether
it can parse the 17 intermediate CSV tables (bus.csv, branch.csv, transformer.csv,
etc.) that contain PSS/e v31 record data in CSV form.

GridCal supports reading network data from: PSS/e `.raw`/`.rawx`, MATPOWER `.m`,
CGMES/CIM XML, DGS, EPC (PowerWorld), PyPSA, pandapower, UCTE, IIDM, DPX, IPA,
and its native `.veragrid` format. The `.csv` handler in GridCal is limited to
time-series profile data, not network topology.

Additionally, GridCal's PSS/e RAW parser was tested against the source RAW file
(`AUC_AN_2026_2026_S01_ON_NETWORK_MODEL.RAW`, v31 format). The parser failed with:
`Exception: PSSe 35 load data came with 1 elements and 18 or 17 were expected :/`

This indicates GridCal's PSS/e parser expects v35 format and cannot parse v31 RAW
files either, representing a secondary compatibility gap.

### Sub-check (b): Record count fidelity

Not applicable -- skipped because sub-check (a) failed.

### Supplemental: MATPOWER fallback

GridCal successfully loaded the cleaned MATPOWER `.m` file
(`data/fnm/reference/cleaned/fnm_main_island.m`), which contains the main-island
subset of the FNM (type-4 isolated buses removed). This confirms the MATPOWER
fallback path is available for G-FNM-3/4/5.

## Output

### Sub-check (a): PSS/E CSV compatibility

| Check | Result |
|-------|--------|
| CSV network import supported | No |
| PSS/e RAW v31 parsing | Failed (expects v35 format) |
| MATPOWER `.m` parsing | Success |
| Intermediate CSVs found | 0 of 17 |

### Supplemental: MATPOWER fallback element counts

| Component | MATPOWER Ingested | RAW Reference | Notes |
|-----------|------------------|---------------|-------|
| Buses | 27,862 | 30,307 | Excludes 2,370 type-4 isolated + 75 other |
| Generators | 5,741 | 5,768 | 27 fewer (on excluded buses) |
| Lines (branches) | 23,125 | 24,117 | 992 fewer (connected to excluded buses) |
| Transformers | 9,481 | 9,723 | 242 fewer (connected to excluded buses) |
| Loads | 8,624 | 15,062 | MATPOWER aggregates multiple loads per bus |
| Shunts | 3,110 | 3,114 | 4 fewer (on excluded buses) |
| Areas | 0 | 49 | MATPOWER `.m` format lost area data |
| Zones | 0 | 90 | MATPOWER `.m` format lost zone data |
| baseMVA | 100.0 | 100.0 | Match |

The MATPOWER fallback loads the main-island subset (type-4 buses filtered). Count
differences are expected due to the main-island filtering applied during MATPOWER
case preparation.

## Workarounds

None applied. The test records a failure because GridCal cannot parse the
intermediate CSV format. The MATPOWER fallback path is available for downstream
G-FNM-3/4/5 tests but does not change the G-FNM-1 result.

## Timing

- **Wall-clock:** 15.32 seconds (includes MATPOWER `.m` load for supplemental data)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/gridcal/tests/fnm_ingestion/test_g_fnm_1_fnm_ingestion_gate.py`

Key finding: GridCal's `open_file()` API accepts `.raw`, `.rawx`, `.m`, and other
format-specific file extensions. There is no CSV-to-network import path. The PSS/e
RAW parser is hardcoded to expect v35 format and cannot parse v31 files.
