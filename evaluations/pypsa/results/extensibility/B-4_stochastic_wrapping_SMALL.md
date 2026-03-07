---
test_id: B-4
tool: pypsa
dimension: extensibility
network: SMALL
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 2217.4
peak_memory_mb: null
loc: null
solver: highs
timestamp: 2026-03-07T00:00:00Z
---

# B-4: Stochastic Wrapping (SMALL)

## Result: PASS

## Approach

Generated 20 scenarios with correlated load/renewable perturbations by resource type
(baseload, intermediate, peaker, wind, solar). Solved 12-hour multi-period DCOPF per
scenario on the 2000-bus network using `n.copy()` + `n.optimize()` loop.

Added 2 renewable generators (Wind_1 at 500 MW, Solar_1 at 400 MW) with time-varying
availability profiles.

## Output

| Metric | Value |
|--------|-------|
| Scenarios requested | 20 |
| Scenarios solved | 20 |
| Total time | 2217 s |
| Mean solve time | 110.6 s |
| Min solve time | 44.4 s |
| Max solve time | 311.6 s |
| Objective mean | $10,245,324 |
| Objective std | $658,393 |

**LMP summary (across scenarios):**

| Metric | Value |
|--------|-------|
| Mean LMP | 18.18 $/MWh |
| LMP range | [0.0, 24.85] $/MWh |

## API Pattern

```python
n_base = load_network(...)
for scenario in scenarios:
    n = n_base.copy()
    n.loads_t.p_set = scenario_loads
    n.generators_t.p_max_pu = scenario_profiles
    n.generators.loc[gen, "p_nom"] = p_nom * factor
    n.optimize(solver_name="highs", solver_options=...)
```

The pattern is clean: `n.copy()` creates independent network instances, DataFrame
assignment handles timeseries perturbation, and `n.optimize()` solves each scenario.
No excessive per-scenario overhead beyond the solve itself.

## Workarounds

- **What:** Manually set marginal_cost from gencost data (PPC importer does not
  import gencost). Stochastic optimization implemented as deterministic loop (PyPSA
  has no native scenario-indexed optimization).
- **Durability:** stable — uses only public API (copy, DataFrame assignment, optimize).
- **Grade impact:** The loop approach works but is not a native stochastic optimization.
  This is expected given A-8's finding that PyPSA lacks native stochastic support.
- **Version tested:** PyPSA 1.1.2

## Timing

- **Wall-clock:** 2217 s (20 scenarios x ~111s each)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b4_stochastic_wrapping_small.py`
