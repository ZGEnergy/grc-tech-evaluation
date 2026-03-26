---
tag: solver-issues
source_dimension: scalability
source_test: C-7
tool: gridcal
severity: low
timestamp: "2026-03-24T18:00:00Z"
---

# Observation: GLPK missing from enum; CBC/PDLP enum values non-functional

## Finding

GridCal's `MIPSolvers` enum does not include GLPK. The enum lists 7 solvers (HIGHS, SCIP,
CPLEX, GUROBI, XPRESS, CBC, PDLP), but only 5 are functional through the PuLP interface
(HIGHS, SCIP, CPLEX, GUROBI, XPRESS). CBC and PDLP raise `Exception: PuLP Unsupported
MIP solver CBC` at runtime despite being valid enum values.
[tool-specific: incomplete solver enum mapping in PuLP interface]

Solver swap itself is well-designed: a single parameter change (`mip_solver=MIPSolvers.X`)
with no reformulation required. The PTDF-based LP formulation is constructed once and
dispatched to PuLP, which routes to the backend solver. Both HiGHS and SCIP produce
identical results (0.0 MW dispatch difference, identical LMPs within 1.94e-08).

## Context

HiGHS (8.91 s) and SCIP (8.53 s) both converge on the 10000-bus MEDIUM network with
single-threaded execution. SCIP is used as the GLPK substitute per the protocol's
open-source solver requirement.

## Implications

The GLPK absence is a minor gap -- SCIP provides equivalent LP/MILP functionality. The
non-functional CBC/PDLP enum values are a code quality concern: users who select these
solvers via the documented API receive unhelpful runtime exceptions. This does not block
evaluation but reduces the effective open-source solver count from 3 (protocol request)
to 2 (available).
