---
test_id: A-3
tool: powermodels
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: stable
wall_clock_seconds: 3.134
peak_memory_mb: 183.8
loc: 149
solver: Ipopt
timestamp: 2026-03-07T00:00:00Z
---

# A-3: Solve DC OPF on MEDIUM (ACTIVSg 10000-bus)

## Result: PASS

## Approach

Used `PowerModels.solve_dc_opf` with Ipopt (interior point, handles QP natively). Required data preparation for generators with empty cost arrays.

1. `PowerModels.parse_file("case_ACTIVSg10k.m")`
2. Fixed 1,349 generators with empty cost arrays (`ncost=0` or `cost=[]`) by setting `cost=[0.0, 0.0, 0.0]`, `ncost=3`
3. Noted 2,462 / 12,706 branches have `rate_a = 0.0` -- PowerModels handles these by assigning large default limits internally
4. `PowerModels.solve_dc_opf(data, Ipopt.Optimizer, setting=Dict("output"=>Dict("duals"=>true)))` to enable LMP extraction

## Output

- **Termination:** LOCALLY_SOLVED (Ipopt optimal)
- **Objective:** 2,436,631.22 $/hr
- **Ipopt iterations:** 25
- **Ipopt internal time:** 1.153s (total wall-clock including model build: 3.134s)
- **Total generation:** 1,509.17 p.u. (150,917 MW at 100 MVA base)
- **Generators dispatched:** 1,937 / 1,937 (all with pg > 0)
- **LMPs:** 10,000 nodal prices extracted from `bus["lam_kcl_r"]`
  - All LMPs = -2,073.77 $/p.u. (uniform across all buses)
  - No congestion: zero LMP spread indicates no binding branch flow constraints
  - Negative sign is PowerModels convention (shadow price of power balance equality)
- **Branch flows:** 12,706

## Data Workaround

1,349 generators in ACTIVSg10k have empty cost arrays (`ncost=0` or `cost=[]`), which causes PowerModels to error during model construction. These were patched to zero-cost quadratic functions before solving. This is a data quality issue in the ACTIVSg10k case file, not a PowerModels limitation.

## Solver Comparison

| Solver | Termination | Time | Objective | Note |
|--------|------------|------|-----------|------|
| Ipopt | LOCALLY_SOLVED | 3.13s | 2,436,631.22 | QP (quadratic costs) |
| HiGHS | TIME_LIMIT | 300s | 2,436,631.2 (approx) | QP ASM solver too slow for this scale |
| GLPK | OPTIMAL | 50.91s | 2,401,337.08 | LP only (costs linearized) |

The Ipopt/GLPK objective difference (~35k) is expected: GLPK solves a linearized version (quadratic cost terms removed), producing a lower objective.

## Timing

- Wall-clock: 3.134s (Ipopt, including model build)
- Ipopt internal: 1.153s (25 iterations)
- Peak memory: 183.8 MB
- Memory delta: 108.9 MB (from OPF solve)

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a3_dcopf_medium.jl`
Batch runner: `evaluations/powermodels/tests/test_medium_all.jl`
Supplemental: `evaluations/powermodels/tests/test_medium_supplemental.jl`
