---
test_id: B-2
tool: pandapower
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.091
peak_memory_mb: null
loc: 105
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-2: BFS to depth 3 from a chosen bus, return subgraph

## Result: PASS

## Approach

Used pandapower's documented `create_nxgraph()` function from `pandapower.topology` to export the network as a NetworkX `MultiGraph`. Then used standard NetworkX BFS functions to explore the graph to depth 3 from bus 0.

API calls used:
1. `pandapower.topology.create_nxgraph(net, respect_switches=True)` -- creates NetworkX graph
2. `networkx.single_source_shortest_path_length(graph, start_bus, cutoff=3)` -- BFS with depth limit
3. `graph.subgraph(buses).copy()` -- extract subgraph

All APIs are public and documented. No workarounds needed.

## Output

| Metric | Value |
|--------|-------|
| Full graph nodes | 39 |
| Full graph edges | 46 |
| Start bus | 0 |
| BFS depth | 3 |
| Buses in subgraph | 12 |
| Lines in subgraph | 9 |
| Trafos in subgraph | 2 |
| Total branches in subgraph | 11 |

Bus depths from bus 0:

| Depth | Buses |
|-------|-------|
| 0 | 0 |
| 1 | 1, 38 |
| 2 | 2, 8, 24, 29 |
| 3 | 3, 7, 17, 25, 36 |

The subgraph contains all buses reachable within 3 hops and all branches (lines + transformers) whose both endpoints are within the subgraph.

## Workarounds

None required.

## Timing

- **Wall-clock:** 0.091 s
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b2_graph_access.py`
