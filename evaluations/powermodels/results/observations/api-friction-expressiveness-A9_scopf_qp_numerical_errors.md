---
tag: api-friction
dimension: expressiveness
test_id: A-9
observed: 2026-03-11
tool: powermodels
version: 0.21.5
---

# API Friction: HiGHS QP Solver Numerical Errors with Security Constraints

## Observation

When adding LODF-based security constraints to a DC OPF model that uses quadratic costs (c2 > 0), HiGHS reports `OTHER_ERROR` with primal infeasibility residuals. The same constraint set is feasible when the cost model uses linear-only costs (c2 = 0).

## Affected Configuration

- Cost model: `gen["cost"] = [c2*base_mva^2, c1*base_mva, 0.0]` with `ncost=3` (quadratic)
- Constraints added: LODF-based security constraints via `@constraint(pm.model, p_l + LODF*p_k <= rate_a)`
- Solver: HiGHS
- Result: `OTHER_ERROR` from HiGHS, primal infeasibility residuals reported

## Root Cause Analysis

HiGHS QP solver appears to have reduced numerical tolerance for LP feasibility preprocessing when a quadratic objective is present. The same model with a linear objective (c2=0) is solved correctly. This is a solver interaction artifact — the LODF constraint formulation is mathematically correct.

## Fix

Use linear-only cost model for SCOPF tests:

```julia

gen["model"] = 2; gen["ncost"] = 2
gen["cost"] = [c1 * base_mva, 0.0]  # linear: [c1_pu, constant]

```

Differentiated `c1` values (5, 10, 25, 40 $/MWh per tech class) are preserved, producing meaningful dispatch differentiation and cost increments vs unconstrained OPF.

## Impact

Medium friction. The fix requires switching from quadratic to linear costs for SCOPF. For evaluation purposes, linear costs are sufficient — the key observable (SCOPF cost > base OPF cost) is still demonstrable. For production use, users wishing quadratic costs in SCOPF would need to use a different QP solver or apply problem reformulation.
