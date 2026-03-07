---
test_id: A-8
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 0.013
peak_memory_mb: null
loc: 80
solver: "HiGHS"
timestamp: 2026-03-06T01:00:00Z
---

# A-8: Stochastic Time-series DCOPF

## Result: FAIL

## Approach

Investigated GridCal's API for native stochastic programming support (scenario-tree, two-stage stochastic OPF). Found:

1. `StochasticPowerFlowDriver` exists but is Monte Carlo simulation, not stochastic optimization
2. `OptimalPowerFlowTimeSeriesDriver` solves deterministic multi-period problems — no scenario indexing
3. No scenario-related options in `OptimalPowerFlowOptions`
4. No stochastic OPF formulation in the MIP code

Attempted loop-based workaround using `OptimalPowerFlowTimeSeriesDriver` with per-scenario profile perturbations. All 5 scenarios failed:
- Scenario 0: `ValueError: 0 is not a valid TapPhaseControl`
- Scenarios 1-4: `TypeError: 'NoneType' object is not subscriptable`

These errors indicate the time-series OPF driver has issues with the case39.m network's transformer data when time profiles are set.

## Output

No successful output — all scenarios errored.

## Workarounds

- **What:** Loop-based multi-scenario DCOPF (each scenario solved independently)
- **Why:** GridCal has no native stochastic programming formulation
- **Durability:** blocking — implementing scenario-tree or two-stage stochastic programming would require modifying the MIP formulation source code
- **Grade impact:** Significant — the pass condition explicitly requires native stochastic structure in the optimization formulation, not independent deterministic solves in a loop

## Timing

- **Wall-clock:** 0.013s (all scenarios errored quickly)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a8_stochastic_timeseries.py`
