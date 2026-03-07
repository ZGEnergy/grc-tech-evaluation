---
test_id: B-2
tool: pandapower
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 2.01
peak_memory_mb: null
loc: 112
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-2: From a chosen bus, run BFS to depth 3. Return all buses and branches.

## Result: PASS

## Approach

1. Loaded ACTIVSg10k (~10,000 buses)
2. Created NetworkX graph via `pandapower.topology.create_nxgraph(net, respect_switches=True)`
3. Ran BFS from bus 10000 to depth 3 via `nx.single_source_shortest_path_length(graph, bus, cutoff=3)`
4. Identified all buses and branches in the BFS subgraph

All via public, documented APIs.

## Output

| Metric | Value |
|--------|-------|
| Network buses | 10,000 |
| Graph nodes | 10,000 |
| Graph edges | 12,706 |
| Graph type | MultiGraph |
| Start bus | 10000 |
| BFS depth | 3 |
| Buses in subgraph | 10 |
| Lines in subgraph | 8 |
| Trafos in subgraph | 1 |
| Total branches in subgraph | 9 |

Buses by depth: depth 0 = 1, depth 1 = 2, depth 2 = 2, depth 3 = 5.

## Workarounds

None required.

## Timing

- **Wall-clock:** 2.01 s (includes network loading + graph creation + BFS)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b2_graph_access_medium.py`
