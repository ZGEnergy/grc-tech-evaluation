---
test_id: B-3
tool: powermodels
dimension: extensibility
network: TINY
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.327
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 8
solver: null
protocol_version: "v9"
skill_version: v1
test_hash: 3907fb16
timestamp: 2026-03-12T03:38:50Z
---

# B-3: Contingency Loop (TINY)

## Result: PASS

## Approach

Network parsed once from file. For each of 46 N-1 branch outages:
1. `deepcopy(data)` — clone the parsed data dict in memory
2. Set `d["branch"][string(br_id)]["br_status"] = 0`
3. Check connectivity: `PowerModels.calc_connected_components(d)`
4. If connected: `PowerModels.compute_dc_pf(d)` + `calc_branch_flow_dc(d)` for max loading

No re-parse from file in the loop. Clone overhead measured at 0.61 ms vs parse time of 2.82 ms — `deepcopy` is 4.65× faster than re-parsing from file.

## Output

| Metric | Value |
|--------|-------|
| Total contingencies | 46 |
| Converged | 35 |
| Islands (connectivity loss) | 11 |
| Diverged | 0 |
| Loop wall-clock | 0.128 s |
| Avg time per contingency | 2.78 ms |
| Min/Median/Max contingency | 0.57 / 0.81 / 93 ms |
| Parse time (once) | 2.82 ms |
| deepcopy time | 0.61 ms |
| Parse/copy ratio | 4.65× |

### Top 5 most stressed N-1 contingencies (by max branch loading):

| Outage Branch | Max Loading % | Loaded Branch |
|--------------|--------------|---------------|
| 35 | 160.42% | 38 |
| 23 | 133.64% | 13 |
| 28 | 114.75% | 38 |
| 38 | 114.75% | 28 |
| 19 | 113.65% | 13 |

Worst case: outage of branch 35 causes branch 38 to reach 160% loading — significant overload.

11 of 46 contingencies cause islands (connectivity loss), which is expected for a radial-ish network like case39 where some branches are sole connections to radial sub-networks.

## Workarounds

None required. `deepcopy()` is standard Julia. The data dict mutation pattern (`br_status=0`) is documented behavior. `calc_connected_components()` is a public PowerModels API.

## Timing

- **Wall-clock:** 0.327 s total (parse once + 46 contingencies)
- **Timing source:** measured
- **Peak memory:** not measured
- **Loop time:** 0.128 s for 46 contingencies
- **Per-contingency average:** 2.78 ms

## Test Script

**Path:** `evaluations/powermodels/tests/extensibility/test_b3_contingency_loop_tiny.jl`

Core pattern:

```julia

data = PowerModels.parse_file(network_file)  # once
for outage_br_id in branch_ids
    d = deepcopy(data)                        # clone, no re-parse
    d["branch"][string(outage_br_id)]["br_status"] = 0
    pf_result = PowerModels.compute_dc_pf(d)
    # ... collect results
end

```
