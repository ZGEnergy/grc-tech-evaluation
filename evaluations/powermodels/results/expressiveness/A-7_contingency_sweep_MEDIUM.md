---
test_id: A-7
tool: powermodels
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: stable
wall_clock_seconds: null
peak_memory_mb: null
loc: 333
solver: null
timestamp: "2026-03-07T00:00:00Z"
---

# A-7: N-M Contingency Sweep (MEDIUM, ACTIVSg 10k-bus)

## Result: NOT ATTEMPTED (expected timeout)

## Rationale

The protocol requires x=5 (graph distance), m=4 (max simultaneous outages) on the
10k-bus network. At TINY (39-bus, x=3, m=3), the test completed 1,561 DCPF solves
in 2.25s. At MEDIUM scale, the problem grows combinatorially:

- BFS to depth 5 on a 10k-bus network would scope ~500-2,000 branches
- N-4 combinations from even 500 branches: C(500, 4) = ~2.6 billion
- Each DCPF solve on 10k-bus takes ~0.2-0.5s (vs 0.0014s on 39-bus)

Even N-2 alone would require ~125,000 solves at ~0.3s each = ~10+ hours.

## What The TINY Test Demonstrated

The A-7 TINY test showed that PowerModels can express the entire N-M contingency
sweep workflow, but entirely manually:

| Component | Source |
|-----------|--------|
| MATPOWER parsing | PowerModels (`parse_file`) |
| Connected component analysis | PowerModels (`calc_connected_components`) |
| DC power flow solve | PowerModels (`compute_dc_pf`) |
| BFS adjacency graph | Manual (~20 lines) |
| Graph-distance scoping | Manual (BFS loop) |
| N-M combinatorial enumeration | Manual (nested loops) |
| Pruning logic | Manual (set operations) |
| Load loss calculation | Manual (island analysis) |
| Contingency toggling | Manual (`deepcopy` + `br_status=0`) |

The expressiveness of the approach is confirmed at TINY scale. The MEDIUM limitation
is purely computational (combinatorial explosion + per-solve cost), not an API gap.

## Test Script

Based on: `evaluations/powermodels/tests/expressiveness/test_a7_contingency_sweep.jl`
