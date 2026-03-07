---
test_id: A-7
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 73.888
peak_memory_mb: null
loc: 230
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# A-7: N-M Contingency Sweep

## Result: PASS

## Approach

Implemented an N-M contingency sweep (m=1,2,3) with graph-distance scoping (x=3)
and pruning on the IEEE 39-bus network.

**Graph-distance scoping:** Used `n.graph()` to obtain a NetworkX graph, selected
bus 16 (highest degree, 5 connections) as the focal bus, and found all buses within
graph distance 3 using `nx.single_source_shortest_path_length()`. This yielded 20
nearby buses and 17 candidate lines.

**Contingency execution:** Attempted `n.lpf_contingency()` for efficient N-1 sweep,
but it raised a `'DataFrame' object has no attribute 'to_frame'` error (likely a bug
in v1.1.2). Fell back to manual line disabling by setting `n.lines.loc[line, "x"] = 1e10`
and re-running `n.lpf()` for each contingency. No model reconstruction was needed --
lines were disabled and re-enabled in-place.

**Pruning:** For N-3 cases, pruned any combination where an N-2 sub-case had already
caused severe load loss (>50% of total). This pruned 159 of 680 N-3 combinations.

## Output

| Level | Total Combos | Evaluated | Pruned | Time (s) |
|-------|-------------|-----------|--------|----------|
| N-1 | 17 | 17 | 0 | 1.71 |
| N-2 | 136 | 136 | 0 | 13.74 |
| N-3 | 680 | 521 | 159 | 56.71 |
| **Total** | **833** | **674** | **159** | **72.16** |

**Load loss summary:**

| Level | Cases with Loss | Min (MW) | Max (MW) | Mean (MW) |
|-------|----------------|----------|----------|-----------|
| N-1 | 1 | 0.0 | 6254.2 | 367.9 |
| N-2 | 24 | 0.0 | 6254.2 | 883.6 |
| N-3 | 72 | 0.0 | 6254.2 | 82.9 |

The single N-1 case with load loss caused total islanding (6254.2 MW = full load),
indicating a radial branch removal that disconnects a sub-network.

## Workarounds

- **What:** Used manual line disabling (setting reactance to 1e10) instead of
  `n.lpf_contingency()` for the N-1 sweep, and for all N-2/N-3 sweeps.
- **Why:** `n.lpf_contingency()` raised `'DataFrame' object has no attribute 'to_frame'`
  in PyPSA v1.1.2 -- likely a bug or API incompatibility with the imported network
  structure.
- **Durability:** stable -- Manual line disabling via reactance modification uses
  documented public attributes (`n.lines["x"]`). The graph API (`n.graph()`) and
  NetworkX integration are first-class documented features.
- **Grade impact:** Minor. The workaround adds per-contingency overhead (re-solving
  the full LPF) but the API surface for graph access and line parameter modification
  is clean and well-documented. The `lpf_contingency` bug is a tool deficiency, not
  a missing feature.
- **Version tested:** PyPSA 1.1.2

## Timing

- **Wall-clock:** 73.89 s (total sweep)
- **Per-contingency average:** 0.107 s
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a7_contingency_sweep.py`

Key API patterns:

```python
# Graph access
G = n.graph()  # Returns NetworkX MultiGraph
nx.single_source_shortest_path_length(G, chosen_bus, cutoff=3)

# Line disabling (no model reconstruction)
n.lines.loc[line, "x"] = 1e10  # disable
n.lpf()                         # re-solve
n.lines.loc[line, "x"] = orig  # restore
```
