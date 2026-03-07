---
test_id: C-6
tool: gridcal
dimension: scalability
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: null
peak_memory_mb: null
loc: 0
solver: "HiGHS"
timestamp: 2026-03-06T04:00:00Z
---

# C-6: Stochastic Scale (Grade: SMALL)

## Result: FAIL

Not tested. Stochastic OPF failed at the TINY tier (A-8) due to architectural limitations:

1. No native stochastic programming formulation (no scenario-tree, no two-stage OPF).
2. `StochasticPowerFlowDriver` is Monte Carlo simulation, not stochastic optimization.
3. Time-series OPF driver crashes on MATPOWER files, preventing even loop-based workarounds.

These are fundamental capability gaps unrelated to network size. No scalability test is possible.

## Reference

- **A-8 result:** FAIL (blocking)
- **Test script:** N/A (not run)
