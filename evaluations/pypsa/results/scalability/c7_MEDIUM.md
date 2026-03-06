---
test_id: c7
tool: pypsa
dimension: scalability
network: MEDIUM
status: qualified_pass
wall_clock_seconds: 8.93
peak_memory_mb: 2880.09
solver: highs
timestamp: 2026-03-05T00:00:00Z
---

# C-7: Solver Swap on MEDIUM (ACTIVSg 10k)

## Result: QUALIFIED PASS

## Approach
Tested DCOPF solver swap by attempting `n.optimize()` with three open-source solvers: HiGHS, GLPK, and SCIP.

PyPSA uses linopy as its optimization backend. Solver swap is performed by changing the `solver_name` parameter only -- no reformulation is required. The API is:

```python
n.optimize(solver_name="highs", solver_options={...})
n.optimize(solver_name="glpk", solver_options={...})
n.optimize(solver_name="scip", solver_options={...})
```

## Output

| Solver | Status | Objective | Wall-clock | Notes |
|--------|--------|-----------|------------|-------|
| HiGHS | Optimal | $1,254,138.73 | 8.93s (solver), ~500s (total w/ model build) | Only available solver |
| GLPK | Not installed | N/A | 31.69s (model build only) | `Solver glpk not installed` |
| SCIP | Not installed | N/A | 65.24s (model build only) | `Solver scip not installed` |

## Swap Mechanism
- **Reformulation required**: No
- **API change**: Only `solver_name` parameter
- **Solver options**: Solver-specific keys (e.g., `time_limit` for HiGHS, `tm_lim` for GLPK, `limits/time` for SCIP) but the model formulation is identical
- **Available solvers**: `linopy.available_solvers` reports `['highs']` in this environment

## Timing
- HiGHS solver time: 8.93s (HiGHS internal), total with model build: ~500s
- GLPK model build time: 31.69s (solver not installed)
- SCIP model build time: 65.24s (solver not installed)
- HiGHS peak memory: 2,880.09 MB
- CPU cores: 1 (single-threaded)

## Notes
- PyPSA/linopy provides clean solver swap with zero reformulation overhead -- just change `solver_name`. This is a strong design feature.
- Only HiGHS is installed in the devcontainer. GLPK and SCIP would need to be installed (via `uv add pyglpk`/`uv add pyscipopt`) for cross-solver benchmarking.
- The "qualified pass" reflects that the swap mechanism works correctly (parameter-only change, no reformulation) but actual cross-solver comparison could not be performed due to missing installations.

## Test Script
Path: `evaluations/pypsa/tests/scalability/test_c7_solver_swap.py`
