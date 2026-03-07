---
test_id: A-7
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 23.02
peak_memory_mb: null
loc: 217
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# A-7: N-M contingency sweep with graph-distance scoping and pruning

## Result: PASS

## Approach

Parameters: m=3 (up to 3 simultaneous outages), x=3 (graph distance scoping).

1. Loaded IEEE 39-bus network and built a NetworkX graph via `pandapower.topology.create_nxgraph()`.
2. Computed all-pairs shortest path lengths with cutoff=3 using `nx.all_pairs_shortest_path_length()`.
3. Enumerated all combinations of 1, 2, and 3 branch outages; pruned to keep only those where all branches are pairwise within graph distance 3.
4. Evaluated each contingency by toggling `in_service` flags in-place on `net.line` / `net.trafo` DataFrames. No model reconstruction per case.
5. Solved DCPF for each case and recorded load loss.

## Output

| Metric | Value |
|--------|-------|
| Total branches | 46 (35 lines + 11 trafos) |
| Total possible cases (N-1 + N-2 + N-3) | 16,261 |
| Pruned cases (within distance 3) | 3,684 |
| Pruning ratio | 77.3% |
| Cases evaluated | 3,684 |
| Cases with load loss > 0.01 MW | 1,171 |
| Cases non-converged | 0 |
| Max load loss | 6,245 MW (near-total, trafo 1 outage in combo) |
| Per-case avg time | 0.006 s |

Cases by order:

| Order | Count |
|-------|-------|
| N-1 | 46 |
| N-2 | 535 |
| N-3 | 3,103 |

The graph-distance pruning eliminated 77.3% of possible combinations, reducing evaluation from 16,261 to 3,684 cases.

## Workarounds

None required. pandapower's API natively supports:
- NetworkX graph creation via `create_nxgraph()`
- In-place branch switching via `net.line.at[idx, "in_service"] = False`
- Re-solving without model reconstruction

## Timing

- **Wall-clock:** 23.02 s (3,684 DCPF solves)
- **Per-case average:** 0.006 s
- **Peak memory:** not measured
- **CPU cores used:** 1 (sequential evaluation)

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a7_contingency_sweep.py`
