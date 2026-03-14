---
test_id: C-9
tool: gridcal
dimension: scalability
network: MEDIUM
status: pass
workaround_class: null
blocked_by: null
protocol_version: "v10"
skill_version: v1
test_hash: "efb6f322"
wall_clock_seconds: 6.670
timing_source: measured
peak_memory_mb: 7585.74
convergence_residual: null
convergence_iterations: null
loc: 207
solver: null
timestamp: "2026-03-13T22:40:00Z"
---

# C-9: PTDF matrix computation on MEDIUM

## Result: PASS

## Approach

Scaled B-9 (PTDF on TINY, 46x39 matrix, 0.081s) to MEDIUM (ACTIVSg 10000-bus, 12706
branches). Used the same `vge.linear_power_flow(grid)` API call. Verified PTDF matrix
dimensions, density, internal consistency, and documented phase-shifter correction effects.

## Output

### PTDF Matrix Properties

| Metric | TINY (B-9) | MEDIUM (C-9) | Ratio |
|--------|-----------|-------------|-------|
| Shape | 46 x 39 | 12,706 x 10,000 | -- |
| Elements | 1,794 | 127,060,000 | 70,825x |
| Nonzero entries | 75.7% | 73.82% | -- |
| Matrix memory | ~14 KB | 969.39 MB | -- |
| LODF memory | ~17 KB | 1,231.71 MB | -- |
| Compute time (s) | 0.081 | 6.67 | 82.3x |
| Peak memory (MB) | -- | 7,585.74 | -- |
| Max |PTDF| value | 1.0 | 2.34 | -- |

### Internal Consistency

| Check | Result |
|-------|--------|
| PTDF @ Pinj == la_results.Sf | **0.0** (exact match) |
| PTDF shape correct (branches x buses) | Yes (12706 x 10000) |
| DCPF converged | Yes |

The PTDF matrix is perfectly internally consistent: `PTDF @ Pinj` exactly equals the
`LinearAnalysisResults.Sf` array (difference = 0.0).

### Phase-Shifter Correction Terms

ACTIVSg10k contains 5 phase-shifting transformers. The simple `PTDF @ Pinj` flow
reconstruction differs from full B-matrix DCPF by up to 743 MW on phase-shifter-adjacent
branches. This is a known limitation of the PTDF formulation -- the full equation requires
Pbusinj and Pfinj correction terms for branches with nonzero shift angles.

| Phase-Shifter Branch | DCPF Flow (MW) | PTDF Flow (MW) | Diff (MW) |
|---------------------|---------------|----------------|-----------|
| 28737_28745_1 | 2,035.4 | 1,291.9 | 743.5 |
| 50203_50207_1 | 461.8 | -101.1 | 562.9 |
| 10784_10788_1 | 307.6 | 109.3 | 198.3 |
| 77254_77262_1 (x2) | 512.0 | 402.7 | 109.3 |

These deviations are not a tool bug -- they reflect the inherent difference between
PTDF-based linear analysis (single-slack reference, no phase-shift injection corrections)
and the full B-matrix DCPF which incorporates phase shifts directly. The PTDF matrix
itself is correct; the reconstruction formula `flow = PTDF @ Pinj` is incomplete for
networks with phase-shifting transformers.

### Scale Performance

| Metric | Value |
|--------|-------|
| PTDF compute time | 6.67 s |
| Total script time | 13.10 s |
| Peak memory | 7,585.74 MB |
| PTDF density | 73.82% |
| Time/element ratio | 5.25e-08 s/element |

The 82.3x time increase for a 70,825x element increase demonstrates sub-linear scaling --
the analytical PTDF computation (introduced in v4.0.0) handles the MEDIUM network
efficiently.

## Workarounds

None required. PTDF computation via `vge.linear_power_flow()` is a one-line API call that
returns full PTDF and LODF matrices as dense NumPy arrays. The API is identical at TINY
and MEDIUM scale.

## Timing

- **Wall-clock:** 6.67 s (PTDF computation only)
- **Timing source:** measured
- **Peak memory:** 7,585.74 MB (includes PTDF + LODF dense matrices)
- **Total script time:** 13.10 s (includes network loading + DCPF verification)

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c9_ptdf_scale_medium.py`
