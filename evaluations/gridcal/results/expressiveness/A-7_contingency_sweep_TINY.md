---
test_id: A-7
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 0.730
peak_memory_mb: null
loc: 85
solver: null
timestamp: 2026-03-06T01:00:00Z
---

# A-7: N-M Contingency Sweep

## Result: QUALIFIED PASS

## Approach

Used `grid.build_graph()` to get a NetworkX `MultiDiGraph`, then `nx.single_source_shortest_path_length()` for BFS to depth 3 from bus 0. Found 10 buses and 9 candidate branches within the subgraph.

Ran escalating-order contingency sweep (m=1,2,3) by toggling `branch.active = False`, solving DCPF via `vge.power_flow()`, and re-enabling. No full model reconstruction needed — branches are toggled in-place.

GridCal has a `ContingencyAnalysisDriver` but it handles pre-defined N-1 contingency groups only, not arbitrary N-M with custom pruning logic. The manual loop approach was necessary.

## Output

| Order | Cases | Max Load Loss (MW) | Non-converged |
|-------|-------|---------------------|---------------|
| 1 | 9 | 108.88 | 0 |
| 2 | 36 | 125.50 | 0 |
| 3 | 84 | 390.09 | 0 |
| **Total** | **129** | | |

- Pruning ratio: 0.0 (all order-1 contingencies produced measurable load loss)
- Base total load: 5456.7 MW
- All 129 cases converged

## Workarounds

- **What:** Manual branch.active toggle loop with NetworkX for graph distance scoping
- **Why:** ContingencyAnalysisDriver supports N-1 only, not N-M with pruning
- **Durability:** stable — uses documented public API (`branch.active`, `vge.power_flow()`, `grid.build_graph()`)
- **Grade impact:** Minor — the workaround is clean and uses first-class APIs

## Timing

- **Wall-clock:** 0.730s (129 contingency cases)
- **Per-contingency average:** 5.7ms
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a7_contingency_sweep.py`
