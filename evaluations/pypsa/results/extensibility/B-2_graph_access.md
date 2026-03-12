---
test_id: B-2
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: v9
skill_version: v1
test_hash: 67b71101
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.046
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 125
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# B-2: Graph Access — BFS from chosen bus

## Result: PASS

## Approach

Loaded the IEEE 39-bus network using the same matpowercaseframes pipeline as A-1. Called `n.graph()` which returns a `networkx.OrderedGraph` (a subclass of `networkx.MultiGraph`). All buses are nodes and all branches (lines + transformers) are edges. Used `nx.single_source_shortest_path_length(G, '1', cutoff=3)` to find all buses reachable from bus '1' within depth 3, then constructed the induced subgraph.

The entire graph access operation requires 3 lines of substantive code beyond network loading:
1. `G = n.graph()`
2. `reachable = set(nx.single_source_shortest_path_length(G, root, cutoff=3).keys())`
3. `subgraph = G.subgraph(reachable)`

## Output

**Graph properties:**
- Graph type: `networkx.OrderedGraph` (MultiGraph subclass)
- Nodes: 39 (buses), Edges: 46 (35 lines + 11 transformers)

**BFS from bus '1' to depth 3:**
- Buses in subgraph (12): `['1', '18', '2', '25', '26', '3', '30', '37', '39', '4', '8', '9']`
- Branches in subgraph (11): L0, L1, L13, L14, L2, L3, L30, L4, L5, T0, T9
- LOC for graph access operation: 3

## Workarounds

None required. `n.graph()` returns a native NetworkX object with the full NetworkX API available. No intermediate conversion step is needed.

## Timing

- **Wall-clock:** 1.046 s (includes network loading; graph operations alone take < 1 ms)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** N/A (no solver used)
- **Convergence residual:** N/A

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b2_graph_access_tiny.py`

Key API sequence:
```python
G = n.graph()                                           # returns networkx.OrderedGraph
reachable = set(nx.single_source_shortest_path_length(G, '1', cutoff=3).keys())
subgraph = G.subgraph(reachable)
buses = list(subgraph.nodes())                          # 12 buses
edges = list(subgraph.edges(keys=True))                 # 11 branches
```
