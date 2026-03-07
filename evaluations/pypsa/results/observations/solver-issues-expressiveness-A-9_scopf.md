---
tag: solver-issues
source_dimension: expressiveness
source_test: A-9
tool: pypsa
severity: medium
timestamp: 2026-03-06T00:00:00Z
---

# Observation: SCOPF infeasible at original thermal ratings on case39

## Finding

`optimize_security_constrained()` returns infeasible on case39 with original thermal
ratings (s_nom). Feasibility is restored by scaling ratings to 150%. This is expected
for a tightly constrained network under full N-1 security, but the infeasibility
diagnostic is opaque -- the solver reports "Infeasible" without identifying which
contingency constraint causes the violation.

## Context

During A-9 (SCOPF), the first solve attempt with all 35 lines as contingencies and
original s_nom values was infeasible (HiGHS returned infeasible after 31 iterations).
Scaling s_nom to 150% resolved the issue. The solver log does not indicate which
specific contingency or line constraint caused infeasibility. Users must diagnose
binding constraints by examining duals or running contingencies individually.

## Implications

The lack of infeasibility diagnosis in SCOPF affects usability for larger networks
where identifying the binding contingency is critical. This should be noted in the
accessibility assessment. Additionally, bug #1356 (SCLOPF overloads up to 7%) could
not be verified because `lpf_contingency()` is broken (see separate observation).
