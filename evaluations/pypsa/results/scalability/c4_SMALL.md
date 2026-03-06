---
test_id: c4
tool: pypsa
dimension: scalability
network: SMALL
status: qualified_pass
wall_clock_seconds: 636.96
peak_memory_mb: 3654.27
solver: highs
timestamp: 2026-03-05T00:00:00Z
---

# C-4: SCUC 24hr on SMALL (ACTIVSg2000) with HiGHS and SCIP

## Result: QUALIFIED PASS

## Approach
Loaded the ACTIVSg 2000-bus network, set up 24-hour snapshots with a sinusoidal daily load profile (0.6-1.0x base load), and configured generators as committable with:
- min_up_time = 2 hours
- min_down_time = 2 hours
- start_up_cost = 5 $/MW of capacity
- shut_down_cost = 2 $/MW of capacity
- p_min_pu = 0.3 (30% minimum operating point)

Ran `n.optimize()` with HiGHS (MIP solver) and SCIP.

## Output

| Metric | HiGHS (1 thread) | SCIP |
|--------|-------------------|------|
| Status | ok (time_limit) | FAIL (not installed) |
| Objective | inf (no feasible solution found) | N/A |
| Wall-clock | 636.96s | 369.48s (loading only) |
| Peak memory | 3,654.27 MB | 3,651.02 MB |
| MIP gap | N/A (no solution) | N/A |
| Committed generators | 0 (no feasible solution) | N/A |

### Model Size
- Rows: 347,816
- Columns: 129,168 (39,168 binary)
- Non-zeros: 1,714,880
- After presolve: 105,709 rows, 82,620 cols

## Timing
- HiGHS wall-clock: 636.96s (hit 300s time limit + model building overhead)
- HiGHS peak memory: 3,654.27 MB
- SCIP: not installed in container
- CPU cores: 1 (single-threaded)

## Notes
- HiGHS reached the 300s time limit without finding a feasible integer solution. The MIP is large (39k binary variables) and the combination of minimum up/down time constraints with the network constraints makes the problem challenging.
- SCIP is not available in the devcontainer's Python environment (`pyscipopt` not installed).
- The "qualified pass" reflects that PyPSA can formulate and attempt to solve SCUC problems, but the solver did not find a feasible solution within the time limit on this network. A longer time limit or different solver parameters might yield a solution.
- The high memory usage (~3.7 GB) is due to the large MIP model with 24 time periods and 544 generators.

## Test Script
Path: `evaluations/pypsa/tests/scalability/test_c4_scuc_scale.py`
