---
test_id: A-10
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 0.600
peak_memory_mb: null
loc: 220
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# A-10: Lossy DCOPF with LMP Decomposition

## Result: PASS

## Approach

Solved DC OPF with transmission loss approximation using
`n.optimize(transmission_losses=2)` (2 piecewise linear tangent segments per line).
Compared results against the lossless DCOPF baseline. Extracted LMP decomposition
from bus marginal prices and line constraint duals via the Linopy model object.

Per-line congestion rent was computed as `flow * (LMP_sink - LMP_source)` for each
line, and reconciled against the LMP structure.

## Output

**Lossy vs Lossless DCOPF:**

| Metric | Lossless | Lossy | Difference |
|--------|----------|-------|-----------|
| Objective | 1876.269 | 1884.246 | +7.977 (+0.43%) |
| LMP min ($/MWh) | 0.300 | 0.300 | 0.000 |
| LMP max ($/MWh) | 0.300 | 0.306 | +0.006 |
| LMP mean ($/MWh) | 0.300 | 0.302 | +0.002 |
| LMP spread | 0.000 | 0.006 | +0.006 |

The lossy formulation increases the objective by 0.43% and introduces LMP variation
across buses (spread of 0.006 $/MWh). In the lossless case, all LMPs are uniform
at 0.30 $/MWh since all generators have identical marginal costs and there is no
congestion. Losses break this uniformity.

**LMP Decomposition (sample buses):**

| Bus | Total LMP | Energy | Loss Component | Lossless LMP |
|-----|-----------|--------|---------------|--------------|
| 1 | 0.3012 | 0.300 | 0.0012 | 0.300 |
| 2 | 0.3000 | 0.300 | 0.0000 | 0.300 |
| 3 | 0.3043 | 0.300 | 0.0043 | 0.300 |
| 4 | 0.3040 | 0.300 | 0.0040 | 0.300 |
| 5 | 0.3024 | 0.300 | 0.0024 | 0.300 |

Since the lossless case has uniform LMPs (no congestion), the entire LMP variation
in the lossy case is attributable to loss components. Bus 2 has zero loss component
(it is a reference/slack bus location). Remote buses (e.g., bus 3 at 0.0043 $/MWh
loss adder) have higher loss components reflecting the marginal cost of transmitting
power to compensate for losses on longer electrical paths.

**Linopy Model Constraint Duals:**

The model exposes 18 constraint groups, including loss-specific constraints:
- `Line-loss_tangents-1--1`: nonzero duals (binding)
- `Line-loss_tangents-1-1`: nonzero duals (binding)
- `Line-loss_tangents-2--1`: nonzero duals (binding)
- `Line-fix-s-lower`, `Line-fix-s-upper`: zero duals (no congestion)

This confirms that loss tangent constraints are active while thermal limits are not
binding, consistent with the all-loss, no-congestion LMP structure.

**Per-Line Congestion Rent:**

| Metric | Value |
|--------|-------|
| Total rent (all lines) | 13.05 |
| Largest single-line rent | 2.10 (L2) |

Note: In this case, "congestion rent" is entirely driven by loss-induced LMP
differences, not thermal congestion (no lines are at their thermal limit).

## Workarounds

- **What:** LMP decomposition extracted by combining bus marginal prices
  (`n.buses_t.marginal_price`) with constraint duals from the Linopy model
  (`n.model.constraints`).
- **Why:** PyPSA does not provide a built-in LMP decomposition method. The bus
  marginal prices are total LMPs; decomposing into energy/congestion/loss requires
  accessing the underlying optimization model's dual variables.
- **Durability:** stable -- `n.model` is a documented public attribute providing
  access to the Linopy model. The constraint labels are accessible via
  `model.constraints.labels`. Constraint duals are accessed via the standard Linopy
  `constraint.dual` property. The `transmission_losses` parameter is documented.
- **Grade impact:** Minor. The decomposition requires knowledge of the underlying
  optimization structure, but all access paths use public API.
- **Version tested:** PyPSA 1.1.2

## Timing

- **Wall-clock:** 0.600 s (lossy DCOPF solve)
- **Peak memory:** not measured
- **Solver iterations:** 65 (HiGHS dual simplex)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a10_lossy_dcopf_lmp.py`

Key API patterns:

```python
# Lossy DCOPF
n.optimize(solver_name="highs", transmission_losses=2)

# LMP decomposition via model duals
constraint_names = list(n.model.constraints.labels)
dual = getattr(n.model.constraints, cname).dual

# Per-line congestion rent
rent = flow * (lmp_sink - lmp_source)
```
