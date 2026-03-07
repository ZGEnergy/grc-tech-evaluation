---
test_id: A-5
tool: pypsa
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: 664.0
peak_memory_mb: null
loc: 245
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# A-5: Security-Constrained Unit Commitment (SMALL)

## Result: FAIL

## Approach

Attempted 24-hour SCUC on ACTIVSg 2000-bus network using `n.optimize()` with
`committable=True` on thermal generators (~410 of 544 generators). HiGHS solver
with single-threaded, 600s time limit, 10% MIP gap tolerance.

UC parameters: min_up_time=3, min_down_time=2, ramp_limit_up=0.3,
ramp_limit_down=0.3, p_min_pu=0.3.

## Output

| Metric | Value |
|--------|-------|
| Wall-clock | 664 s |
| Solver status | time_limit |
| Dispatch | all zeros |
| Committable generators | 410 |
| Total generators | 544 |

The HiGHS solver hit the 600-second time limit. While it reported a feasible
status, the dispatch values are all zeros, indicating the solution is degenerate
or the solver did not find a meaningful feasible integer solution before timeout.

## Analysis

The SCUC problem at SMALL scale (2000 buses, 410 committable generators x 24 hours
= 9,840 binary variables) is too large for HiGHS single-threaded within 600s. This
is a significant scalability limitation for UC on realistic networks.

Built-in UC constraint types (min up/down time, startup/shutdown costs, ramp limits,
p_min_pu) are all available as declarative attributes. Reserve constraints require
`extra_functionality` callback.

## Workarounds

No workaround available — the solver cannot find a feasible solution within the
time budget. Multi-threading or a commercial solver (Gurobi, CPLEX) would likely
help but are outside the evaluation scope.

## Timing

- **Wall-clock:** 664 s (600s solver + overhead)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a5_scuc_small.py`
