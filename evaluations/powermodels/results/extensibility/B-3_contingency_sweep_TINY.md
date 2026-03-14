---
test_id: B-3
tool: powermodels
dimension: extensibility
network: TINY
protocol_version: v10
skill_version: v1
test_hash: eceb2bf4
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.098
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 320
solver: null
timestamp: 2026-03-14T00:47:28Z
---

# B-3: N-M Contingency Sweep (TINY)

## Result: PASS

## Approach

N-M contingency sweep with escalating order (x=3, m=3) and graph-distance pruning. This is a new test in v10 replacing the v9 N-1 contingency loop.

**Enumeration strategy:**
1. Order 1 (N-1): all 46 single-branch outages
2. Order 2 (N-2): pairs of branches within graph distance 2 of each other
3. Order 3 (N-3): triples of branches where all three are within distance 2 of each other

**Graph-distance scoping** (reuses B-2 adjacency pattern): BFS from each branch's endpoint buses to find nearby branches within the specified distance. Branches outside the distance threshold are pruned from consideration as co-outages, dramatically reducing the combinatorial space.

**Per-contingency workflow:**
1. `deepcopy(data)` — clone the parsed data dict (no re-parse from file)
2. Set `d["branch"][br_id]["br_status"] = 0` for each outaged branch
3. `calc_connected_components(d)` — check for islands
4. If connected: `compute_dc_pf(d)` + `update_data!` + `calc_branch_flow_dc(d)` for max loading

No model reconstruction per contingency case. All contingencies use the same `deepcopy` + mutation pattern.

## Output

| Metric | Value |
|--------|-------|
| Total evaluated | 595 |
| Order 1 (N-1) | 46 |
| Order 2 (N-2) | 206 |
| Order 3 (N-3) | 343 |
| Pruned (distance-based) | 4,657 |
| Converged | 223 |
| Islands (connectivity loss) | 372 |
| Overloaded (>100%) | 124 |
| Loop wall-clock | 0.68 s |
| Avg time per contingency | 1.14 ms |

### Top 5 worst contingencies (by max branch loading):

| Order | Outages | Max Loading % |
|-------|---------|--------------|
| 3 | [10, 12, 16] | 218.27% |
| 2 | [10, 12] | 213.88% |
| 3 | [10, 12, 18] | 213.88% |
| 3 | [10, 12, 21] | 213.88% |
| 3 | [8, 10, 12] | 211.08% |

Branches 10 and 12 are a critical corridor: their simultaneous outage causes severe overloading regardless of the third outaged branch. Graph-distance pruning eliminated 4,657 out of 5,252 candidate contingencies (88.7% reduction), keeping only topologically proximate combinations.

372 of 595 contingencies cause islands — expected for case39's tree-like topology where removing 2-3 nearby branches easily disconnects radial sub-networks.

## Workarounds

None required. The `deepcopy()` + `br_status=0` pattern is idiomatic Julia and uses documented PowerModels API. Graph-distance scoping uses the same adjacency construction from B-2 (`data["branch"]` f_bus/t_bus traversal). `calc_connected_components()` is a public PowerModels function.

## Timing

- **Wall-clock:** 1.098 s total (parse + 595 contingencies)
- **Timing source:** measured
- **Peak memory:** not measured
- **Loop time:** 0.68 s for 595 contingencies
- **Per-contingency average:** 1.14 ms
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/extensibility/test_b3_contingency_sweep_tiny.jl`

Core pattern:

```julia
# Helper: solve DCPF and compute max branch loading
function solve_and_max_loading(d::Dict)
    pf_result = PowerModels.compute_dc_pf(d)
    PowerModels.update_data!(d, pf_result["solution"])
    flow_dict = PowerModels.calc_branch_flow_dc(d)
    # ... compute max loading from flow_dict
end

# N-M loop with pruning
for br1 in branch_ids
    nearby = branches_within_distance(br1, graph_distance_prune)
    for br2 in branch_ids[i+1:end]
        !(br2 in nearby) && continue  # prune
        d = deepcopy(data)
        d["branch"][string(br1)]["br_status"] = 0
        d["branch"][string(br2)]["br_status"] = 0
        # ... solve and collect results
    end
end
```
