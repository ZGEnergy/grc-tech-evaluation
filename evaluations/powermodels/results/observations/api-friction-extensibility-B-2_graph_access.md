# Observation: api-friction — B-2 Graph Access

## Tool
PowerModels.jl v0.21.5

## Finding
PowerModels has **no Graphs.jl integration** and no native graph traversal API. The network topology is stored as a flat `Dict{String,Any}` of branch records with `f_bus`/`t_bus` integer fields. Any graph algorithm (BFS, shortest path, connected components) requires the user to first build an adjacency list manually from `data["branch"]` (~15 LOC).

The `ref_add_core!` function does pre-compute `bus_arcs` and `arcs_from`/`arcs_to` mappings, but these are only available after model instantiation, not from the raw data dict. There is no utility function like `build_adjacency(data)`.

## Impact
- Medium friction for topology analysis use cases
- ~30 LOC boilerplate for any graph algorithm
- No interop with the Julia Graphs.jl ecosystem without manual conversion

## Recommendation
A utility function `calc_adjacency(data)` or export to `Graphs.SimpleGraph` would eliminate this friction.
