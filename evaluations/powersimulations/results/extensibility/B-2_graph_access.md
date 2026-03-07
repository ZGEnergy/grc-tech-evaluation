---
test_id: B-2
tool: powersimulations
dimension: extensibility
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 10.85
peak_memory_mb: null
loc: 190
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# B-2: Network Graph Access (BFS from bus to depth 3)

## Result: QUALIFIED PASS

## Approach

PSI has **no native Graphs.jl integration**. Neither PowerSimulations.jl,
PowerSystems.jl, PowerNetworkMatrices.jl, nor InfrastructureSystems.jl depend on
Graphs.jl. Network topology is represented via component collections and
incidence/PTDF matrices.

The test builds an adjacency list manually from PowerSystems.jl's bus/branch
component iterators and performs BFS:

1. Iterate `get_components(ACBus, sys)` to get all 39 buses.
2. Iterate `get_components(Branch, sys)` to get all 46 branches.
3. For each branch, extract from/to bus numbers via `get_arc()`, `get_from()`, `get_to()`.
4. Build adjacency dict: `bus_number -> Set{(neighbor_number, branch_name)}`.
5. BFS from bus 16 to depth 3.

## Output

**BFS from bus 16, depth 3:**

| Depth | Buses | Count |
|-------|-------|-------|
| 0 | 16 | 1 |
| 1 | 15, 17, 19, 21, 24 | 5 |
| 2 | 14, 18, 20, 22, 23, 27, 33 | 7 |
| 3 | 3, 4, 13, 26, 34, 35, 36 | 7 |

**Subgraph totals:** 20 buses, 20 branches within depth-3 neighborhood.

**Timing:**
- Adjacency build: 0.083s (includes JIT overhead)
- BFS execution: 0.00004s

**Connectivity validation:** All buses at depth d are reachable from at least one bus
at depth d-1. PASS.

## API Used

```julia
get_components(ACBus, sys)        # iterate buses
get_components(Branch, sys)       # iterate all branch types
get_number(bus)                   # bus number
get_arc(branch)                   # arc connecting from/to buses
get_from(arc) / get_to(arc)       # terminal buses
get_name(branch)                  # branch identifier
```

## Qualification Reason

No native graph primitives or Graphs.jl export. Manual adjacency construction
is clean (~32 LOC for adjacency + BFS) and uses documented PowerSystems.jl API,
but is not provided out of the box. Users must implement their own graph algorithms
or convert to Graphs.jl manually.

The PowerSystems data model provides excellent component access for building a graph,
but there is no utility function like `to_graph(sys)` or `build_adjacency(sys)`.

## Workarounds

- **What:** Manual adjacency list construction from bus/branch component iterators.
- **Why:** No Graphs.jl integration exists in the Sienna ecosystem.
- **Durability:** stable -- uses public PowerSystems.jl API (get_components, get_arc, etc.).
- **LOC overhead:** ~32 lines for adjacency build + BFS.

## Timing

- **Wall-clock (total):** 10.85s (includes JIT for PowerSystems)
- **Adjacency build:** 0.083s
- **BFS:** 0.00004s
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/powersimulations/tests/extensibility/test_b2_graph_access.jl`
