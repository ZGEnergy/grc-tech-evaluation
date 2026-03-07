---
test_id: A-8
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 1.284
peak_memory_mb: null
loc: 194
solver: PYPOWER interior point
timestamp: 2026-03-06T00:00:00Z
---

# A-8: Solve multi-period (12hr, hourly) DCOPF with stochastic load and renewable generation scenarios

## Result: FAIL

## Approach

pandapower does not support scenario-indexed stochastic OPF. The pass condition explicitly requires that the stochastic structure be part of the optimization formulation (e.g., scenario tree, two-stage stochastic program), not just independent deterministic solves in a loop.

To demonstrate what IS achievable, the test script:
1. Loaded IEEE 39-bus network and classified generators by cost quartile (baseload/intermediate/peaker).
2. Generated 5 scenarios with 12 hourly timesteps, applying independent load perturbations.
3. Solved each (scenario, hour) pair independently using `pp.rundcopp(net)`.

This sequential loop-based approach does NOT satisfy the pass condition.

## Output

| Metric | Value |
|--------|-------|
| Scenarios | 5 |
| Hours | 12 |
| Total solves | 60 |
| Converged solves | 54 (90%) |
| Per-solve avg time | 0.021 s |
| Total time | 1.284 s |

Sample results (scenario 0, hours 0-2):

| Hour | Converged | Objective | Mean LMP | Total Gen (MW) |
|------|-----------|-----------|----------|----------------|
| 0 | Yes | 22,499 | 9.49 | 4,136 |
| 1 | Yes | 17,277 | 8.32 | 3,608 |
| 2 | Yes | 17,165 | 8.29 | 3,596 |

6 of 60 solves did not converge (likely due to very low load scaling factors driving the system to infeasibility with the PYPOWER interior point solver).

## Workarounds

- **What:** pandapower has no native stochastic OPF formulation. No workaround exists within the tool.
- **Why:** The tool's architecture is built around single-snapshot power system analysis. Multi-period analysis is supported via `run_timeseries()` but this is sequential deterministic solving, not stochastic programming. There is no scenario tree, no recourse variable structure, and no expectation-based objective.
- **Durability:** blocking -- this is an architectural limitation. pandapower would need a fundamental redesign to support stochastic optimization natively.
- **Grade impact:** Fail on this sub-question. The tool can loop over scenarios but cannot formulate a stochastic program.

## Timing

- **Wall-clock:** 1.284 s (60 sequential DCOPF solves)
- **Per-solve average:** 0.021 s
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a8_stochastic_timeseries.py`
