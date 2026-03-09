---
probe_id: probe-002
tool: pypsa
source_test: D-2
probe_type: claim_verification
classification: claim_supported
reason: "D-2 correctly states stochastic API is documented; A-8 incorrectly states API methods don't exist but correctly concludes FAIL due to optimizer integration bugs"
solver_version: "pypsa 1.1.2, highs 1.13.1"
solver_version_match: true
timeout_seconds: 300
wall_clock_seconds: 12
timestamp: 2026-03-09T00:00:00Z
---

# Probe 002: PyPSA stochastic optimization documentation vs functionality

## Original Claim

From `evaluations/pypsa/results/accessibility/D-2_documentation_audit.md` (v4 evaluation):

> A-8 Stochastic Optimization: **Documented: YES (as of v1.x).** Dedicated page
> (`user-guide/optimization/stochastic/`) documents `n.set_scenarios()`,
> `n.set_risk_preference()`, and the two-stage stochastic programming formulation.
> An example notebook exists at `examples/stochastic-optimization/`.

From `evaluations/pypsa/results/expressiveness/A-8_stochastic_timeseries.md` (v4 evaluation):

> `n.optimize()` parameters **do not include a `scenarios` argument**. [...]
> No `optimize_stochastic()` or scenario-weighted objective method exists. [...]
> PyPSA v1.1.2 does not support scenario-indexed stochastic optimization.
>
> Result: FAIL

The tension: D-2 says the stochastic API is documented with dedicated pages and methods;
A-8 says those methods don't exist and the feature doesn't work.

## Probe Methodology

Two scripts were run:

1. **probe-002_script.py**: Inspected PyPSA v1.1.2 for stochastic-related attributes,
   methods, and source references.

2. **probe-002b_script.py**: Functional test that actually calls `set_scenarios()`,
   `set_risk_preference()`, and `optimize()` on simple networks with scenarios.

## Probe Results

### API Inspection (probe-002_script.py)

```
n.set_scenarios exists
  signature: (scenarios: dict | Sequence | pd.Series | pd.DataFrame | None = None, **kwargs: Any) -> None
  docstring: "Set scenarios for the network to create a stochastic network."

n.set_risk_preference exists
  signature: (alpha: float, omega: float) -> None
  docstring: "Set risk aversion preferences for stochastic optimization using CVaR formulation."

n.scenarios = Index([], dtype='object', name='scenario')
n.has_scenarios = False
n.scenario_weightings = Empty DataFrame with 'weight' column
n._scenarios_data, n._risk_preference, n.get_scenario all present
```

Extensive scenario/stochastic references found in PyPSA source: 61 mentions in
`networks.py`, 115 in `consistency.py`, 110 in `network/index.py`, 97 in
`optimization/global_constraints.py`, 32 in `optimization/optimize.py`.

### Functional Test (probe-002b_script.py)

#### Test 1: Single-bus network with scenarios + risk preference -- WORKS

```
n.set_scenarios(low=0.5, high=0.5)  # Scenarios set successfully
n.set_risk_preference(alpha=0.5, omega=0.5)  # Risk preference set
n.optimize(solver_name="highs")  # Status: ok, Condition: optimal, Objective: 1500.0
```

The CVaR-based stochastic optimization ran successfully on a simple single-bus
network. HiGHS solved an LP with 21 rows, 10 cols. The solver log shows
CVaR-related constraints (`CVaR-excess-low`, `CVaR-excess-high`, `CVaR-def`).

#### Test 2: Two-bus network with scenario-indexed load time series -- CRASHES

```
n.set_scenarios(low=0.5, high=0.5)  # OK
n.loads_t.p_set = scenario_indexed_dataframe  # OK, data accepted
n.optimize(solver_name="highs")  # CRASHES:
  ValueError: Buffer dtype mismatch, expected 'Python object' but got 'long'
```

The crash occurs deep in the constraint definition code when trying to reindex
scenario-indexed time series data. This is a pandas compatibility bug in the
optimizer's constraint builder.

## Analysis

The probe reveals a nuanced situation:

1. **D-2 is correct** that PyPSA v1.1.2 has a documented stochastic optimization API.
   The methods `set_scenarios()`, `set_risk_preference()`, `scenarios`, `has_scenarios`,
   `scenario_weightings`, etc. all exist. The `set_risk_preference` docstring describes
   CVaR formulation with alpha/omega parameters and includes usage examples.

2. **A-8 is partially incorrect** in its claims. It states:
   - "No `optimize_stochastic()` or scenario-weighted objective method exists" -- while
     there's no `optimize_stochastic()`, the standard `optimize()` does handle scenarios
     when `set_scenarios()` has been called (proven by Test 1).
   - "`n.optimize()` parameters do not include a `scenarios` argument" -- true, but
     scenarios are set on the network object, not passed to optimize.
   - "The `n.scenarios` attribute exists but is not wired into the optimizer" -- incorrect;
     the simple case works and the optimizer generates CVaR constraints.

3. **A-8's FAIL conclusion is defensible** but for the wrong reason. The stochastic API
   exists and partially works, but crashes on multi-component networks with
   scenario-indexed time series. The original test likely hit this bug (or didn't discover
   `set_scenarios()` at all) and concluded the feature was absent rather than buggy.

4. **The D-2/A-8 tension is real**: the documentation says stochastic optimization works,
   and the API partially does, but there's a bug that prevents it from working on
   realistic networks with heterogeneous time series.

## Classification Rationale

Classified as **claim_supported** because the D-2 claim under scrutiny -- that stochastic
optimization is "documented with dedicated page and example notebook" while A-8 FAILs --
is accurate. The API methods exist and are documented. The A-8 FAIL is also legitimate
(the feature doesn't work reliably on realistic networks), though the A-8 result
mischaracterizes the root cause as "feature architecturally absent" when it's actually
"feature exists but has integration bugs."

The probe adds a data point that the original A-8 evaluation did not discover: the
stochastic API works on simple cases but crashes on multi-component scenarios due to a
pandas dtype mismatch in the constraint builder. This is a more nuanced finding than
either the A-8 or D-2 results captured individually.
