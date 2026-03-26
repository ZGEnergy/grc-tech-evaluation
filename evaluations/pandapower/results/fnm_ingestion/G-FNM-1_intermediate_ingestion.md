---
test_id: G-FNM-1
tool: pandapower
dimension: fnm_ingestion
network: LARGE
protocol_version: "v11"
skill_version: "v2"
test_hash: "ad14fbd0"
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 3.149
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 115
solver: null
ingestion_path: matpower_fallback
timestamp: 2026-03-24T12:00:00Z
---

# G-FNM-1: Intermediate Format Ingestion (Two-Check Gate)

## Result: FAIL

pandapower 3.4.0 has no native PSS/E CSV parser. Sub-check (a) -- PSS/E format
compatibility -- fails because the tool cannot ingest the intermediate CSV tables
(bus.csv, branch.csv, transformer.csv, etc.) that represent PSS/E v31 record
types. Sub-check (b) -- post-ingestion fidelity checks -- is skipped because no
network model is produced from sub-check (a).

The tool's supported import paths are MATPOWER .m/.mat (via `from_mpc` /
`from_ppc`) and pandapower's own JSON/pickle serialization. Neither path can
consume PSS/E-derived CSV tables directly.

## Approach

1. Loaded `data/fnm/manifest.json` to confirm the expected intermediate format
   structure (17 CSV tables, one per PSS/E v31 record type).
2. Checked for the existence of intermediate CSV files in `data/fnm/intermediate/`.
   No CSV data files exist (only JSON Schema definitions).
3. Scanned pandapower's public API (`dir(pp)` and `dir(pp.converter)`) for any
   function name containing "psse", "pss_e", "raw", or "csv_import". The only
   match was `get_raw_data_from_pickle`, which loads pandapower's own pickle
   format -- not PSS/E RAW or CSV data.
4. Concluded that pandapower cannot ingest the intermediate CSV format.
   Sub-check (a) fails with `failure_reason: psse_parse_error`.
5. Sub-check (b) skipped because no network model was produced.

## Output

| Sub-Check | Description | Result |
|-----------|-------------|--------|
| (a) | PSS/E intermediate CSV ingestion | FAIL |
| (b) | Post-ingestion fidelity checks | SKIP (blocked by (a)) |

**pandapower version:** 3.4.0

**PSS/E-related APIs found:** `get_raw_data_from_pickle` (not a PSS/E parser)

**Intermediate CSV files found:** 0 of 17 expected tables (no CSV data files
present in `data/fnm/intermediate/`; only JSON Schema definitions exist)

**Ingestion path:** `matpower_fallback` -- G-FNM-3/4/5 proceed via MATPOWER
.mat import, which is a separate and functional ingestion path.

## Workarounds

- **What:** No workaround available for PSS/E CSV ingestion. pandapower's
  architecture does not include a PSS/E parser of any kind (RAW, CSV, or
  otherwise).
- **Why:** The tool was designed around MATPOWER-compatible data formats and
  its own JSON serialization. PSS/E format support was never implemented.
- **Durability:** blocking -- No API path (public or private) exists to achieve
  PSS/E CSV ingestion. Would require implementing a custom CSV-to-pandapower
  converter or adding PSS/E parsing to the tool's source code.
- **Grade impact:** G-FNM-1 fails. G-FNM-2 is blocked. G-FNM-3/4/5 proceed
  via MATPOWER fallback path, which is a separate evaluation track.

## Timing

- **Wall-clock:** 3.149 s (manifest load + API scan)
- **Timing source:** measured (time.perf_counter)
- **Peak memory:** not measured (no network loaded)
- **Solver iterations:** N/A
- **Convergence residual:** N/A
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/fnm_ingestion/test_g_fnm_1_intermediate_ingestion.py`
