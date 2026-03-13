---
test_id: A-9
tool: powermodels
dimension: expressiveness
network: SMALL
protocol_version: "v9"
skill_version: v1
test_hash: 4c844fba
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 109.58
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: 2
loc: 220
solver: HiGHS
timestamp: 2026-03-11T00:00:00Z
---

# A-9: SCOPF (Security-Constrained OPF) — SMALL

## Result: PASS

## Approach

Iterative Benders cutting-plane (same algorithm as TINY, adapted for 2000-bus network):

1. **Preprocessing**: Applied SMALL preprocessing (zero-x and zero-RATE_A fixes). 134 generator cost arrays were empty and were fixed/linearized (c2=0 for HiGHS LP stability).

2. **Base DC OPF**: Solved unconstrained DC OPF with HiGHS — OPTIMAL, objective $1,187,342.95/h.

3. **PTDF/LODF**: Computed PTDF matrix (3206×2000) via `PowerModels.calc_basic_ptdf_matrix`. Computed LODF matrix from PTDF (19.7s + 12.5s respectively).

4. **Contingency selection**: Top 50 branches by base-case loading fraction selected. Maximum loading: 91.9% of rating. No islanding pre-screening needed (LODF handles radial branches via near-zero denominator detection).

5. **Iterative loop**: Two-level PowerModels API (`instantiate_model` + `var(pm, :p)` + `optimize_model!`) with PTDF/LODF security constraints added as JuMP `@constraint`:
   - Iteration 1: No cuts → solve → 13 violations found → add 7 cuts (worst violation per contingency)
   - Iteration 2: 14 constraint rows applied → solve → 0 violations → **CONVERGED**

Security constraint form: `p_l + LODF_lk * p_k <= rate_a_l`

## Output

| Metric | Value |
|--------|-------|
| Network | 2000 buses, 3206 branches, 544 generators |
| Contingencies | 50 (highest-flow branches) |
| PTDF/LODF dims | 3206 × 2000 |
| Base OPF cost (unconstrained) | $1,187,342.95/h |
| SCOPF cost | $1,188,040.31/h |
| Cost increase | +$697.36/h (+0.059%) |
| SCOPF more expensive than base | YES |
| Iterative iterations | 2 |
| Security cuts added | 7 violation pairs |
| Contingency constraints in optimization | YES |
| Wall clock | 109.58s |

**Top 5 branch loadings (base case):** 91.9%, 86.5%, 85.9%, 85.9%, 85.3%

### Iteration log:

| Iter | Cuts accumulated | New violations | Objective |
|------|-----------------|----------------|-----------|
| 1 | 0 | 13 | $1,187,342.95/h |
| 2 | 7 | 0 (converged) | $1,188,040.31/h |

## Workarounds

- **What:** No built-in SCOPF in PowerModels.jl. Implemented iterative Benders cutting-plane using the documented two-level API.
- **Why:** PowerModelsSecurityConstrained.jl not installed. Iterative approach avoids building the prohibitively large monolithic SCOPF model (2000 buses × 51 scenarios = 102,544 variables, which exceeded 300s time limit at SMALL scale).
- **Durability:** stable — `instantiate_model`, `var(pm, :p)`, `@constraint(pm.model, ...)`, `optimize_model!`, `calc_basic_ptdf_matrix`, and `make_basic_network` are all documented public API.
- **Grade impact:** B-level. The mechanism is fully correct. The network converges in 2 iterations with a cost premium confirming SCOPF redispatch is required.

## Timing

- **Wall-clock:** 109.58s total
- **Breakdown:** Base OPF ~50s (includes JIT), PTDF ~20s, LODF ~12s, iteration 1 solve ~5s, iteration 2 solve ~5s
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** 2 Benders iterations
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a9_scopf_small.jl`

Key pattern:

```julia

pm = PowerModels.instantiate_model(deepcopy(data), PowerModels.DCPPowerModel,
                                   PowerModels.build_opf)
p_vars = PowerModels.var(pm, :p)
# LODF security constraint
@constraint(pm.model, p_vars[arc_l] + lodf_lk * p_vars[arc_k] <= rate_a_l)
@constraint(pm.model, p_vars[arc_l] + lodf_lk * p_vars[arc_k] >= -rate_a_l)
result = PowerModels.optimize_model!(pm; optimizer=highs_opt,
                                     solution_processors=[PowerModels.sol_data_model!])

```
