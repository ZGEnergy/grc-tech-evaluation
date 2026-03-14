---
test_id: C-3
tool: gridcal
dimension: scalability
network: MEDIUM
status: pass
workaround_class: stable
blocked_by: null
protocol_version: "v10"
skill_version: v1
test_hash: "47a0bc24"
wall_clock_seconds: 8.449
timing_source: measured
peak_memory_mb: 127.15
convergence_residual: null
convergence_iterations: null
loc: 171
solver: HiGHS, SCIP
timestamp: 2026-03-13T00:00:00Z
---

# C-3: DC OPF on MEDIUM with HiGHS and GLPK

## Result: PASS

## Approach

DC OPF on the ACTIVSg 10000-bus network using GridCal's linear OPF formulation (`SolverType.LINEAR_OPF`) with two solvers. GLPK is not available in GridCal's `MIPSolvers` enum — SCIP was used as the open-source substitute.

**Solver availability finding:** GridCal's `MIPSolvers` enum lists 7 solvers: HIGHS, SCIP, CPLEX, GUROBI, XPRESS, CBC, PDLP. However, the PuLP interface (`get_solver()`) only maps 5 of them: HIGHS, SCIP, CPLEX, GUROBI, XPRESS. Attempting to use CBC or PDLP raises `Exception: PuLP Unsupported MIP solver CBC` at runtime despite these being valid enum values. GLPK is not in the enum at all.

## Output

### HiGHS Results

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Solve time | 8.449 s |
| Peak memory | 127.15 MB |
| Total generation | 150,916.88 MW |
| LMP range | [20.064, 20.064] $/MWh |
| LMP spread | 1.94e-08 $/MWh |
| Max loading | 84.72% |
| Binding branches | 0 |

### SCIP Results

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Solve time | 8.115 s |
| Peak memory | 114.53 MB |
| Total generation | 150,916.88 MW |
| LMP range | [20.064, 20.064] $/MWh |
| LMP spread | 1.94e-08 $/MWh |
| Max loading | 84.72% |
| Binding branches | 0 |

### Cross-Solver Comparison

| Metric | HiGHS | SCIP |
|--------|-------|------|
| Total gen (MW) | 150,916.88 | 150,916.88 |
| Solve time (s) | 8.449 | 8.115 |
| Gen difference | 0.0 MW | — |
| Speed ratio | 1.0x | 1.04x faster |

Both solvers produce identical dispatch (0.0 MW difference). LMPs are essentially uniform across all buses (spread < 20 nano-$/MWh), consistent with the ACTIVSg10k network having no binding branch constraints in base-case DCOPF (max loading 84.72%).

## Workarounds

- **What:** GLPK substituted with SCIP for the second solver comparison.
- **Why:** GLPK is not available in GridCal's `MIPSolvers` enum. Additionally, CBC is in the enum but not mapped in the PuLP solver interface — it raises a runtime exception.
- **Durability:** stable — SCIP is a documented, public solver option in GridCal's enum and works correctly via `SCIP_CMD` in PuLP.
- **Grade impact:** Minor. The test goal (dual-solver comparison) is met. The finding that 2 of 7 enum values (CBC, PDLP) raise runtime errors is a quality concern but does not block functionality.

## Timing

- **Wall-clock:** 8.449 s (HiGHS), 8.115 s (SCIP) — solve only
- **Timing source:** measured
- **Peak memory:** 127.15 MB (HiGHS), 114.53 MB (SCIP)
- **Total script time:** 29.06 s (includes two network loads + two solves)

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c3_dcopf_scale_medium.py`
