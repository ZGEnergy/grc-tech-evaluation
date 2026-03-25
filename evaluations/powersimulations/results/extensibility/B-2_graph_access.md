---
test_id: B-2
tool: powersimulations
dimension: extensibility
network: TINY
protocol_version: v11
skill_version: v2
test_hash: "5068a626"
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.16
timing_source: measured
peak_memory_mb: 695.5
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 205
solver: null
cpu_threads_used: null
cpu_threads_available: null
ingestion_path: null
sced_mode: null
test_category: null
timestamp: 2026-03-24T00:00:00Z
---

# B-2: Graph Access (BFS to depth 3 from chosen bus)

## Result: QUALIFIED PASS

## Approach

Used `PowerNetworkMatrices.jl`'s `AdjacencyMatrix(sys)` to obtain the network topology
as a matrix indexed by integer bus numbers. Built an adjacency dictionary by iterating
matrix entries, then implemented BFS manually. Also obtained `IncidenceMatrix(sys)` for
documentation.

BFS started from bus 16 (well-connected hub in IEEE 39-bus) to depth 3.

No solver required -- this is a pure topology test.

## Output

### Adjacency Matrix

| Property | Value |
|----------|-------|
| Type | `AdjacencyMatrix{Tuple{Vector{Int64}, ...}}` |
| Buses | 39 |
| Edges | 46 |
| Axes indexed by | Integer bus numbers |

### Incidence Matrix

| Property | Value |
|----------|-------|
| Type | `IncidenceMatrix{Tuple{Vector{String}, Vector{Int64}}, ...}` |
| Shape | 46 branches x 39 buses |
| Row index | String branch names |
| Column index | Integer bus numbers |

### BFS from bus 16, depth 3

| Depth | Count | Buses |
|-------|-------|-------|
| 0 | 1 | [16] |
| 1 | 5 | [15, 17, 19, 21, 24] |
| 2 | 7 | [14, 18, 20, 22, 23, 27, 33] |
| 3 | 7 | [3, 4, 13, 26, 34, 35, 36] |

**Total reachable in 3 hops:** 20 of 39 buses (51%)

### PowerSystems topology inventory

| Component type | Count |
|----------------|-------|
| Line | 34 |
| Transformer2W | 1 |
| TapTransformer | 11 |
| **Total branches** | **46** |

## Workarounds

- **What:** Manual BFS implementation over the adjacency matrix. PowerNetworkMatrices.jl
  provides `AdjacencyMatrix` and `IncidenceMatrix` but no graph traversal algorithms
  (no BFS, DFS, shortest path, connected components). [tool-specific]
- **Why:** The PSI ecosystem has no Graphs.jl dependency. The adjacency matrix is a
  numerical structure (KeyedArray-like), not a graph object.
- **Durability:** stable -- `AdjacencyMatrix` and `IncidenceMatrix` are documented public
  API in PowerNetworkMatrices.jl. Constructing a `Graphs.jl SimpleGraph` from the
  adjacency matrix would be straightforward (~5 lines) but requires adding Graphs.jl as
  an external dependency.
- **Grade impact:** Minor. The topology data is cleanly accessible; only the traversal
  primitives require user code.

## Timing

- **Wall-clock:** 0.16s (second invocation, post-JIT)
- **Timing source:** measured
- **Peak memory:** 696 MB

## Test Script

**Path:** `evaluations/powersimulations/tests/extensibility/test_b2_graph_access.jl`

Key API pattern for topology access:

```julia
using PowerNetworkMatrices

adj_matrix = AdjacencyMatrix(sys)       # indexed by bus number
inc_matrix = IncidenceMatrix(sys)       # rows=branches (String), cols=buses (Int)

# Read adjacency: nonzero entry means connected
bus_ids = collect(axes(adj_matrix)[1])
for bus2 in bus_ids
    if abs(adj_matrix[bus1, bus2]) > 1e-10
        # bus1 and bus2 are connected
    end
end
```
