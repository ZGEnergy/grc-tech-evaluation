---
test_id: B-3
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v11"
skill_version: v2
test_hash: "49124456"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 3.13
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 204
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# B-3: N-M contingency sweep from a chosen bus, graph distance x=3, up to m=3 outages

## Result: PASS

## Approach

Used the BFS/graph approach established in B-2, then enumerated N-M outage combinations and solved DCPF for each:

1. Load network via `load_gridcal()`
2. Build NetworkX graph via `grid.build_graph()` (returns `MultiDiGraph` with integer node indices)
3. BFS to depth 3 from bus index 15 (bus "16") using `nx.single_source_shortest_path_length()`
4. Identify 13 branches within the BFS subgraph by checking `bus_from`/`bus_to` membership
5. Enumerate all N-M combinations for m=1,2,3 using `itertools.combinations()`
6. For each contingency, toggle `branch.active = False` on the outaged branches, solve DCPF via `vge.power_flow()`, then restore. No model reconstruction is required.
7. Compute load loss by checking which buses remain energized (voltage magnitude > 0.5 pu)

The key finding is that `branch.active` is a simple boolean toggle on each branch object. Setting it to `False` removes the branch from the next power flow solve without requiring any model rebuild. This is a clean, documented API pattern.

## Output

| Metric | Value |
|--------|-------|
| Start bus | index 15 (bus "16") |
| BFS depth | 3 |
| Nodes in BFS subgraph | 13 |
| Branches in subgraph | 13 |
| N-1 contingencies | 13 |
| N-2 contingencies | 78 |
| N-3 contingencies | 286 |
| **Total contingencies** | **377** |
| Solve time | 1.85 s |
| Time per contingency | 4.92 ms |
| Contingencies with load loss | 38 |
| Max load loss | 680.0 MW |
| Mean load loss (where >0) | 423.8 MW |

**Top-5 worst contingencies by load loss:**

| Outaged Branches | m | Load Loss (MW) |
|-----------------|---|----------------|
| 19_20_1, 20_34_1 | 2 | 680.0 |
| 16_17_1, 19_20_1, 20_34_1 | 3 | 680.0 |
| 16_19_1, 19_20_1, 20_34_1 | 3 | 680.0 |
| 16_19_1, 19_33_1, 20_34_1 | 3 | 680.0 |
| 16_21_1, 19_20_1, 20_34_1 | 3 | 680.0 |

The 680 MW load loss corresponds to bus 20 (load = 680 MW) being islanded when its connecting branches are removed.

No N-1 contingencies caused load loss in this subgraph, which is expected for a well-connected portion of the IEEE 39-bus system. Load loss appears starting at N-2 when multiple branches isolating a load bus are removed simultaneously.

## Workarounds

None required. Branch toggling via `branch.active`, graph construction via `build_graph()`, and BFS via NetworkX are all documented public API features.

## Timing

- **Wall-clock:** 3.13 seconds (including network loading and graph construction)
- **Solve time only:** 1.85 seconds for 377 DCPF solves
- **Timing source:** measured
- **Peak memory:** not measured
- **Time per contingency:** 4.92 ms

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b3_contingency_sweep.py`
