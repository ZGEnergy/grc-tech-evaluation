---
test_id: B-9
tool: powermodels
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 274.4
peak_memory_mb: 2451.8
loc: 187
solver: null
timestamp: "2026-03-07T00:00:00Z"
---

# B-9: PTDF Matrix Extraction (MEDIUM, ACTIVSg 10k-bus)

## Result: PASS

## Approach

Same native API as TINY:

```julia

basic_data = PowerModels.make_basic_network(deepcopy(data))
ptdf = PowerModels.calc_basic_ptdf_matrix(basic_data)

```

Validated by comparing PTDF-predicted flows (`flow = PTDF * P_inj`) against actual
DCPF flows.

## Output

- **PTDF dimensions:** 12,706 x 10,000 (branches x buses) -- correct
- **PTDF rank:** 9,999 (= N_bus - 1, as expected)
- **PTDF matrix memory:** 1,016.5 MB (12,706 x 10,000 Float64)
- **Process memory after PTDF:** 2,451.8 MB
- **Max flow prediction error:** 2.18e-11 (tolerance: 1e-6) -- PASS
- **Mean flow prediction error:** 9.93e-14
- **PTDF compute time:** 3.73s
- **make_basic_network time:** 2.92s
- **Total time (including rank):** 274.4s

## Timing Breakdown

| Step | Time |
|------|------|
| `make_basic_network()` | 2.92s |
| `calc_basic_ptdf_matrix()` | 3.73s |
| DCPF validation solve | ~2s |
| `rank()` (SVD of 12706x10000) | ~265s |
| **Total** | **274.4s** |

The `rank()` call dominates total time due to the full SVD decomposition of the
12,706 x 10,000 matrix. The actual PTDF computation is fast (3.73s) and the
validation confirms sub-picowatt prediction accuracy.

## Scaling Analysis

| Metric | TINY (39-bus) | MEDIUM (10k-bus) | Ratio |
|--------|--------------|------------------|-------|
| PTDF dimensions | 46 x 39 | 12,706 x 10,000 | 276x x 256x |
| PTDF compute time | <0.01s | 3.73s | ~370x |
| Matrix memory | ~14 KB | 1,016 MB | ~73,000x |
| Max prediction error | 1.33e-14 | 2.18e-11 | ~1,600x |

The prediction error increase is expected for larger matrices due to floating-point
accumulation, but remains 5 orders of magnitude below the 1e-6 tolerance.

## Workarounds

None. PTDF extraction is a native API feature via `calc_basic_ptdf_matrix()`. The
API scales transparently to 10k-bus networks.

## Test Script

Path: `evaluations/powermodels/tests/test_medium_batch2.jl`
