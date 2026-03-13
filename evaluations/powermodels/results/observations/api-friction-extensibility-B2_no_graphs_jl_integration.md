# Observation: api-friction — No Graphs.jl integration; manual adjacency required

**Tag:** api-friction
**Dimension:** extensibility
**Test:** B-2
**Severity:** minor

## Finding

PowerModels has no native Graphs.jl integration. Graph traversal algorithms (BFS, shortest path, spanning tree, etc.) cannot be applied to the network without first manually constructing an adjacency structure from `data["branch"]` f_bus/t_bus fields (~12 lines of code).

The only built-in graph function is `PowerModels.calc_connected_components(data)`, which identifies connected components but does not expose a Graphs.jl-compatible type.

`pm.ref[:bus_arcs]` (available after `instantiate_model`) provides preprocessed arc tuples `(branch_id, from_bus, to_bus)` per bus, which is a convenient alternative for neighbor enumeration when a JuMP model is already being built. However, this is still not a Graphs.jl `AbstractGraph`.

Graphs.jl was not installed in the evaluation environment (not in depot at all).

## Evidence

- B-2 test: `using Graphs` raised `ArgumentError: Package Graphs not found`
- Manual adjacency construction: 12 lines, uses `data["branch"]` dict
- PowerModelsAnalytics.jl (not installed) may provide visualization-oriented graph support but does not expose a Graphs.jl-compatible type per available documentation

## Workaround

Build adjacency manually from `data["branch"]` f_bus/t_bus fields. 12 lines, stable (documented public API).

## Implication

Minor friction for users who want to run graph algorithms on power network topology. The workaround is short and uses stable public API. Not a blocking limitation — power engineers rarely need arbitrary graph traversal, and connectivity checks are available via `calc_connected_components`.
