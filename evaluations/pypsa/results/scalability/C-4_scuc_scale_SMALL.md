---
test_id: C-4
tool: pypsa
dimension: scalability
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: 700.0
peak_memory_mb: 4000
loc: null
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# C-4: SCUC 24-Hour Scale Test (SMALL)

## Result: FAIL

## Approach

Attempted 24-hour SCUC (unit commitment as MILP) on the ACTIVSg 2000-bus network
with HiGHS solver, single-threaded, 600s time limit, 10% MIP gap tolerance.

All 544 generators set as committable with min_up_time=3, min_down_time=2,
ramp_limit_up=0.3, ramp_limit_down=0.3, p_min_pu=0.3.

## Output

| Metric | Value |
|--------|-------|
| Solver status | time_limit |
| Wall-clock | ~700 s (600s solver + overhead) |
| Feasible solution found | No |
| Objective | inf |
| MIP gap | unknown (no feasible solution) |
| Peak memory | ~4 GB |
| Generators committable | 544 |
| Snapshots | 24 |

HiGHS exhausted the 600-second time limit without finding any feasible integer solution.
The problem has 544 binary commitment variables x 24 hours = 13,056 binary variables,
plus continuous dispatch and flow variables.

## Analysis

The SCUC problem at this scale (2000 buses, 544 committable generators, 24 hours) is
too large for HiGHS single-threaded within the 600s budget. Contributing factors:

1. **All generators committable:** Making all 544 generators committable (vs. only
   thermal generators) creates a much larger MILP.
2. **Single-threaded solver:** HiGHS with `threads=1` per solver-config.md.
3. **No warm-start:** No initial commitment schedule provided.

Note: The expressiveness test A-5 SMALL uses the same network but only makes thermal
generators committable (~410), which also times out. This is a fundamental scalability
limitation of PyPSA + HiGHS for SCUC at the 2000-bus scale.

## Timing

- **Wall-clock:** ~700 s
- **Peak memory:** ~4 GB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c4_scuc_scale.py`
