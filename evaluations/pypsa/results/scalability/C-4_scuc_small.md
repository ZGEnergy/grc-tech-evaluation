---
test_id: C-4
tool: pypsa
dimension: scalability
network: SMALL
protocol_version: v11
skill_version: v2
test_hash: 45ab9101
status: constrained_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1836.53
timing_source: measured
peak_memory_mb: 3653.8
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 353
solver: HiGHS
cpu_threads_used: 32
cpu_threads_available: 32
timestamp: 2026-03-24T22:30:00Z
---

# C-4: SCUC 24hr on SMALL with HiGHS and SCIP

## Result: CONSTRAINED PASS

The SCUC completes with a feasible solution on multi-threaded HiGHS (32 threads,
1800s budget) with 1.63% MIP gap and 78 cycling generators. Single-threaded
HiGHS (600s budget) fails to solve the root LP relaxation. SCIP is not
available in the evaluation environment. The result is constrained because the
1% MIP gap target was not achieved within the time budget, and the solution
requires multi-threaded parallelism.

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

Tested three solver configurations:
1. HiGHS single-threaded (1T, 600s time limit)
2. HiGHS multi-threaded (32T, 1800s time limit)
3. SCIP (not available)

## Output

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
| After presolve: rows | 85,868 |
| After presolve: cols | 73,378 (25,474 binary) |
| After presolve: nonzeros | 957,923 |

### HiGHS 1-Thread (600s limit)

| Metric | Value |
|--------|-------|
| Termination | Time limit (600s) |
| Feasible solution found | No |
| Primal bound | inf |
| Dual bound | -124,555,392 |
| MIP gap | inf |
| B&B nodes | 0 |
| LP iterations | 75,861 |
| Wall-clock time | 636.0 s |
| Peak memory | 3,653.8 MB |

The root LP relaxation was not solved within 600s. The dual bound remained
at the initial value, indicating the simplex solver was still iterating
on the root LP. [solver-specific: HiGHS single-threaded LP performance]

### HiGHS 32-Thread (1800s limit)

| Metric | Value |
|--------|-------|
| Termination | Time limit (1800s) |
| **Feasible solution found** | **Yes** |
| **Objective** | **$67,362,584** |
| Primal bound | 67,362,583.80 |
| Dual bound | 66,263,085.59 |
| **MIP gap** | **1.63%** (target: 1%) |
| B&B nodes | 0 |
| LP iterations | 152,390 |
| Heuristic iterations | 49,384 |
| Repair LPs | 1 (feasible, 39,187 iterations) |
| Wall-clock time | 1,836.5 s |
| Peak memory | 3,650.7 MB |
| **Cycling generators** | **78 / 544** |

Root LP solved after ~1,230s (103,006 LP iterations). Feasible integer solution
found via central rounding heuristic at ~1,670s. No branch-and-bound nodes were
processed -- the solution comes purely from heuristics applied at the root node.
Zero bound, integer, and row violations in the final solution.

**Multi-threading impact:** The root LP that took >600s on 1 thread completed in
~1,230s on 32 threads (1.36x the elapsed wall time but with concurrent simplex).
The critical difference is that 32 threads provided enough time budget after the
root LP to run heuristics that found a feasible solution.

### SCIP Result

| Metric | Value |
|--------|-------|
| Status | Solver not installed |
| Error | `AssertionError: Solver scip not installed` |
| Wall-clock time | 26.8 s (model build + error) |

### Solver Comparison Summary

| Config | Feasible | Time (s) | MIP Gap | Cycling Gens |
|--------|----------|----------|---------|--------------|
| HiGHS 1T (600s) | No | 636 | inf | N/A |
| HiGHS 32T (1800s) | Yes | 1,837 | 1.63% | 78 |
| SCIP | N/A | N/A | N/A | N/A |

## Workarounds

None required. The MILP formulation via linopy is well-structured (presolve
reduces rows by 75%). The scalability bottleneck is the solver's ability to
handle the root LP relaxation, not the tool's API or formulation.

## Timing

- **Wall-clock (HiGHS 1T):** 636.0 s (hit time limit, no feasible solution)
- **Wall-clock (HiGHS 32T):** 1,836.5 s (hit time limit, feasible solution found)
- **Wall-clock (SCIP):** N/A (not installed)
- **Total script time:** 2,500.9 s
- **Timing source:** measured
- **Peak memory:** 3,653.8 MB (1T), 3,650.7 MB (32T)
- **CPU threads used:** 1 (1T config), 32 (MT config)
- **CPU threads available:** 32

## Analysis

The 544-generator, 24-hour SCUC on ACTIVSg2000 is a genuinely large MILP
(39,168 binary variables). HiGHS at 32 threads can find a feasible solution
within 30 minutes via heuristics, but cannot close the MIP gap to 1% within
that budget. The root LP relaxation alone requires ~1,230s with 32 threads
(>600s with 1 thread), which dominates the solve time.

This is a [solver-specific: HiGHS root LP relaxation performance on large SCUC]
limitation. The PyPSA/linopy formulation is clean and efficient (presolve
reduces the problem by 75%), and the tool overhead beyond solve time is minimal
(~25s for model construction). A commercial solver (Gurobi, CPLEX) with
advanced MIP heuristics and cuts would likely solve this faster.

For reference, A-5 (SCUC on TINY with 10 generators) completed in 4.35 seconds
with HiGHS. The jump from 10 to 544 committable generators produces a ~3,900x
increase in binary variables.

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c4_scuc_small.py`
