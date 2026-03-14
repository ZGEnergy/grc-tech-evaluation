---
test_id: P2-2
tool: gridcal
dimension: p2_readiness
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "5dfd4d01"
timestamp: "2026-03-13T00:00:00Z"
---

# P2-2: Piecewise-linear cost curve support

## Finding

GridCal/VeraGrid does not support piecewise-linear cost curves. The generator data model uses a polynomial cost representation (`Cost2 * P^2 + Cost * P + Cost0`) only. When MATPOWER files with piecewise-linear costs (model type 1) are imported, the breakpoints are fitted to a quadratic polynomial, losing the piecewise structure.

## Evidence

**Generator cost model.** The `Generator` class exposes three cost attributes:

| Attribute | Description | Default |
|-----------|-------------|---------|
| `Cost2` | Quadratic coefficient ($/MW^2) | 0.0 |
| `Cost` | Linear coefficient ($/MW) | 1.0 |
| `Cost0` | Constant term ($) | 0.0 |

There is no attribute, data structure, or API for defining cost breakpoints, segments, or piecewise-linear curves. A search of the entire `VeraGridEngine` package for "piecewise" and "pwl" found zero matches in any OPF formulation code.

**MATPOWER import behavior.** The MATPOWER parser (`IO/matpower/legacy/matpower_parser.py`, line 275) handles piecewise-linear gencost entries (model type 1) by fitting them to a quadratic polynomial:

```python
elif curve_model == 1:
    # fit a quadratic curve
    x = points[0::1]
    y = points[0::2]
    if len(x) == len(y):
        coeff = np.polyfit(x, y, 2)
        gen_dict[i].Cost = coeff[1]
```

This converts piecewise-linear breakpoints into a single quadratic curve via `np.polyfit`, discarding the piecewise structure entirely. The polynomial coefficients are then stored in `Cost2`, `Cost`, `Cost0`.

**OPF formulation.** The linear OPF objective function (`Formulations/linear_opf_ts_b.py`) uses `cost1_pu * gen_vars.p[t, k] + cost0_pu` for the generation cost term. This is a strictly linear cost per generator -- there is no mechanism to introduce breakpoints, SOS2 variables, or lambda-method piecewise linearization in the MIP formulation.

**No piecewise-linear in AC OPF either.** The nonlinear OPF (interior point solver) was also searched; it uses the same polynomial cost model.

## Implications

- **Phase 2 production modeling** with realistic generator offer curves (which are typically 3-10 segment piecewise-linear in ISO markets) cannot be represented natively. The polynomial approximation may be acceptable for screening studies but introduces systematic cost errors at generation extremes.
- **Workaround feasibility:** A user could manually approximate a piecewise-linear curve with a quadratic fit and accept the approximation error. Alternatively, since GridCal uses PuLP/OR-Tools for the linear OPF, it is theoretically possible to intercept the model construction and inject SOS2/lambda variables, but this would require modifying internal formulation code -- there is no public extension point.
- **Estimated effort to add native support:** High. Requires changes to: (1) the `Generator` data model to store breakpoint arrays, (2) the OPF formulation code to emit SOS2 constraints or equivalent, (3) the MATPOWER/PSS/E importers to preserve breakpoint data, and (4) the serialization layer.
