---
test_id: C-7
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: "v2"
test_hash: "7f1a1ad3"
status: pass
workaround_class: fragile
blocked_by: null
wall_clock_seconds: 129.863
wall_clock_per_solver:
  highs_seconds: 11.612
  glpk_seconds: 54.898
  scip_seconds: 26.424
  ipopt_seconds: 36.930
timing_source: measured
peak_memory_mb: 1823.6
loc: 367
solver: HiGHS, GLPK, SCIP, Ipopt
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: "2026-03-24T00:00:00Z"
---

# C-7: Solver Swap on MEDIUM -- DCOPF with 4 Open-Source Solvers

## Result: PASS

## Approach

Solved the same DCOPF problem (ACTIVSg 10000-bus, `DCPPowerModel`, `ThermalDispatchNoMin`) with
all four open-source solvers: HiGHS, GLPK, SCIP, and Ipopt. The primary question is whether
solver swap requires reformulation or is a parameter-only change.

Same workarounds as C-3 apply (initialize_model=false, linear costs, all generators available,
StaticBranchUnbounded, no hydro).

## Output

### Solver Comparison

| Solver | Status | Wall-clock | Objective ($) | Peak RSS | Notes |
|--------|--------|------------|---------------|----------|-------|
| HiGHS | OPTIMAL | 11.6 s | 3,659,662.46 | 1,636 MB | LP solver |
| GLPK | OPTIMAL | 54.9 s | 3,659,662.46 | 1,701 MB | LP solver |
| SCIP | OPTIMAL | 26.4 s | 3,659,662.46 | 1,773 MB | MIP solver (LP mode) |
| Ipopt | LOCALLY_SOLVED | 36.9 s | 3,659,662.38 | 1,824 MB | NLP solver (LP mode) |

### Objective Consistency

All four solvers agree on the objective value to within 0.000002% (6 significant digits).
Ipopt shows slight numerical difference at the 6th decimal place, which is expected for an
interior-point NLP solver applied to an LP.

| Metric | Value |
|--------|-------|
| Max pairwise difference | < 0.0001% |
| Consistent (< 1%) | Yes |

### Problem Size

| Metric | Value |
|--------|-------|
| Variables | 24,476 |
| Constraints | 41,370 |
| Thermal generators | 1,136 (all set available) |
| Renewable generators | 634 (all set available) |
| Hydro generators | 715 (not modeled) |

## Solver Swap Effort

**Solver swap is a parameter-only change.** The identical `ProblemTemplate` and `DecisionModel`
formulation is used for all four solvers. The only change is the `optimizer=` argument:

```julia
# All that changes between solvers:
model = DecisionModel(template, sys; optimizer=HiGHS.Optimizer, ...)
model = DecisionModel(template, sys; optimizer=GLPK.Optimizer, ...)
model = DecisionModel(template, sys; optimizer=SCIP.Optimizer, ...)
model = DecisionModel(template, sys; optimizer=Ipopt.Optimizer, ...)
```

| Aspect | Detail |
|--------|--------|
| Lines of code to swap | 1 (optimizer parameter) |
| Template change needed | No |
| Reformulation needed | No |
| Solver-specific params | Yes (time limit names differ: `time_limit`, `tm_lim`, `limits/time`, `max_wall_time`) |

**Caveat:** GLPK requires linear cost functions (no QP support). If the original MATPOWER
quadratic costs are used, GLPK fails at the build stage with "solver does not support
ScalarQuadraticFunction." The other three solvers (HiGHS, SCIP, Ipopt) handle QP natively.
This is the only reformulation constraint across the four solvers.

## Workarounds

Same as C-3:
1. `initialize_model=false` + `JuMP.optimize!()` -- PSI's internal `solve!` pathway triggers
   initialization errors at 10k scale [tool-specific]
2. Linear cost override -- GLPK QP limitation [solver-specific: GLPK]
3. All generators set available -- hydro deficit workaround [tool-specific]
4. `StaticBranchUnbounded` -- numerical infeasibility with branch flow limits at 10K [tool-specific]
5. HydroDispatch omitted -- no PSI formulation [tool-specific]

- **What:** Five workarounds inherited from C-3 DCOPF baseline
- **Why:** PSI v0.30.2 cannot solve a standard DCOPF on ACTIVSg10k without these modifications
- **Durability:** fragile -- `initialize_model=false` + `JuMP.optimize!()` bypasses PSI's
  internal solve pipeline using undocumented internal API (`PSI.get_optimization_container`,
  `PSI.get_jump_model`)
- **Grade impact:** Fragile workaround caps at B- range

## Timing

- **Wall-clock (total, all 4 solvers):** 129.9 s
- **Fastest solver:** HiGHS (11.6 s) -- simplex LP solver
- **Slowest solver:** GLPK (54.9 s)
- **Timing source:** measured
- **Peak memory:** 1,824 MB (cumulative RSS after all 4 solves)
- **CPU cores used:** 1 (32 available)

### Speed Ranking

1. HiGHS: 11.6 s (simplex, native LP solver)
2. SCIP: 26.4 s (branch-and-cut, MIP solver on LP)
3. Ipopt: 36.9 s (interior-point, NLP solver on LP problem)
4. GLPK: 54.9 s (simplex, LP solver)

HiGHS is the fastest solver on this 24K-variable LP at 10k-bus scale. SCIP (designed for MIP)
outperforms both Ipopt and GLPK. GLPK is the slowest by a factor of 4.7x vs HiGHS.

## Test Script

**Path:** `evaluations/powersimulations/tests/scalability/test_c7_solver_swap.jl`

## Observations

- **solver-issues:** HiGHS is the fastest solver for this DCOPF LP at 10K scale (11.6s). SCIP
  (26.4s) outperforms Ipopt (36.9s) and GLPK (54.9s). The speed ranking is HiGHS > SCIP > Ipopt
  > GLPK, consistent with solver architectural expectations for LP problems.
- **api-friction:** Solver-specific parameter names are completely different across solvers
  (e.g., time limit: `time_limit` vs `tm_lim` vs `limits/time` vs `max_wall_time`). JuMP's
  `optimizer_with_attributes` abstraction handles this, but users must look up each solver's
  parameter names. No unified parameter mapping exists.
- **api-friction:** GLPK's inability to handle quadratic objectives is discovered at build time
  (not at model definition time), forcing cost reformulation for cross-solver portability.
