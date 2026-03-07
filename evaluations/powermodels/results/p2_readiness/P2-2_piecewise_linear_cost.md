---
test_id: P2-2
tool: powermodels
dimension: p2_readiness
network: TINY
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: "2026-03-07T00:00:00Z"
---

# P2-2: Piecewise-Linear Cost Curve for DC OPF

## Result: INFORMATIONAL

## Finding

PowerModels.jl has **built-in support for piecewise-linear (PWL) cost curves**(model=1) alongside polynomial/quadratic costs (model=2). PWL costs are set via the data dictionary with no API friction. The internal formulation uses a **lambda-based convex combination**(continuous LP variables), not SOS2 constraints, meaning PWL cost curves do not introduce integer variables and remain solvable as a pure LP with any LP-capable solver.

## Evidence

### Capability: YES -- native PWL support

#### Test 1: Single generator PWL (gen 1), rest quadratic

Modified gen 1 cost from quadratic (model=2, cost=[100.0, 30.0, 0.2]) to 3-segment PWL (model=1, ncost=4):
- Breakpoints (MW): [0.0, 3.432, 6.968, 10.4]
- Breakpoint costs: [0.2, 0.886, 2.124, 3.84]
- Marginal costs per segment: [0.20, 0.35, 0.50 $/MWh] (convex, increasing)

```

DC OPF Status: OPTIMAL
Objective: 33,860.79
Gen 1 dispatch: 9.0 p.u. (dispatched into segment 3)

```

#### Test 2: All 10 generators PWL (converted from quadratic via breakpoint evaluation)

```

DC OPF Status: OPTIMAL
Objective: 41,583.32

```

The all-PWL objective (41,583) is slightly higher than the quadratic baseline (41,264) because the 3-segment PWL approximation overestimates the true quadratic cost curve. This confirms the PWL formulation is working correctly -- the approximation error is consistent with a convex outer approximation.

#### Test 3: Original quadratic costs (baseline)

```

DC OPF Status: OPTIMAL
Objective: 41,263.94

```

### Formulation Details

Inspecting the JuMP model built by `PowerModels.instantiate_model` with `DCPPowerModel`:

- **PWL variables**: 4 lambda variables for the single PWL generator: `0_pg_cost_lambda_1[1]` through `0_pg_cost_lambda_1[4]` (one per breakpoint)
- **Total variables**: 99 (vs. 95 for all-quadratic -- only 4 additional variables per PWL generator)
- **Constraint types**: All `AffExpr` with `EqualTo` or `Interval` bounds, plus `VariableRef` bounds. No `SOS2`, no binary/integer variables.
- **Formulation type**: Pure LP (continuous). The convex combination lambda formulation exploits the convexity of the PWL function, so no integrality is needed for cost minimization.
- **Has SOS2**: No

### Data Dictionary Format

PWL cost specification in the PowerModels data dict:

```julia

gen["model"] = 1          # 1 = piecewise-linear
gen["ncost"] = 4          # number of breakpoints (= segments + 1)
gen["cost"] = [p0, c0, p1, c1, p2, c2, p3, c3]  # interleaved (MW, cost) pairs

```

This matches the MATPOWER convention. PowerModels parses MATPOWER `.m` files with model=1 costs natively.

### Solver Compatibility

- **HiGHS**: Works (LP). PWL with convex costs remains an LP.
- **Ipopt**: Works (NLP solver can solve LPs).
- **Any LP solver**: Compatible because no integer variables are introduced.
- **Non-convex PWL**: If the PWL function is non-convex (decreasing marginal cost), the lambda formulation may produce incorrect results without SOS2 or binary variables. PowerModels does not enforce convexity or add integrality constraints for non-convex PWL.

### Limitations

1. **Non-convex PWL costs**: The lambda formulation assumes convexity. Non-convex (concave) cost curves will silently produce incorrect results. Users must ensure breakpoints define a convex function or add their own SOS2/binary constraints.
2. **Breakpoint count**: The number of breakpoints is limited only by memory/solver capacity. Each additional breakpoint adds one continuous variable and one constraint per generator.
3. **No automatic quadratic-to-PWL conversion**: Users must manually compute breakpoints from quadratic coefficients. No built-in utility for this conversion.

## Implications

- **Phase 2 readiness: HIGH.** PWL costs are a first-class feature in PowerModels, requiring only data dict modifications. The LP formulation means no solver upgrade is needed (HiGHS suffices).
- For production use with ERCOT-style offer curves (typically 3-10 segments, convex), the native PWL support is directly applicable.
- The ~0.8% cost approximation error (PWL vs quadratic with 3 segments) can be reduced by increasing the number of breakpoints.

## Test Script

Path: `evaluations/powermodels/tests/p2_readiness/test_p2_2_pwl_cost.jl`
