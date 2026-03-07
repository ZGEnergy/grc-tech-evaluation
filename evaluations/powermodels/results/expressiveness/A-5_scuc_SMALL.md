---
test_id: A-5
tool: powermodels
dimension: expressiveness
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

# A-5: 24-hour SCUC (Unit Commitment) on SMALL (ACTIVSg 2000-bus)

## Result: FAIL (solver timeout)

The 24-hour SCUC on the ACTIVSg 2000-bus network (544 generators, 3206 branches) exceeded the 300-second HiGHS solver timeout without finding a feasible integer solution. HiGHS could not solve the LP relaxation within a reasonable time for this problem size.

## Problem Scale

- **Generators:** 544 (including 112 inactive removed by PowerModels)
- **Buses:** 2000
- **Branches:** 3206
- **Time periods:** 24
- **Binary variables:** ~39,168 (544 generators x 24 periods x 3 binary vars)
- **Continuous variables:** ~61,056 (generation + angles)
- **Total constraints:** estimated >500,000

## What Happened

1. PowerModels parsed the case_ACTIVSg2000.m file successfully
2. The JuMP MILP model was built from scratch (same approach as TINY)
3. HiGHS began solving with `mip_rel_gap=0.10`, `time_limit=300s`
4. After 300 seconds, HiGHS had not found any feasible integer solution
5. The LP relaxation itself was still being solved

## Why It Failed

The ACTIVSg 2000-bus SCUC is a genuinely large MILP problem. Key factors:

1. **LP relaxation size:** ~500k constraints with dense DC power flow formulation. HiGHS spent the entire time limit on presolve and initial LP solve.
2. **Cost linearization:** HiGHS cannot solve MIQP, so quadratic generator costs were linearized. This is a structural limitation.
3. **Single-threaded:** HiGHS was configured with `threads=1` per protocol.
4. **No warm-start:** No LP basis or heuristic initial solution was provided.

A commercial solver (Gurobi, CPLEX) with multi-threading and better MIP heuristics would likely find a feasible solution within the time limit, but HiGHS's open-source MIP solver is not competitive at this scale.

## Workarounds

Same as TINY: PowerModels has no built-in SCUC. The entire formulation was user-assembled via JuMP (~240 lines). The timeout is a solver capability issue, not a PowerModels expressiveness issue per se.

## Timing

- Wall-clock: 494.5s (including ~190s model build + 300s solver timeout)
- Solver status: TIME_LIMIT (no feasible solution found)

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a5_scuc_small.jl`
