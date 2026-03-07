---
test_id: A-8
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 1.54
peak_memory_mb: null
loc: 360
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# A-8: Stochastic Timeseries

## Result: FAIL

## Approach

Loaded IEEE 39-bus network from `case39.m`. Added wind (200 MW) and solar (150 MW) generators with time-varying capacity factors over 12 hourly snapshots. Created 3 scenarios with independent perturbations per resource type:

- **Load:** +/- 5% std normal perturbation on base profile
- **Wind:** +/- 15% std normal perturbation on base CF profile
- **Solar:** +/- 10% std normal perturbation on base CF profile

Perturbations were generated independently for each resource type using `numpy.random.Generator` with seed 42.

### Investigation of native stochastic support

1. **`n.scenarios` attribute exists** -- it is a `pandas.Index([], dtype='object', name='scenario')`, suggesting the data model has a placeholder for scenario indexing, but it is empty and no API method populates it for optimization.

2. **`n.optimize()` parameters** do not include a `scenarios` argument. The available parameters are: `snapshots`, `multi_investment_periods`, `transmission_losses`, `linearized_unit_commitment`, `model_kwargs`, `extra_functionality`, `assign_all_duals`, `solver_name`, `solver_options`, etc.

3. **Available optimize sub-methods** include MGA (`optimize_mga`), SCOPF (`optimize_security_constrained`), rolling horizon (`optimize_with_rolling_horizon`), and transmission expansion (`optimize_transmission_expansion_iteratively`) -- but no stochastic/scenario method.

4. **No scenario-indexed optimization module** exists in the PyPSA v1.1.2 optimization subsystem. The research context noted v1.0 added "stochastic optimization" but this appears to refer to the scenario data structure in the Network object, not a joint stochastic optimization formulation.

### Fallback: Deterministic loop

As a fallback, solved each scenario independently via sequential `n.optimize()` calls. All 3 scenarios converged optimally with prices extractable from `n.buses_t.marginal_price`.

## Output

### Native Stochastic Support: NOT AVAILABLE

PyPSA v1.1.2 does not support scenario-indexed stochastic optimization where scenarios are jointly optimized (e.g., two-stage stochastic program, scenario tree). The `n.scenarios` attribute exists as an empty Index in the data model but is not wired into the optimizer.

### Deterministic Loop Results (fallback, does not satisfy pass condition)

| Scenario | Objective ($) | Solve Time (s) | Mean LMP ($/MWh) | Status |
|----------|--------------|----------------|-------------------|--------|
| 0 | 17,568.03 | 0.45 | 0.30 | Optimal |
| 1 | 17,849.47 | 0.36 | 0.30 | Optimal |
| 2 | 17,729.86 | 0.38 | 0.30 | Optimal |

### Perturbation Independence: VERIFIED

All three resource types (load, wind, solar) had distinct profiles across scenarios, confirming independent perturbation generation.

### Price Extraction: FUNCTIONAL (per-scenario)

LMPs are extractable from each deterministic solve via `n.buses_t.marginal_price`. However, since scenarios are solved independently, there is no cross-scenario price structure (e.g., expected cost, scenario-weighted prices).

## Workarounds

- **What:** No workaround possible for native stochastic optimization. Only sequential independent deterministic solves are achievable.
- **Why:** PyPSA v1.1.2 lacks a stochastic optimization formulation. The `n.scenarios` data structure exists but is not connected to the optimizer. No `optimize_stochastic()` or scenario-weighted objective method exists.
- **Durability:** blocking -- the feature is architecturally absent. Would require either (a) PyPSA to implement a stochastic optimization backend, or (b) the user to manually construct a combined Linopy model spanning all scenarios via `extra_functionality`, which would be extremely complex and fragile.
- **Grade impact:** This is a core capability gap. The pass condition explicitly requires the stochastic structure to be part of the optimization formulation, not independent deterministic solves in a loop.

## Timing

- **Wall-clock (total):** 1.54s (3 sequential deterministic solves + overhead)
- **Total solver time:** 1.20s (across 3 solves)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a8_stochastic_timeseries.py`
