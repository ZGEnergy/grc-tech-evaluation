---
test_id: P2-2
tool: gridcal
dimension: p2_readiness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: null
timestamp: 2026-03-06T04:00:00Z
---

# P2-2: Piecewise Linear Cost Curve Support

## Result: FAIL

## Capability: No (piecewise linear). Partial (quadratic, AC OPF only).

## Cost Model

GridCal generators have three cost parameters:

| Attribute | Role | Default |
|-----------|------|---------|
| `Cost` (c1) | Linear cost coefficient ($/MWh) | 1.0 |
| `Cost2` (c2) | Quadratic cost coefficient ($/MW^2h) | 0.0 |
| `Cost0` (c0) | Constant cost ($/h) | 0.0 |

The objective function is documented as: `f = c2 * Pg^2 + c1 * Pg + c0`

## Piecewise Linear Support: NOT AVAILABLE

There is no API for defining piecewise-linear cost curves (no block/segment arrays, no SOS2 formulation, no lambda method, no incremental cost representation). The generator cost model is strictly polynomial (constant + linear + quadratic).

## Quadratic Cost: AC OPF Only

**Functional probe results:**

- **DC OPF (`linear_opf`):** The `Cost2` (quadratic) term is **ignored**. Verified by running identical networks with and without quadratic costs -- dispatch and shadow prices were identical. The DC OPF formulation source (`linear_opf_ts_b.py`) contains no reference to `Cost2` or `cost_2`. Only the AC OPF formulation (`ac_opf_problem.py`) uses `cost_2`.

- **AC OPF (`nonlinear_opf`):** Quadratic cost is supported. The interior-point solver's KKT formulation includes `self.c2 = nc.generator_data.cost_2[...]` for quadratic terms.

## Solver Compatibility

- **DC OPF (PuLP/HiGHS):** Linear cost only. Quadratic terms silently ignored.
- **AC OPF (custom IPS):** Quadratic cost supported. No external solver dependency.

## Limitations

1. No piecewise-linear cost curves.
2. No SOS2 or incremental formulation.
3. Quadratic cost only works in AC OPF, not DC OPF.
4. DC OPF silently ignores quadratic cost terms with no warning.
5. No cost curve validation -- zero or negative costs accepted silently.

## Implications for Phase 2

Market-grade dispatch requires piecewise-linear cost curves to model realistic generator heat rate curves. GridCal's polynomial cost model is insufficient for production SCED. Adding piecewise-linear support would require modifying the internal PuLP/OR-Tools formulation in the DC OPF path -- a significant engineering effort given the lack of a custom constraint API (B-1).
