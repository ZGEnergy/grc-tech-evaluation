---
test_id: A-2
tool: gridcal
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.701
peak_memory_mb: null
loc: 35
solver: "GridCal built-in Newton-Raphson"
timestamp: 2026-03-06T03:00:00Z
---

# A-2: AC Power Flow (Grade: MEDIUM)

## Result: PASS

## Network

ACTIVSg10k -- 10,000 buses, 12,706 branches, 2,485 generators.

## Approach

Same as TINY: Newton-Raphson with flat start. Converged on first attempt (no DC warm start needed).

## Output

| Metric | Value |
|--------|-------|
| Converged | Yes (flat start) |
| Convergence error | 2.73e-07 |
| Vm range (pu) | 0.957 -- 1.089 |
| Va range (deg) | -41.01 -- 66.73 |
| P flow range (MW) | -1720.7 to 2774.9 |
| Q flow range (Mvar) | -1765.1 to 3530.1 |
| Total P losses (MW) | 2585.7 |
| Total Q losses (Mvar) | -65981.9 |
| Bus DataFrame shape | 10000 x 4 |
| Branch DataFrame shape | 12706 x 7 |

## Scaling from TINY

| Metric | TINY (39 bus) | MEDIUM (10k bus) | Ratio |
|--------|--------------|-----------------|-------|
| Buses | 39 | 10,000 | 256x |
| Solve time (s) | ~0.05 | 1.701 | ~34x |
| Convergence | Flat start | Flat start | Same |

NR converges on flat start for both TINY and MEDIUM. Solve time scales roughly O(n) with bus count.

## Workarounds

None required (flat start sufficient on MEDIUM).

## Timing

- **Wall-clock (solve only):** 1.701s
- **File load time:** 7.48s
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a2_acpf_medium.py`
