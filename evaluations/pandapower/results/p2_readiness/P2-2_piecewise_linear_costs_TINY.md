---
test_id: P2-2
tool: pandapower
dimension: p2_readiness
network: TINY
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: 0.47
peak_memory_mb: null
loc: 145
solver: PYPOWER interior point
timestamp: 2026-03-06T00:00:00Z
---

# P2-2: Piecewise-linear and quadratic cost curve support

## Result: INFORMATIONAL

## Finding

pandapower supports both piecewise-linear (PWL) and quadratic (polynomial) cost curves natively. Both types converge with the PYPOWER interior point solver on DC OPF.

## Evidence

### Piecewise-Linear Cost Curves

**API:** `pp.create_pwl_cost(net, element, et, points=[[p_start, p_end, marginal_cost], ...])`

**Format:** Each segment is defined by `[p_start, p_end, marginal_cost_per_mw]`. Segments must be contiguous (end of one = start of next).

**Test configuration:** 3-segment PWL cost for each of 9 generators:
- Segment 1: min_p to 33% capacity at $10/MWh
- Segment 2: 33% to 66% capacity at $20/MWh
- Segment 3: 66% to max capacity at $40/MWh

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Objective | 141,943.67 |
| LMP min | 30.33 |
| LMP max | 52.68 |
| LMP mean | 44.64 |
| LMPs extractable | Yes |

Dispatch reflects the cost structure: generators with lower marginal costs are dispatched first, and the spread of LMPs across buses indicates price separation from the multi-segment costs.

### Quadratic (Polynomial) Cost Curves

**API:** `pp.create_poly_cost(net, element, et, cp2_eur_per_mw2=..., cp1_eur_per_mw=..., cp0_eur=...)`

**Test configuration:** Quadratic costs c(p) = cp2*p^2 + cp1*p + cp0 with varying coefficients per generator.

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Objective | 195,431.83 |
| LMP min | 28.00 |
| LMP max | 80.60 |
| LMP mean | 65.47 |
| LMPs extractable | Yes |

The wider LMP spread (28-81 vs 30-53 for PWL) reflects the nonlinear marginal costs from the quadratic terms.

### Comparison

| Feature | PWL | Quadratic |
|---------|-----|-----------|
| Supported | Yes | Yes |
| Converges (DC OPF) | Yes | Yes |
| LMPs extractable | Yes | Yes |
| Solver | PYPOWER IP | PYPOWER IP |
| External solver support | No (native only) | No (native only) |
| API friction | Low | Low |

### Limitations

1. **Solver lock-in:** Both cost types can only be used with PYPOWER's built-in interior point solver via `rundcopp()`. No mechanism exists to use HiGHS or GLPK with native pandapower OPF (would require PowerModels.jl bridge).
2. **PWL format:** The `[[p_start, p_end, marginal_cost]]` format differs from common conventions (e.g., MATPOWER uses `[[p, c]]` pairs). Documentation is clear but the format is non-obvious.
3. **Mixed costs:** Both PWL and polynomial cost entries can coexist in the same network, but each element should have only one cost type.

## Test Script

**Path:** `evaluations/pandapower/tests/p2_readiness/test_p2_2_piecewise_linear_costs.py`
