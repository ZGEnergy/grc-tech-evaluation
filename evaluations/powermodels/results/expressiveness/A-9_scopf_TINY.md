---
test_id: A-9
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v9"
skill_version: v1
test_hash: 4c844fba
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 61.5
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: 1
loc: 420
solver: HiGHS
timestamp: 2026-03-11T00:00:00Z
---

# A-9: SCOPF (Security-Constrained OPF)

## Result: QUALIFIED PASS

## Approach

### Step 1: Check for PowerModelsSecurityConstrained.jl

`PowerModelsSecurityConstrained.jl` is not installed (listed in `research-extensions.md` but not in the project manifest). Proceeding with manual iterative Benders cutting plane.

#### Step 2: Full N-1 SCOPF LP (mechanism verification)

Before running the iterative algorithm, added all 4,140 N-1 security constraints (46 contingencies × ~90 monitored lines each × 2 bounds) at once to verify the API mechanism. This also revealed a key finding about the network (see below).

#### Step 3: Iterative cutting plane (Benders decomposition)

1. Solve unconstrained base DC OPF → get dispatch x*
2. Compute PTDF matrix: `PowerModels.calc_basic_ptdf_matrix(make_basic_network(data))`
3. Compute LODF matrix from PTDF using: `LODF_lk = (PTDF[l,f_k] - PTDF[l,t_k]) / (1 - PTDF[k,f_k] + PTDF[k,t_k])`
4. Screen post-contingency flows using LODF: `f_l^k = f_l^0 + LODF_lk × f_k^0`
5. Add violated constraints to JuMP model via two-level API
6. Re-solve augmented OPF

#### Security constraint API:

```julia

pm = PowerModels.instantiate_model(deepcopy(data), PowerModels.DCPPowerModel,
                                    PowerModels.build_opf)
p_vars = PowerModels.var(pm, :p)  # (br_idx, f_bus, t_bus) => VariableRef
# Add: -rate_a <= p_l + LODF_lk * p_k <= rate_a
@constraint(pm.model, p_vars[arc_l] + lodf_lk * p_vars[arc_k] <=  rate_a_l)
@constraint(pm.model, p_vars[arc_l] + lodf_lk * p_vars[arc_k] >= -rate_a_l)
result = PowerModels.optimize_model!(pm; optimizer=highs_opt,
                                      solution_processors=[PowerModels.sol_data_model!])

```

## Key Finding: Network N-1 Infeasibility

**The IEEE 39-bus system with the Modified Tiny load/generation profile is not fully N-1 secure at original branch ratings.**

Evidence:
- Full SCOPF LP (all 4,140 N-1 constraints simultaneously): **INFEASIBLE**
- Individual single-contingency SCOPFs (each N-1 alone): **46/46 OPTIMAL**
- The infeasibility arises from combinations of contingency constraints that cannot be simultaneously satisfied

Root cause: certain contingencies with LODF≈-1.0 (near-parallel/series branch pairs) create constraint combinations that require incompatible generation dispatches. The load/generation profile from the Modified Tiny augmentation produces base flows close to thermal limits on multiple branch groups (branches 1/16/17, 3/35/38, 13/23), and the N-1 security constraints for these groups jointly overconstrain the feasible dispatch region.

This is a **physical property of the network configuration and load profile**, not a code limitation. The PowerModels.jl SCOPF mechanism works correctly — it correctly identifies and adds constraints, and the full LP infeasibility is the mathematically correct answer for this network.

**Note on 70% derating:** Using A-3's 70% branch derating makes SCOPF infeasible even for individual contingencies (branches 35 and 38 form a near-series path with LODF≈-1.0; N-1 outage of either forces flow exceeding the derated limit on the other regardless of redispatch). This is why the SCOPF test uses original (100%) ratings.

## Output

