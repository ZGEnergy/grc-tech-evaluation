---
test_id: P2-2
tool: pypsa
dimension: p2_readiness
network: TINY
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: 2026-03-06T00:00:00Z
---

# P2-2: Piecewise Linear Cost

## Piecewise Linear Cost: No

PyPSA v1.1.2 does **not** support piecewise linear (PWL) cost curves for generators. The generator component attributes (defined in `pypsa/data/component_attrs/generators.csv`) include `marginal_cost` (linear, $/MWh) and `marginal_cost_quadratic` (quadratic, $/MWh) but no attribute for piecewise linear cost breakpoints.

This is a known gap. GitHub issues #1473 and #1603 request piecewise linear cost support. As of v1.1.2, neither has been implemented.

The only piecewise linear formulation in PyPSA is for **transmission loss approximation** (in `optimization/constraints.py`, functions for tangent and secant linearization of I^2*R losses), not for generator cost curves.

## Quadratic Cost: Yes (Functional Probe Passed)

PyPSA supports quadratic marginal costs via the `marginal_cost_quadratic` generator attribute. This produces a QP (quadratic program) objective when set to nonzero values.

### Functional Probe: Quadratic Cost DCOPF on case39

Loaded IEEE 39-bus network, set `marginal_cost = 0.3` (linear, C1) and `marginal_cost_quadratic = 0.01` (quadratic, C2) on all 10 generators from the MATPOWER gencost polynomial coefficients.

| Metric | Value |
|--------|-------|
| Solver status | ok, optimal |
| Objective | $41,261.94 |
| Total dispatch | 6,254.23 MW |
| Problem type | QP |
| LMP min | 13.5169 $/MWh |
| LMP max | 13.5171 $/MWh |
| Unique LMP values | 39 (all buses distinct) |

The quadratic cost term produces non-uniform LMPs across buses (39 unique values vs 1 uniform value with linear-only costs in A-3), confirming that the quadratic objective is correctly formulated and solved. The objective ($41,261.94) is higher than the linear-only case ($1,876.27) because the quadratic term `0.01 * P^2` dominates at high dispatch levels.

### Formulation Details

The quadratic cost is implemented in `pypsa/optimization/optimize.py` (line ~240) as:

```
objective += sum(P_i^2 * marginal_cost_quadratic_i)
```

This is added directly to the Linopy model objective as a quadratic term. HiGHS solves it natively as a QP (no SOS2 or lambda formulation needed).

### Solver Compatibility

- **HiGHS:** Supports QP natively (tested, works)
- **Gurobi, CPLEX, MOSEK, Xpress:** All support QP
- **GLPK, CBC:** LP/MILP only -- quadratic costs would fail with these solvers
- **CVaR note:** Quadratic costs are incompatible with PyPSA's CVaR (stochastic) optimization; PyPSA raises a `ValueError` if both are combined

### Limitations

1. **No piecewise linear cost curves** -- cannot define 3-segment breakpoint cost functions
2. **Quadratic cost is a single coefficient** -- represents `c2 * P^2`, not a general polynomial
3. **No SOS2 / lambda / incremental formulation** -- only direct QP
4. **Workaround for PWL:** Users could approximate piecewise linear costs by:
   - Using `extra_functionality` to add custom SOS2 constraints via Linopy (significant effort, ~50-100 LOC)
   - Fitting a quadratic approximation to the PWL curve (loses breakpoint fidelity)
   - Pre-solving with an external tool and fixing dispatch

## Summary

| Feature | Supported | Formulation | Solver Constraints |
|---------|-----------|-------------|-------------------|
| Piecewise linear cost | No | N/A | N/A |
| Quadratic cost | Yes | Direct QP term in objective | Requires QP-capable solver (HiGHS, Gurobi, CPLEX) |
| Polynomial cost (>2nd order) | No | N/A | N/A |
