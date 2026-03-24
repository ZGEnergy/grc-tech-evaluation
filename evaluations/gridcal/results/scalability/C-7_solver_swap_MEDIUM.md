---
test_id: C-7
tool: gridcal
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: v2
test_hash: "1d6a794d"
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 8.911
timing_source: measured
peak_memory_mb: 127.15
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 251
solver: HiGHS, SCIP
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T18:00:00Z
---

# C-7: Repeat C-3 with each available open-source solver on MEDIUM

## Result: QUALIFIED PASS

## Approach

Tested all open-source solvers in GridCal's `MIPSolvers` enum on the ACTIVSg 10000-bus
network. Solver swap is a single parameter change (`mip_solver=MIPSolvers.<SOLVER>` in
`OptimalPowerFlowOptions`) -- no reformulation, no model rebuild, no code changes.

**Solver availability audit:**

| Solver | In Enum | Works | Notes |
|--------|---------|-------|-------|
| HiGHS | Yes | Yes | Primary solver, via PuLP HIGHS_CMD |
| SCIP | Yes | Yes | Secondary solver, via PuLP SCIP_CMD |
| CBC | Yes | No | `Exception: PuLP Unsupported MIP solver CBC` |
| PDLP | Yes | No | `Exception: PuLP Unsupported MIP solver PDLP` |
| GLPK | **No** | N/A | Not in `MIPSolvers` enum at all |
| CPLEX | Yes | N/T | Commercial -- not tested |
| GUROBI | Yes | N/T | Commercial -- not tested |
| XPRESS | Yes | N/T | Commercial -- not tested |

**Key finding:** Solver swap requires **no reformulation** -- it is a trivial parameter
change. The PTDF-based LP formulation is constructed once and passed to PuLP, which
dispatches to the backend solver. All working solvers receive the identical formulation.
[tool-specific: solver swap is parameter-only, but GLPK excluded from enum]

## Output

### Per-Solver Results

| Metric | HiGHS | SCIP |
|--------|-------|------|
| Converged | Yes | Yes |
| Solve time (s) | 8.91 | 8.53 |
| Peak memory (MB) | 127.15 | 114.53 |
| Total gen (MW) | 150,916.88 | 150,916.88 |
| LMP min ($/MWh) | 20.064 | 20.064 |
| LMP max ($/MWh) | 20.064 | 20.064 |
| LMP spread | 1.94e-08 | 1.94e-08 |
| Max loading (%) | 84.72 | 84.72 |
| Binding branches | 0 | 0 |

### Cross-Solver Comparison

| Metric | Value |
|--------|-------|
| Total gen difference | 0.0 MW |
| Dispatch identical | Yes |
| SCIP/HiGHS speed ratio | 0.96x (SCIP 4% faster) |
| LMPs identical | Yes (within 1.94e-08) |

Both solvers produce identical dispatch and LMPs. The ACTIVSg10k network is uncongested
(max loading 84.72%, no binding branches), so LMPs are uniform.

### Failed Solvers

| Solver | Error |
|--------|-------|
| CBC | `Exception: PuLP Unsupported MIP solver CBC` |
| PDLP | `Exception: PuLP Unsupported MIP solver PDLP` |

CBC and PDLP are valid enum values but not mapped in the PuLP solver interface
(`get_solver()` function). They crash at runtime despite being selectable via the API.

## Workarounds

- **What:** GLPK substituted with SCIP (both open-source LP/MILP solvers).
- **Why:** GLPK is not in GridCal's `MIPSolvers` enum. There is no mechanism to add it.
- **Durability:** stable -- SCIP is a documented, public solver option. The solver swap
  mechanism itself is clean and well-designed (single parameter change, no reformulation).
- **Grade impact:** Minor. The protocol requests HiGHS/GLPK/SCIP; GridCal provides
  HiGHS/SCIP but not GLPK. The swap mechanism is excellent (parameter-only, no
  reformulation). The broken CBC/PDLP enum values are a quality concern but do not
  affect the two working open-source solvers.
- **Version tested:** VeraGridEngine 5.6.28

## Timing

- **Wall-clock:** 8.91 s (HiGHS), 8.53 s (SCIP) -- solve only
- **Timing source:** measured
- **Peak memory:** 127.15 MB (HiGHS), 114.53 MB (SCIP)
- **CPU threads used:** 1
- **CPU threads available:** 32
- **Total script time:** 62.77 s (includes 4 solver attempts + 2 network loads)

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c7_solver_swap_medium.py`

Key code showing the swap mechanism:

```python
# Solver swap is a single parameter change -- no reformulation
opf_opts = vge.OptimalPowerFlowOptions(
    solver=SolverType.LINEAR_OPF,
    mip_solver=MIPSolvers.HIGHS,   # swap to MIPSolvers.SCIP
)
opf_results = vge.linear_opf(grid, opf_opts)
```
