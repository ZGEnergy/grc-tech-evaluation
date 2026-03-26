---
tag: solver-issues
source_dimension: scalability
source_test: C-3
tool: gridcal
severity: low
timestamp: "2026-03-24T12:00:00Z"
---

# Observation: GLPK unavailable; soft constraints not triggered on uncongested MEDIUM

## Finding

GridCal's `MIPSolvers` enum does not include GLPK. The enum lists HIGHS, SCIP, CPLEX,
GUROBI, XPRESS, CBC, PDLP, but the PuLP interface only maps 5 of them (HIGHS, SCIP,
CPLEX, GUROBI, XPRESS). CBC and PDLP raise `Exception: PuLP Unsupported MIP solver CBC`
at runtime despite being valid enum values. [tool-specific: incomplete solver enum mapping]

The soft-constraint formulation (confirmed in A-3 on congested TINY) does not manifest
on the uncongested MEDIUM network. Max branch loading is 84.72% with zero binding
constraints, so the soft-constraint penalty has no effect. The soft-constraint finding
remains a documented tool characteristic but produces no observable impact at MEDIUM scale
without artificial branch derating.

## Context

SCIP was used as the GLPK substitute. Both HiGHS and SCIP produce identical dispatch
(0.0 MW difference) and LMPs (uniform at 20.064 $/MWh). The ACTIVSg10k network has
no binding branch constraints in base-case DCOPF, consistent with the cross-tool
watchpoint documentation.

## Implications

The GLPK unavailability is a minor gap -- SCIP provides equivalent functionality as an
open-source LP/MILP solver. The non-functional CBC/PDLP enum values are a quality concern
that could confuse users but do not block evaluation. The soft-constraint formulation
requires congestion to test; a future evaluation with tightened branch limits could verify
scaling behavior of the penalty coefficient.
