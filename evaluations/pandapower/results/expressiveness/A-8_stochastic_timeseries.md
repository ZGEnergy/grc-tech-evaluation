---
test_id: A-8
tool: pandapower
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# A-8: Solve multi-period (12hr) DCOPF with stochastic load and renewable generation scenarios

## Result: FAIL

## Approach

Skipped on MEDIUM. A-8 FAILED on TINY due to architectural limitation: pandapower has no native stochastic OPF formulation. The pass condition requires the stochastic structure to be part of the optimization formulation (scenario tree, two-stage stochastic program), not just independent deterministic solves in a loop.

A loop-based workaround is tested separately in B-4 and C-6.

See `A-8_stochastic_timeseries_TINY.md` for full analysis.

## Workarounds

- **What:** No workaround exists within the tool for native stochastic OPF.
- **Why:** pandapower's architecture is built around single-snapshot analysis.
- **Durability:** blocking
- **Grade impact:** Fail. Loop-based workaround tested in B-4/C-6.

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a8_stochastic_timeseries.py`
