---
test_id: A-5
tool: pypsa
dimension: expressiveness
network: SMALL
status: fail
workaround_class: null
wall_clock_seconds: 396.9
peak_memory_mb: null
loc: 50
solver: highs
timestamp: 2026-03-05T00:00:00Z
---

# A-5: SCUC on SMALL (ACTIVSg2000)

## Result: FAIL

## Approach
24-hour unit commitment MILP with HiGHS solver. All 544 generators configured as committable with min_up_time=3, min_down_time=2, start_up_cost=500, shut_down_cost=200, ramp limits=30%, p_min_pu=0.2. Time-varying load profile applied.

## Output
- Solver hit 300s time limit
- Solver status: `('ok', 'time_limit')`
- Objective: Infinity (no feasible solution found)
- All 544 units stayed off (commitment schedule all zeros)
- Dispatch: all zeros

## Workarounds
HiGHS MILP solver cannot handle SCUC with 544 committable generators and min_up/down_time constraints within 300s on SMALL network. On TINY (39-bus, 10 generators) this passed in ~2s. The combinatorial explosion from 544 binary variables x 24 hours overwhelms HiGHS. A commercial solver (Gurobi/CPLEX) or reduced generator set would be needed.

## Timing
- Wall-clock: 396.9s (hit solver time limit)
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/expressiveness/test_a5_scuc_small.py`
