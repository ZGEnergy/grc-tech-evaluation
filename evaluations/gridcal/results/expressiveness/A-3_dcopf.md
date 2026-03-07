---
test_id: A-3
tool: gridcal
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 5.416
peak_memory_mb: null
loc: 35
solver: "HiGHS"
timestamp: 2026-03-06T03:00:00Z
---

# A-3: DC OPF (Grade: MEDIUM)

## Result: PASS

## Network

ACTIVSg10k -- 10,000 buses, 12,706 branches (all with rate limits), 2,485 generators.

## Approach

Same as TINY: `vge.linear_opf()` with HiGHS solver.

## Output

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Total generation (MW) | 150,916.9 |
| Active generators | 1,937 of 2,485 |
| Gen dispatch range (MW) | 0.0 -- 1403.2 |
| LMP range ($/MWh) | 20.064 (uniform) |
| Branch flow range (MW) | -2060.5 to 1855.1 |
| Max loading | 84.72% |
| Binding branches | 0 |
| Load shedding (MW) | 0.0 |
| Gen shedding (MW) | 0.0 |

LMPs are uniform at $20.064/MWh because no branches are binding (max loading 84.7%).

## Scaling from TINY

| Metric | TINY (39 bus) | MEDIUM (10k bus) | Ratio |
|--------|--------------|-----------------|-------|
| Buses | 39 | 10,000 | 256x |
| Generators | 10 | 2,485 | 249x |
| Solve time (s) | ~0.1 | 5.416 | ~54x |

DC OPF scales well to 10k buses. HiGHS solves the LP in 5.4s.

## Workarounds

None required.

## Timing

- **Wall-clock (solve only):** 5.416s
- **File load time:** 7.40s
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a3_dcopf_medium.py`
