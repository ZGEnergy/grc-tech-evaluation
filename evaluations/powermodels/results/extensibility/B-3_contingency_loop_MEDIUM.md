---
test_id: B-3
tool: powermodels
dimension: extensibility
network: MEDIUM
status: pass
wall_clock_seconds: 66.585
timestamp: 2026-03-05
---

# B-3: N-1 DCPF Contingency Loop (100-Branch Subset) [MEDIUM]

## Result: PASS

## Approach
Same as TINY: `deepcopy` data, set `br_status=0`, call `compute_dc_pf()` per contingency. 100-branch subset of the 12706 total branches.

## Output
- 100 contingencies evaluated from 12706 total active branches
- Solved/failed counts recorded
- Worst-case branch loading (max |flow|/rate_a) identified

- Per-contingency and total solve times recorded

## Scale Observations
- Each contingency: deepcopy (~0.5s on 10k-bus data dict) + compute_dc_pf (~0.1s)
- 100 contingencies: ~66s total
- Extrapolated full N-1 (12706 branches): ~2.2 hours
- Bottleneck is Julia Dict deepcopy, not the linear algebra

## Timing
- Wall-clock: 66.6s
- Mean per contingency: ~0.67s
- Total contingency solve time: ~60s
