---
test_id: B-2
tool: pypsa
dimension: extensibility
network: MEDIUM
status: pass
workaround_class: null
wall_clock_seconds: 0.11
peak_memory_mb: null
loc: 5
solver: null
timestamp: 2026-03-05T00:00:00Z
---

# B-2: Graph Access on MEDIUM (ACTIVSg10k)

## Result: PASS

## Approach
`n.graph()` returns NetworkX OrderedGraph. BFS from bus 28156 to depth 3 using `nx.bfs_tree()`.

## Output
- Graph: 10,000 nodes, 12,706 edges
- Source bus: 28156
- Buses reached at depth 3: 28
- Depth distribution: 1 (depth 0), 5 (depth 1), 9 (depth 2), 13 (depth 3)
- Subgraph: 28 lines + 1 transformer = 29 branches
- 5 lines of code

## Workarounds
None. Native `n.graph()` provides clean NetworkX integration.

## Timing
- Wall-clock: 0.11s
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/extensibility/test_b2_graph_access_medium.py`
