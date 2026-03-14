---
test_id: C-7
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v10"
skill_version: "v1"
test_hash: "7f1a1ad3"
status: pass
workaround_class: fragile
blocked_by: null
wall_clock_seconds: 95.895
wall_clock_per_solver:
  highs_seconds: 11.488
  glpk_seconds: 50.697
  scip_seconds: 24.050
  ipopt_seconds: 9.659
timing_source: measured
peak_memory_mb: 2003.6
loc: 370
solver: HiGHS, GLPK, SCIP, Ipopt
timestamp: "2026-03-14T00:00:00Z"
---

# C-7: Solver Swap on MEDIUM — DCOPF with 4 Open-Source Solvers

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
| HiGHS | OPTIMAL | 11.5 s | 3,659,662.46 | 1,515 MB | LP solver |
| GLPK | OPTIMAL | 50.7 s | 3,659,662.46 | 1,595 MB | LP solver |
| SCIP | OPTIMAL | 24.1 s | 3,659,662.46 | 1,859 MB | MIP solver (LP mode) |
| Ipopt | LOCALLY_SOLVED | 9.7 s | 3,659,662.38 | 2,004 MB | NLP solver (LP mode) |

### Objective Consistency

All four solvers agree on the objective value to within 0.000002% (6 significant digits).
Ipopt shows slight numerical difference at the 6th decimal place, which is expected for an
interior-point NLP solver applied to an LP.

| Metric | Value |
|--------|-------|
| Max pairwise difference | 0.0000% |
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
1. `initialize_model=false` + `JuMP.optimize!()`
2. Linear cost override (GLPK QP limitation)
3. All generators set available (hydro deficit)
4. `StaticBranchUnbounded` (numerical infeasibility at 10K)
5. HydroDispatch omitted (no PSI formulation)

## Timing

- **Wall-clock (total, all 4 solvers):** 95.9 s
- **Fastest solver:** Ipopt (9.7 s) — interior-point method on LP
- **Slowest solver:** GLPK (50.7 s)
- **Timing source:** measured
- **Peak memory:** 2,004 MB (cumulative RSS after all 4 solves)
- **CPU cores used:** 1 (32 available)

### Speed Ranking

1. Ipopt: 9.7 s (interior-point, NLP solver on LP problem)
2. HiGHS: 11.5 s (simplex, native LP solver)
3. SCIP: 24.1 s (branch-and-cut, MIP solver on LP)
4. GLPK: 50.7 s (simplex, LP solver)

Ipopt's speed advantage is surprising — its interior-point method converges faster than
HiGHS's simplex on this 24K-variable LP. SCIP (designed for MIP) is faster than GLPK
(designed for LP) on this problem.

## Test Script

**Path:** `evaluations/powersimulations/tests/scalability/test_c7_solver_swap.jl`

## Observations

- **solver-issues:** Ipopt (NLP interior-point) is the fastest solver on this DCOPF LP at 10K
  scale (9.7s vs HiGHS 11.5s). This is counterintuitive — interior-point methods typically
  have higher per-iteration cost but converge in fewer iterations on well-structured LPs.
- **api-friction:** Solver-specific parameter names are completely different across solvers
  (e.g., time limit: `time_limit` vs `tm_lim` vs `limits/time` vs `max_wall_time`). JuMP's
  `optimizer_with_attributes` abstraction handles this, but users must look up each solver's
  parameter names. No unified parameter mapping exists.
- **api-friction:** GLPK's inability to handle quadratic objectives is discovered at build time
  (not at model definition time), forcing cost reformulation for cross-solver portability.
