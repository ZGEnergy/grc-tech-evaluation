---
test_id: A-1
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: v2
test_hash: "05bc255c"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.37
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 137
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# A-1: Solve DC power flow on TINY

## Result: PASS

## Approach

Loaded the IEEE 39-bus network via the shared `load_gridcal()` loader (calls `vge.open_file()`).
Configured DC power flow using `PowerFlowOptions(solver_type=SolverType.Linear)` and executed
via `vge.power_flow(grid, options=opts)`.

Results are accessed through typed result attributes:
- `results.voltage` -- complex bus voltages (magnitudes are 1.0 pu for DCPF; angles carry the DC solution)
- `results.Sf` -- complex branch power flows from the sending end (MW + jMVAr)
- `results.get_bus_df()` -- pandas DataFrame with columns `[Vm, Va, P, Q]`
- `results.get_branch_df()` -- pandas DataFrame with columns `[Pf, Qf, Pt, Qt, loading, Ploss, Qloss]`

The API is clean: 3 lines to load, configure, and solve. Result extraction is straightforward
via named attributes and built-in DataFrame export.

## Output

| Metric | Value |
|--------|-------|
| Buses | 39 |
| Branches | 46 |
| Generators | 10 |
| Converged | True |
| Max angle (deg) | 13.46 |
| Max flow (MW) | 830.0 |

Sample bus voltage angles (degrees):

| Bus | Angle |
|-----|-------|
| 1 | -12.30 |
| 31 (slack) | 0.00 |
| 39 | -13.46 |

Sample branch flows (MW):

| Branch | Flow |
|--------|------|
| 29_38_1 | -830.0 |
| 6_31_1 | -625.0 |
| 10_32_1 | -650.0 |

DataFrame export produces well-structured pandas DataFrames with 39 rows (buses)
and 46 rows (branches), with intuitive column names.

## Workarounds

None required.

## Timing

- **Wall-clock:** 1.37 s
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** N/A (direct linear solve)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a1_dcpf.py`
