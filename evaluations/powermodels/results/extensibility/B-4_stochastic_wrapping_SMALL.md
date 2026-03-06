---
test_id: B-4
tool: powermodels
dimension: extensibility
network: SMALL
status: pass
wall_clock_seconds: 3613.37
timestamp: 2026-03-05
---

# B-4: Stochastic Wrapping (50 Scenarios x 24hr DCPF) [SMALL]

## Result: PASS

## Approach
Same as TINY: `replicate()` for 24-period multi-network, `deepcopy` + load perturbation per scenario, `solve_mn_opf` with Ipopt. 50 scenarios with correlated load perturbations.

## Data Preprocessing
- Standard preprocessing (costs, rate_a)

## Output
- All 50 scenarios solved successfully
- Mean solve time per scenario: ~72s
- Total solve time: ~3600s (60 min)
- Cost statistics (mean, std) computed across scenarios

## Scale Impact
- TINY (case39): 50 scenarios completed in ~2s total
- SMALL (2000-bus): 50 scenarios took ~60 min (1800x slowdown)
- Each scenario solve on 2000-bus x 24-period is ~72s with Ipopt
- Note: concurrent Julia processes on the same machine inflated solve times

## Timing
- Wall-clock: 3613s (~60 min)
- Per-scenario: ~72s average
