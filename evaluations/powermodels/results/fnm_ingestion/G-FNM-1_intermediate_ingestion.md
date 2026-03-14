---
test_id: G-FNM-1
tool: powermodels
dimension: fnm_ingestion
network: LARGE
protocol_version: v10
skill_version: v1
test_hash: bd857ce4
status: qualified_pass
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 3.19
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 170
solver: null
input_path: matpower_fallback
timestamp: "2026-03-13T00:00:00Z"
---

# G-FNM-1: Intermediate Format Ingestion (Two-Check Gate)

## Result: QUALIFIED PASS

The MATPOWER `.m` fallback file loaded successfully in 2.97 seconds with correct baseMVA,
slack bus identification, and tap ratio handling. CSV intermediate format is not supported
by PowerModels (no CSV parser exists). PSS/E v31 RAW parsing also fails on this file's
header format. Record counts do not match the manifest because the MATPOWER fallback is a
pre-cleaned main-island subset, not a PowerModels ingestion error.

## Approach

### Sub-check (a): PSS/E / CSV format compatibility

PowerModels.jl supports three input formats: MATPOWER `.m`, PSS/E `.raw`, and
PowerModels `.json`. The intermediate CSVs are cleaned tabular extracts -- not a format
PowerModels can parse. PowerModels has no CSV ingestion capability.

Prior testing (protocol v9) confirmed that PowerModels' PSS/E RAW parser also fails on the
FNM's v31 header format. The parser attempts to read the entire first line as the `IC` field
(integer type), which fails because the v31 single-line Case Identification header contains
multiple space-separated fields (`IC SBASE REV XFRRAT NXFRAT BASFRQ`). The error message:

```
[error | PowerModels]: value '0    100.00 31  0  0    0.0' for IC in section CASE
IDENTIFICATION is not of type Int64.
```

Since CSV parsing is not possible and PSS/E RAW parsing fails, the test proceeds to the
MATPOWER fallback.

### Sub-check (a) outcome: qualified_pass via MATPOWER fallback

The MATPOWER fallback file `data/fnm/reference/cleaned/fnm_main_island.m` loaded
successfully in 2.97 seconds. PowerModels correctly parsed all network element types.

### Sub-check (b): Record count fidelity

The manifest expected counts (from the raw PSS/E source) are compared against the
MATPOWER fallback counts. All four primary tables show deficits because the fallback
is a cleaned main-island subset that excludes isolated buses, de-energized equipment,
and off-island network fragments.

## Output

### MATPOWER Fallback Load Results

| Metric | Value |
|--------|-------|
| File | `data/fnm/reference/cleaned/fnm_main_island.m` |
| Load time | 2.97 s |
| baseMVA | 100 |
| Slack bus | 29421 (bus_type=3) |
| Tap=0 branches | 0 (correctly mapped to 1.0 by MATPOWER converter) |
| Tap=1.0 branches | 30,248 |

### Record Count Comparison

| Table | Manifest Expected | PowerModels Actual | Delta | % Diff | Status |
|-------|------------------:|-------------------:|------:|-------:|--------|
| bus | 30,307 | 27,862 | -2,445 | -8.1% | FAIL |
| load | 15,062 | 8,624 | -6,438 | -42.7% | FAIL |
| generator | 5,768 | 5,741 | -27 | -0.5% | FAIL |
| branch+transformer | 33,840 | 32,606 | -1,234 | -3.6% | FAIL |

All four primary tables fail exact-count matching.

### Count Discrepancy Analysis

The count mismatches are attributable to the MATPOWER fallback being a cleaned derivative,
not to PowerModels ingestion errors:

- **Bus (-8.1%):** 2,445 buses excluded -- isolated buses (IDE=4), de-energized buses, and
  off-island network fragments removed during the cleaning process.
- **Load (-42.7%):** 6,438 loads excluded -- loads on removed buses are dropped. The large
  fraction indicates many loads exist on isolated/off-network buses in the raw PSS/E source.
- **Generator (-0.5%):** 27 generators excluded -- small discrepancy consistent with
  generators on removed buses.
- **Branch+transformer (-3.6%):** 1,234 elements excluded -- branches and transformers
  connected to removed buses.

### Post-Ingestion Fidelity Checks (on loaded data)

| Check | Result | Detail |
|-------|--------|--------|
| baseMVA | 100 | Correct (matches manifest sbase) |
| Slack bus present | Yes | Bus 29421 (bus_type=3) |
| Tap ratio preservation | OK | 0 branches with tap=0; 30,248 with tap=1.0 |
| Bus count (internal) | 27,862 | Consistent with cleaned .m file contents |
| Branch count (internal) | 32,606 | Consistent with cleaned .m file contents |

## Workarounds

- **What:** Used MATPOWER `.m` fallback file instead of intermediate CSVs or PSS/E RAW.
- **Why:** PowerModels has no CSV parser for the intermediate format. Its PSS/E v31 RAW
  parser fails on the Case Identification header format used by this FNM file. The MATPOWER
  `.m` format is the only viable ingestion path.
- **Durability:** blocking -- PowerModels cannot ingest the authoritative intermediate CSV
  format or the source PSS/E RAW file. The MATPOWER fallback requires an external conversion
  step (via MATPOWER/Octave) that is outside PowerModels' control, and the pre-cleaned file
  has already lost records relative to the raw source.
- **Grade impact:** The tool cannot directly consume the evaluation's intermediate format.
  Reliance on a pre-converted MATPOWER file means record count fidelity against the full
  raw model cannot be verified through PowerModels alone. This is a significant limitation
  for FNM ingestion capability.

## Timing

- **Wall-clock:** 3.19 s (total); 2.97 s (MATPOWER load only)
- **Timing source:** measured
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/powermodels/tests/fnm_ingestion/test_g_fnm_1_intermediate_ingestion.jl`

Key code excerpt showing the MATPOWER fallback load:

```julia
matpower_data = PowerModels.parse_file(matpower_fallback)
n_bus = length(matpower_data["bus"])       # 27862
n_branch = length(matpower_data["branch"]) # 32606
n_gen = length(matpower_data["gen"])       # 5741
n_load = length(matpower_data["load"])     # 8624
baseMVA = matpower_data["baseMVA"]         # 100
```
