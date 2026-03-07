---
test_id: B-2
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.070
peak_memory_mb: null
loc: 4
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-2: Graph Access

## Result: PASS

## Approach

PyPSA provides first-class NetworkX graph access via `n.graph()`, which returns an
`OrderedGraph` (a `networkx.MultiGraph` subclass). From there, standard NetworkX
graph algorithms work directly with no adaptation or conversion required.

The test loads the IEEE 39-bus case via the matpowercaseframes pipeline, calls
`n.graph()` to obtain the NetworkX graph, then uses `networkx.bfs_tree()` with
`depth_limit=3` from bus "1" to extract all reachable buses within 3 hops. The
subgraph of those buses (including all connecting branches) is extracted via
`G.subgraph(bfs_buses).copy()`.

Core code (4 lines beyond network loading):

```python
G = n.graph()
bfs_tree = nx.bfs_tree(G, start_bus, depth_limit=3)
bfs_buses = list(bfs_tree.nodes())
subgraph = G.subgraph(bfs_buses).copy()
```

## Output

| Metric | Value |
|--------|-------|
| Graph type | OrderedGraph (networkx.MultiGraph subclass) |
| Total graph nodes | 39 |
| Total graph edges | 46 |
| Start bus | 1 |
| BFS depth limit | 3 |
| Buses found (BFS) | 12 |
| Subgraph edges | 11 |

Buses found within 3 hops of bus 1: 1, 2, 39, 30, 3, 25, 9, 4, 18, 37, 26, 8.

All nodes verified to be within 3 hops via `nx.shortest_path_length()`.

## Workarounds

None required. `n.graph()` is a documented public API that returns a standard
NetworkX graph. All standard NetworkX algorithms (BFS, DFS, shortest path,
subgraph extraction, etc.) work directly.

## Timing

- **Wall-clock:** 0.070s (includes network loading + graph construction + BFS)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b2_graph_access.py`
