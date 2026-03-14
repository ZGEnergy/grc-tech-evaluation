---
tag: solver-issues
source_dimension: expressiveness
source_test: A-12
tool: matpower
severity: medium
timestamp: 2026-03-13T00:00:00Z
---

# Observation: MIPS numerical instability on multi-period QP with storage

## Finding

MATPOWER's built-in MIPS solver encounters singular matrix numerical issues when solving
multi-period DCOPF with quadratic costs on the case39 network augmented with renewables
and storage (16 generators x 24 periods). This forced the use of linear costs and GLPK
(LP solver) instead of the specified quadratic costs.

## Context

A-12 requires multi-period DCOPF with quadratic costs (c2 = c1 * 0.001), 70% branch
derating, 5 renewable generators, and 1 BESS unit. The MOST formulation with `addstorage()`
and `loadmd()` sets up the problem correctly. However:

- MIPS (interior point) fails with "matrix singular to machine precision" warnings and
  returns exitflag=-1 after ~17 iterations of progressive conditioning degradation.
- GLPK rejects QP entirely ("GLPK handles only LP problems, not QP problems").
- No other QP-capable solvers (HiGHS, CPLEX, Gurobi, MOSEK) are available for MOST in
  the Octave devcontainer.

With linear costs and GLPK, all three behavioral pass conditions are met. The limitation
is purely a solver availability issue on Octave, not a formulation limitation of MOST.

## Implications

This is the same solver ecosystem limitation identified in A-5 (GLPK MIP gap issue) but
manifests differently: MIPS numerical conditioning vs. GLPK exit flag mapping. Both point
to MATPOWER's Octave deployment having a narrower effective solver stack than the MATLAB
deployment. The scalability dimension (C-4, C-7) should verify whether this issue worsens
at larger network scales. The accessibility dimension should note that the solver stack
documentation assumes MATLAB availability.
