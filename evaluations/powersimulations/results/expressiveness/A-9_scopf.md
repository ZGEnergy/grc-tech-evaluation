---
test_id: A-9
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "1771767b"
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.759
timing_source: measured
peak_memory_mb: 1290.0
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 387
solver: HiGHS
timestamp: "2026-03-24T00:00:00Z"
---

# A-9: SCOPF (DC OPF with N-1 Contingency Constraints)

## Result: QUALIFIED PASS

## Approach

No built-in SCOPF in PowerSimulations.jl. Manually assembled N-1 contingency constraints
using documented public APIs from three Sienna ecosystem packages:
1. **PowerNetworkMatrices.jl** -- `LODF(sys)` to compute the 46x46 Line Outage Distribution
   Factor matrix for all branches (Lines, Transformer2W, TapTransformer)
2. **PowerSimulations.jl** -- `PSI.get_optimization_container()` + `PSI.get_variables()` +
   `PSI.get_jump_model()` to access the underlying JuMP model and PSI variable containers
3. **JuMP.jl** -- `@constraint` macro to add post-contingency flow limit constraints directly
   to the optimization model

**Network configuration:** Full (100%) branch ratings, differentiated costs (same cost curves
as A-3). 70% derating with N-1 contingencies renders the problem infeasible on case39 due to
its radial sub-topology, so full ratings are used. The comparison DCOPF also uses full ratings.

**Contingency filtering:** Of 46 branches, 29 were skipped because their outage causes
islanding (max |LODF| >= 1.0 - 1e-6 for some monitored branch, indicating near-radial
topology). 17 contingencies were applied. This is a fundamental property of the IEEE 39-bus
network, which has several radial branches connecting generator buses.

**Constraint formulation:** For each applied contingency k and each monitored branch l
(l != k): `|flow_l + LODF[l,k] * flow_k| <= rating_l`. Total: 312 N-1 contingency constraints
added to the JuMP model. These are embedded in the optimization (not post-hoc checks).

## Output

**Termination status:** OPTIMAL

**Cost comparison:**

| Metric | DCOPF | SCOPF | Difference |
|--------|-------|-------|-----------|
| Objective ($) | 155,569.55 | 183,119.36 | +27,549.81 (+17.71%) |

SCOPF is 17.7% more expensive than unconstrained DCOPF, confirming that contingency constraints
are binding and affecting dispatch. [tool-specific: cost premium reflects manual constraint effort]

**Dispatch comparison (MW):**

| Generator | Bus | Tech | DCOPF | SCOPF | Difference |
|-----------|-----|------|-------|-------|-----------|
| gen-1 | 30 | Hydro | 859.09 | 807.61 | -51.48 |
| gen-2 | 31 | Nuclear | 646.00 | 646.00 | 0.00 |
| gen-3 | 32 | Nuclear | 725.00 | 501.72 | -223.28 |
| gen-4 | 33 | Coal | 652.00 | 652.00 | 0.00 |
| gen-5 | 34 | Coal | 508.00 | 508.00 | 0.00 |
| gen-6 | 35 | Nuclear | 687.00 | 687.00 | 0.00 |
| gen-7 | 36 | Gas CC | 467.80 | 580.00 | +112.20 |
| gen-8 | 37 | Nuclear | 564.00 | 368.91 | -195.09 |
| gen-9 | 38 | Nuclear | 865.00 | 859.61 | -5.39 |
| gen-10 | 39 | Gas CC | 280.34 | 643.37 | +363.03 |

Dispatches clearly differ: 6 of 10 generators have different dispatch. The SCOPF shifts
generation from cheap baseload (gen-1 hydro, gen-3 nuclear, gen-8 nuclear) to more expensive
peakers (gen-7 gas CC +112 MW, gen-10 gas CC +363 MW) to maintain N-1 security margins.

**Contingency statistics:**

| Metric | Value |
|--------|-------|
| Total branches in LODF | 46 |
| Contingencies applied | 17 |
| Contingencies skipped (islanding) | 29 |
| N-1 constraints added | 312 |
| All branch types included | Yes (Line + Transformer2W + TapTransformer) |

## Workarounds

- **What:** Manually assembled N-1 contingency constraints via LODF matrix and JuMP model
  access instead of using a built-in SCOPF formulation.
- **Why:** PowerSimulations.jl does not have a built-in SCOPF capability. The legacy N-1/G-1
  code was removed in v0.33.0 and was undocumented in v0.30.2.
- **Durability:** stable -- Uses documented public APIs: `LODF(sys)` from PowerNetworkMatrices.jl,
  `PSI.get_optimization_container()` / `PSI.get_variables()` / `PSI.get_jump_model()` from
  PowerSimulations.jl, and `@constraint` from JuMP.jl. All three are core ecosystem packages.
  The `get_jump_model` access pattern is documented in the arXiv paper and PSI tutorials.
- **Grade impact:** B-level. The approach requires ~50 lines of manual constraint assembly code
  using documented APIs from three packages. The LODF matrix and JuMP model access are stable
  public interfaces. The workaround produces mathematically correct results but requires
  power systems domain knowledge to implement correctly (LODF formulation, islanding detection).

## Timing

- **Wall-clock:** 0.759 s (second run, after JIT warm-up; includes model build + LODF computation + constraint injection + solve + reference DCOPF solve)
- **Timing source:** measured
- **Peak memory:** 1290.0 MB (Julia process RSS)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a9_scopf.jl`

Key API pattern:
```julia
# Step 1: Build DCOPF model
model = build_dcopf_model(sys, solver)

# Step 2: Compute LODF for all 46 branches
lodf_matrix = LODF(sys)

# Step 3: Access JuMP model and PSI flow variables (all branch types)
oc = PSI.get_optimization_container(model)
jm = PSI.get_jump_model(oc)
psi_vars = PSI.get_variables(oc)
# Collects FlowActivePowerVariable for Line, Transformer2W, TapTransformer

# Step 4: Add N-1 contingency constraints
for cont_branch in applied_contingencies
    for mon_branch in monitored_branches
        lodf_val = lodf_matrix[mon_branch, cont_branch]
        @constraint(jm, f_mon + lodf_val * f_cont <= rating)
        @constraint(jm, -(f_mon + lodf_val * f_cont) <= rating)
    end
end

# Step 5: Solve SCOPF
JuMP.optimize!(jm)
```

## Observations

- **workaround-needed:** PowerSimulations.jl lacks built-in SCOPF. N-1 security constraints
  must be manually assembled using LODF matrices and JuMP model access. This requires
  domain-specific knowledge (LODF formulation, islanding detection, constraint directionality).
  The approach works but is approximately 50 lines of manual code per test. Severity: medium.
- **api-friction:** The LODF matrix axes use PSI branch names (e.g., "bus-2-bus-3-i_3") which
  must be matched against PSI variable container axes. The namespace is consistent but not
  documented. Severity: low.
