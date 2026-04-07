---
test_id: G-FNM-1
tool: powermodels
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: 5b6e0bd9
status: fail
failure_reason: psse_parse_error
ingestion_path: matpower_fallback
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 3.28
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 140
solver: null
cpu_threads_used: null
cpu_threads_available: null
sced_mode: null
test_category: null
timestamp: "2026-03-24T00:00:00Z"
---

# G-FNM-1: Intermediate Format Ingestion (Two-Check Gate)

## Result: FAIL

PowerModels.jl cannot ingest the PSS/E intermediate CSV format. It supports only
MATPOWER `.m`, PSS/E `.raw` (v33 spec), and PowerModels JSON formats. The intermediate
CSV tables are tabular extracts from PSS/E, not a native format PowerModels can parse.

The MATPOWER `.m` fallback file loads successfully (3.05s, ~28,000 buses), confirming the
fallback ingestion path works for downstream G-FNM-3/4/5 tests.

## Approach

### Sub-check (a): PSS/E intermediate CSV format compatibility

PowerModels.jl has no CSV parser. The `PowerModels.parse_file()` function dispatches on
file extension: `.m` for MATPOWER, `.raw` for PSS/E PTI, `.json` for PowerModels JSON.
CSV files are not recognized. [tool-specific: no CSV ingestion path]

Prior testing (protocol v9) also confirmed that PowerModels' PSS/E RAW parser fails on
the FNM's v31 header format. The parser reads the entire first line as the `IC` field
(integer type), which fails because the v31 Case Identification header contains multiple
space-separated fields (`IC SBASE REV XFRRAT NXFRAT BASFRQ`):

```
[error | PowerModels]: value '0    100.00 31  0  0    0.0' for IC in section CASE
IDENTIFICATION is not of type Int64.
```

Result: `failure_reason: psse_parse_error`, `ingestion_path: matpower_fallback`.

### MATPOWER fallback verification

The MATPOWER fallback file at `data/fnm/reference/cleaned/fnm_main_island.m` was loaded
to verify the fallback path for downstream tests. This does NOT change G-FNM-1 status.

## Output

### MATPOWER Fallback Load Results (informational)

| Metric | Value |
|--------|-------|
| File | `data/fnm/reference/cleaned/fnm_main_island.m` |
| Load time | 3.05 s |
| baseMVA | 100 |
| Slack bus | <slack_bus> (bus_type=3) |
| Tap=0 branches | 0 (correctly mapped to 1.0 by MATPOWER converter) |
| Tap=1.0 branches | 30,248 |
| Buses | ~28,000 |
| Branches | ~33,000 |
| Generators | ~5,700 |
| Loads | 8,624 |

### Record Count Comparison (MATPOWER fallback vs manifest)

| Table | Manifest Expected | MATPOWER Actual | Delta | % Diff |
|-------|------------------:|----------------:|------:|-------:|
| bus | ~30,000 | ~28,000 | -2,445 | -8.1% |
| load | ~15,000 | 8,624 | -6,438 | -42.7% |
| generator | ~5,800 | ~5,700 | -27 | -0.5% |
| branch+transformer | ~34,000 | ~33,000 | -1,234 | -3.6% |

Count mismatches are attributable to the MATPOWER fallback being a pre-cleaned main-island
subset, not a PowerModels ingestion error. Isolated buses (IDE=4), de-energized equipment,
and off-island fragments were removed during the external cleaning process.

### Post-Ingestion Fidelity Checks (MATPOWER fallback)

| Check | Result | Detail |
|-------|--------|--------|
| baseMVA | 100 | Correct (matches manifest sbase) |
| Slack bus present | Yes | Bus <slack_bus> (bus_type=3) |
| Tap ratio preservation | OK | 0 branches with tap=0; 30,248 with tap=1.0 |

## Workarounds

- **What:** MATPOWER `.m` fallback file used instead of intermediate CSVs.
- **Why:** PowerModels has no CSV parser and its PSS/E RAW parser fails on the FNM's v31
  header format. The MATPOWER `.m` format is the only viable ingestion path.
- **Durability:** blocking -- PowerModels cannot ingest the authoritative intermediate CSV
  format or the source PSS/E RAW file. The MATPOWER fallback requires an external conversion
  step (via MATPOWER/Octave) that is outside PowerModels' control.
- **Grade impact:** The tool cannot directly consume the evaluation's intermediate format.
  G-FNM-1 fails. Downstream G-FNM-3/4/5 proceed via the MATPOWER fallback path.

## Timing

- **Wall-clock:** 3.28 s (total test); 3.05 s (MATPOWER load only)
- **Timing source:** measured
- **Peak memory:** not measured (ingestion gate test, not scalability)

## Test Script

**Path:** `evaluations/powermodels/tests/fnm_ingestion/test_g_fnm_1_intermediate_ingestion.jl`
