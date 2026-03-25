---
tag: solver-issues
source_dimension: scalability
source_test: C-4
tool: pypsa
severity: high
timestamp: 2026-03-24T22:30:00Z
---

# Observation: HiGHS MILP scalability wall at 544 committable generators

## Finding

HiGHS requires ~1,230 seconds (32 threads) to solve the root LP relaxation of a
24-hour SCUC on ACTIVSg2000 (544 committable generators, 39,168 binary variables).
Single-threaded HiGHS (600s budget) cannot solve the root LP at all. With 32
threads and 1,800s budget, a feasible solution is found via heuristics at 1.63%
MIP gap, but the 1% target gap is not achieved.

## Context

C-4 runs 24-hour SCUC on ACTIVSg2000 with `n.optimize(solver_name="highs")`.
The MILP has 347,272 constraints, 129,168 variables (39,168 binary), and
1,689,312 nonzeros. After presolve: 85,868 rows, 73,378 columns, 957,923
nonzeros.

- **1-thread (600s):** 75,861 LP iterations, root LP not solved, no feasible solution.
- **32-thread (1800s):** Root LP solved at ~1,230s (103,006 iterations). Central
  rounding heuristic found feasible solution at ~1,670s. Final gap: 1.63%.
  78 generators cycle across 24 hours.

SCIP was not available in the devcontainer (`AssertionError: Solver scip not installed`).

## Implications

This is a [solver-specific] finding relevant to all tools using HiGHS for MILP.
The root LP relaxation of a ~86k-row MILP is the bottleneck; the tool's formulation
(via linopy) is well-structured. For commercial operations on 2,000-bus networks,
a commercial solver (Gurobi, CPLEX) would likely be required to achieve tight
MIP gaps within acceptable time budgets. Multi-threading is essential -- 1-thread
HiGHS cannot even complete the root LP within 10 minutes.
