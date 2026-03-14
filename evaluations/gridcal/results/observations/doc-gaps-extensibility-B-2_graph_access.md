---
tag: doc-gaps
source_dimension: extensibility
source_test: B-2
tool: gridcal
severity: low
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: build_graph() node type not documented

## Finding

`MultiCircuit.build_graph()` returns a NetworkX MultiDiGraph with `Bus` objects as nodes, not integers or strings. This is not documented in the API reference or examples, requiring source code inspection to discover.

## Context

During B-2 (graph access), the initial attempt to use `single_source_shortest_path_length` with a bus name string failed with `NodeNotFound`. The graph nodes are Bus objects, so the BFS source must be a Bus object obtained from `grid.get_buses()` or `list(graph.nodes())`.

## Implications

Minor documentation gap. The `build_graph()` method is discoverable and works correctly once the node type is known. This should be noted in the Accessibility audit as a minor friction point.
