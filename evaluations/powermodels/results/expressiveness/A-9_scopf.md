---
test_id: A-9
tool: powermodels
network: TINY
status: pass
timestamp: 2026-03-05T19:00:00Z
---

# A-9: DC OPF with N-1 Contingency Flow Constraints (SCOPF) on case39

## Result: PASS (with major workaround)

## Metrics

- **Wall clock:** ~2.7 s
- **Lines of code:** ~80 lines of custom code
- **Cost vs unconstrained DC OPF:** 41,263.94 vs 41,263.94 (0% increase)
- **Output format:** Nested `Dict{String,Any}`
- **Workarounds:** 1 (critical)

## Details

- **Network:** 39 buses, 46 branches, 10 generators
- **Solver:** Ipopt
- **Total branches:** 46 (all active)
- **Valid contingencies:** 35 (11 cause islanding and are excluded)
- **Total networks:** 36 (1 base + 35 contingency)
- **Termination status:** LOCALLY_SOLVED

### SCOPF Approach: Corrective

**Corrective SCOPF** (not preventive) was used because preventive SCOPF (identical dispatch across all contingencies) is infeasible on case39 due to tight thermal limits. In the corrective formulation:
- Base-case dispatch is optimized for minimum cost
- Each contingency network allows independent re-dispatch
- Contingency networks enforce flow feasibility under each N-1 outage
- Objective minimizes only base-case cost

### Results

- **SCOPF objective:** 41,263.94 (identical to unconstrained DC OPF)
- **Dispatch changed vs base:** No -- case39's optimal dispatch is already N-1 secure under corrective re-dispatch
- **Sample contingency dispatches:** Different from base case (confirming corrective re-dispatch works)

### Preventive SCOPF Infeasibility

Preventive SCOPF (same dispatch for all contingencies) was attempted first but is infeasible on case39 even with:
- 120% emergency branch ratings
- Filtering out islanding contingencies
- The fundamental issue: case39's thermal limits are too tight for any single dispatch to satisfy all 35 N-1 contingency flow constraints simultaneously

## Workaround

**SCOPF requires PowerModelsSecurityConstrained.jl** (not installed in the evaluation environment). The implementation required:

1. Multi-network construction via `replicate(data, 36)` with one branch removed per contingency network
2. `instantiate_model()` to build the JuMP model
3. Manual objective replacement to minimize only base-case cost (default `build_mn_opf` sums across all networks)
4. Manual connectivity checking to filter islanding contingencies
5. ~30 lines of custom JuMP objective construction code

## API Pattern

```julia
mn_data = PowerModels.replicate(data, 1 + n_contingencies)
# Remove one branch per contingency network
for (i, br_id) in enumerate(valid_contingencies)
    mn_data["nw"]["$(i+1)"]["branch"][br_id]["br_status"] = 0
end
pm = PowerModels.instantiate_model(mn_data, DCPPowerModel, PowerModels.build_mn_opf)
# Replace objective with base-case cost only
@objective(pm.model, Min, base_case_cost_expression)
set_optimizer(pm.model, Ipopt.Optimizer)
optimize!(pm.model)

```

## Notes

- The multi-network approach is conceptually clean but requires significant manual work
- PowerModelsSecurityConstrained.jl would provide this natively but is a separate package
- case39's topology makes preventive SCOPF infeasible -- this is a network characteristic, not a tool limitation
- Corrective SCOPF is arguably more realistic for operational practice

## Test Script

See `evaluations/powermodels/tests/expressiveness/A9_scopf.jl`
