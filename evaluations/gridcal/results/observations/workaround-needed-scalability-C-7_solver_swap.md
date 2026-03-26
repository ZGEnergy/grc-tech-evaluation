---
tag: workaround-needed
source_dimension: scalability
source_test: C-7
tool: gridcal
severity: low
timestamp: "2026-03-24T18:00:00Z"
---

# Observation: GLPK substituted with SCIP for solver swap test

## Finding

The protocol specifies testing HiGHS, GLPK, and SCIP as the three open-source solvers.
GridCal's `MIPSolvers` enum does not include GLPK, so SCIP was used as the substitute.
This is a stable workaround -- SCIP is a documented, public solver option that provides
equivalent LP/MILP functionality. [tool-specific: GLPK omitted from solver enum]

The solver swap mechanism itself is excellent: a single parameter change
(`mip_solver=MIPSolvers.SCIP`) with no reformulation or model rebuild. Both HiGHS and
SCIP produce identical dispatch results on the MEDIUM network.

## Context

SCIP serves as an adequate substitute because both GLPK and SCIP are open-source LP/MILP
solvers. The workaround does not affect the evaluation of the swap mechanism, which is the
core question of C-7.

## Implications

Minor. The swap mechanism is well-designed (qualified_pass). The GLPK absence reduces
solver diversity but does not impair the tool's ability to swap between available solvers.
