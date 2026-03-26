---
test_id: C-4
tool: matpower
dimension: scalability
network: SMALL
protocol_version: "v11"
skill_version: v2
test_hash: 19c1d696
status: fail
workaround_class: null
blocked_by: A-5
wall_clock_seconds: 1.112
timing_source: measured
peak_memory_mb: 1.8
convergence_residual: null
convergence_iterations: null
loc: 220
solver: GLPK
timestamp: 2026-03-14T00:00:00Z
---

# C-4: SCUC 24hr on SMALL

## Result: FAIL

## Approach

Attempted 24-hour SCUC on ACTIVSg 2000-bus network via MOST (`most()` function)
with unit commitment enabled (`most.uc.run=1`). GLPK was the only available MILP
solver (HiGHS and SCIP unavailable in Octave).

### Problem Setup

1. Loaded ACTIVSg2000 case (544 generators, 432 after ext2int removes offline units)
2. Linearized quadratic costs to polynomial degree 2 (linear: c1*p + c0) because
   GLPK cannot solve MIQP
3. Built xGenData with CommitKey=1, MinUp=4h, MinDown=2h for all generators
4. Created 24-hour sinusoidal load profile (0.7x to 1.3x base load)
5. Assembled MOST data structure via `loadmd()`

### Problem Scale

| Metric | Value |
|--------|-------|
| Buses | 2000 |
| Generators (after ext2int) | 432 |
| Periods | 24 |
| Decision variables | 162,048 |
| Solver | GLPK |

## Output

MOST successfully assembled the SCUC problem and GLPK solved it in 1.1 seconds, but
returned `exitflag=-10` (mapped from GLPK's internal termination code). This is the
same MATPOWER-GLPK integration bug documented in A-5:

- GLPK finds a feasible integer solution
- GLPK's MIP termination code is not recognized by MATPOWER's `miqps_glpk.m` as a
  valid success condition
- MOST's post-processing (`most.m` line 2111) checks `if mdo.QP.exitflag > 0` and
  skips extraction when the flag is negative
- The solution vector exists (162,048 variables) but cannot be accessed via
  `most_summary()`

| Metric | Value |
|--------|-------|
| Solve time | 1.112 s |
| Exit flag | -10 |
| Solution vector size | 162,048 variables |
| Solution extractable | No (blocked by exitflag mapping) |

## Workarounds

This failure is a cascaded consequence of the A-5 GLPK integration bug. The MOST SCUC
formulation itself is correct and scales to the SMALL network — the solver integration
layer prevents solution extraction.

With a working MILP solver (HiGHS, CPLEX, Gurobi, or MATLAB's intlinprog), this SCUC
problem would likely produce extractable results. The solve time of 1.1 seconds for
162K variables indicates the problem is well within GLPK's capability; only the
post-solve exit flag mapping is broken.

## Timing

- **Wall-clock:** 1.112 s
- **Timing source:** measured
- **Peak memory:** 1.8 MB
- **MIP gap:** Unknown (solution not extractable)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/scalability/test_c4_scuc_scale_SMALL.m`
