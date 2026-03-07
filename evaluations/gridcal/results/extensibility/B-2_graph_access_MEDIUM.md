---
test_id: B-2
tool: gridcal
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.107
peak_memory_mb: null
loc: 140
solver: null
timestamp: 2026-03-06T03:00:00Z
---

# B-2: Graph Access (MEDIUM)

## Result: PASS

## Approach

Used `grid.build_graph()` which returns a NetworkX `MultiDiGraph`. Converted to undirected for BFS (directed graph may have asymmetric edge directions). Ran BFS via `nx.single_source_shortest_path_length()` to depth 3 from bus 0.

## Output

### Graph Structure

- Graph type: `MultiDiGraph` (NetworkX)
- Nodes: 10,000 (one per bus)
- Edges: 12,706 (one per branch)
- Edge data: `weight` attribute (reactance value)
- Node data: empty dict

### BFS from Bus 0 ("NEAH BAY 1") to Depth 3

| Depth | Count | Sample Bus Indices |
|-------|-------|--------------------|
| 0 | 1 | [0] |
| 1 | 2 | [1, 10] |
| 2 | 2 | [13, 19] |
| 3 | 5 | [9, 12, 14, 18, 28] |

**Total subgraph:** 10 buses, 9 branches (7 Lines + 2 Transformer2W types found among 9)

### Subgraph Properties

- Connected: Yes
- Diameter: 6

### Timing

- **Graph build:** 86.5ms
- **BFS to depth 3:** 0.3ms
- **Branch scan:** 20.3ms (using dict-based bus index lookup)
- **Subgraph extraction:** 0.2ms
- **Total wall clock:** 107ms

## API Quality

- `grid.build_graph()` scales to 10k buses in 87ms
- Full NetworkX API available for traversal, analysis, and subgraph extraction
- BFS on 10k-node graph completes in sub-millisecond time
- No workarounds needed

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b2_graph_access_medium.py`
