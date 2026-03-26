---
tag: workaround-needed
source_dimension: scalability
source_test: C-3
tool: gridcal
severity: low
timestamp: "2026-03-24T12:00:00Z"
---

# Observation: SCIP used as GLPK substitute in dual-solver DCOPF comparison

## Finding

The C-3 test requires DCOPF with both HiGHS and GLPK. GLPK is not available in GridCal's
`MIPSolvers` enum. SCIP was used as the substitute -- it is a documented, public solver
option in GridCal and works correctly via `SCIP_CMD` in PuLP. Classification: stable
workaround (documented public API, unlikely to break on version upgrade).
[tool-specific: GLPK missing from solver enum]

## Context

Both HiGHS and SCIP converge to identical solutions on the 10k-bus MEDIUM network.
The SCIP substitution satisfies the test goal of dual-solver comparison with open-source
solvers. Performance is comparable (HiGHS 8.86s vs SCIP 8.61s).

## Implications

Grade impact: minor. The workaround uses a documented public API path and produces
valid comparison results. The finding that GLPK is absent from the solver interface
is worth noting for the Accessibility dimension but does not reduce scalability grade.
