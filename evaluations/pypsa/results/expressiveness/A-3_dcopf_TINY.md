# A-3: DC OPF with Gen Costs and Line Flow Limits (TINY)

- **Test ID:** A-3
- **Slug:** dcopf
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Solver:** HiGHS 1.13.1
- **Status:** PASS

## Pass Condition

Converges. Optimal dispatch and LMPs/shadow prices extractable from solution.

## Results

| Metric | Value |
|--------|-------|
| Wall clock | 0.349 s |
| Solver status | optimal |
| Objective value | 41261.94 |
| Total dispatch | 6254.23 MW |
| Total load | 6254.23 MW |
| Binding lines | 0 |
| LMP range | 13.5169 - 13.5171 |
| LMP mean | 13.517 |

### Generator Costs

All 10 generators have identical quadratic costs: `0.01*P^2 + 0.3*P + 0.2`.
PyPSA supports both `marginal_cost` (linear) and `marginal_cost_quadratic` (quadratic) terms.

### Dispatch (MW)

| G0 | G1 | G2 | G3 | G4 | G5 | G6 | G7 | G8 | G9 |
|----|----|----|----|----|----|----|----|----|-----|
| 660.9 | 646.0 | 660.8 | 652.0 | 508.0 | 660.8 | 580.0 | 564.0 | 660.9 | 660.9 |

Several generators are at their Pmax limits (G1=646, G3=652, G4=508, G6=580, G7=564).

### LMPs

Near-uniform at ~13.517 across all buses. No congestion (no binding line limits), so LMPs reflect only the marginal cost of generation.

## API

```python
n.optimize(solver_name="highs", solver_options={...})
# Results: n.generators_t.p, n.buses_t.marginal_price, n.lines_t.p0
```

## LOC

~15 lines beyond network loading (set costs, call optimize, access results).

## Workarounds

1. **Manual cost assignment (stable):** `import_from_pypower_ppc()` ignores gencost data. Must manually set `marginal_cost` and `marginal_cost_quadratic` on each generator from the CaseFrames gencost data.

## Errors

None.
