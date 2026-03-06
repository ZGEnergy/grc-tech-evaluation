---
test_id: A-7
tool: powermodels
dimension: expressiveness
network: MEDIUM
status: pass
wall_clock_seconds: 983.936
timestamp: 2026-03-05
---

# A-7: N-M Contingency Sweep [MEDIUM]

## Result: PASS

## Approach
Same as TINY: manual branch removal + `compute_dc_pf()` per contingency. Parameters: x=5 (graph distance), m=4 (max contingency order).

## Data Preprocessing
- Standard preprocessing (costs, rate_a defaults)

## Scale Adaptations
- Candidate branches limited to 30 (within BFS distance 5 of focus bus) to manage combinatorial growth
- Higher-order contingencies (N-2, N-3, N-4) limited to 200 combinations each
- Focus bus: highest-degree node in 10k-bus network

## Output
- N-1 through N-4 contingencies evaluated
- Total contingencies evaluated across all orders
- Each contingency: deepcopy data, toggle br_status, compute_dc_pf
- Convergence tracked per contingency

## Timing
- Wall-clock: 984s (~16.4 min)
- Per-contingency: dominated by deepcopy of 10k-bus data dict (~0.5s each)
- The native `compute_dc_pf` solver itself is fast; the overhead is Julia Dict deepcopy

## Workarounds
- No built-in contingency sweep in PowerModels
- Manual implementation: toggle branch status in data dict + recompute DC PF
- Native solver avoids JuMP model reconstruction overhead
