---
test_id: C-6
tool: powermodels
dimension: scalability
network: SMALL
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 281.58
peak_memory_mb: null
loc: 220
solver: HiGHS
timestamp: "2026-03-07T00:00:00Z"
---

# C-6: Stochastic Scale (SMALL, ACTIVSg 2000-bus)

## Result: PASS

## Problem Scale

- **Network:** ACTIVSg 2000-bus (544 generators, 3,206 branches)
- **Scenarios:** 20
- **Periods per scenario:** 12 (hourly)
- **Variables per scenario:** ~13,000 (gen dispatch + bus angles x 12 periods)
- **Total solves:** 20

## Per-Scenario Timing

| Scenario | Time (s) | Status |
|----------|----------|--------|
| 1 | 12.44 | OPTIMAL |
| 2 | 12.46 | OPTIMAL |
| 3 | 12.72 | OPTIMAL |
| 4 | 12.75 | OPTIMAL |
| 5 | 12.39 | OPTIMAL |
| 6 | 12.66 | OPTIMAL |
| 7 | 12.51 | OPTIMAL |
| 8 | 12.78 | OPTIMAL |
| 9 | 12.83 | OPTIMAL |
| 10 | 12.76 | OPTIMAL |
| 11 | 12.78 | OPTIMAL |
| 12 | 13.04 | OPTIMAL |
| 13 | 12.00 | OPTIMAL |
| 14 | 12.21 | OPTIMAL |
| 15 | 12.36 | OPTIMAL |
| 16 | 15.03 | OPTIMAL |
| 17 | 12.57 | OPTIMAL |
| 18 | 12.78 | OPTIMAL |
| 19 | 15.32 | OPTIMAL |
| 20 | 15.41 | OPTIMAL |

## Aggregate Statistics

- **Total time:** 281.58s
- **Mean per scenario:** 14.08s
- **Min / Max:** 12.00s / 15.41s
- **Std dev:** ~1.1s (consistent performance)
- **Objective range:** 11,731,592 to 12,143,354
- **Objective spread:** 411,762

## Scaling Analysis

| Metric | TINY (39-bus) | SMALL (2000-bus) | Ratio |
|--------|---------------|------------------|-------|
| Mean solve time | 0.114s | 14.08s | 123x |
| Network buses | 39 | 2,000 | 51x |
| Network branches | 46 | 3,206 | 70x |
| LP variables per period | ~100 | ~2,500 | 25x |

The 123x solve-time increase for a 51x bus increase reflects the LP solve complexity
scaling, which is typical for interior-point and simplex methods on sparse networks.

## Solver

HiGHS with linearized costs (LP mode). HiGHS QP fails on ACTIVSg2000. Generator pmax
not perturbed due to tight margins (21% capacity margin).

## Test Script

Path: `evaluations/powermodels/tests/test_small_b4_c6.jl`
