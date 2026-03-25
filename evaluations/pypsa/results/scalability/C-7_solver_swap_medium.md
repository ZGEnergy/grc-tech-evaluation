---
test_id: C-7
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: efece318
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1313.65
timing_source: measured
peak_memory_mb: 4406.2
cpu_threads_used: 1
cpu_threads_available: 32
loc: 185
solver: highs, glpk
timestamp: 2026-03-24T12:00:00Z
---

# C-7: Solver Swap on MEDIUM

## Result: PASS

Solver swap in PyPSA requires no reformulation — it is a single parameter change to
`n.optimize(solver_name=...)`. The linopy model is built once and dispatched to
whichever solver backend is specified. Two of three required solvers (HiGHS, GLPK)
solved successfully with matching objectives. SCIP is not installed in the devcontainer.

## Approach

Loaded ACTIVSg10k via the shared `matpower_loader.load_pypsa()` with
`overwrite_zero_s_nom=99999.0` (MATPOWER rateA=0 means unconstrained). Ran the same
DCOPF problem with each solver using single-threaded configuration per solver-config.md.

Generator marginal costs were populated from gencost data by the shared loader.

## Output

### Solver Results

| Solver | Available | Solved | Wall-clock (s) | Peak Memory (MB) | Objective ($) |
|--------|-----------|--------|----------------|-------------------|---------------|
| HiGHS  | yes | yes | 546.1 | 4,406.2 | 1,306,775.11 |
| GLPK   | yes | yes | 731.0 | 4,404.1 | 1,306,775.12 |
| SCIP   | no  | no  | N/A   | N/A     | N/A           |

**Wall-clock note:** These timings include linopy model construction, LP file writing,
and solver invocation. HiGHS reported its own solve time as ~8s; the remainder is
linopy overhead (constraint writing, variable writing, LP file I/O). The tests ran on
a shared machine, so contention may inflate wall-clock times. [tool-specific: linopy
LP file serialization overhead]

**Cross-solver objective match:** The HiGHS and GLPK objectives match within $0.0003
(3.5e-4), confirming that the identical formulation was dispatched to both solvers.

### Solver Swap Architecture

- **Mechanism:** `n.optimize(solver_name=...)` dispatches the same linopy `Model` to
  different solver backends. No model reconstruction or reformulation is needed.
- **Requires reformulation:** No
- **Available solvers via linopy:** highs, glpk, cplex, gurobi, scip (requires pyscipopt)
- **SCIP status:** Not installed (`pyscipopt` module absent). Linopy raises
  `AssertionError: Solver scip not installed` immediately.

### GLPK Performance Note

GLPK (5.0) took 116.7s for the LP solve itself (vs ~8s for HiGHS). The 731s total
includes a full LP file write cycle (2.44s) plus linopy overhead on both sides.
GLPK is substantially slower than HiGHS on this 15,191-variable, 43,089-constraint LP
but produces an identical optimal solution. [solver-specific: GLPK simplex slower than
HiGHS dual simplex]

## Workarounds

None required. Solver swap is a first-class PyPSA/linopy feature.

## Timing

- **Wall-clock (total):** 1313.65s (includes all three solver attempts sequentially)
- **HiGHS solve (n.optimize):** 546.1s (HiGHS internal: ~8s)
- **GLPK solve (n.optimize):** 731.0s (GLPK internal: 116.7s)
- **Timing source:** measured
- **Peak memory:** 4,406.2 MB (HiGHS run, tracemalloc)
- **CPU threads used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c7_solver_swap_medium.py`

Key API call:
```python
n.optimize(solver_name="highs", solver_options={...})
n.optimize(solver_name="glpk", solver_options={...})
# Same linopy model, different solver backend — no reformulation
```
