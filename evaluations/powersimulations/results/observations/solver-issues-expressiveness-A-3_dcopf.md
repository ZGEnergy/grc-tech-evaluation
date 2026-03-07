---
tag: solver-issues
source_dimension: expressiveness
source_test: A-3
tool: powersimulations
severity: low
timestamp: "2026-03-07T01:30:00Z"
---

# Observation: GLPK cannot solve quadratic cost curves from MATPOWER

## Finding

GLPK fails at model build stage when the system has generators with quadratic cost curves
(`CostCurve{QuadraticCurve}`). PSI constructs a QP objective from these curves, which GLPK
does not support. The build failure message is generic (`FAILED`) with no indication that the
solver lacks QP capability.

## Context

In test A-3, case39.m generators have quadratic cost curves
`QuadraticCurve(0.01, 0.3, 0.0)`. HiGHS handles QP and solves successfully. GLPK's build
failure means it cannot serve as a secondary solver for this problem class unless costs are
linearized.

## Implications

For scalability tests (C-3, C-7 solver swap), GLPK should not be expected to solve problems
with quadratic cost curves. This is a solver limitation, not a PSI limitation. The
observation is relevant to Scalability's solver swap assessment.
