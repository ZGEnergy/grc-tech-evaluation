# Observation: API Friction -- B-2 Graph Access

**Tag:** api-friction
**Test:** B-2 (Graph Access)
**Dimension:** extensibility

## Observation

PowerSystems.jl provides clean component iterators (`get_components`, `get_arc`,
`get_from`, `get_to`) that make topology extraction straightforward, but there is
no built-in graph representation or Graphs.jl integration anywhere in the Sienna
ecosystem.

Users must write ~32 lines of boilerplate to build an adjacency list and perform
basic graph algorithms (BFS, shortest path, connected components). This is a gap
in an otherwise comprehensive data model.

PowerNetworkMatrices.jl provides incidence and PTDF matrices, which encode topology
algebraically but are not suitable for graph traversal algorithms.

## Impact

Minor friction for users needing topological analysis. The PowerSystems data model
is well-designed enough that the manual construction is clean and reliable. However,
common operations like "find all buses within N hops" or "detect islands" require
custom code that could be a one-liner with Graphs.jl integration.
