---
test_id: B-2
tool: powermodels
dimension: extensibility
network: TINY
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.215
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 12
solver: null
protocol_version: "v9"
skill_version: v1
test_hash: df63b316
timestamp: 2026-03-12T03:38:50Z
---

# B-2: Graph Access (TINY)

## Result: QUALIFIED PASS

## Approach

PowerModels has no native Graphs.jl integration. Three access paths were tested:

### Path 1: Manual adjacency from `data["branch"]`
Iterated `data["branch"]` dict, read `f_bus`/`t_bus` fields, built `Dict{Int, Vector{Tuple{Int,Int}}}`. ~12 lines. BFS traversal then implemented manually.

#### Path 2: `pm.ref[:bus_arcs]`
After `instantiate_model`, `PowerModels.ref(pm, nw_id, :bus_arcs)` returns preprocessed arc tuples `(branch_id, from_bus, to_bus)` per bus — a ready-made neighbor lookup table. This is cleaner than re-extracting from `data["branch"]` for post-model-build use.

#### Path 3: Graphs.jl
`using Graphs` failed — Graphs.jl is not installed in the evaluation environment. No native bridge from PowerModels to Graphs.jl exists.

### BFS result (seed bus 16, depth 3):
- Bus 16 degree: 5 (neighbors: 15, 17, 19, 21, 24)
- Depth-1: [15, 17, 19, 21, 24]
- Depth-2: [14, 18, 20, 22, 23, 27, 33]
- Depth-3: [3, 4, 13, 26, 34, 35, 36]
- Subgraph: 20 buses, 21 branches (51% of network within depth-3 of bus 16)

**Built-in graph function:** `PowerModels.calc_connected_components(data)` confirmed the network is fully connected (1 component).

## Output

| Metric | Value |
|--------|-------|
| Total buses | 39 |
| Total branches | 46 |
| Seed bus | 16 |
| BFS depth | 3 |
| Subgraph buses | 20 |
| Subgraph branches | 21 |
| Network connected | true (1 component) |
| Graphs.jl available | false |
| pm.ref[:bus_arcs] available | true (39 buses, 92 arc entries) |

Bus 16 arcs from `pm.ref[:bus_arcs]`: branches 25, 26, 27, 28, 29 connecting to buses 15, 17, 19, 21, 24.

## Workarounds

- **What:** Manual adjacency construction from `data["branch"]` f_bus/t_bus fields. ~12 lines.
- **Why:** PowerModels provides no Graphs.jl integration and no native BFS/traversal function beyond `calc_connected_components`.
- **Durability:** stable — `data["branch"]` is documented public API. The dict structure is guaranteed by the MATPOWER parsing layer.
- **Grade impact:** B-level. Workaround is short (~12 LOC), uses only public API, and is idiomatic Julia. No source patching required. The `pm.ref[:bus_arcs]` alternative reduces this to ~5 lines for neighbor enumeration post-instantiation.

## Timing

- **Wall-clock:** 0.215 s (includes parse, model instantiation, and BFS)
- **Timing source:** measured
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/powermodels/tests/extensibility/test_b2_graph_access_tiny.jl`

Key adjacency construction pattern (~12 lines):

```julia

adjacency = Dict{Int,Vector{Tuple{Int,Int}}}()
for b in bus_ids; adjacency[b] = Tuple{Int,Int}[]; end
for br_id in branch_ids
    br = data["branch"][string(br_id)]
    f, t = br["f_bus"], br["t_bus"]
    push!(adjacency[f], (t, br_id))
    push!(adjacency[t], (f, br_id))
end

```

Alternative using `pm.ref[:bus_arcs]` (requires model instantiation):

```julia

pm = PowerModels.instantiate_model(data, DCPPowerModel, PowerModels.build_opf)
bus_arcs = PowerModels.ref(pm, nw_id, :bus_arcs)
# bus_arcs[16] = [(branch_id, f_bus, t_bus), ...]

```
