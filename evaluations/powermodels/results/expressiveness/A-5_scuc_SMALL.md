---
test_id: A-5
tool: powermodels
dimension: expressiveness
network: SMALL
status: qualified_pass
wall_clock_seconds: 320.501
timestamp: 2026-03-05
---

# A-5: 24-Hour SCUC [SMALL]

## Result: QUALIFIED PASS

## Approach
Same as TINY: multi-network DC OPF via `replicate()` + `instantiate_model()`, then add binary commitment variables (u, v, w) and UC constraints via JuMP model access.

## Data Preprocessing
- 134/544 generators missing cost data: added default $20/MWh
- Rate_a defaults applied

## Scale-Specific Issues
- 544 total generators, 432 active (gen_status != 0) -- must filter to active generators only
- 432 active generators x 24 periods = 10,368 pg variables successfully accessed
- Binary variables: 432 x 24 x 3 (u, v, w) = 31,104 binary variables
- MILP model size: ~200k constraints + 41k variables (10k continuous + 31k binary)

## Output
- SCUC model successfully built and submitted to SCIP solver
- Solver hit 300s time limit (TIME_LIMIT status)
- MIP gap at timeout: solver was making progress but could not close gap within time budget
- This is expected behavior for a 432-generator 24-period MILP on a single-threaded solver

## Qualification Rationale
The PowerModels + JuMP approach successfully builds the SCUC formulation at 2000-bus scale. The limitation is solver performance on the resulting MILP, not the modeling framework. A commercial solver (Gurobi, CPLEX) would likely solve this within the time budget.

## Workarounds
- No built-in SCUC; manual binary vars + UC constraints via JuMP (~60 LOC)
- Must filter to active generators (gen_status != 0) at this scale

## Timing
- Model construction: ~9s
- Solver: 300s (hit time limit)
- Wall-clock: 320.5s
