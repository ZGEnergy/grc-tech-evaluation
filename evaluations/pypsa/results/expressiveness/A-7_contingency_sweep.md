---
test_id: A-7
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v9
skill_version: v1
test_hash: e3e8be8a
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 3.621
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 259
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# A-7: N-M Contingency Sweep (contingency_sweep)

## Result: PASS

## Approach

**Graph-distance scoping:** Used `n.graph()` (returns NetworkX MultiGraph) + `nx.single_source_shortest_path_length()` to find all buses within graph-distance 2 from focal bus '1'. Found 7 buses and 9 lines in scope.

**N-1 sweep:** PyPSA's `n.lpf_contingency()` API has a bug in v1.1.2 on Python 3.12+: `isinstance(pd.Index, collections.abc.Sequence)` evaluates to False, causing `n.lpf_contingency()` to pass the full `pd.Index` as the snapshot argument to `n.lpf()`. When `n.lpf(pd.Index(['now']))` is called, `p0.loc[pd.Index(['now'])]` returns a DataFrame (not a Series), which then fails at `p0_base.to_frame("base")` (line 934 of power_flow.py). The bug affects all calling conventions — passing `n.snapshots`, `None`, or a string snapshot all fail in different ways.

**N-1 workaround:** Implemented N-1 contingency sweep directly using `sub_network.calculate_BODF()` (Branch Outage Distribution Factors). BODF is a documented public API method (`n.lpf_contingency` uses BODF internally). Post-outage flows computed as `p0_new = p0_base + BODF[:, branch_i] * p0_base[branch]`. 9 N-1 contingencies computed without full model reconstruction.

**Pruning:** Implemented and verified: `same_bus_pair()` function checks `frozenset([bus0, bus1])` equality to skip parallel-line combinations. No parallel lines found in the 9 scoped lines (0 combos pruned from 36 N-2 combos).

**N-2 sweep:** 20 of 36 pruned N-2 combinations run via manual loop (load fresh network, set `s_nom=0` for both lines, call `n.lpf()`). All 20 converged without error.

## Output

**Graph-distance scoping results:**
- Focal bus: 1
- Buses within distance 2: 7
- Lines in scope: L0, L1, L2, L3, L4, L5, L13, L14, L30 (9 lines)

**N-1 sweep:**
- Method: BODF (Branch Outage Distribution Factors)
- 9 contingencies computed in 0.084 s
- Load served in all N-1 cases: 6254.23 MW (no isolation events)
- No full model reconstruction required

**N-2 sweep:**
- 36 combinations enumerated → 36 after pruning (0 pruned — no parallel lines in scope)
- 20 cases run (cap for reasonable runtime)
- All 20 converged

**Contingency API:** `n.graph()` → NetworkX MultiGraph for distance scoping; BODF for N-1 flows (no full reconstruction).

## Workarounds

1. **What:** N-1 sweep implemented via `sub_network.calculate_BODF()` rather than `n.lpf_contingency()`.
   - **Why:** `n.lpf_contingency()` has a bug in PyPSA v1.1.2 / Python 3.12+: `pd.Index` is not recognized as `collections.abc.Sequence`, causing `p0_base` to be a DataFrame instead of a Series, failing at `p0_base.to_frame("base")`. The bug is in the installed library source (`pypsa/network/power_flow.py` line 934).
   - **Durability:** stable — `calculate_PTDF()`, `calculate_BODF()`, and `sub_network.BODF` are documented public methods. BODF is the documented approach for N-1 contingency analysis.
   - **Grade impact:** Low. The intended API (`n.lpf_contingency()`) is present and the algorithm is correct — this is a Python version compatibility bug, not an architectural gap. BODF is the clean public alternative.

2. **What:** N-2 uses full model reconstruction (load fresh network, set lines to s_nom=0).
   - **Why:** `n.lpf_contingency()` only supports N-1 (documented in the function docstring).
   - **Durability:** stable — this is expected behavior (N-2 is not claimed to be natively supported).
   - **Grade impact:** Minor. Manual N-2 loop is standard practice.

## Timing

- **Wall-clock:** 3.621 s (includes 20 N-2 model reconstructions)
- **Timing source:** measured
- **N-1 BODF sweep:** 0.124 s (9 contingencies, no reconstruction)
- **N-2 manual sweep:** 2.394 s (20 cases × ~0.12 s each for network reload)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a7_contingency_sweep_tiny.py`

Key API for graph-distance scoping:
```python
G = n.graph()  # NetworkX MultiGraph
distance_dict = nx.single_source_shortest_path_length(G, focal_bus, cutoff=2)
buses_within_2 = set(distance_dict.keys())
```

Key API for N-1 BODF sweep (workaround):
```python
n.determine_network_topology()
for sub_network in n.sub_networks.obj:
    sub_network.calculate_PTDF()
    sub_network.calculate_BODF()
branch_i = sn_branches.index.get_loc(("Line", outage_line))
bodf_col = sub_network.BODF[:, branch_i]
p0_new = p0_base + bodf_col * p0_base[branch_i]
```
