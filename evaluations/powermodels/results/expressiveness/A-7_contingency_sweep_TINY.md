---
test_id: A-7
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v9"
skill_version: v1
test_hash: fc535c5d
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 1.712
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 180
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# A-7: N-M Contingency Sweep

## Result: QUALIFIED PASS

## Approach

PowerModels.jl has no built-in N-x contingency solver. The sweep is implemented using the documented `deepcopy` + in-place dict modification + `compute_dc_pf` pattern. This avoids full model reconstruction from file per contingency.

### Key pattern:

```julia

# Load once
base_data = PowerModels.parse_file(network_file)

# Per contingency: deepcopy + in-place modification (no file I/O)
cont_data = deepcopy(base_data)
cont_data["branch"][br_id]["br_status"] = 0
result = PowerModels.compute_dc_pf(cont_data)

```

## Graph-distance scoping (pruning demonstration):

Implemented manually using BFS on branch `f_bus`/`t_bus` fields. Identified the 3-hop bus neighborhood around the largest load bus (bus 39, 1104 MW) to create a 10-bus area for targeted N-2 sweeps. No built-in graph library integration exists; the BFS is ~20 lines of user code.

### Contingency enumeration:

- N-1: all 46 single-branch outages
- N-2 (area): all pairs among 9 branches in the 3-hop neighborhood (C(9,2) = 36 cases)
- N-2 (full): all pairs among 46 branches (C(46,2) = 1,035 cases)

#### Load loss computation:

For DC PF contingencies, load loss occurs via islanding. Used BFS connectivity check to detect islanded buses before running DCPF. Load at islanded buses is reported as the load loss. For connected contingencies, DC PF always converges (linear system), so load loss = 0.

## Output

| Metric | Value |
|--------|-------|
| Network | 39 buses, 46 branches, 10 gens |
| Total system load | 6,254.23 MW |
| N-1 cases | 46 |
| N-1 islanding cases | 11 |
| N-2 area cases | 36 (C(9,2)) |
| N-2 area islanding | 14 |
| N-2 full cases | 1,035 (C(46,2)) |
| N-2 full islanding | 473 |
| N-1 sweep time | 0.111s |
| N-2 area sweep time | 0.089s |
| N-2 full sweep time | 0.725s |
| Total sweep time | 0.925s |
| Total wall clock | 1.712s (includes JIT) |

### Worst-case N-1 contingencies by load loss:

| Branch | From→To | Load Loss (MW) | Islanded Buses |
|--------|---------|---------------|----------------|
| 32 | 19→20 | 680.0 | [20, 34] |
| 27 | 16→19 | 680.0 | [20, 19, 33, 34] |
| 14 | 6→31 | 9.2 | [31] |
| 41 | 25→37 | 0.0 | [37] (gen only) |
| 33 | 19→33 | 0.0 | [33] (gen only) |

N-1 cases with no islanding (load loss = 0): 35 / 46

#### Worst-case N-2 contingencies (area, by load loss):

| Branches | Load Loss (MW) | Islanded Buses |
|----------|---------------|----------------|
| 1, 16 | 1,208.1 | [1, 9, 39] |
| 1, 17 | 1,201.6 | [1, 39] |
| 2, 16 | 1,110.5 | [9, 39] |
| 2, 17 | 1,104.0 | [39] |
| 1, 2 | 97.6 | [1] |

#### Graph-distance scoping:

- Largest load bus: 39 (1,104 MW)
- 10 buses within 3 hops of bus 39
- 9 branches with both endpoints in the 3-hop area
- This area accounts for 36/1,035 (3.5%) of N-2 cases but captures the highest load-loss contingencies (bus 39 is isolated in 4 of the top 5 N-2 cases)

## Workarounds

- **What:** No built-in N-x contingency solver. Sweep implemented via `deepcopy` + `br_status=0` modification + `compute_dc_pf` loop.
- **Why:** PowerModels.jl is a single-period steady-state OPF library. There is no dedicated contingency screening or N-1 security check function in the API.
- **Durability:** stable — `deepcopy`, dict key assignment, and `compute_dc_pf` are all documented public API operations. This pattern is widely used in the PowerModels ecosystem and is unlikely to break on version upgrade.
- **Grade impact:** B-level. The pattern is clean and expressive — the contingency loop is fully implementable in ~20 lines. The limitation is that there is no higher-level API that abstracts the loop, but the building blocks are first-class public API.

- **What:** Graph-distance scoping (pruning) requires manual BFS from `f_bus`/`t_bus` fields. No `Graphs.jl` or topology API is integrated.
- **Why:** PowerModels has no native graph representation beyond the data dict. `PowerModelsAnalytics.jl` (not installed) provides a `Graphs.jl` bridge.
- **Durability:** stable — manual BFS from public dict fields is reliable. The `f_bus`/`t_bus` field names are part of the stable data model specification.
- **Grade impact:** Minor. The ~20-line BFS is straightforward to write. Not a blocking limitation.

## Timing

- **Wall-clock:** 1.712s total (first invocation, includes JIT)
- **N-1 sweep (46 cases):** 0.111s (2.4ms/contingency)
- **N-2 area (36 cases):** 0.089s (2.5ms/contingency)
- **N-2 full (1,035 cases):** 0.725s (0.7ms/contingency after JIT warmup)
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a7_contingency_sweep_tiny.jl`

Key patterns:

```julia

# Single parse, then deepcopy per contingency — no file reconstruction
base_data = PowerModels.parse_file(network_file)

# N-1 loop
for br_id in all_branch_ids
    cont_data = deepcopy(base_data)
    cont_data["branch"][br_id]["br_status"] = 0
    # Connectivity check before solving
    connected, islanded = check_connectivity(cont_data)
    if !connected
        # load_loss = sum of load at islanded buses
    else
        result = PowerModels.compute_dc_pf(cont_data)
    end
end

# Graph-distance scoping (BFS, ~20 lines)
function bfs_distance(adj, source)
    # returns Dict: bus_id => distance
end
area_buses = find_buses_within_distance(base_data, center_bus, max_dist=3)
area_branch_ids = find_branches_in_area(base_data, area_buses)

```
