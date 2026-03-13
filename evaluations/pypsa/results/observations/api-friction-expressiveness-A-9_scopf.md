---
tag: api-friction
source_dimension: expressiveness
source_test: A-9
tool: pypsa
severity: medium
timestamp: 2026-03-11T00:00:00Z
---

# Observation: SCOPF infeasible at 70% branch derating — contingency selection requires network awareness

## Finding

`n.optimize.optimize_security_constrained()` with any N-1 contingency is infeasible when branch limits are derated to 70% of original s_nom (as used in A-3). The network at 70% derating already has multiple lines at 90–100% utilization, leaving zero headroom for contingency flow redistribution. Any single-line outage creates unresolvable thermal violations.

## Context

Discovered during A-9 SCOPF test. The test specification says "use same network setup with differentiated costs and 70% derating." However, the SCOPF API correctly identifies the resulting problem as infeasible rather than silently returning a wrong answer. The 70% derating was appropriate for A-3 (to force binding constraints in unconstrained OPF), but it makes A-9 unsolvable.

Solution: use full s_nom (no derating) for SCOPF, selecting contingency lines with 30–65% utilization in the base case.

## Implications

Users of `optimize_security_constrained()` must be aware that:
1. The contingency set must be carefully selected to avoid creating infeasible N-1 problems
2. The SCOPF will NOT automatically relax constraints or find a relaxed feasible point — it returns infeasible
3. There is no automatic contingency filtering or fallback mechanism

Accessibility audit (D-4) should note the absence of diagnostic guidance when SCOPF is infeasible (the error message is just "Infeasible" with no indication of which contingency caused the issue).
