---
test_id: A-6
tool: pypsa
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: 930.5
peak_memory_mb: null
loc: null
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# A-6: Security-Constrained Economic Dispatch (SMALL)

## Result: FAIL

## Approach

Two-stage SCUC→SCED workflow on ACTIVSg 2000-bus network:
1. Stage 1: Solve 24-hour SCUC (MILP) to get commitment schedule
2. Stage 2: Fix commitment via p_min_pu/p_max_pu encoding, re-solve as LP

## Output

| Stage | Status | Wall-clock | Objective |
|-------|--------|------------|-----------|
| SCUC | time_limit | 689 s | Infinity |
| SCED | infeasible | 221 s | N/A |

**Failure chain:** The SCUC solver (HiGHS, single-threaded) hit the 600s time limit
without finding a feasible integer solution (objective = Infinity). The commitment
schedule extracted after timeout was degenerate (134 generators "always on" but with
zero dispatch). When this schedule was encoded into p_min_pu/p_max_pu bounds for the
SCED LP, the resulting problem was infeasible.

The SCED LP had 275,828 rows, 90,000 columns, and 1,534,552 nonzeros. HiGHS
determined infeasibility after 30,867 simplex iterations (220s).

## Analysis

This failure is a direct consequence of A-5 SMALL failing — the two-stage workflow
cannot succeed if the UC stage does not produce a valid commitment schedule. The SCED
implementation itself is correct (demonstrated at TINY tier, A-6 TINY: PASS).

The encoding pattern (committable=False + p_min_pu/p_max_pu from UC status) is a
stable workaround for PyPSA's lack of a built-in `fix_commitment()` method, and works
correctly when given a valid commitment schedule.

## Timing

- **Wall-clock:** 930.5 s total (689s SCUC + 221s SCED + overhead)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a6_sced_small.py`
