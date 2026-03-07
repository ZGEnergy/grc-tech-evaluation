---
test_id: B-4
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 9.68
peak_memory_mb: null
loc: 316
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# B-4: Stochastic Wrapping

## Result: PASS

## Approach

Built a 20-scenario stochastic wrapping loop around PyPSA's DC OPF on the IEEE 39-bus
network. Each scenario uses 12 hourly snapshots with correlated perturbations
independent by resource type:

1. Loaded case39.m via the standard MATPOWER import pipeline with manual gencost
   assignment (inherited workaround from A-3).
2. Set up 12 hourly snapshots via `n.set_snapshots(pd.date_range(...))`.
3. Added two renewable generators (Wind_1 at bus 3, Solar_1 at bus 7) with
   time-varying `p_max_pu` profiles (sinusoidal wind, diurnal solar).
4. Classified existing generators by cost quartile into baseload/intermediate/peaker.
5. Generated 20 scenarios with independent perturbations per resource type using
   `np.random.default_rng(seed=42)` with uniform distributions.
6. For each scenario: `n_base.copy()` to clone the network, update `loads_t.p_set`
   (load scaling), `generators.p_nom` (capacity perturbation by type),
   `generators_t.p_max_pu` (renewable profile perturbation), then `n.optimize()`.
7. Collected LMPs (`n.buses_t.marginal_price`), dispatch (`n.generators_t.p`), and
   objectives into pandas DataFrames with scenario labels.

## Output

| Metric | Value |
|--------|-------|
| Scenarios requested | 20 |
| Scenarios solved | 20 |
| Hours per scenario | 12 |
| Total wall-clock | 9.68 s |
| Solve time (total) | 7.86 s |
| Solve time (mean) | 0.39 s |
| Solve time (std) | 0.09 s |
| Solve time (min) | 0.34 s |
| Solve time (max) | 0.75 s |

**Objective value statistics across 20 scenarios:**

| Statistic | Value ($/hr) |
|-----------|-------------|
| Mean | 22,351.45 |
| Std | 1,047.0 |
| Min | 20,509.33 |
| Max | 23,710.30 |

**LMP statistics across all scenarios and buses:**

| Statistic | Value ($/MWh) |
|-----------|--------------|
| Mean | 0.319 |
| Std | 0.010 |
| Min | 0.300 |
| Max | 0.335 |

**Dispatch total mean:** 6,277.3 MW

**Result format:** pandas DataFrame with scenario column -- structured and immediately
usable for statistical analysis.

## Workarounds

- **What:** Manually set `marginal_cost` from gencost data.
- **Why:** PPC importer does not import gencost.
- **Durability:** stable -- Uses documented public API.
- **Grade impact:** Minimal; inherited limitation from MATPOWER import.

## Timing

- **Wall-clock:** 9.68 s (total for 20 scenarios including network copy and data setup)
- **Solve time per scenario:** 0.39 s mean (HiGHS, 12-hour multi-period DCOPF)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b4_stochastic_wrapping.py`

Key API pattern for scenario loop:

```python
n_base.set_snapshots(pd.date_range("2024-01-01", periods=12, freq="h"))
n_base.loads_t.p_set = load_df  # DataFrame assignment for time-varying loads
n_base.generators_t.p_max_pu = p_max_pu_df  # DataFrame for renewable profiles

for scenario in scenarios:
    n = n_base.copy()
    # Update loads, gen capacity, renewable profiles via DataFrame assignment
    n.loads_t.p_set = load_scenario_df
    n.generators_t.p_max_pu = p_max_pu_scenario_df
    n.optimize(solver_name="highs", solver_options={...})
    # Collect: n.buses_t.marginal_price, n.generators_t.p, n.objective
```

The `n.copy()` + direct DataFrame assignment pattern makes scenario loops clean and
efficient. No model reconstruction, no configuration files, no per-scenario overhead
beyond the copy itself. Results are immediately available as pandas DataFrames.
