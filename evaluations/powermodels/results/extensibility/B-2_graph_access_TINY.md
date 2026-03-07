---
test_id: B-2
tool: powermodels
dimension: extensibility
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 0.161
peak_memory_mb: null
loc: 172
solver: null
timestamp: "2026-03-06T00:00:00Z"
---

# B-2: BFS graph traversal to depth 3 from a chosen bus

## Result: QUALIFIED PASS

## Approach

PowerModels has no native graph API and no Graphs.jl integration. The adjacency structure must be built manually from the branch data dictionary:

1. Iterated over `data["branch"]` entries, extracting `f_bus` and `t_bus` for each branch.
2. Built a manual adjacency list: `Dict{Int, Vector{Tuple{Int, Int}}}` mapping each bus to its neighbors and connecting branch IDs.
3. Ran standard BFS from seed bus 16 to depth 3.
4. Collected all buses within the BFS scope and all branches with both endpoints in the scope.

This required ~15 lines of adjacency construction code and ~15 lines of BFS logic -- straightforward Julia but entirely manual.

## Output

- **Seed bus:** 16 (degree = 5, well-connected interior bus)
- **BFS max depth:** 3
- **Subgraph buses (20):** 3, 4, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 26, 27, 33, 34, 35, 36
  - Depth 0: [16]
  - Depth 1: [15, 17, 19, 21, 24]
  - Depth 2: [14, 18, 20, 22, 23, 27, 33]
  - Depth 3: [3, 4, 13, 26, 34, 35, 36]
- **Subgraph branches (21):** 6, 7, 9, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 42
- **Coverage:** 51.3% of buses, 45.7% of branches (depth-3 subgraph covers roughly half the 39-bus network)

## Workarounds

PowerModels has NO native graph API or Graphs.jl integration. Adjacency must be built manually from branch `f_bus`/`t_bus` data (~15 lines). BFS is a standard algorithm easily implemented in Julia. `PowerModelsAnalytics.jl` would provide a Graphs.jl bridge but is a separate optional package not installed.

This is a stable workaround -- the `data["branch"]` dict structure is documented and stable. The manual code is simple and reliable.

## Timing

- Wall-clock: 0.161s (dominated by parse_file; BFS itself is negligible)
- Peak memory: not measured

## Test Script

Path: `evaluations/powermodels/tests/extensibility/test_b2_graph_access.jl`
