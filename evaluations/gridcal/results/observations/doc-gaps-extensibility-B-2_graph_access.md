---
tag: doc-gaps
source_dimension: extensibility
source_test: B-2
tool: gridcal
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: build_graph() returns integer-indexed nodes without documentation

## Finding

`MultiCircuit.build_graph()` returns a NetworkX MultiDiGraph with integer node indices (0-based), not Bus objects or bus names. The return type and node semantics are not documented in the API reference or examples.

## Context

During B-2 (graph access), the graph returned by `build_graph()` used integer indices matching the internal bus ordering. While this is actually clean and works well with all NetworkX algorithms, the behavior is not documented. Users must inspect the graph at runtime to discover the node type and index mapping.

## Implications

Minor documentation gap. The `build_graph()` method works correctly and produces a standard NetworkX graph that integrates cleanly with the full algorithm library. This should be noted in the Accessibility audit as a minor friction point -- the method is discoverable but its semantics are underdocumented.
