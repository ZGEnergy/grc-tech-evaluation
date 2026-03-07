# Observation: api-friction -- A-7 contingency_sweep

**Test:** A-7 (N-M Contingency Sweep)
**Dimension:** expressiveness
**Tool:** PowerModels.jl v0.21.5

## Finding

PowerModels has no native graph library or adjacency structure. The `ref` dict provides `:arcs_from`, `:arcs_to`, and `:bus_arcs` mappings, but these are only available after model instantiation (not from the parsed data dict). To perform BFS for graph-distance scoping, the user must manually build an adjacency list from branch `f_bus`/`t_bus` pairs (~20 lines of code).

Additionally, `compute_dc_pf()` throws an unhandled `LinearAlgebra.SingularException` when a contingency creates network islands (singular admittance matrix). The user must pre-check connectivity via `calc_connected_components()` before calling `compute_dc_pf()`, or wrap calls in try-catch. This is an API friction point -- a power flow function should handle islanded networks gracefully rather than throwing a linear algebra error.

The `deepcopy(data)` pattern for each contingency is memory-intensive. PowerModels provides no lightweight "toggle branch" mechanism for repeated contingency analysis (e.g., a branch status stack or undo capability).

## Impact

Medium. The workarounds are straightforward but add ~40 lines of boilerplate code that other tools handle natively. The SingularException is particularly surprising for users unfamiliar with the internal matrix solver.
