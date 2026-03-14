---
tag: solver-issues
source_dimension: scalability
source_test: C-4
tool: pypsa
severity: high
timestamp: 2026-03-14T01:30:00Z
---

# Observation: HiGHS MILP scalability wall at 544 committable generators

## Finding

HiGHS cannot solve the root LP relaxation of a 24-hour SCUC on ACTIVSg2000
(544 committable generators, 39,168 binary variables) within 600 seconds on a
single thread. Zero branch-and-bound nodes are processed.

## Context

C-4 runs 24-hour SCUC on ACTIVSg2000 with `n.optimize(solver_name="highs")`.
The MILP has 347,272 constraints, 129,168 variables (39,168 binary), and
1,689,312 nonzeros. After presolve: 85,868 rows, 73,378 columns, 957,923
nonzeros. HiGHS spent 600 seconds on the root LP relaxation (80,488 LP
iterations) without finding a feasible integer solution.

SCIP was also tested but is not installed in the devcontainer despite the
feature being listed, producing `AssertionError: Solver scip not installed`.

## Implications

This finding is relevant to the scalability grade for C-4. The 544-generator
SCUC is intractable for HiGHS at single-thread settings within a reasonable
time budget. Multi-threaded solving or a different solver (SCIP, if available)
might improve performance. The MILP formulation itself (via linopy) is
well-structured (presolve reduces rows by 75%), but the problem scale exceeds
what HiGHS can handle in the allocated time.

For commercial operations on networks of this size, a commercial solver
(Gurobi, CPLEX) would likely be required.
