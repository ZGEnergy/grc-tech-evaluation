---
test_id: B-2
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: v10
skill_version: v1
test_hash: 5068a626
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.09
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 126
solver: null
timestamp: 2026-03-13T00:00:00Z
---

# B-2: From a chosen bus, run BFS to depth 3 on TINY

## Result: PASS

## Approach

Used PyPSA's documented `n.graph()` method which returns a NetworkX `OrderedGraph` (a subclass of `nx.Graph`). Buses are nodes and branches (lines + transformers) are edges. From this graph, standard NetworkX BFS via `nx.single_source_shortest_path_length()` with `cutoff=3` was used to find all buses reachable within 3 hops from the chosen root bus.

The entire operation requires 3 lines of substantive code:
1. `G = n.graph()` -- export to NetworkX
2. `depths = nx.single_source_shortest_path_length(G, root, cutoff=3)` -- BFS
3. `subgraph = G.subgraph(depths.keys())` -- extract induced subgraph

No workarounds, no undocumented internals, no source patching.

## Output

**Graph properties:**
- Type: `OrderedGraph`
- Total nodes: 39 (all buses)
- Total edges: 46 (35 lines + 11 transformers)

**BFS from bus "1" to depth 3:**

| Depth | Buses |
|-------|-------|
| 0 | 1 |
| 1 | 2, 39 |
| 2 | 3, 9, 25, 30 |
| 3 | 4, 8, 18, 26, 37 |

- **Buses in depth-3 subgraph:** 12
- **Edges in depth-3 subgraph:** 11
- **Branches:** L0, L1, L2, L3, L4, L5, L13, L14, L30, T0, T9

The subgraph covers 31% of the network's buses (12/39) and 24% of edges (11/46), demonstrating that the graph faithfully represents the network topology including both lines and transformers.

**Additional documented graph APIs:**
- `n.adjacency_matrix()` -- sparse adjacency matrix
- `n.incidence_matrix()` -- sparse incidence matrix
- `n.determine_network_topology()` -- connected component detection

## Workarounds

None required.

## Timing

- **Wall-clock:** 1.09s (includes network loading)
- **Timing source:** measured
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b2_graph_access.py`
