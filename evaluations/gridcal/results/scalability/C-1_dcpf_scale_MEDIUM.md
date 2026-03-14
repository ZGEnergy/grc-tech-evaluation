---
test_id: C-1
tool: gridcal
dimension: scalability
network: MEDIUM
status: pass
workaround_class: null
blocked_by: null
protocol_version: "v10"
skill_version: v1
test_hash: "9aaf33f3"
wall_clock_seconds: 1.049
timing_source: measured
peak_memory_mb: 82.55
convergence_residual: null
convergence_iterations: null
loc: 130
solver: Linear (direct)
timestamp: 2026-03-13T00:00:00Z
---

# C-1: DCPF on MEDIUM — wall-clock time and peak memory

## Result: PASS

## Approach

DC power flow on the ACTIVSg 10000-bus network using GridCal's native linear solver (`SolverType.Linear`). No external optimizer required — DCPF is a direct linear system solve. Network loaded via `load_gridcal()` from the shared MATPOWER loader.

## Output

| Metric | Value |
|--------|-------|
| Bus count | 10,000 |
| Branch count | 12,706 |
| Generator count | 2,485 |
| Load count | 4,170 |
| Converged | Yes |
| Solve time | 1.049 s |
| Peak memory | 82.55 MB |
| Max angle | 104.88 deg |
| Mean angle | 25.74 deg |
| Max flow | 2,035.4 MW |
| Mean flow | 89.1 MW |
| Total losses | 0.0 MW (DC approximation) |

All buses have nonzero voltage angles and all branches carry nonzero flows, confirming a nontrivial solution.

## Workarounds

None required.

## Timing

- **Wall-clock:** 1.049 s (solve only, excludes network loading)
- **Timing source:** measured
- **Peak memory:** 82.55 MB (tracemalloc)
- **Total script time:** 7.16 s (includes network loading from MATPOWER .m file)

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c1_dcpf_scale_medium.py`
