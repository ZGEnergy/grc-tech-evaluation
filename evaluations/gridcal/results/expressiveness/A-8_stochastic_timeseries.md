---
test_id: A-8
tool: gridcal
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: null
peak_memory_mb: null
loc: 80
solver: "HiGHS"
timestamp: 2026-03-06T03:00:00Z
---

# A-8: Stochastic Time-series DCOPF (Grade: SMALL)

## Result: FAIL

Same failure as TINY -- not re-tested on grade network. The failure is architectural:

1. No native stochastic programming formulation (no scenario-tree, no two-stage OPF).
2. `StochasticPowerFlowDriver` is Monte Carlo simulation, not stochastic optimization.
3. Time-series OPF driver crashes on case39.m, preventing even loop-based workarounds.

These are fundamental capability gaps unrelated to network size.

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a8_stochastic_timeseries.py` (TINY version; grade test not run)
