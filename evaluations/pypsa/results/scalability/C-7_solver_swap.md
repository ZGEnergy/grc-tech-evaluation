---
test_id: C-7
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: "v9"
skill_version: v1
test_hash: 1449cf75
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 2645.2
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: highs
timestamp: 2026-03-11T00:00:00Z
---

# C-7: Solver Swap

## Result: PASS

## Approach

Tested PyPSA's solver-swap mechanism on the C-3 DC OPF setup (ACTIVSg10k, same LP formulation).
Key architectural question: does swapping solvers require reformulation or just a parameter change?

Architecture: PyPSA uses `linopy` as its optimization layer. The `n.optimize(solver_name=...)` call
dispatches the same linopy model to different solver backends. The solver name is a runtime parameter;
no model reconstruction is needed. The LP formulation is identical regardless of solver.

Available solvers tested: HiGHS (only available solver in devcontainer).
Unavailable solvers documented: GLPK, Ipopt, SCIP, CPLEX, Gurobi — all not installed.

## Output

### HiGHS (available)

| Metric | Value |
|--------|-------|
| Solver | HiGHS 1.13.1 |
| LP formulation | 43,089 rows, 15,191 cols, 274,129 nonzeros |
| **HiGHS solve time** | **43.3 s** |
| Simplex iterations | 5,166 |
| Status | Optimal |
| Objective | $6,692,949 |

### Solver Architecture

| Property | Value |
|----------|-------|
| Reformulation required for solver swap | **No** |
| Mechanism | Single parameter `solver_name` to `n.optimize()` |
| Linopy model | Solver-agnostic; same LP/MILP exported to any backend |
| Available in devcontainer | HiGHS only |
| Unavailable | GLPK, Ipopt, SCIP, CPLEX, Gurobi |

### Unavailable Solver Handling

| Solver | Status |
|--------|--------|
| GLPK | Not installed — gracefully rejected (exception raised) |
| Ipopt | Not installed — gracefully rejected |
| SCIP | Not installed — gracefully rejected |
| CPLEX | Not installed — gracefully rejected |
| Gurobi | Not installed — gracefully rejected |

## Workarounds

None required. PyPSA's linopy-based architecture makes solver swap a first-class feature —
no reformulation needed when changing `solver_name`.

## Timing

- **Wall-clock:** ~2,645 s total (same as C-3: ~2,560 s linopy build + 43.3 s HiGHS solve + load/extraction)
- **HiGHS solve time:** 43.3 s (measured by HiGHS)
- **Timing source:** measured
- **Peak memory:** not captured
- **CPU cores used:** 1 (threads=1)

Note: The key architectural question for C-7 is whether solver swap requires reformulation.
The answer is No — solver swap is a single `solver_name` parameter change. The 43.3 s HiGHS
solve time is the relevant metric for solver comparison; the linopy build time is constant
across all solver backends.

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c7_solver_swap.py`
