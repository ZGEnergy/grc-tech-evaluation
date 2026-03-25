---
tag: doc-gaps
source_dimension: extensibility
source_test: B-2
tool: powersimulations
severity: low
timestamp: 2026-03-24T00:00:00Z
---

# Observation: No documentation for topology traversal from adjacency matrices

## Finding

PowerNetworkMatrices.jl documentation does not show examples of topology traversal or
graph construction from the `AdjacencyMatrix` or `IncidenceMatrix` types.

## Context

During B-2 (graph access), the evaluator had to discover the axis indexing convention
and nonzero-entry semantics by inspecting the returned object types. The `AdjacencyMatrix`
is indexed by integer bus numbers and uses nonzero entries to indicate connectivity, but
this is not documented with examples.

## Implications

For the Accessibility audit: users performing topology analysis will need to inspect
return types at the REPL or read source code to understand how to use these matrix types
for graph operations.
