---
tag: api-friction
dimension: extensibility
test_id: B-2
slug: graph_access
tool: powermodels
---

# api-friction: No native graph API requires manual adjacency construction

PowerModels stores network topology in a flat dictionary of branches with `f_bus` and
`t_bus` fields but provides no graph abstraction (adjacency lists, BFS, shortest path,
connected subgraphs, etc.). Users must build graph structures manually from branch data.

The `ref` dict (constructed during model instantiation) has `:arcs_from`, `:bus_arcs`
mappings, but these are arc-oriented (for variable indexing) rather than graph-oriented.
They are not available from the raw parsed data dict.

`PowerModelsAnalytics.jl` exists as a separate package providing Graphs.jl integration,
but it is optional and not part of the core PowerModels dependency tree.

Impact: ~15 lines of boilerplate adjacency construction needed for any graph analysis
(BFS, DFS, shortest path, connected components). The workaround is stable since the
`data["branch"]` dict structure is documented and unlikely to change. However, this is
a common enough need (contingency scoping, topology analysis, visualization) that native
graph primitives would be valuable.

Note: `PowerModels.calc_connected_components(data)` does exist for island detection,
suggesting some internal graph logic exists but is not exposed as a general-purpose API.