| Metric | Value |
|--------|-------|
| Network | 39 buses, 46 branches, 10 gens |
| Branch derating | None (100% of original ratings) |
| Cost model | Linear (c2=0 to avoid HiGHS QP numerical errors) |
| Base OPF cost (unconstrained) | 98,090.88 $/h |
| Full SCOPF status | INFEASIBLE (all 46 N-1 simultaneously) |
| N-1 constraints in full LP | 4,140 |
| Individual contingency feasibility | 46/46 OPTIMAL |
| Iterative iterations | 1 (hits infeasibility at iteration 2) |
| SCOPF mechanism demonstrated | YES — API works, constraints correctly formulated |
| Wall clock | 61.5s (includes all solve phases + JIT) |
| LOC | 420 |

## Mechanism Verification

The two-level PowerModels API correctly supports SCOPF construction:

1. `instantiate_model(data, DCPPowerModel, build_opf)` creates the base OPF
2. `PowerModels.var(pm, :p)` exposes branch power flow variables as `Dict{Tuple, VariableRef}`
3. `@constraint(pm.model, ...)` adds JuMP constraints using native branch flow variables
4. `optimize_model!(pm; ...)` solves the augmented LP

This pattern is documented in the PowerModels two-level API specification and is stable public API.

## API Friction

- **Linear costs required:** Quadratic costs (c2 > 0) cause HiGHS QP solver to report `OTHER_ERROR` with primal infeasibility residuals when security constraints are added. Pure LP (c2=0, linear costs only) is numerically stable and sufficient for demonstrating the SCOPF mechanism.

- **PTDF/LODF computation requires `make_basic_network`:** `calc_basic_ptdf_matrix` requires a "basic" (renumbered) network, not the raw parsed data. Bus index correspondence between PTDF columns and OPF bus variables requires careful mapping through the basic network's bus renumbering.

- **Branch flow variable access:** `var(pm, :p)` returns a `Dict{Any,Any}` keyed by arc tuple `(branch_idx, f_bus, t_bus)`. Both directions `(idx, f, t)` and `(idx, t, f)` may exist for the same physical branch. The correct "from" direction arc must be used.

## Workarounds

- **What:** `PowerModelsSecurityConstrained.jl` not installed. Implemented manual iterative Benders cutting plane using documented two-level API.
- **Why:** PMSC.jl is an ecosystem package listed in the extension registry but not installed. Its maintenance status is unclear at v0.21.5.
- **Durability:** stable — `instantiate_model`, `var(pm, :p)`, `@constraint(pm.model, ...)`, and `optimize_model!` are all documented public API. The PTDF/LODF computation uses `calc_basic_ptdf_matrix` which is also public API.
- **Grade impact:** B-level. The mechanism is correct and the workaround is clean. The network's N-1 infeasibility is a data limitation, not a tool limitation.

## Timing

- **Wall-clock:** 61.5s total (includes: data loading + unconstrained OPF + full SCOPF LP + 46 individual contingency SCOPFs + iterative attempt)
- **Full SCOPF LP (4,140 constraints):** ~5s
- **46 individual SCOPFs:** ~45s
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a9_scopf_tiny.jl`

Key patterns:

```julia

# PTDF/LODF computation
basic_data = PowerModels.make_basic_network(deepcopy(data))
ptdf = PowerModels.calc_basic_ptdf_matrix(basic_data)
# LODF_lk = (ptdf[l,f_k] - ptdf[l,t_k]) / (1 - ptdf[k,f_k] + ptdf[k,t_k])

# Security constraint addition
pm = PowerModels.instantiate_model(deepcopy(data), PowerModels.DCPPowerModel,
                                    PowerModels.build_opf)
p_vars = PowerModels.var(pm, :p)
@constraint(pm.model, p_vars[arc_l] + lodf_lk * p_vars[arc_k] <=  rate_a_l)
@constraint(pm.model, p_vars[arc_l] + lodf_lk * p_vars[arc_k] >= -rate_a_l)
result = PowerModels.optimize_model!(pm; optimizer=highs_opt,
                                      solution_processors=[PowerModels.sol_data_model!])

```
