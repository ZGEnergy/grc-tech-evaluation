---
test_id: A-6
tool: pypsa
dimension: expressiveness
network: SMALL
status: fail
workaround_class: null
wall_clock_seconds: 0
peak_memory_mb: null
loc: 60
solver: highs
timestamp: 2026-03-05T00:00:00Z
---

# A-6: SCED on SMALL (ACTIVSg2000)

## Result: FAIL

## Approach
Two-stage SCUC/SCED workflow: Stage 1 runs SCUC (A-5), Stage 2 fixes commitment and solves ED as LP. However, Stage 1 (SCUC) fails on SMALL -- HiGHS cannot solve the MILP with 544 committable generators x 24 hours within 300s.

## Output
- Stage 1 (SCUC): FAIL -- solver hit time limit with no feasible solution (same as A-5)
- Stage 2 (ED): Not reached
- The MILP has 39,168 binary variables (544 generators x 24 hours x 3 binary vars per generator for commitment status, startup, shutdown)
- HiGHS stuck at root node with no incumbent solution

## Workarounds
Would need either: (1) commercial MIP solver (Gurobi/CPLEX), (2) reduced generator set, or (3) relaxed UC constraints. The two-stage workflow pattern itself is sound -- demonstrated on TINY.

## Timing
- Wall-clock: 0s (test aborted due to Stage 1 failure)
- Peak memory: null

## Test Script
Path: `evaluations/pypsa/tests/expressiveness/test_a6_sced_small.py`
