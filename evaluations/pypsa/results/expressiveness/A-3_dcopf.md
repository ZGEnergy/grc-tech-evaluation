---
test_id: A-3
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 0.478
peak_memory_mb: null
loc: 109
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# A-3: Solve DC OPF with generation costs and line flow limits

## Result: PASS

## Approach

Loaded the IEEE 39-bus network via the standard MATPOWER import pipeline. The PPC
importer does **not** import `gencost` data (PyPSA warns: "some PYPOWER features not
supported: areas, gencosts, component status"). Therefore, cost data was parsed from
the `.m` file via `matpowercaseframes` and manually assigned to
`n.generators["marginal_cost"]`.

For case39, all 10 generators have polynomial cost curves (type 2) with coefficients
C2=0.01, C1=0.3, C0=0.2. The linear coefficient C1=0.3 was used as `marginal_cost`
for the DC OPF LP formulation.

Solved DC OPF using `n.optimize(solver_name="highs")` with normalized HiGHS settings:
- `time_limit`: 300
- `presolve`: on
- `threads`: 1
- `output_flag`: True

## Output

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Solver status | optimal |
| Objective value | 1876.269 |
| HiGHS iterations | 27 (dual simplex) |
| Output format | pandas DataFrame |

**Generator dispatch (MW):**

| Generator | Dispatch (MW) |
|-----------|--------------|
| G0 | 900.0 |
| G1 | 646.0 |
| G2 | 725.0 |
| G3 | 652.0 |
| G4 | 508.0 |
| G5 | 687.0 |
| G6 | 580.0 |
| G7 | 456.23 |
| G8 | 0.0 |
| G9 | 1100.0 |
| **Total** | **6254.23** |

**LMPs ($/MWh):**

| Statistic | Value |
|-----------|-------|
| Min | 0.30 |
| Max | 0.30 |
| Mean | 0.30 |
| Buses with LMP | 39 |

All LMPs are uniform at 0.30 $/MWh because all generators have identical marginal
costs (C1=0.3) and no line congestion occurs (all flows within thermal limits).

**Line flows (MW):**

| Statistic | Value |
|-----------|-------|
| Min | -643.22 |
| Max | 501.85 |
| Num lines | 35 |

**Line shadow prices:** PyPSA's `n.optimize()` assigns bus-level LMPs
(`n.buses_t.marginal_price`) but does **not** assign line flow constraint duals
(`mu_upper`/`mu_lower`) to the network by default. The solver log confirms:
"The shadow-prices of the constraints ... Line-fix-s-lower, Line-fix-s-upper ...
were not assigned to the network." Line congestion duals would need to be extracted
from the Linopy model object at `n.model`.

## Workarounds

- **What:** Manually parsed gencost data from the MATPOWER `.m` file and set
  `n.generators["marginal_cost"]` for each generator.
- **Why:** PyPSA's `import_from_pypower_ppc()` does not import the `gencost` table.
  Without marginal costs, the optimizer has no cost objective.
- **Durability:** stable -- Uses the documented public `marginal_cost` attribute on
  generators. The limitation is well-documented (PyPSA emits a warning about
  unsupported PPC features). The workaround uses `matpowercaseframes` (a public
  package) to parse costs and the standard DataFrame column assignment to set them.
- **Grade impact:** Minor. The workaround is straightforward (5 lines of code) and
  uses only public API. It reflects a limitation of the PPC importer, not of PyPSA's
  OPF capability itself.
- **Version tested:** PyPSA 1.1.2

## Timing

- **Wall-clock:** 0.478 s (includes Linopy model construction + HiGHS solve)
- **Peak memory:** not measured
- **Solver iterations:** 27 (HiGHS dual simplex)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a3_dcopf.py`

Key API pattern:

```python
n.optimize(solver_name="highs", solver_options={...})
# Results:
n.generators_t.p          # dispatch
n.buses_t.marginal_price  # LMPs
n.lines_t.p0              # line flows
n.objective               # objective value
```
