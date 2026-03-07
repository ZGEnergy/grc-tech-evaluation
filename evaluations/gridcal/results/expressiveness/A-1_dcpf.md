---
test_id: A-1
tool: gridcal
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.358
peak_memory_mb: null
loc: 30
solver: "Direct (SolverType.Linear)"
timestamp: 2026-03-06T03:00:00Z
---

# A-1: DC Power Flow (Grade: MEDIUM)

## Result: PASS

## Network

ACTIVSg10k -- 10,000 buses, 12,706 branches, 2,485 generators.

## Approach

Same as TINY: `PowerFlowOptions(solver_type=SolverType.Linear)` with `vge.power_flow()`.

## Output

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Voltage angles range | -21.63 to 104.88 deg |
| Branch flow range (MW) | -1839.6 to 2035.4 |
| Bus injection range (MW) | -14695.5 to 15139.3 |
| Q flows zero | Yes |
| Losses zero | Yes |
| Bus DataFrame shape | 10000 x 4 |
| Branch DataFrame shape | 12706 x 7 |

## Scaling from TINY

| Metric | TINY (39 bus) | MEDIUM (10k bus) | Ratio |
|--------|--------------|-----------------|-------|
| Buses | 39 | 10,000 | 256x |
| Solve time (s) | 0.126 | 0.358 | 2.8x |
| Load time (s) | ~0.1 | 7.29 | ~73x |

DCPF solve time scales sub-linearly (2.8x for 256x more buses). File loading dominates at 7.3s due to MATPOWER parser overhead on the large .m file.

## Workarounds

None required.

## Timing

- **Wall-clock (solve only):** 0.358s
- **File load time:** 7.29s
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a1_dcpf_medium.py`
