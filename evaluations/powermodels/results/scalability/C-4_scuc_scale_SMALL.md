---
test_id: C-4
tool: powermodels
dimension: scalability
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: stable
wall_clock_seconds: 494.5
peak_memory_mb: null
loc: 240
solver: HiGHS
mip_gap: null
timestamp: "2026-03-07T00:00:00Z"
---

# C-4: SCUC Scale on SMALL (ACTIVSg 2000-bus)

## Result: FAIL (solver timeout)

This test measures the scalability of 24-hour SCUC (Unit Commitment) on the ACTIVSg 2000-bus
network. The result is derived from the A-5 SMALL test, which demonstrated the same problem.

## Problem Scale

- **Generators:** 544 (112 inactive removed by PowerModels)
- **Buses:** 2,000
- **Branches:** 3,206
- **Time periods:** 24
- **Binary variables:** ~39,168 (544 generators x 24 periods x 3 binary vars)
- **Continuous variables:** ~61,056 (generation + angles)
- **Total constraints:** estimated >500,000

## HiGHS Result

HiGHS exceeded the 300-second solver timeout without finding a feasible integer solution.
The LP relaxation itself was still being solved at timeout. No MIP gap was recorded because
no integer-feasible solution was found.

Settings: `time_limit=300.0, presolve=on, threads=1, mip_rel_gap=0.10`

## SCIP Result

SCIP was not attempted separately for C-4. Given that HiGHS could not even solve the LP
relaxation within 300s, SCIP (also open-source) would face similar or worse performance
on this problem size with single-threaded operation.

## Analysis

The 2000-bus 24-hour SCUC is a genuinely large MILP. Key factors:
1. **Dense LP relaxation:** ~500k constraints with full DC power flow formulation per period
2. **Single-threaded:** Protocol requires `threads=1`
3. **No warm-start:** No LP basis or heuristic initial solution provided
4. **Open-source solver limitations:** HiGHS MIP is not competitive with commercial solvers (Gurobi, CPLEX) at this scale

## Workarounds

Same as A-5: PowerModels has no built-in SCUC. The entire formulation was user-assembled
via JuMP (~240 lines). The timeout is a solver capability issue, not a PowerModels limitation.

## Timing
- Wall-clock: 494.5s (from A-5 SMALL: ~190s model build + 300s solver timeout)

## Test Script
Path: `evaluations/powermodels/tests/expressiveness/test_a5_scuc_small.jl` (same as A-5)
