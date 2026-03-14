---
test_id: C-3
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: v10
skill_version: v1
test_hash: 1967bffe
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 72.45
timing_source: measured
peak_memory_mb: 877.4
convergence_residual: null
convergence_iterations: null
loc: 204
solver: HiGHS, GLPK
timestamp: 2026-03-13T23:00:00Z
---

# C-3: DC OPF Scale MEDIUM

## Result: QUALIFIED PASS

## Approach

Loaded `case_ACTIVSg10k.m` with MEDIUM preprocessing (2,462 branches rate_a set to 9999 MVA). Solved DC OPF using `PowerModels.solve_dc_opf(data, optimizer)` with two solvers per C-3 pass condition: **HiGHS** (primary) and **GLPK** (secondary).

**Required workaround -- quadratic cost linearization:** ACTIVSg10k uses polynomial cost model 2 (quadratic), which causes `solve_dc_opf` to generate a QP formulation. Costs were linearized to LP by dropping the c2 (quadratic) coefficient for 1,130 generators (45.5% of the generator fleet).

JIT warm-up on `case39.m` was performed for both HiGHS and GLPK before the timed runs.

## Output

### Per-Solver Results

| Solver | Status | Objective ($/h) | Solver Time (s) | Wall Clock (s) | Iterations |
|--------|--------|-----------------|-----------------|----------------|------------|
| HiGHS | OPTIMAL | 2,401,337.08 | 3.91 | 6.34 | 6,032 simplex |
| GLPK | OPTIMAL | 2,401,337.08 | 61.86 | 63.20 | 50,193 simplex |

**Objective consistency: VERIFIED.** Both solvers produce the same objective value to within machine precision (diff: 3.19e-6 $/h, 1.33e-10%).

### Network Metrics

| Metric | Value |
|--------|-------|
| Buses | 10,000 |
| Branches | 12,706 |
| Generators (total) | 2,485 |
| Generators dispatched (HiGHS) | 1,937 |
| Base MVA | 100 |
| Preprocessing: rate_a fixed | 2,462 (19.4%) |
| Generators cost-linearized | 1,130 (45.5%) |
| LP dimensions | 34,924 rows x 24,643 cols |
| LP nonzeros | 89,902 |
| Binding branches | 0 / 12,706 |
| LMPs (all buses) | 20.064 $/MWh (uniform) |

**LMP uniformity note:** All 10,000 buses have identical LMPs ($20.064/MWh). Per `cross-tool-watchpoints.md`, ACTIVSg10k has no binding branch constraints in base-case DCOPF (~84-85% maximum loading). Uniform LMPs indicate an uncongested network, not a tool limitation.

### Solver Comparison Analysis

HiGHS outperforms GLPK by ~16x on this problem (3.91s vs 61.86s solver time). HiGHS used dual simplex with a warm-start basis from preprocessing (6,032 iterations), while GLPK used primal simplex from cold start (50,193 iterations). Both converged to the same optimal solution.

**Improvement from v9:** In the v9 evaluation, GLPK hit the 300s time limit without finding an optimal solution. In this v10 run, GLPK converged in 61.86s. The difference may be due to JIT warm-up improving the model construction or solver configuration differences.

**Solver swap friction:** Swapping from HiGHS to GLPK requires only a one-line optimizer change -- no reformulation needed. The solver interface abstracts cleanly through JuMP/MathOptInterface.

## Workarounds

1. **Quadratic cost linearization:**
   - **What:** ACTIVSg10k uses polynomial cost model 2 (quadratic). `solve_dc_opf` passes these to the solver as QP. Costs were linearized by dropping the c2 coefficient for 1,130 generators.
   - **Why:** PowerModels.jl does not warn users that quadratic costs trigger QP formulation. At MEDIUM scale, QP solve times are significantly longer than LP.
   - **Durability:** stable -- dropping c2 is a well-understood approximation. The linearized costs remain monotonically increasing (LP-valid) because the original quadratic terms are non-negative.
   - **Grade impact:** Moderate. The workaround changes the cost function structure but not network topology. Dispatch and LMPs are physically meaningful.

## Timing

- **HiGHS wall-clock:** 6.34s (includes JuMP model build + solve)
- **HiGHS solver time (pure LP solve):** 3.91s
- **GLPK wall-clock:** 63.20s (includes JuMP model build + solve)
- **GLPK solver time:** 61.86s
- **Total wall-clock (both solvers + parse):** 72.45s
- **Timing source:** measured
- **Peak memory:** 877.4 MB RSS
- **CPU cores used:** 1 (single-threaded per solver-config.md)

## Test Script

**Path:** `evaluations/powermodels/tests/scalability/test_c3_dcopf_scale_medium.jl`

Key API calls:

```julia
# Cost linearization (required workaround)
for (_, gen) in data["gen"]
    if gen["model"] == 2 && gen["ncost"] >= 3 && abs(gen["cost"][1]) > 1e-10
        gen["cost"]  = [gen["cost"][2], gen["cost"][3]]  # drop c2
        gen["ncost"] = 2
    end
end

# HiGHS solve
highs_opt = JuMP.optimizer_with_attributes(
    HiGHS.Optimizer, "output_flag"=>true, "presolve"=>"on",
    "time_limit"=>300.0, "threads"=>1
)
result_h = PowerModels.solve_dc_opf(data_highs, highs_opt;
    setting=Dict("output"=>Dict("duals"=>true)))

# GLPK solve (same problem, one-line solver change)
glpk_opt = JuMP.optimizer_with_attributes(
    GLPK.Optimizer, "tm_lim"=>300_000, "msg_lev"=>GLPK.GLP_MSG_ON
)
result_g = PowerModels.solve_dc_opf(data_glpk, glpk_opt;
    setting=Dict("output"=>Dict("duals"=>true)))

# LMP extraction (HiGHS)
lmp = -result_h["solution"]["bus"][bus_id]["lam_kcl_r"] / base_mva  # $/MWh
```
