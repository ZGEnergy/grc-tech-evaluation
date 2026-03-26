---
test_id: B-2
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v11"
skill_version: v2
test_hash: "5068a626"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.20
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 133
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# B-2: From a chosen bus, run BFS to depth 3 and return subgraph

## Result: PASS

## Approach

GridCal provides `MultiCircuit.build_graph()` which returns a `networkx.MultiDiGraph` with integer node indices matching bus ordering. This is a documented public API method that integrates cleanly with the full NetworkX algorithm library.

1. Load network via `load_gridcal(network_file)`
2. Call `grid.build_graph()` to get NetworkX `MultiDiGraph`
3. Use `nx.single_source_shortest_path_length(graph, start_bus, cutoff=3)` for BFS
4. Extract subgraph via `graph.subgraph(bfs_nodes).copy()`

The graph nodes are integers (0-based bus indices), which makes BFS straightforward. The returned graph has 39 nodes and 46 edges matching the network topology exactly.

## Output

| Metric | Value |
|--------|-------|
| Graph type | MultiDiGraph |
| Graph nodes | 39 |
| Graph edges | 46 |
| Start bus | 0 (first bus) |
| BFS depth | 3 |
| BFS nodes found | 10 |
| Subgraph nodes | 10 |
| Subgraph edges | 9 |
| Subgraph connected | Yes |

**Depth layers:**

| Depth | Nodes |
|-------|-------|
| 0 | 0 |
| 1 | 1, 38 |
| 2 | 2, 24, 29 |
| 3 | 3, 17, 25, 36 |

## Workarounds

None required. The `build_graph()` method returns a standard NetworkX graph that works with all NetworkX algorithms out of the box.

## Timing

- **Wall-clock:** 1.20 seconds (includes network loading)
- **Timing source:** measured
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b2_graph_access.py`
