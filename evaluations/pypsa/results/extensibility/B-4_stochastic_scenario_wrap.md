---
test_id: B-4
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: v9
skill_version: v1
test_hash: 0f696058
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 8.35
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 168
solver: highs
timestamp: 2026-03-11T00:00:00Z
---

# B-4: Stochastic Scenario Wrap (stochastic_scenario_wrap)

## Result: PASS

## Approach

Loaded case39.m with differentiated marginal costs ($10–$100/MWh). Added 200 MW wind generator (bus '6') and 150 MW solar generator (bus '7'). Set 12-hour snapshots via `n.set_snapshots(pd.date_range(..., periods=12, freq='h'))`.

Generated 20 scenarios using `numpy.random.default_rng(42)`:
- Load multiplier: Uniform(0.85, 1.05) × 12 hours
- Wind CF: Uniform(0.1, 0.7) × 12 hours
- Solar CF: Uniform(0.0, 0.5) × 12 hours

For each scenario, the per-scenario timeseries was injected programmatically:
```python
n_s.loads_t.p_set[load_name] = load_mult_series * base_p
n_s.generators_t.p_max_pu["Wind"] = scenario["wind_cf"]
n_s.generators_t.p_max_pu["Solar"] = scenario["solar_cf"]
```

This is the documented PyPSA timeseries assignment API — no file I/O required.

Each scenario ran `n_s.optimize(snapshots=n_s.snapshots, solver_name="highs")` and collected LMPs, total cost, and dispatch.

**Workaround required:** Each scenario requires a full network re-construction (re-load from `.m` file, re-add components). PyPSA has no native "reset scenario parameters" mechanism on an existing network object. After `n.optimize()`, the linopy model is attached to the network; re-running with different timeseries would require clearing the model state. The clean approach is per-scenario network construction.

## Output

**Run summary:**
- 20/20 scenarios solved successfully
- Total wall-clock: 8.35 s (including ~1.1 s overhead for base network load)
- Mean per-scenario wall-clock: 0.361 s
- Solve time per scenario: ~0.34 s (network build + linopy model + HiGHS solve)

**Cost statistics across 20 scenarios:**

| Metric | Value |
|--------|-------|
| Min total cost | $3,110,734/12h |
| Max total cost | $3,468,636/12h |
| Mean total cost | $3,309,517/12h |
| Std dev | $94,997/12h |

**LMP statistics:**
- Mean LMP across all scenarios: $90.91/MWh
- LMP range observed: varies by scenario (wind/solar CFs and load levels)

**Overhead assessment:**
- Per-scenario overhead ≈ 0.36 s total (network build ~0.02 s + linopy model build ~0.1 s + solve ~0.24 s for 12-hour LP)
- Loop is expressible as a clean Python `for` loop — no framework ceremony required
- Timeseries injection is 2 lines of code per component type

**Scenario expressiveness:** Clean. The loop pattern is:
```python
for scenario in scenarios:
    n_s = build_network()
    n_s.loads_t.p_set[...] = scenario["loads"]
    n_s.generators_t.p_max_pu[...] = scenario["cf"]
    n_s.optimize(...)
    collect_results(n_s)
```

## Workarounds

- **What:** Full per-scenario network reconstruction (re-load from `.m` file + re-add wind/solar generators + reassign costs/limits).
- **Why:** PyPSA has no built-in mechanism to reset network state between successive solves when timeseries change. The linopy model is not reusable across different `optimize()` calls on the same network with different `loads_t.p_set`. Clearing and rebuilding is the standard pattern.
- **Durability:** stable — per-scenario network construction is the documented and intended pattern in PyPSA's stochastic examples. The network object is lightweight; linopy model build adds ~0.1 s per scenario for this size.
- **Grade impact:** Low. The timeseries injection API itself (`loads_t.p_set`, `generators_t.p_max_pu`) is clean and documented. The reconstruction overhead is modest (~0.36 s/scenario for 39-bus, 12-hour LP).

## Timing

- **Wall-clock:** 8.35 s total (20 scenarios × 12-hour LP)
- **Timing source:** measured
- **Mean per-scenario:** 0.361 s
- **Peak memory:** not measured
- **CPU cores used:** 1 (configured)

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b4_stochastic_scenario_wrap_tiny.py`
