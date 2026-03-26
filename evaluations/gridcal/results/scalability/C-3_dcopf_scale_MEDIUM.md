---
test_id: C-3
tool: gridcal
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: v2
test_hash: "a89c9055"
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 8.862
timing_source: measured
peak_memory_mb: 127.15
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 179
solver: HiGHS, SCIP
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T12:00:00Z
---

# C-3: DC OPF on MEDIUM with HiGHS and GLPK

## Result: QUALIFIED PASS

## Approach

DC OPF on the ACTIVSg 10000-bus network using GridCal's linear OPF formulation (`SolverType.LINEAR_OPF`) with two solvers. GLPK is not available in GridCal's `MIPSolvers` enum -- SCIP was used as the open-source substitute.

**Solver availability finding:** GridCal's `MIPSolvers` enum lists 7 solvers: HIGHS, SCIP, CPLEX, GUROBI, XPRESS, CBC, PDLP. However, the PuLP interface (`get_solver()`) only maps 5 of them: HIGHS, SCIP, CPLEX, GUROBI, XPRESS. Attempting to use CBC or PDLP raises `Exception: PuLP Unsupported MIP solver CBC` at runtime despite these being valid enum values. GLPK is not in the enum at all.

**v11 soft-constraint check:** Max branch loading is 84.72% for both solvers. No branches exceed 100% + 1e-4 p.u. tolerance, so the soft-constraint finding from A-3 (observed on the congested TINY network with 70% derating) does not manifest on the uncongested MEDIUM network. The ACTIVSg10k base case has no binding branch constraints.

## Output

### HiGHS Results

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Solve time | 8.862 s |
| Peak memory | 127.15 MB |
| Total generation | 150,916.88 MW |
| LMP range | [20.064, 20.064] $/MWh |
| LMP spread | 1.941e-08 $/MWh |
| Max loading | 84.72% |
| Binding branches | 0 |
| Soft constraint branches | 0 |

### SCIP Results

| Metric | Value |
|--------|-------|
| Converged | Yes |
| Solve time | 8.614 s |
| Peak memory | 114.53 MB |
| Total generation | 150,916.88 MW |
| LMP range | [20.064, 20.064] $/MWh |
| LMP spread | 1.941e-08 $/MWh |
| Max loading | 84.72% |
| Binding branches | 0 |
| Soft constraint branches | 0 |

### Cross-Solver Comparison

| Metric | HiGHS | SCIP |
|--------|-------|------|
| Total gen (MW) | 150,916.88 | 150,916.88 |
| Solve time (s) | 8.862 | 8.614 |
| Gen difference | 0.0 MW | -- |
| Speed ratio | 1.0x | 1.03x faster |

Both solvers produce identical dispatch (0.0 MW difference). LMPs are essentially uniform across all buses (spread < 20 nano-$/MWh), consistent with the ACTIVSg10k network having no binding branch constraints in base-case DCOPF (max loading 84.72%).

**Soft-constraint finding (from A-3):** GridCal's `linear_opf` uses soft branch flow constraints (LP slack variables) [tool-specific]. This was confirmed in A-3 on the congested TINY network with 70% branch derating, where one branch showed 112.24% loading. On the uncongested MEDIUM network, no branch exceeds its thermal limit, so the soft constraint behavior is not observable. The soft-constraint formulation remains a documented characteristic of the tool.

## Workarounds

- **What:** GLPK substituted with SCIP for the second solver comparison.
- **Why:** GLPK is not available in GridCal's `MIPSolvers` enum. Additionally, CBC is in the enum but not mapped in the PuLP solver interface -- it raises a runtime exception.
- **Durability:** stable -- SCIP is a documented, public solver option in GridCal's enum and works correctly via `SCIP_CMD` in PuLP.
- **Grade impact:** Minor. The test goal (dual-solver comparison) is met. The finding that 2 of 7 enum values (CBC, PDLP) raise runtime errors is a quality concern but does not block functionality.

## Timing

- **Wall-clock:** 8.862 s (HiGHS), 8.614 s (SCIP) -- solve only
- **Timing source:** measured
- **Peak memory:** 127.15 MB (HiGHS), 114.53 MB (SCIP)
- **CPU threads used:** 1
- **CPU threads available:** 32
- **Total script time:** 31.65 s (includes two network loads + two solves)

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c3_dcopf_scale_medium.py`
