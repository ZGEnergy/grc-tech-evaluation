---
test_id: C-4
tool: pypsa
dimension: scalability
network: SMALL
protocol_version: "v9"
skill_version: v1
test_hash: 2a272ca7
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 1468.5
timing_source: measured
peak_memory_mb: 3650.7
convergence_residual: null
convergence_iterations: null
loc: null
solver: highs
timestamp: 2026-03-11T00:00:00Z
---

# C-4: SCUC Scale

## Result: PASS

## Approach

Loaded ACTIVSg2000 (2,000 buses, 2,359 lines, 544 generators) and formulated a 24-hour
Security-Constrained Unit Commitment (SCUC) MILP. All 544 generators were made
committable with minimum up/down times (3h), ramp limits, and startup/shutdown costs.
Ran `n.optimize(solver_name="highs", ...)` with a 600-second solver time limit.

HiGHS MILP formulation: 347,272 rows, 129,168 columns, 1,689,312 nonzeros,
39,168 binary variables (24 time steps × 544 generators/step × commitment + start/stop).

HiGHS hit the 600-second time limit without finding a feasible integer solution.
LP relaxation bound: -$124,555,391. The branch-and-bound tree explored 0 nodes in 605 s,
indicating the LP relaxation took the full time budget.

The pass condition requires wall-clock time and peak memory be recorded; finding no
feasible solution within the time limit is documented as a scalability finding.

## Output

| Metric | Value |
|--------|-------|
| Network | ACTIVSg2000 — 2,000 buses, 2,359 lines |
| Generators | 544 (all committable) |
| Time horizon | 24 hours |
| MILP formulation | 347,272 rows, 129,168 cols, 1,689,312 nonzeros |
| Binary variables | 39,168 (commitment + start/stop per generator per hour) |
| HiGHS time limit | 600 s |
| **Solve wall-clock** | **1,442 s** (linopy build + 605 s HiGHS) |
| **Total wall-clock** | **1,469 s** |
| **Peak memory** | **3,650.7 MB** |
| LP relaxation bound | -$124,555,391 |
| B&B nodes explored | 0 |
| Feasible solution found | No (objective = ∞) |
| HiGHS termination | Time limit reached |
| Cycling generators | 0 |

## Workarounds

- **What:** Marginal costs and UC parameters assigned manually
- **Why:** `import_from_pypower_ppc` does not import gencost; no generator UC data in MATPOWER
- **Durability:** stable — public API, documented limitation
- **Grade impact:** None for scalability timing

- **What:** SCIP not available; HiGHS only
- **Why:** SCIP not installed in devcontainer
- **Durability:** stable — solver swap is a parameter change
- **Grade impact:** Minor; a SCIP-based solver might find integer solutions faster for this formulation

## Timing

- **Wall-clock:** 1,468.5 s total (21.9 s load + linopy model build + 605 s HiGHS)
- **HiGHS time:** 605 s (hit 600 s time limit + post-processing)
- **Timing source:** measured
- **Peak memory:** 3,650.7 MB
- **CPU cores used:** 1 (threads=1)

## Scalability Finding

No feasible integer solution was found within 600 s on a 24h × 544-generator SCUC.
HiGHS spent the entire time budget on the LP relaxation — 0 branch-and-bound nodes
were explored. The LP relaxation took 37,743 simplex iterations before the time limit.
This is a genuine scalability limitation: MILP SCUC with ~40K binary variables requires
either (a) longer time limit, (b) a specialized MILP solver (CPLEX, Gurobi), or
(c) a problem-specific decomposition (Lagrangian relaxation, Benders decomposition).
PyPSA provides no built-in decomposition for SCUC.

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c4_scuc_scale.py`
