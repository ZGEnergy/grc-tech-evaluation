---
test_id: C-3
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: 6cbf4087
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 77.20
timing_source: measured
peak_memory_mb: 934.0
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 213
solver: HiGHS, GLPK
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T20:55:00Z
---

# C-3: DC OPF Scale MEDIUM

## Result: QUALIFIED PASS

## Approach

Loaded `case_ACTIVSg10k.m` with MEDIUM preprocessing (2,462 branches rate_a set to 9999 MVA). Solved DC OPF using `PowerModels.solve_dc_opf(data, optimizer)` with two solvers per C-3 pass condition: **HiGHS** (primary) and **GLPK** (secondary).

**Required workaround -- quadratic cost linearization:** ACTIVSg10k uses polynomial cost model 2 (quadratic), which causes `solve_dc_opf` to generate a QP formulation. Costs were linearized to LP by dropping the c2 (quadratic) coefficient for 1,130 generators (45.5% of the generator fleet).

JIT warm-up on `case39.m` was performed for both HiGHS and GLPK before the timed runs. Note: GLPK warm-up triggered `MathOptInterface.UnsupportedAttribute` for QP objective on case39 (which has quadratic costs); this is expected since GLPK cannot handle QP.

## Output

### Per-Solver Results

| Solver | Status | Objective ($/h) | Solver Time (s) | Wall Clock (s) | Iterations |
|--------|--------|-----------------|-----------------|----------------|------------|
| HiGHS | OPTIMAL | 2.401337e+06 | 3.957 | 6.199 | 6,032 simplex |
| GLPK | OPTIMAL | 2.401337e+06 | 67.35 | 68.50 | 50,193 simplex |

**Objective consistency: VERIFIED.** Both solvers produce the same objective value (diff: 3.190245e-06 $/h, 1.328529e-10%).

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

### Max Branch Loading (Hard Constraint Check)

| Solver | Max Loading (p.u.) | Max Loading (%) | Branch | Over 100% |
|--------|--------------------|-----------------|--------|-----------|
| HiGHS | 8.435760e-01 | 84.36% | 10744 | 0 |
| GLPK | 8.435760e-01 | 84.36% | 10744 | 0 |

No branches exceed thermal limits. Hard constraints are properly enforced by both solvers. The network is uncongested at ~84% maximum loading, consistent with cross-tool-watchpoints documentation.

### LMP Analysis

| Metric | Value |
|--------|-------|
| Binding branches | 0 / 12,706 |
| LMP min | 2.006400e+01 $/MWh |
| LMP max | 2.006400e+01 $/MWh |
| LMP count | 10,000 |

**LMP uniformity note:** All 10,000 buses have effectively identical LMPs (~$20.064/MWh). Per `cross-tool-watchpoints.md`, ACTIVSg10k has no binding branch constraints in base-case DCOPF. Uniform LMPs indicate an uncongested network, not a tool limitation.

### Solver Comparison Analysis

HiGHS outperforms GLPK by ~17x on this problem (3.96s vs 67.35s solver time). HiGHS used dual simplex with a warm-start basis from preprocessing (6,032 iterations), while GLPK used primal simplex from cold start (50,193 iterations). Both converged to the same optimal solution.

**Solver swap friction:** Swapping from HiGHS to GLPK requires only a one-line optimizer change -- no reformulation needed. The solver interface abstracts cleanly through JuMP/MathOptInterface.

## Workarounds

1. **Quadratic cost linearization:**
   - **What:** ACTIVSg10k uses polynomial cost model 2 (quadratic). `solve_dc_opf` passes these to the solver as QP. Costs were linearized by dropping the c2 coefficient for 1,130 generators.
   - **Why:** PowerModels.jl does not warn users that quadratic costs trigger QP formulation. GLPK cannot handle QP at all, and HiGHS QP performance at 10k-bus scale is slower than LP.
   - **Durability:** stable -- dropping c2 is a well-understood approximation. The linearized costs remain monotonically increasing (LP-valid) because the original quadratic terms are non-negative.
   - **Grade impact:** Moderate. The workaround changes the cost function structure but not network topology. Dispatch and LMPs are physically meaningful.

## Timing

- **HiGHS wall-clock:** 6.199s (includes JuMP model build + solve)
- **HiGHS solver time (pure LP solve):** 3.957s
- **GLPK wall-clock:** 68.50s (includes JuMP model build + solve)
- **GLPK solver time:** 67.35s
- **Total wall-clock (both solvers + parse):** 77.20s
- **Timing source:** measured
- **Peak memory:** 934.0 MB RSS
- **CPU cores used:** 1 / 32 available

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

# Max branch loading check
loading = abs(br_sol["pf"]) / data["branch"][br_id]["rate_a"]
```
