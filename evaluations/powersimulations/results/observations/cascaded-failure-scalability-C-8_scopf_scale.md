---
tag: cascaded-failure
source_dimension: scalability
source_test: C-8
tool: powersimulations
severity: high
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: C-8 SCOPF Inherits and Amplifies C-3 Workarounds

## Finding

The C-8 SCOPF test requires all six workarounds from C-3 (DCOPF at MEDIUM scale) plus the
manual SCOPF constraint assembly from A-9. The C-3 workarounds are necessary but not sufficient:
even with all workarounds applied, the MEDIUM SCOPF fails because the brute-force constraint
approach generates 474k constraints that overwhelm the solver.

## Context

**Inherited workarounds from C-3:**
1. `initialize_model=false` + `JuMP.optimize!()` -- PSI initialization bypass
2. `StaticBranchUnbounded` -- PSI branch flow limits cause numerical infeasibility
3. Linear cost override -- quadratic costs + initialize_model=false causes QP issues
4. All generators available -- hydro omission creates capacity deficit
5. HydroDispatch omitted -- no PSI formulation
6. Manual base-case flow limits via JuMP (new for C-8, compensates for StaticBranchUnbounded)

**C-8 additional workaround:**
7. Manual SCOPF via LODF + JuMP constraints (from A-9, scaled up)

The cascading pattern: C-3's `StaticBranchUnbounded` removes branch flow limits from the PSI
formulation, requiring C-8 to add them back manually via JuMP alongside the N-1 constraints.
This means C-8 has 19,452 manually-added base-case flow constraints that would be free with
`StaticBranch` -- but `StaticBranch` itself causes infeasibility at scale.

## Implications

The seven-workaround stack makes SCOPF at MEDIUM scale fundamentally fragile. Each workaround
addresses a different PSI limitation, and together they produce a problem that exceeds solver
capability. The SMALL success (160k constraints, 9.6s solve) shows the approach is sound in
principle; the scaling failure is a consequence of the brute-force constraint generation
necessitated by lacking a built-in iterative SCOPF.
