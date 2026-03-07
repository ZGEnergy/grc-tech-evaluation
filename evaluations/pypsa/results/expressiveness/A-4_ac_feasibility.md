---
test_id: A-4
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 0.117
peak_memory_mb: null
loc: 175
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# A-4: AC Feasibility Check

## Result: PASS

## Approach

Ran DC OPF via `n.optimize()` to obtain generator dispatch, then set `p_set` on each
generator from the dispatch results and ran `n.pf()` for full AC power flow -- all
within the same model context (no export/reimport). This follows the convergence
protocol with a flat-start attempt first.

The AC PF converged on the flat start (no DC warm start needed). Voltage magnitude
and thermal limit violations were then extracted from the solution.

## Output

| Metric | Value |
|--------|-------|
| DCOPF converged | Yes |
| DCOPF objective | 1876.269 |
| ACPF converged | Yes (flat start) |
| Same model context | Yes |

**Voltage magnitudes (pu):**

| Statistic | Value |
|-----------|-------|
| Min | 0.982 |
| Max | 1.064 |
| Mean | 1.023 |
| Violations (outside 0.95-1.05) | 2 buses |

Buses with voltage violations (above 1.05 pu):
- Bus 2: 1.052 pu
- Bus 36: 1.064 pu

No buses below 0.95 pu.

**Thermal loading:**

| Statistic | Value |
|-----------|-------|
| Max loading | 101.2% |
| Mean loading | 44.9% |
| Violations (>100%) | 1 line |

Line L2 loaded at 101.2% of its MVA rating.

**Reactive power:**

| Statistic | Value |
|-----------|-------|
| Total gen Q | 1510.8 Mvar |
| Min gen Q | 41.1 Mvar |
| Max gen Q | 233.7 Mvar |

**Voltage angle spread:** 29.9 degrees

## Workarounds

- **What:** Manually set `p_set` on generators from DC OPF dispatch results before
  running `n.pf()`.
- **Why:** PyPSA separates OPF (`n.optimize()`) from PF (`n.pf()`). To run AC PF on
  OPF dispatch, the user must transfer dispatch results to generator `p_set` attributes.
  This is a two-step workflow but remains within the same network object.
- **Durability:** stable -- Uses documented public API (`generators.p_set` and `n.pf()`).
  The approach is shown in PyPSA examples and the `optimize_and_run_non_linear_powerflow()`
  convenience method exists for this exact pattern.
- **Grade impact:** Minimal. The two-step pattern is standard and well-documented.
- **Version tested:** PyPSA 1.1.2

- **What:** Manually set marginal_cost from gencost (inherited from A-3).
- **Why:** PPC importer does not import gencost.
- **Durability:** stable
- **Grade impact:** Minor, well-documented limitation.

## Timing

- **Wall-clock:** 0.117 s (AC PF solve only)
- **Peak memory:** not measured
- **Solver iterations:** Newton-Raphson (converged on flat start)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a4_ac_feasibility.py`

Key API pattern:

```python
# DC OPF
n.optimize(solver_name="highs", solver_options={...})
# Transfer dispatch to PF
for gen in n.generators.index:
    n.generators.loc[gen, "p_set"] = float(n.generators_t.p.iloc[0][gen])
# AC PF (same network object)
n.pf()
# Check violations
v_mag = n.buses_t.v_mag_pu.iloc[0]
s_flow = np.sqrt(n.lines_t.p0.iloc[0]**2 + n.lines_t.q0.iloc[0]**2)
```
