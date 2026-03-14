---
tag: arch-quality
source_dimension: extensibility
source_test: B-2
tool: pypsa
severity: low
timestamp: 2026-03-13T00:00:00Z
---

# Observation: Native NetworkX graph export with zero friction

## Finding

PyPSA's `n.graph()` returns a NetworkX graph object (OrderedGraph) directly, making the full NetworkX algorithm library available with zero boilerplate. Buses are nodes, branches (both lines and transformers) are edges with component type as edge keys.

## Context

During B-2 (BFS graph access test), calling `n.graph()` and then `nx.single_source_shortest_path_length()` required exactly 3 lines of substantive code. PyPSA also exposes `n.adjacency_matrix()`, `n.incidence_matrix()`, and `n.determine_network_topology()` as additional documented graph primitives. The graph correctly includes both Line and Transformer components as edges.

## Implications

This is a positive architecture finding for Accessibility (Suite D). The graph export is a first-class, documented API method rather than a workaround, and the choice of NetworkX as the graph backend means users have immediate access to hundreds of graph algorithms without additional dependencies. Other tools that require manual graph construction from bus/branch tables should be noted as having higher friction for topology-based analysis.
