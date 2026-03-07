---
tag: api-strength
source_dimension: extensibility
source_test: B-2
tool: gridcal
severity: positive
timestamp: 2026-03-06T02:00:00Z
---

# Observation: NetworkX graph export is first-class

## Finding

`grid.build_graph()` returns a standard `nx.MultiDiGraph` with bus indices as nodes and branches as edges (weight = reactance). This makes the full NetworkX API (BFS, DFS, shortest path, centrality, community detection, etc.) immediately available with zero workarounds.

## Context

B-2 required BFS to depth 3 and subgraph extraction. Both operations completed in sub-millisecond time using standard NetworkX functions. No adapter code or custom graph conversion needed.

## Implications

This is a significant extensibility strength. Users can leverage the entire NetworkX ecosystem for topology analysis, visualization, and algorithm prototyping without learning a custom graph API.
