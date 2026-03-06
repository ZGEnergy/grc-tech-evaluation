---
test_id: D-3
tool: pypsa
dimension: accessibility
status: pass
timestamp: 2026-03-05
---

# D-3: Example verification -- getting-started examples

## Finding

The canonical PyPSA getting-started pattern (build network with `n.add()`, run
`n.optimize()`) works correctly on PyPSA v1.1.2 in the devcontainer. The example
produces correct results with no errors.

## Evidence

Ran a representative getting-started example based on the docs.pypsa.org patterns:

```python
import pypsa
import pandas as pd

n = pypsa.Network()
n.set_snapshots(pd.date_range('2024-01-01', periods=3, freq='h'))
n.add('Bus', 'bus0')
n.add('Bus', 'bus1')
n.add('Bus', 'bus2')
n.add('Line', 'line01', bus0='bus0', bus1='bus1', s_nom=100, x=0.1)
n.add('Line', 'line12', bus0='bus1', bus1='bus2', s_nom=100, x=0.1)
n.add('Generator', 'gen0', bus='bus0', p_nom=100, marginal_cost=10)
n.add('Generator', 'gen1', bus='bus1', p_nom=100, marginal_cost=20)
n.add('Load', 'load2', bus='bus2', p_set=50)
result = n.optimize(solver_name='highs')
```

**Results:**
- Status: `('ok', 'optimal')`
- Objective: 1500.00 (correct: 50 MW x 3 hours x $10/MWh)
- Dispatch: gen0=50 MW (cheapest), gen1=0 MW -- correct economic dispatch
- LMPs: uniform $10/MWh at all buses (no congestion) -- correct

**Warnings emitted (non-fatal):**
- `FutureWarning` about `include_objective_constant` default changing in v2.0
- Consistency warnings about undefined carriers and zero-resistance lines
- These are cosmetic and do not affect results

**Notable:** The `n.add()` pathway works flawlessly. The friction documented in D-1
(import path issues, gencost drop) only affects users loading external case files
via `import_from_pypower_ppc()` or `import_from_pandapower_net()`.

## Implications

PyPSA's primary tutorial pathway (build-from-scratch via `n.add()`) is reliable and
produces correct results. This is a positive signal for new-user onboarding when
following the documentation's intended workflow. The gap is between this clean pathway
and the MATPOWER import pathway that power-systems researchers commonly need.
