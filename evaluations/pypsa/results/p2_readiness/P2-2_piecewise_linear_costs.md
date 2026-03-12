---
test_id: P2-2
tool: pypsa
dimension: p2_readiness
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 901ffa0d
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
timestamp: 2026-03-11T00:00:00Z
---

# P2-2: Piecewise-Linear Cost Curves

## Result: INFORMATIONAL

## Finding

PyPSA 1.1.2 has no native piecewise-linear cost (PLC) formulation for generators. The built-in cost model is linear (`marginal_cost`) plus quadratic (`marginal_cost_quadratic`). However, convex PLC can be implemented via the `extra_functionality` callback using linopy auxiliary variables and segment constraints; linopy 0.6.4 also exposes `add_sos_constraints()` for SOS2 formulations when a MILP solver is needed. The approach is functional but requires ~30–50 LOC of custom formulation per generator type.

## Evidence

**Native PyPSA generator cost attributes:**

```python
import pypsa
n = pypsa.Network()
n.add('Bus', 'b1', v_nom=345., carrier='AC')
n.add('Generator', 'g1', bus='b1', p_nom=100.)
cost_cols = [c for c in n.generators.columns if 'cost' in c.lower()]
# → ['marginal_cost', 'marginal_cost_quadratic', 'capital_cost',
#     'overnight_cost', 'fom_cost', 'start_up_cost', 'shut_down_cost', 'stand_by_cost']
```

No piecewise, PWL, or SOS2 cost attribute exists in the generator schema. Source search confirms:

```bash
$ grep -ri 'piecewise\|pwl\|sos2\|piece_wise\|piecewise_generator' \
    .venv/lib/python3.12/site-packages/pypsa/optimization/optimize.py
357: "or use a piecewise-linear approximation)."   # only in a warning about CVaR+quadratic
```

The only piecewise reference in `optimize.py` is a warning that CVaR constraints cannot be combined with quadratic costs, which suggests using "a piecewise-linear approximation" as an alternative — but the framework provides no such built-in approximation for generator costs.

**`marginal_cost_quadratic` is the native non-linear cost option:**

From `pypsa/optimization/optimize.py` lines 239–256:
```python
# marginal cost quadratic
for c_name, attr in lookup.query("marginal_cost_quadratic").index:
    ...
    cost = c.da.marginal_cost_quadratic.sel(snapshot=sns)
    is_quadratic = True
```

This produces a QP objective solvable by HiGHS in QP mode, but QP ≠ PLC. QP approximates a smooth convex cost curve; PLC exactly represents a stepped marginal cost function as required for MATPOWER-style gencost type 1.

**Convex PLC via auxiliary variables — confirmed working:**

A 3-segment PLC was successfully implemented using linopy's model API directly:

```python
import linopy, numpy as np

m = linopy.Model()
# 3-segment PLC: [0,30]@$10/MWh, [30,70]@$20/MWh, [70,100]@$35/MWh
p_max = np.array([30., 40., 30.])   # segment widths (MW)
slopes = np.array([10., 20., 35.])  # $/MWh per segment

segs = [m.add_variables(lower=0., upper=p_max[k], name=f's{k}') for k in range(3)]
total_p = m.add_variables(lower=0., upper=100., name='p_total')
m.add_constraints(segs[0] + segs[1] + segs[2] == total_p, name='sum_segs')
m.add_constraints(total_p == 75., name='load_balance')
m.add_objective(slopes[0]*segs[0] + slopes[1]*segs[1] + slopes[2]*segs[2])

m.solve(solver_name='highs')
# → s0=30.00 MW, s1=40.00 MW, s2=5.00 MW
# → PLC cost: 30×10 + 40×20 + 5×35 = 1275 USD ✓ (optimizer fills cheapest segments first)
```

The auxiliary variable approach is an LP reformulation of convex PLC: since slopes are non-decreasing, the LP relaxation is tight and no binary variables are required. This is standard and well-known (equivalent to MATPOWER's gencost type 1 with convex breakpoints).

**Integration into PyPSA via `extra_functionality`:**

The same auxiliary variable pattern works inside PyPSA's `extra_functionality` callback:

```python
def add_plc_cost(n, sns):
    m = n.model
    gen_p_pu = m.variables['Generator-p']  # per-unit dispatch variable
    # (add segment variables, PLC-sum constraint, modify objective)
    m.add_objective(plc_cost_expr, overwrite=True)  # must overwrite=True
```

Friction points:
1. The generator must have `marginal_cost=1e-9` (non-zero) to pass PyPSA's objective validation before `extra_functionality` is called. Then `overwrite=True` replaces the trivial cost with the PLC expression.
2. `marginal_cost_quadratic` cannot coexist with CVaR stochastic constraints — not relevant for standard OPF.
3. Segment variable coordinates must use `pd.Index(..., name='name')` to match PyPSA's xarray dimension naming convention.

**SOS2 support in linopy 0.6.4:**

```python
import linopy
m = linopy.Model()
lam = m.add_variables(lower=0., upper=1., coords=[pd.Index([0,30,70,100], name='bp')], name='lambda')
m.add_sos_constraints(lam, sos_type=2, sos_dim='bp')  # ← succeeds, no error
```

`linopy.Model.add_sos_constraints(variable, sos_type, sos_dim)` is a supported method. SOS2 enables non-convex PLC (where a generator can be at any point along the piecewise curve, including non-convex segments), but requires the solver to handle SOS constraints. HiGHS supports SOS2 (it is included in HiGHS's MILP branch-and-bound). Whether PyPSA's `n.optimize()` correctly propagates SOS2 constraints to HiGHS via linopy was not fully verified — the SOS2 constraint was added to a raw linopy model but not routed through `n.optimize()`.

**Solver compatibility:**

| Formulation | Solver requirement | Status |
|---|---|---|
| Linear `marginal_cost` | LP (HiGHS) | Native, fully supported |
| `marginal_cost_quadratic` | QP (HiGHS supports) | Native, fully supported |
| Convex PLC via aux vars | LP (HiGHS) | Functional via `extra_functionality` |
| Non-convex PLC via SOS2 | MILP+SOS2 (HiGHS) | Linopy has API; PyPSA integration not fully verified |

## Phase 2 Implications

If PyPSA is selected for Phase 2, piecewise-linear cost curves (MATPOWER gencost type 1) will require the auxiliary-variable workaround for each generator. The operational implications are:

- **Convex PLC (non-decreasing slopes):** Fully achievable as LP via `extra_functionality`. ~30–50 LOC per generator type (or ~80–100 LOC for a generic PLC helper function). No solver upgrade needed — HiGHS LP handles it.
- **Non-convex PLC (non-monotone slopes, rare in practice):** Would require SOS2 MILP. The linopy API supports it but PyPSA-to-HiGHS routing for SOS2 was not confirmed. This scenario is uncommon in grid operations (monotone heat rates are the norm).
- **MATPOWER gencost import gap:** The `import_from_pypower_ppc()` path does not import gencost (confirmed in prior research — gencost arrays are silently discarded). Both PW_LINEAR (type 1) and POLYNOMIAL (type 2) costs must be assigned manually after import. This is a consistent limitation across all cost types, not specific to PLC.
- **Recommended Phase 2 approach:** Implement a `add_piecewise_cost(n, gen_name, breakpoints, costs)` helper that uses the auxiliary variable pattern. This provides a reusable, tested abstraction and isolates the formulation complexity from test scripts.
