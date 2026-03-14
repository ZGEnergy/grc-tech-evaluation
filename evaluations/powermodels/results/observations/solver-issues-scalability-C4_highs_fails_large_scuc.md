---
tag: solver-issues
source_dimension: scalability
source_test: C-4
tool: powermodels
severity: high
timestamp: 2026-03-13T22:30:00Z
---

# Observation: HiGHS fails to find feasible SCUC solution on 2000-bus network

## Finding

HiGHS 1.13.1 hit the 30-minute time limit without finding any feasible solution for the 2000-bus 24-hour SCUC MILP (100K variables, 13K binary, 340K constraints). The root LP relaxation alone consumed ~808 seconds. In contrast, SCIP solved the same problem in 902 seconds with a 0.20% MIP gap, using its feasibility pump heuristic.

## Context

C-4 tests SCUC scalability on the ACTIVSg 2000-bus network with 544 generators over 24 hours. Both HiGHS (primary MILP solver) and SCIP (secondary) were tested with 1 thread and 30-minute timeout. SCIP's more aggressive presolving (symmetry detection with log10 group size 99.3) and primal heuristics (feasibility pump) were decisive. HiGHS produced no incumbent despite solving the root LP to the same dual bound (~$27.47M).

## Implications

For scalability assessment: HiGHS, the primary evaluation MILP solver, is inadequate for large-scale SCUC problems. SCIP should be considered the primary solver for MILP problems at SMALL scale and above. This is a solver capability difference, not a tool limitation -- the user-assembled JuMP model is solver-agnostic and works correctly with SCIP. This finding should inform C-7 (Solver Swap) cross-referencing.
