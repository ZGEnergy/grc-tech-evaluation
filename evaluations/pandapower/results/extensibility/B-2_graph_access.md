---
test_id: B-2
tool: pandapower
dimension: extensibility
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "5068a626"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.94
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 152
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# B-2: BFS to depth 3 from a chosen bus

## Result: PASS

## Approach

pandapower provides a documented, first-class NetworkX graph export via `pandapower.topology.create_nxgraph(net)`. This creates a `MultiGraph` with buses as nodes and branches (lines, transformers, impedances) as edges. BFS is then trivially performed using standard NetworkX functions.

1. Loaded the IEEE 39-bus network using `load_pandapower`.
2. Created a NetworkX graph via `top.create_nxgraph(net, respect_switches=True)`.
3. Performed BFS from bus 0 (MATPOWER bus 1) to depth 3 using `nx.bfs_tree(mg, source=0, depth_limit=3)`.
4. Computed depth distribution using `nx.single_source_shortest_path_length(mg, 0, cutoff=3)`.
5. Verified additional graph features: impedance-weighted edges, connected components, distance calculation.

No workarounds were needed. The entire workflow uses documented public APIs.

## Output

**Graph statistics:**
- Graph type: `MultiGraph` (allows parallel edges)
- Nodes: 39 (all buses)
- Edges: 46 (35 lines + 11 transformers)
- Graph creation time: 0.5 ms

**BFS from bus 0, depth limit 3:**
- Nodes discovered: 12
- Edges in BFS tree: 11

| Depth | Buses |
|-------|-------|
| 0 | 0 |
| 1 | 1, 38 |
| 2 | 2, 8, 24, 29 |
| 3 | 3, 7, 17, 25, 36 |

**Additional graph features tested:**
- Connected component from bus 0: 39 buses (entire network is connected)
- Impedance-weighted graph: edge attributes include `r_ohm`, `x_ohm`, `z_ohm`, `weight`
- `calc_distance_to_bus(net, 0)`: returns hop distances from bus 0 to all buses
- BFS on weighted graph produces identical topology (BFS is unweighted)

## Workarounds

None required. `pandapower.topology.create_nxgraph()` is a documented public API that produces a standard NetworkX graph. All graph operations use standard NetworkX functions.

## Timing

- **Wall-clock:** 0.94 s (includes network loading)
- **Timing source:** measured
- **Graph creation:** 0.5 ms
- **BFS execution:** 0.4 ms
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b2_graph_access.py`

Key code pattern:

```python
import pandapower.topology as top
import networkx as nx

mg = top.create_nxgraph(net, respect_switches=True)
bfs_tree = nx.bfs_tree(mg, source=0, depth_limit=3)
depths = nx.single_source_shortest_path_length(mg, 0, cutoff=3)
```
