---
test_id: B-2
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.001
peak_memory_mb: null
loc: 130
solver: null
timestamp: 2026-03-06T02:00:00Z
---

# B-2: Graph Access

## Result: PASS

## Approach

Used `grid.build_graph()` which returns a NetworkX `MultiDiGraph` with bus indices as nodes and branches as edges (weight = reactance). Ran BFS via `nx.single_source_shortest_path_length()` to depth 3 from bus 0.

## Output

### Graph Structure

- Graph type: `MultiDiGraph` (NetworkX)
- Nodes: 39 (one per bus)
- Edges: 46 (one per branch)
- Edge data: `weight` attribute (reactance value)
- Node data: empty dict (no bus attributes stored on graph nodes)

### BFS from Bus 0 (bus name "1") to Depth 3

| Depth | Count | Bus Indices | Bus Names |
|-------|-------|-------------|-----------|
| 0 | 1 | [0] | [1] |
| 1 | 2 | [1, 38] | [2, 39] |
| 2 | 3 | [2, 24, 29] | [3, 25, 30] |
| 3 | 4 | [3, 17, 25, 36] | [4, 18, 26, 37] |

**Total subgraph:** 10 buses, 9 branches

### Subgraph Properties

- Connected: Yes
- Diameter: 4
- Branch types: 7 Lines + 2 Transformer2W

### Branch Identification

Branches in subgraph identified by matching `bus_from` / `bus_to` indices against the BFS-discovered bus set. Both line and transformer branches included.

## API Quality

- `grid.build_graph()` -- single call, returns standard NetworkX graph
- Full NetworkX API available (BFS, DFS, shortest path, centrality, etc.)
- `G.subgraph(nodes).copy()` works for extracting subgraphs
- NetworkX is a first-class dependency (imported in GridCal core)
- No workarounds needed

## Timing

- **Graph build:** 0.418ms
- **BFS to depth 3:** 0.108ms
- **Subgraph extraction:** 0.133ms

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b2_graph_access.py`
