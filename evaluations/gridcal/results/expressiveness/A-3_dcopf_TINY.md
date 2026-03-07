---
test_id: A-3
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.102
peak_memory_mb: null
loc: 45
solver: "HiGHS, SCIP"
timestamp: 2026-03-06T01:00:00Z
---

# A-3: DC OPF with Gen Costs and Line Flow Limits

## Result: PASS

## Approach

Loaded IEEE 39-bus. Ran DC OPF via `vge.linear_opf(grid, options=opts)` with `MIPSolvers.HIGHS` and `MIPSolvers.SCIP`. CBC was attempted but is unsupported ("PuLP Unsupported MIP solver CBC"). GLPK is not available via GridCal's MIP solver enum.

All 10 generators have identical cost (0.3 $/MWh linear + 0.01 quadratic + 0.2 constant), so LMPs are uniform at 0.3 when no lines are binding.

## Output

| Metric | HiGHS | SCIP |
|--------|-------|------|
| Converged | Yes | Yes |
| Wall-clock (s) | 0.102 | 0.008 |
| Total gen (MW) | 6254.23 | 6254.23 |
| LMP range ($/MWh) | 0.3 — 0.3 | 0.3 — 0.3 |
| LMPs uniform | Yes | Yes |
| Binding branches | 2 | 2 |
| Max loading (%) | 100.0 | 100.0 |
| Load shedding (MW) | 0.0 | 0.0 |
| Gen shedding (MW) | 0.0 | 0.0 |

Shadow prices accessible via `results.bus_shadow_prices` (numpy array). Generator dispatch via `results.generator_power`.

## Workarounds

None required.

## Timing

- **Wall-clock:** 0.102s (HiGHS), 0.008s (SCIP)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a3_dcopf.py`
