---
test_id: C-7
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: 1fe43054
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 134.68
timing_source: measured
peak_memory_mb: 1633.2
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 319
solver: HiGHS, GLPK, SCIP, Ipopt
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T22:00:00Z
---

# C-7: Solver Swap MEDIUM

## Result: QUALIFIED PASS

## Approach

C-7 evaluates whether swapping solvers for DC OPF on the MEDIUM (ACTIVSg 10k-bus) network requires model reformulation or is a parameter-only change. Four open-source solvers were tested: HiGHS, GLPK, SCIP, and Ipopt.

The DC OPF problem was set up identically for all solvers using `PowerModels.solve_dc_opf(data, optimizer)`. The only difference per solver is the `optimizer` object -- a one-line parameter change via `JuMP.optimizer_with_attributes(<Solver>.Optimizer, ...)`.

**Required workaround from C-3:** ACTIVSg10k uses polynomial cost model 2 (quadratic). Costs were linearized to LP by dropping the c2 coefficient for 1,130 generators (45.5% of the fleet). This workaround applies uniformly to all solvers.

JIT warm-up was performed on `case39.m` before the timed runs.

### Key Finding: Solver swap is parameter-only (no reformulation), but SCIP has a compatibility issue

The JuMP/MathOptInterface (MOI) abstraction layer provides a clean solver swap: `PowerModels.solve_dc_opf(data, optimizer)` is identical for all solvers. No reformulation, no model rebuilding. However, SCIP v0.11.6 does not support `ConstraintDual` extraction, and InfrastructureModels v0.7.8 unconditionally attempts dual extraction during solution building -- causing SCIP runs to crash on solution retrieval despite solving the problem optimally. The test script handles this via a two-level API fallback (`instantiate_model` + `optimize_model!` with manual solution extraction). [solver-specific: SCIP dual extraction incompatibility]

## Output

### Per-Solver Results

| Solver | Status | Objective ($/h) | Solver Time (s) | Wall Clock (s) | Reformulation? | Duals Available? |
|--------|--------|-----------------|-----------------|----------------|----------------|------------------|
| HiGHS | OPTIMAL | 2,401,337.08 | 4.20 | 6.49 | No | Yes |
| GLPK | OPTIMAL | 2,401,337.08 | 61.68 | 63.29 | No | Yes |
| SCIP | OPTIMAL | 2,401,337.08 | 26.73 | 58.75 | No | No (two-level API fallback) |
| Ipopt | LOCALLY_SOLVED | 2,401,337.08 | 1.81 | 2.82 | No | Yes |

**Objective consistency:** All four solvers produce the same objective value to within numerical tolerance ($2,401,337.08/h). HiGHS: 2.401337e+06, GLPK: 2.401337e+06, SCIP: 2.401337e+06, Ipopt: 2.401337e+06.

**Ipopt note:** Ipopt solved the linearized DC OPF (LP) using its interior-point method in 37 iterations (1.81s solver time). Despite being an NLP solver, Ipopt is competitive on this LP because the interior-point approach converges in fewer iterations than simplex on well-scaled problems. The LOCALLY_SOLVED status is Ipopt's standard success indicator.

**SCIP note:** SCIP solved the problem optimally in 26.73s. The dual extraction crash was handled via the two-level API fallback. The SCIP wall-clock (58.75s) includes both the failed `solve_dc_opf` attempt and the successful two-level API fallback solve. The actual SCIP solve time (26.73s) is from the second (successful) run. [solver-specific: SCIP.jl v0.11.6 does not support MathOptInterface.ConstraintDual]

### Solver Swap Mechanism

The JuMP/MOI solver abstraction layer means:

- **No PowerModels code changes** -- `solve_dc_opf` is the same call regardless of solver
- **No model rebuilding** -- the JuMP model is built from the same PowerModels data dictionary
- **Attribute namespace isolation** -- each solver has its own attribute names (`output_flag` for HiGHS, `tm_lim` for GLPK, `display/verblevel` for SCIP, `print_level` for Ipopt)
- **MOI bridges** -- solver-specific IR (LP/MIP/NLP) is handled by MOI bridges automatically

### Network Metrics

| Metric | Value |
|--------|-------|
| Buses | 10,000 |
| Branches | 12,706 |
| Generators | 2,485 |
| Generators cost-linearized | 1,130 (45.5%) |
| LP dimensions | 34,924 rows x 24,643 cols, 89,902 nonzeros |

## Workarounds

1. **Quadratic cost linearization (inherited from C-3):**
   - **What:** ACTIVSg10k generators use polynomial cost model 2 (quadratic). Costs linearized by dropping the c2 coefficient for 1,130 generators.
   - **Why:** PowerModels passes quadratic costs to the solver as QP. At MEDIUM scale, QP solve is not required for the solver swap evaluation -- LP is sufficient.
   - **Durability:** stable -- well-understood approximation, LP-valid costs remain monotonically increasing.
   - **Grade impact:** Moderate API friction. The solver swap itself is clean; only the cost structure workaround qualifies the pass.

2. **SCIP dual extraction incompatibility:**
   - **What:** SCIP.jl v0.11.6 does not support `ConstraintDual` attribute extraction. InfrastructureModels v0.7.8 unconditionally attempts dual extraction during `build_solution`, causing a crash after SCIP has already solved optimally.
   - **Why:** This is a compatibility gap between SCIP.jl and InfrastructureModels, not a PowerModels design flaw.
   - **Durability:** stable -- SCIP can be used via the two-level API (`instantiate_model` + `optimize_model!` with manual JuMP solution extraction). The solver itself works correctly.
   - **Grade impact:** Minor. The swap mechanism is parameter-only. The crash is in solution retrieval, not in problem formulation or solving. [solver-specific]

## Timing

- **HiGHS wall-clock:** 6.49s (post-JIT warm-up), solver time 4.20s (dual simplex, 6,032 iterations)
- **GLPK wall-clock:** 63.29s, solver time 61.68s (primal simplex)
- **SCIP wall-clock:** 58.75s (includes failed + fallback), solver time 26.73s
- **Ipopt wall-clock:** 2.82s, solver time 1.81s (37 iterations)
- **Total wall-clock:** 134.68s (all four solvers sequentially)
- **Timing source:** measured
- **Peak memory:** 1,633.2 MB RSS
- **CPU threads used:** 1 (single-threaded per solver-config.md)
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/powermodels/tests/scalability/test_c7_solver_swap_medium.jl`

Key solver swap lines (the direct C-7 evidence):

```julia
# All use the identical PowerModels call -- no reformulation:
highs_res = PowerModels.solve_dc_opf(data_highs, highs_opt; setting=Dict("output"=>Dict("duals"=>true)))
glpk_res  = PowerModels.solve_dc_opf(data_glpk,  glpk_opt;  setting=Dict("output"=>Dict("duals"=>true)))
scip_res  = PowerModels.solve_dc_opf(data_scip,  scip_opt;  setting=Dict("output"=>Dict("duals"=>true)))
ipopt_res = PowerModels.solve_dc_opf(data_ipopt, ipopt_opt;  setting=Dict("output"=>Dict("duals"=>true)))
```
