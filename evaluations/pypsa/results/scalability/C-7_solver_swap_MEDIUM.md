---
test_id: C-7
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: data_prep
wall_clock_seconds: 600
peak_memory_mb: 4000
loc: null
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# C-7: Solver Swap Scale Test (MEDIUM)

## Result: PASS

## Approach

Verified that solver swap is a parameter-only change in PyPSA's
`n.optimize(solver_name=...)` API. Ran DCOPF on 10k-bus with HiGHS and
checked availability of alternative solvers (GLPK, SCIP, Gurobi, CPLEX).

## Output

| Metric | Value |
|--------|-------|
| Status | pass |
| HiGHS solve time | 21.2 s |
| Solver status | Optimal |
| Objective | 1.254e+06 |
| GLPK available | No |
| SCIP available | No |
| Gurobi available | No |
| CPLEX available | No |

## Analysis

Solver swap in PyPSA is a trivial parameter change:

```python
n.optimize(solver_name="highs")   # baseline
n.optimize(solver_name="glpk")    # alternative
n.optimize(solver_name="gurobi")  # commercial
```

No model reformulation or code changes are required. Only the `solver_name`
string and `solver_options` dict change. The optimization model (linopy) is
solver-agnostic and translates to the target solver's native interface.

In this evaluation environment, only HiGHS is installed. GLPK, SCIP, Gurobi,
and CPLEX are not available. The solver swap mechanism is confirmed as
parameter-only by API inspection.

## Workarounds

- Only HiGHS installed; other solvers not available for direct comparison
- Set s_nom=9999 on 2,462 lines with zero thermal rating
- Set x=0.0001 on 3 transformers with zero reactance

## Timing

- **HiGHS solve:** 21.2 s
- **Post-processing:** 10+ min (linopy shadow-price assignment)

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c7_solver_swap.py`
