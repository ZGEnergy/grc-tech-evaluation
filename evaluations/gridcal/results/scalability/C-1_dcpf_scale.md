---
test_id: C-1
tool: gridcal
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.84
peak_memory_mb: 82.55
loc: 30
solver: "Direct (SolverType.Linear)"
timestamp: 2026-03-06T04:00:00Z
---

# C-1: DCPF Scale (Grade: MEDIUM)

## Result: PASS

## Network

ACTIVSg10k -- 10,000 buses, 12,706 branches, 2,485 generators.

## Approach

Same as TINY/expressiveness: `PowerFlowOptions(solver_type=SolverType.Linear)` with `vge.power_flow()`.

## Output

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Solve time | 1.84s |
| Peak memory (solve) | 82.55 MB |
| File load time | 10.81s |
| Voltage angles range | -21.63 to 104.88 deg |
| Branch flow range (MW) | -1839.58 to 2035.36 |

## Scaling

DCPF on 10k buses solves in under 2 seconds. File parsing dominates total execution time at ~11s. The solve itself scales sub-linearly with network size.

## Workarounds

None required.

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c1_dcpf_scale.py`
