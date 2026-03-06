# B-4: Stochastic Scenario Wrapping — 50-Scenario DCPF (TINY)

- **Test ID:** B-4
- **Slug:** stochastic_wrapping
- **Tool:** PyPSA 1.1.2
- **Network:** IEEE 39-bus (case39.m)
- **Status:** PASS
- **Workaround durability:** N/A (no workaround needed)

## Pass Condition

Timeseries injectable via API, scenario loop without excessive overhead.

## Results

| Metric | Value |
|--------|-------|
| Wall clock (50 scenarios x 24hr) | 5.90 s |
| Per-scenario average | 0.118 s |
| Scenarios completed | 50 / 50 |
| Hours per scenario | 24 |
| Total DCPF solves | 50 |
| Loads perturbed | 21 |
| LOC | ~20 lines |

### Scenario Statistics

| Metric | Range |
|--------|-------|
| Mean total gen (MW) across scenarios | 6113 - 6326 |
| Max line loading across scenarios | 0.765 - 1.281 |

### Scenario Generation

Temporally correlated load perturbations using AR(1) structure (rho=0.8, sigma=5%). Per-load variation drawn from N(1.0, 0.02).

## API

Timeseries injection is fully programmatic via DataFrame assignment:

```python
n.set_snapshots(pd.date_range("2026-01-01", periods=24, freq="h"))
for load_name in n.loads.index:
    n.loads_t.p_set[load_name] = load_profile[load_name].values
n.lpf()
```

No config file rewriting needed. Each scenario creates a fresh Network object, sets snapshots, injects load timeseries, and solves. Results are collected as DataFrames.

## Observations

- Network reconstruction per scenario (re-parsing the MATPOWER file) adds ~0.02s overhead per scenario. For larger networks this could become significant.
- PyPSA's timeseries interface via `n.loads_t.p_set` is clean and Pythonic.
- Multi-period DCPF solves all 24 hours in a single `n.lpf()` call.

## Test Script

`evaluations/pypsa/tests/extensibility/test_b4_stochastic_wrapping_tiny.py`
