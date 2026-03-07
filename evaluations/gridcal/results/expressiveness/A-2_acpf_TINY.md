---
test_id: A-2
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.414
peak_memory_mb: null
loc: 45
solver: "GridCal Newton-Raphson (built-in, not Ipopt)"
timestamp: 2026-03-06T01:00:00Z
---

# A-2: AC Power Flow (Newton-Raphson)

## Result: PASS

## Approach

Loaded IEEE 39-bus. Configured ACPF with `PowerFlowOptions(solver_type=SolverType.NR, max_iter=100, tolerance=1e-6, retry_with_other_methods=False)`.

GridCal uses its own Newton-Raphson implementation for power flow — not Ipopt. Ipopt is not involved in the PF path.

Flat start converged on first attempt (no DC warm start needed).

## Output

| Metric | Value |
|--------|-------|
| Converged | Yes (flat start) |
| Convergence error | 3.32e-11 |
| Vm range (pu) | 0.982 to 1.064 |
| Va range (deg) | -14.54° to 4.47° |
| Pf range (MW) | -824.8 to 453.8 |
| Qf range (MVAr) | -156.7 to 113.1 |
| Total P losses (MW) | 43.64 |
| Total Q losses (MVAr) | -112.16 |

DataFrame access via `results.get_bus_df()` (39×4) and `results.get_branch_df()` (46×7).

## Workarounds

None required.

## Timing

- **Wall-clock:** 1.414s (includes compilation overhead on first run)
- **Peak memory:** not measured
- **Solver iterations:** not directly exposed in results

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a2_acpf.py`
