---
test_id: B-9
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v11"
skill_version: v2
test_hash: "d8e7210b"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.25
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 169
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# B-9: PTDF matrix extraction and verification against DCPF flows

## Result: PASS

## Approach

1. Load IEEE 39-bus network via `load_gridcal()`
2. Compute PTDF matrix using `vge.linear_power_flow(grid)` — the native `LinearAnalysis` driver
3. Run DCPF via `vge.power_flow(grid, options=PowerFlowOptions(solver_type=SolverType.Linear))`
4. Predict flows as `PTDF @ Pinj` using the bus injection vector from the linear analysis results
5. Compare predicted flows against DCPF flows; check for phase-shifting transformers

The `linear_power_flow()` convenience function wraps the `LinearAnalysisDriver` and returns a `LinearAnalysisResults` object with `.PTDF` and `.LODF` attributes as dense NumPy arrays. No workarounds are needed — PTDF extraction is a first-class API feature.

## Output

| Metric | Value |
|--------|-------|
| PTDF shape | (46, 39) — branches x buses |
| LODF shape | (46, 46) — branches x branches |
| PTDF compute time | 0.081 s |
| PTDF max absolute value | 1.0 |
| PTDF nonzero entries | 75.7% |
| Phase-shifting transformers | 0 |
| Max |PTDF@Pinj - DCPF flow| | **1.36e-12** |
| Mean |PTDF@Pinj - DCPF flow| | 3.60e-13 |

**Branch flow comparison (first 10 branches):**

| Branch | DCPF Flow (MW) | PTDF Flow (MW) | Abs Diff |
|--------|---------------|----------------|----------|
| 1_2_1 | -178.354 | -178.354 | 0.0 |
| 1_39_1 | 80.754 | 80.754 | 0.0 |
| 2_3_1 | 333.430 | 333.430 | 0.0 |
| 2_25_1 | -261.784 | -261.784 | 0.0 |
| 3_4_1 | 54.115 | 54.115 | 0.0 |
| 3_18_1 | -42.685 | -42.685 | 0.0 |
| 4_5_1 | -177.686 | -177.686 | 0.0 |
| 4_14_1 | -268.199 | -268.199 | 0.0 |
| 5_6_1 | -514.754 | -514.754 | 0.0 |
| 5_8_1 | 337.068 | 337.068 | 0.0 |

The PTDF-predicted flows match DCPF flows to within 1.36e-12 (machine precision), well within the 1e-6 tolerance. No phase-shifting transformers are present in case39, so no Pbusinj/Pfinj corrections are needed.

**Internal consistency:** The `LinearAnalysisResults.Sf` array also matches both the PTDF-predicted flows and the DCPF flows, confirming that the PTDF matrix, the linear analysis solver, and the DC power flow solver all produce identical results.

## Workarounds

None required. PTDF extraction via `vge.linear_power_flow()` is a documented, one-line API call that returns the full PTDF and LODF matrices as NumPy arrays.

## Timing

- **Wall-clock:** 1.25 seconds (including network loading)
- **PTDF computation:** 0.078 seconds
- **Timing source:** measured
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b9_ptdf_extraction.py`
