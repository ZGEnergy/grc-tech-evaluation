---
test_id: A-7
tool: gridcal
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 297.6
peak_memory_mb: null
loc: 85
solver: null
timestamp: 2026-03-06T03:30:00Z
---

# A-7: N-M Contingency Sweep (MEDIUM)

## Result: QUALIFIED PASS

## Approach

Same manual loop approach as TINY but on ACTIVSg 10k (10000 buses, 12706 branches).
Parameters: x=5 (graph distance), m=4 (max simultaneous outages).

Selected center bus 1385 ("PORTLAND 33 2", degree=20). BFS to depth 5 found 67 buses
and 90 candidate branches. Capped candidates at 12 to keep combinatorial explosion
manageable (793 total cases across orders 1-4).

Used `grid.build_graph()` → NetworkX BFS, then `branch.active` toggle + `vge.power_flow()` loop.

## Output

| Order | Cases | Max Load Loss (MW) | Non-converged |
|-------|-------|---------------------|---------------|
| 1 | 12 | 26.84 | 0 |
| 2 | 66 | 30.50 | 0 |
| 3 | 220 | 34.77 | 0 |
| 4 | 495 | 38.50 | 0 |
| **Total** | **793** | | |

- Network load time: 12.24s
- Base total load: 298,514.8 MW
- Pruning ratio: 0.0 (all order-1 contingencies produced measurable impact)
- All 793 cases converged

## Workarounds

- **What:** Manual branch.active toggle loop with NetworkX for graph-distance scoping
- **Why:** ContingencyAnalysisDriver supports N-1 only, not N-M with custom pruning
- **Durability:** stable — uses documented public API
- **Grade impact:** Minor — the workaround is clean and performant

## Timing

- **Wall-clock:** 297.6s (793 contingency cases on 10k-bus network)
- **Per-contingency average:** 375ms
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a7_contingency_sweep_medium.py`
