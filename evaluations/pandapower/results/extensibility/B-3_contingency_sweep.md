---
test_id: B-3
tool: pandapower
dimension: extensibility
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "49124456"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 22.16
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 258
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# B-3: N-M contingency sweep (x=3, m=3) with pruning

## Result: PASS

## Approach

Performed an N-3 contingency sweep on the IEEE 39-bus network with graph-distance-based pruning, using pandapower's DC power flow, topology module, and NetworkX graph bridge.

**Parameters:**
- x = 3 focal buses (highest-load buses: 38, 19, 7)
- m = 3 simultaneous branch outages
- Graph distance cutoff = 3 hops for pruning

**Workflow:**

1. Loaded network and ran baseline DC power flow via `pp.rundcpp(net)`.
2. Created NetworkX graph via `top.create_nxgraph(net)`.
3. Selected 3 focal buses by highest load (bus 38: 1104 MW, bus 19: 680 MW, bus 7: 522 MW).
4. **Pruning:** For each focal bus, computed all buses within graph distance 3 using `nx.single_source_shortest_path_length()`. Collected all lines with at least one endpoint in the nearby-bus set. This reduced the candidate line set from 35 to 28 (20% reduction).
5. **Enumeration:** Generated all C(28,3) = 3,276 combinations of 3 lines from the pruned set.
6. **Sweep:** For each combination, toggled `net.line.at[idx, 'in_service'] = False`, ran `pp.rundcpp(net, check_connectivity=True)`, detected unsupplied buses via `top.unsupplied_buses(net)`, computed load loss, then restored the lines. No model reconstruction was needed -- just toggling the `in_service` column.

## Output

| Metric | Value |
|--------|-------|
| Total candidate lines after pruning | 28 of 35 |
| Total N-3 combinations | 3,276 |
| Converged cases | 3,276 (100%) |
| Cases with load loss | 924 (28.2%) |
| Max load loss | 6,245 MW (99.9% of total load) |
| Mean load loss | 236.7 MW |
| Sweep time | 20.87 s |
| Time per contingency | 6.4 ms |

**Top 5 worst contingencies:**

| Rank | Lines Removed | Load Loss (MW) | Unsupplied Buses |
|------|---------------|----------------|------------------|
| 1 | 8, 10, 11 | 6,245 | 37 |
| 2 | 8, 10, 17 | 6,237 | 32 |
| 3 | 8, 11, 12 | 6,011 | 36 |
| 4 | 8, 12, 17 | 6,003 | 31 |
| 5 | 6, 11, 13 | 5,489 | 34 |

Line 8 appears in the top 4 worst contingencies, indicating it is a critical transmission corridor.

**Key design characteristics:**

- **No model reconstruction per contingency:** The pandapower network object is reused across all contingency cases. Only `net.line["in_service"]` is toggled. pandapower rebuilds the internal PYPOWER bus-branch model (`net._ppc`) from DataFrames on each `rundcpp()` call, but the pandas DataFrames themselves persist.
- **Pruning via graph bridge:** The `create_nxgraph()` + NetworkX `single_source_shortest_path_length()` combination provides clean, documented graph-distance scoping.
- **Load loss detection:** `pandapower.topology.unsupplied_buses(net)` identifies buses electrically disconnected from all slack/ext_grid buses after branch outages.
- **N-M not natively supported:** pandapower has a built-in `run_contingency()` for N-1 analysis, but it does not natively support N-M (simultaneous multi-branch outage) sweeps. The manual loop approach using in-service toggling is the idiomatic pandapower pattern for N-M analysis.

## Workarounds

None required. The entire workflow uses documented public APIs:
- `pp.rundcpp()` for DC power flow
- `top.create_nxgraph()` for graph creation
- `nx.single_source_shortest_path_length()` for graph-distance pruning
- `top.unsupplied_buses()` for load loss detection
- `net.line.at[idx, 'in_service']` for in-place branch toggling

## Timing

- **Wall-clock:** 22.16 s (total)
- **Timing source:** measured
- **Sweep time:** 20.87 s (3,276 contingency cases)
- **Time per contingency:** 6.4 ms
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/extensibility/test_b3_contingency_sweep.py`
