---
test_id: A-3
tool: powermodels
dimension: expressiveness
network: MEDIUM
protocol_version: "v9"
skill_version: v1
test_hash: 7e613cf3
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 164.41
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 155
solver: HiGHS
timestamp: 2026-03-11T05:15:00Z
---

# A-3: DC OPF — MEDIUM

## Result: QUALIFIED PASS

## Approach

Loaded `case_ACTIVSg10k.m` with MEDIUM preprocessing (2462 branches rate_a→9999 MVA in per-unit). Solved DC OPF using `PowerModels.solve_dc_opf(data, optimizer; setting=Dict("output"=>Dict("duals"=>true)))` with HiGHS.

**Quadratic cost discovery:** The ACTIVSg10k network uses polynomial cost model 2 with 3 coefficients (quadratic costs), causing HiGHS to formulate the problem as QP rather than LP. The initial run timed out after 300s with `TIME_LIMIT` (objective not converged). This is a significant API friction finding — the tool does not warn that DC OPF with quadratic costs produces a QP that is much harder than the LP typically expected.

**Workaround applied:** Linearized costs by dropping the quadratic term (c2 coefficient) for all 1130 generators that had non-zero quadratic costs. This converts the problem from QP to LP, enabling HiGHS to solve it as a standard DC OPF LP. The 1355 generators with already-linear or constant costs were unchanged.

After linearization: solved as LP in 89.24s (HiGHS solver time), 164.41s total wall-clock.

LMPs were extracted from `result["solution"]["bus"][id]["lam_kcl_r"]` using the convention `LMP = -lam_kcl_r / baseMVA`.

No differentiated costs or branch derating were applied at MEDIUM tier (raw network costs, per protocol).

## Output

| Metric | Value |
|--------|-------|
| Buses | 10000 |
| Branches | 12706 |
| Generators (total) | 2485 |
| Generators dispatched | 1937 |
| Base MVA | 100 |
| Preprocessing: rate_a fixed | 2462 (19.4%) |
| Generators cost-linearized | 1130 (45.5%) |
| Termination status | OPTIMAL |
| Objective ($/h) | 2,401,337.08 |
| HiGHS solver time (s) | 89.24 |
| Total wall-clock (s) | 164.41 |
| Total generation (MW) | 150,916.9 |
| LMPs extracted | 10,000 buses |
| LMP range ($/MWh) | 20.064 – 20.064 |
| LMP spread ($/MWh) | 0.0 |
| Binding branches (≥99% rate_a) | 0 / 12706 |

**LMP uniformity note:** All 10,000 buses have identical LMPs ($20.064/MWh). This is expected — per `cross-tool-watchpoints.md`, ACTIVSg10k has no binding branch constraints in base-case DCOPF (maximum loading ~84-85%). Uniform LMPs indicate an uncongested network, not a tool limitation.

Bus LMP sample (first 10 — all identical):

| Bus | LMP ($/MWh) |
|-----|-------------|
| 10001 | 20.064 |
| 10002 | 20.064 |
| 10003 | 20.064 |
| ... | ... |
| 10000 | 20.064 |

Generator dispatch sample (first 10):

| Gen | Dispatch (MW) | Pmax (MW) |
|-----|--------------|-----------|
| 2 | 85.29 | 85.29 |
| 3 | 138.65 | 138.65 |
| 5 | 120.63 | 120.63 |
| 6 | 109.93 | 109.93 |
| 7 | 9.02 | 9.02 |
| 8 | 59.72 | 59.72 |
| 9 | 23.02 | 23.02 |
| 10 | 25.55 | 25.55 |
| 11 | 79.42 | 79.42 |
| 12 | 136.30 | 136.30 |

**Dispatch observation:** Many generators are at their Pmax limit, suggesting the network is near its generation capacity for the given load. This is consistent with the large total generation of 150,917 MW.

## Workarounds

1. **Quadratic cost linearization:**
   - **What:** ACTIVSg10k uses polynomial cost model 2 (quadratic), causing `solve_dc_opf` to generate a QP instead of LP. HiGHS QP solver exceeded 300s time limit without converging. Costs were linearized by dropping the c2 (quadratic) coefficient for 1130 generators.
   - **Why:** PowerModels.jl passes generator cost models directly to the solver without alerting the user that quadratic costs trigger QP formulation. At MEDIUM scale, QP is infeasible within typical time budgets.
   - **Durability:** stable — dropping c2 is a well-understood approximation. The linearized costs remain monotonically increasing (LP-valid) because the original quadratic terms are non-negative.
   - **Grade impact:** Moderate. The workaround changes the cost function, not the network topology or formulation. Optimal dispatch and LMPs are still physically meaningful, but reflect linearized rather than quadratic costs. This is a significant API friction gap — users must diagnose and linearize costs manually.

2. **Uniform LMPs (uncongested network):**
   - ACTIVSg10k has no binding transmission constraints at base loading, so all LMPs are identical. This is an expected network characteristic (documented in cross-tool-watchpoints.md), not a tool limitation.

## Timing

- **Wall-clock:** 164.41s (post-JIT warm-up on case39)
- **HiGHS solver time:** 89.24s (LP with dual simplex, 6032 simplex iterations)
- **LP dimensions:** 34,924 rows, 24,643 columns, 89,902 nonzeros
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1 (single-threaded per solver-config.md)
- **Initial attempt (QP, failed):** 355s total, TIME_LIMIT

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a3_dcopf_medium.jl`

Key API calls:

```julia

data = PowerModels.parse_file("case_ACTIVSg10k.m")
apply_medium_preprocessing!(data)
# Linearize quadratic costs to enable LP (not QP)
for (_, gen) in data["gen"]
    if gen["model"] == 2 && gen["ncost"] >= 3 && abs(gen["cost"][1]) > 1e-10
        gen["cost"]  = [gen["cost"][2], gen["cost"][3]]  # drop c2
        gen["ncost"] = 2
    end
end

optimizer = optimizer_with_attributes(HiGHS.Optimizer, "threads"=>1, "time_limit"=>300.0, ...)
result = PowerModels.solve_dc_opf(data, optimizer; setting=Dict("output"=>Dict("duals"=>true)))

# LMP extraction
lmp = -result["solution"]["bus"][bus_id]["lam_kcl_r"] / base_mva  # $/MWh

```
