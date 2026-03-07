---
tag: solver-issues
dimension: expressiveness
test_id: A-5
tool: powersimulations
timestamp: "2026-03-07T04:30:00Z"
---

# Solver Issue: HiGHS Fails SCUC Build During Initial Condition Initialization

## Observation

HiGHS fails to build the SCUC model. The error occurs during
`handle_initial_conditions!()` where PSI solves an auxiliary optimization to
determine initial conditions. HiGHS returns `NO_SOLUTION` for this sub-problem
after 2 attempts.

Error: `"Optimizer returned NO_SOLUTION after 2 optimize! attempts"`

SCIP solves the same problem successfully with build time 10.9s and solve time 104.9s.

## Impact

HiGHS cannot be used for SCUC with PSI. Only SCIP works among the tested open-source
MIP solvers. This limits solver flexibility for unit commitment problems.

## Possible Root Cause

The failure may be related to HiGHS's handling of quadratic costs in a MIP context
during initial condition computation. The case39 generators use `QuadraticCurve`
cost functions, which produce a MIQP. HiGHS's MIQP support may have limitations
with certain problem structures.
