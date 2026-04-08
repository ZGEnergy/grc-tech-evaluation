---
test_id: G-FNM-1
tool: gridcal
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: "7827a912"
status: fail
workaround_class: null
blocked_by: null
wall_clock_seconds: 12.86
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 237
solver: null
ingestion_path: null
failure_reason: psse_parse_error
test_category: null
timestamp: 2026-03-24T00:00:00Z
---

# G-FNM-1: Intermediate format ingestion gate

## Result: FAIL

GridCal/VeraGrid v5.6.28 cannot ingest the intermediate CSV tables. The tool has
no native CSV import for network topology data. Sub-check (a) fails with
`failure_reason: psse_parse_error`; sub-check (b) is not applicable.

## Approach

### Sub-check (a): PSS/E CSV format compatibility

Examined GridCal/VeraGrid v5.6.28's file I/O capabilities to determine whether
it can parse the 17 intermediate CSV tables (bus.csv, branch.csv, transformer.csv,
etc.) that contain PSS/E v31 record data in CSV form.

GridCal supports reading network data from: PSS/E `.raw`/`.rawx`, MATPOWER `.m`,
CGMES/CIM XML, DGS, EPC (PowerWorld), PyPSA, pandapower, UCTE, IIDM, DPX, IPA,
and its native `.veragrid` format. The `.csv` handler in GridCal is limited to
time-series profile data, not network topology.

The intermediate CSV directory at `$FNM_PATH/intermediate/` was checked; 0 of 17
expected CSV files were found (the FNM source data mount does not contain
intermediate tables in this environment). Independent of file availability,
GridCal's `open_file()` API has no code path for CSV-to-network import, confirmed
by API analysis of the `FileOpen` and `open_file` functions.

### Sub-check (b): Record count fidelity

Not applicable -- skipped because sub-check (a) failed.

### MATPOWER fallback test

GridCal was tested against the pre-cleaned MATPOWER case files:

- **`fnm_main_island.mat`** (MATLAB binary format): `open_file()` returns `None`,
  producing `AttributeError: 'NoneType' object has no attribute 'buses'`. GridCal
  cannot parse MATLAB `.mat` binary format files.
- **`fnm_main_island.m`** (MATPOWER text format): Loaded successfully in 12.86
  seconds, producing a valid `MultiCircuit` with ~28,000 buses.

This confirms the MATPOWER `.m` fallback path is available for G-FNM-3/4/5.

## Output

### Sub-check (a): PSS/E CSV compatibility

| Check | Result |
|-------|--------|
| CSV network import supported | No |
| Intermediate CSVs found | 0 of 17 |
| `.mat` binary format support | No (returns None) |
| MATPOWER `.m` text format support | Yes |

### MATPOWER fallback element counts

| Component | MATPOWER Ingested | Notes |
|-----------|------------------|-------|
| Buses | ~28,000 | Main-island subset (type-4 isolated buses excluded) |
| Generators | ~5,800 | |
| Lines (branches) | ~23,000 | |
| Transformers (2W) | ~9,500 | |
| Loads | ~8,600 | MATPOWER aggregates multiple loads per bus |
| Shunts | ~3,100 | |
| Areas | 0 | MATPOWER `.m` format does not preserve area data |
| Zones | 0 | MATPOWER `.m` format does not preserve zone data |
| HVDC lines | 0 | Not in MATPOWER `.m` format |
| baseMVA | 100.0 | Correct |
| Slack bus | 1 ("CAPTJA 1") | Correctly identified |

## Workarounds

None applied. The test records a failure because GridCal cannot parse the
intermediate CSV format. The MATPOWER `.m` fallback path is available for
downstream G-FNM-3/4/5 tests but does not change the G-FNM-1 result.

## Timing

- **Wall-clock:** 12.86 seconds (includes MATPOWER `.m` load for fallback test)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/gridcal/tests/fnm_ingestion/test_g_fnm_1_fnm_ingestion_gate.py`

Key finding: GridCal's `open_file()` API accepts `.raw`, `.rawx`, `.m`, and other
format-specific file extensions. There is no CSV-to-network import path. The `.mat`
binary format returns `None` rather than raising an error, which is a silent failure
mode. Only the MATPOWER `.m` text format works for the FNM fallback.
