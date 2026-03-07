---
test_id: A-6
tool: powermodels
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: stable
wall_clock_seconds: 0.0
peak_memory_mb: null
loc: 407
solver: HiGHS
timestamp: "2026-03-07T00:00:00Z"
---

# A-6: SCED (Security-Constrained Economic Dispatch) on SMALL (ACTIVSg 2000-bus)

## Result: FAIL (blocked by A-5 failure)

A-6 depends on A-5 (SCUC) to provide the commitment schedule that the economic dispatch fixes as parameters. Since A-5 failed on SMALL (HiGHS timed out after 300s with no feasible solution), A-6 cannot be executed.

## Dependency Chain

1. **A-5 SCUC (FAIL):** 24-hour unit commitment on 544 generators timed out -- HiGHS MIP solver could not find any feasible integer solution within 300s for this problem scale.
2. **A-6 SCED (BLOCKED):** Without a commitment schedule from A-5, the economic dispatch LP has no fixed commitment to solve against.

## What Would Have Been Tested

The TINY version of A-6 solved successfully (pass). The approach was:
1. Solve UC MILP to get binary commitment schedule
2. Fix commitment as parameters in a new LP model (continuous dispatch only)
3. Re-add ramp constraints independently in ED stage
4. Verify UC-ED cleanly separable

The ED LP stage itself (Step 2-4) would likely solve quickly on SMALL if given a commitment schedule -- the LP has no binary variables and HiGHS handles LP well. The bottleneck is entirely in the UC MILP (Step 1).

## Workarounds

Same as TINY: PowerModels has no built-in SCED. The UC-ED two-stage decomposition is user-assembled via JuMP (~200 lines). The failure is a solver capability limitation (HiGHS MIP on large MILP), not an expressiveness limitation.

## Test Script

Not executed for SMALL. TINY script: `evaluations/powermodels/tests/expressiveness/test_a6_sced.jl`
