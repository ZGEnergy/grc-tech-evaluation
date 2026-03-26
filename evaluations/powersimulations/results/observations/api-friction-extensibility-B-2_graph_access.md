---
tag: api-friction
source_dimension: extensibility
source_test: B-2
tool: powersimulations
severity: low
timestamp: 2026-03-24T00:00:00Z
---

# Observation: AdjacencyMatrix provides topology data but no graph traversal

## Finding

PowerNetworkMatrices.jl provides `AdjacencyMatrix` and `IncidenceMatrix` indexed by bus
number, but offers no graph traversal primitives (BFS, DFS, shortest path). Users must
implement traversal manually or add Graphs.jl as an external dependency.

## Context

During B-2 (graph access), BFS to depth 3 was implemented manually by iterating adjacency
matrix entries and building a dictionary. The matrix uses integer bus number indices, not
component names. Converting to a Graphs.jl graph would be ~5 lines of code but is not
provided by the ecosystem.

## Implications

For the Accessibility audit: documentation does not show examples of topology traversal
or graph construction from the adjacency/incidence matrices. Users needing graph algorithms
must know to look outside the PSI ecosystem. The friction is low (the data is there) but
the discoverability gap should be noted.
