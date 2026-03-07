---
test_id: A-1
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.126
peak_memory_mb: null
loc: 30
solver: "Direct (SolverType.Linear)"
timestamp: 2026-03-06T01:00:00Z
---

# A-1: DC Power Flow

## Result: PASS

## Approach

Loaded IEEE 39-bus via `vge.open_file()`. Configured DCPF with `PowerFlowOptions(solver_type=SolverType.Linear)`. Ran via `vge.power_flow(grid, options=opts)`.

Note: GridCal names the DC power flow solver `SolverType.Linear` — the term "DC" does not appear in the enum.

## Output

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Voltage angles range | -13.46° to 7.40° |
| Vm all unity | No (minor numerical variation) |
| Branch flow range (MW) | -830.0 to 448.5 |
| Bus injection range (MW) | -667.6 to 867.3 |
| Q flows zero | Yes |
| Losses zero | Yes |

DataFrame access via `results.get_bus_df()` (39×4: Vm, Va, P, Q) and `results.get_branch_df()` (46×7: Pf, Qf, Pt, Qt, loading, Ploss, Qloss).

## Workarounds

None required.

## Timing

- **Wall-clock:** 0.126s
- **Peak memory:** not measured
- **Solver iterations:** N/A (direct solve)

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a1_dcpf.py`
