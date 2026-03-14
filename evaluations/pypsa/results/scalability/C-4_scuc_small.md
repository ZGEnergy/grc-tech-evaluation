---
test_id: C-4
tool: pypsa
dimension: scalability
network: SMALL
protocol_version: v10
skill_version: v1
test_hash: ee1cca29
status: fail
workaround_class: null
blocked_by: null
wall_clock_seconds: 665.66
timing_source: measured
peak_memory_mb: 3653.8
convergence_residual: null
convergence_iterations: null
loc: 289
solver: HiGHS
timestamp: 2026-03-14T01:30:00Z
---

# C-4: SCUC 24hr on SMALL with HiGHS and SCIP

## Result: FAIL

## Approach

Loaded ACTIVSg2000 (2,000 buses, 2,359 lines, 544 generators) via the shared
MATPOWER loader. Configured all 544 generators as committable with:
- Differentiated marginal costs: $10--$100/MWh (linear scale across generators)
- `p_min_pu = 0.3` (30% minimum stable generation)
- `min_up_time = 1`, `min_down_time = 1` (1-hour minimum)
- `start_up_cost` proportional to marginal cost (cost * 1000)

24-hour snapshots with a synthetic daily load profile (peak factor 1.0 at hour 19,
trough 0.72 at hour 4). Load range: 48,319--67,109 MW. Total generation capacity:
96,292 MW.

Attempted SCUC with both HiGHS and SCIP per the test specification.

### HiGHS (primary)

Used `n.optimize(solver_name="highs")` with solver-config.md settings:
- `time_limit: 600` (10 minutes)
- `mip_rel_gap: 0.01` (1%)
- `threads: 1` (single-threaded for reproducibility)
- `presolve: on`

### SCIP (secondary)

SCIP is not installed in the devcontainer despite the devcontainer feature
claiming to add it. `n.optimize(solver_name="scip")` raises
`AssertionError: Solver scip not installed`.

## Output

### HiGHS Result

| Metric | Value |
|--------|-------|
| Termination | Time limit (600s) |
| Feasible solution found | No (objective = inf) |
| MIP gap at termination | inf (no integer feasible solution) |
| Root LP iterations | 80,488 |
| Branch-and-bound nodes | 0 |
| Wall-clock time | 639.93 s |
| Peak memory | 3,653.8 MB |
| Cycling generators | 0 (no feasible solution) |

The MILP formulation has 347,272 rows, 129,168 columns (39,168 binary variables),
and 1,689,312 nonzeros. After presolve: 85,868 rows, 73,378 columns (25,474
binary), 957,923 nonzeros. HiGHS could not solve the root LP relaxation within the
600-second time limit, processing zero branch-and-bound nodes.

### SCIP Result

| Metric | Value |
|--------|-------|
| Status | Solver not installed |
| Error | `AssertionError: Solver scip not installed` |
| Wall-clock time | 24.39 s (model build + error) |

### Problem Dimensions

| Component | Count |
|-----------|-------|
| Buses | 2,000 |
| Lines | 2,359 |
| Generators (committable) | 544 |
| Snapshots | 24 |
| Binary variables | 39,168 |
| Total variables | 129,168 |
| Constraints | 347,272 |

### Analysis

The 544-generator, 24-hour SCUC on ACTIVSg2000 produces a very large MILP that
HiGHS cannot solve within 10 minutes on a single thread. The root LP relaxation
alone exhausted the time budget. This is a genuine scalability limitation for
single-threaded MILP solving on a 2,000-bus network.

For reference, A-5 (SCUC on TINY with 10 generators) completed in 4.35 seconds
with HiGHS. The jump from 10 to 544 committable generators produces a ~90x
increase in binary variables and makes the problem intractable within the time
budget.

## Workarounds

None required (test failed due to scalability limits, not API limitations).

## Timing

- **Wall-clock (HiGHS):** 639.93 s (hit time limit)
- **Wall-clock (SCIP):** N/A (not installed)
- **Timing source:** measured
- **Peak memory:** 3,653.8 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c4_scuc_small.py`
