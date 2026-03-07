---
test_id: A-7
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 2.251
peak_memory_mb: null
loc: 333
solver: null
timestamp: "2026-03-06T00:00:00Z"
---

# A-7: N-M Contingency Sweep on TINY (IEEE 39-bus)

## Result: QUALIFIED PASS

PowerModels.jl has **no native graph library** and no built-in contingency sweep. The BFS graph-distance scoping, N-M combinatorial enumeration, pruning logic, and load-loss calculation were all implemented manually in Julia using PowerModels' data dict and `calc_connected_components()`. Contingency re-solves use `deepcopy(data)` + `br_status=0` + `compute_dc_pf` -- no model reconstruction from file.

## Approach

Parameters: seed bus = 16, graph distance x = 3, max outage order m = 3.

1. **Build adjacency graph manually** from branch `f_bus`/`t_bus` data (~20 lines). PowerModels has no native graph library -- adjacency is extracted from the parsed data dict.
2. **BFS from seed bus** to find all buses within graph distance 3. Result: 20 buses, 21 branches in scope.
3. **N-1 sweep:** For each of 21 scoped branches, set `br_status=0` in a deep-copied data dict, check connectivity via `calc_connected_components()`, then run `compute_dc_pf`. Load on buses outside the main island (containing the reference bus) is counted as lost.
4. **Pruning:** Branches whose N-1 removal causes total load loss are pruned from higher-order combinations.
5. **N-2 sweep:** Enumerate all C(surviving, 2) combinations. Apply same load-loss calculation. Prune pairs causing total load loss.
6. **N-3 sweep:** Enumerate all C(surviving, 3) combinations, skipping any triple containing an N-2 pair that already caused total load loss.

## Output

- **Buses in scope (distance <= 3):** 20 of 39
- **Branches in scope:** 21 of 46
- **N-1 results:**
  - 21 contingencies evaluated
  - 2 caused load loss (non-zero)
  - 0 caused total load loss (no pruning at N-1)
- **N-2 results:**
  - 210 contingencies evaluated
  - 53 caused load loss
  - 0 caused total load loss (no pruning at N-2)
- **N-3 results:**
  - 1,330 contingencies evaluated
  - 0 pruned (no total-loss pairs at N-2 to prune)
  - 593 caused load loss
- **Total DCPF solves:** 1,561
- **Time per solve:** 0.0014s (amortized, excluding JIT)
- **Total wall-clock:** 2.25s

## Workarounds

1. **No native graph library (stable workaround):** BFS adjacency graph built manually from branch `f_bus`/`t_bus` pairs. This requires ~20 lines of Julia code. Not difficult, but other tools (e.g., pandapower with NetworkX) provide this natively.

2. **SingularException handling (stable workaround):** When a contingency creates network islands, `compute_dc_pf` throws a `LinearAlgebra.SingularException` because the admittance matrix becomes singular. The workaround is to pre-check connectivity using `PowerModels.calc_connected_components()` before attempting DCPF, and compute load loss from island analysis.

3. **Deep copy per contingency (stable workaround):** Each contingency requires `deepcopy(data)` to avoid mutating the base case. This is memory-intensive but functionally correct. PowerModels does not provide a lightweight "toggle branch" mechanism for repeated contingency analysis.

## What PowerModels Contributed vs. What Was Manual

| Component | Source |
|-----------|--------|
| MATPOWER parsing | PowerModels (`parse_file`) |
| Network topology data | PowerModels (parsed `Dict`) |
| Connected component analysis | PowerModels (`calc_connected_components`) |
| DC power flow solve | PowerModels (`compute_dc_pf`) |
| BFS adjacency graph | Manual (~20 lines) |
| Graph-distance scoping | Manual (BFS loop) |
| N-M combinatorial enumeration | Manual (nested loops) |
| Pruning logic | Manual (set operations) |
| Load loss calculation | Manual (island analysis) |
| Contingency toggling | Manual (`deepcopy` + `br_status=0`) |

## Timing

- Wall-clock: 2.25s (1,561 solves + BFS + enumeration, excludes JIT)
- Time per DCPF solve: 0.0014s (amortized)
- Peak memory: not measured (deepcopy per contingency adds overhead)

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a7_contingency_sweep.jl`
