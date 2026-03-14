---
test_id: A-5
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v10
skill_version: v1
test_hash: 2fe64f1c
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 4.347
timing_source: measured
peak_memory_mb: 6.23
convergence_residual: null
convergence_iterations: null
loc: 362
solver: HiGHS
timestamp: 2026-03-14T00:30:00Z
---

# A-5: Solve 24-hour unit commitment as MILP on TINY

## Result: PASS

## Approach

Loaded IEEE 39-bus network via the shared MATPOWER loader, then applied
Modified Tiny augmentation:

1. **Differentiated generator costs** from `gen_temporal_params.csv`:
   hydro $5, nuclear $10, coal $25, gas CC $40 per MWh.

2. **UC parameters** from `gen_temporal_params.csv`: startup costs (cold
   start), ramp rates (MW/hr converted to per-unit), min up/down times
   (hours, cast to int for PyPSA's rolling window constraints).

3. **24-hour load profile** from `load_24h.csv`: distributed proportionally
   across 21 load buses. System load ranges 4,237--6,254 MW.

4. **All generators set `committable=True`** with `p_min_pu=0.3` (30%
   minimum stable generation when committed).

Solved via `n.optimize()` with HiGHS MILP settings per `solver-config.md`
(mip_rel_gap=0.01, time_limit=300, threads=1). PyPSA activates binary
commitment variables automatically when `committable=True`.

### Built-in vs user-assembled constraint types

| Constraint | Type | PyPSA attribute |
|-----------|------|-----------------|
| Binary commitment | built-in | `n.generators.committable = True` |
| Min up time | built-in | `n.generators.min_up_time` |
| Min down time | built-in | `n.generators.min_down_time` |
| Startup cost | built-in | `n.generators.start_up_cost` |
| Shutdown cost | built-in | `n.generators.shut_down_cost` |
| Ramp limits | built-in | `n.generators.ramp_limit_up/down` |
| Min stable gen | built-in | `n.generators.p_min_pu` |
| Reserve requirement | user-assembled | via `extra_functionality` callback |
| Joint UC + dispatch | built-in | single `n.optimize()` call |

All standard SCUC constraints except reserve requirements are expressible
as built-in generator attributes. Reserve constraints require the
`extra_functionality` callback mechanism (tested in B-1).

## Output

### Solver

| Metric | Value |
|--------|-------|
| Solver status | ok (optimal) |
| MIP gap | 0.82% (< 1% threshold) |
| Objective | $1,743,649.64 |
| Solve time | 3.29s |
| HiGHS iterations | 3,213 (LP) |
| Binary variables | 720 (10 gens x 24 hours x 3: status, startup, shutdown) |

### Generator Cycling

3 generators cycle during the 24-hour horizon (pass condition requires >= 2):

| Generator | Tech | Transitions | Startups | Shutdowns |
|-----------|------|------------|----------|-----------|
| G3 | coal | 1 | 0 | 1 |
| G6 | gas CC | 1 | 0 | 1 |
| G9 | gas CC | 3 | 1 | 2 |

G9 (gas CC, $40/MWh) shuts down during hours 3--8 (low load), restarts at
hour 9, shuts down again at hour 22. G6 (gas CC, $40/MWh) shuts down at
hour 20. G3 (coal, $25/MWh) shuts down only in the final hour. The cycling
pattern follows economic merit: expensive gas CC units are decommitted first
during low-load hours, while cheap nuclear and hydro units remain online.

### Commitment Schedule (binary matrix)

```
Hour    G0  G1  G2  G3  G4  G5  G6  G7  G8  G9
  0      1   1   1   1   1   1   1   1   1   1
  1      1   1   1   1   1   1   1   1   1   1
  2      1   1   1   1   1   1   1   1   1   1
  3      1   1   1   1   1   1   1   1   1   0
  4-8    1   1   1   1   1   1   1   1   1   0
  9-19   1   1   1   1   1   1   1   1   1   1
 20-21   1   1   1   1   1   1   0   1   1   1
 22      1   1   1   1   1   1   0   1   1   0
 23      1   1   1   0   1   1   0   1   1   0
```

The commitment schedule is directly extractable as `n.generators_t.status`,
a time-indexed DataFrame with binary (0/1) values per generator per hour.

### Dispatch Summary (MW)

| Generator | Tech | Cost | Min | Max | Mean |
|-----------|------|------|-----|-----|------|
| G0 | hydro | $5 | 843 | 900 | 898 |
| G1 | nuclear | $10 | 461 | 646 | 628 |
| G2 | nuclear | $10 | 725 | 725 | 725 |
| G3 | coal | $25 | 0 | 652 | 452 |
| G4 | coal | $25 | 152 | 508 | 339 |
| G5 | nuclear | $10 | 344 | 687 | 663 |
| G6 | gas CC | $40 | 0 | 472 | 170 |
| G7 | nuclear | $10 | 169 | 564 | 356 |
| G8 | nuclear | $10 | 260 | 865 | 789 |
| G9 | gas CC | $40 | 0 | 330 | 220 |

Capacity-to-peak-load ratio: 1.18. Load range: 4,237--6,254 MW.

## Workarounds

None required. All SCUC formulation elements (binary commitment, min up/down
times, startup costs, ramp limits, minimum stable generation) are built-in
PyPSA generator attributes. The commitment schedule is directly accessible
as a time-indexed binary DataFrame.

## Timing

- **Wall-clock:** 4.347s (total: load + model build + solve + extract)
- **Solve-only:** 3.289s (includes linopy model build + HiGHS MILP solve)
- **Timing source:** measured
- **Peak memory:** 6.23 MB (solve only, via tracemalloc)
- **HiGHS iterations:** 3,213 (LP iterations in branch-and-bound)
- **MIP gap:** 0.82%
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a5_scuc.py`
