---
test_id: A-11
tool: powermodels
network: TINY
status: pass
timestamp: 2026-03-05T21:00:00Z
---

# A-11: DC OPF with Distributed Slack (Load-Proportional) on case39

## Result: PASS (with workaround)

## Metrics

- **Wall clock:** ~2.5 s
- **Lines of code:** ~40 lines custom build function
- **Workarounds:** 1 (no native distributed slack)
- **Depends on:** A-3 (single-slack DC OPF for comparison)

## Details

- **Network:** 39 buses, 10 generators
- **Solver:** HiGHS (QP)
- **Single-slack reference bus:** Bus 31
- **Distributed slack method:** Load-proportional weighted angle-sum constraint

### Objective Comparison

| Config | Objective | Status |

|--------|-----------|--------|

| Single slack (A-3) | 41,263.94 | OPTIMAL |

| Distributed slack | 41,263.94 | OPTIMAL |

Objective difference: 0.0

### LMP Comparison

- **Max LMP difference:** 0.0 (all buses identical to 6 decimal places)
- **All 39 buses** report LMPs in both configurations
- LMPs are uniform across all buses (~-1351.69) because case39 has no binding thermal constraints

### Dispatch Comparison

- **All 10 generators:** dispatch differences = 0.0
- Identical dispatch in both configurations

### Why Results Match

In lossless DC OPF, the slack bus (or distributed slack) only sets the angle reference point. The optimization (dispatch, LMPs, costs) is invariant to the choice of angle reference. This is confirmed by the identical objectives, LMPs, and dispatch values.

## Workaround

**PowerModels has NO native distributed slack.** Required a custom build function (~40 LOC) that:
1. Calls all standard variable/constraint/objective functions from `build_opf`
2. Replaces `constraint_theta_ref` with a load-proportional angle-sum constraint: `sum(w_i * va_i) = 0`
3. Weights `w_i = load_i / total_load` for buses with load, uniform weight for load-free buses
4. Passes custom build function to `solve_model()`

This is the same pattern discovered in B-8 (reference bus configuration).

## API Pattern

```julia
function build_distributed_slack_opf(pm::PowerModels.AbstractPowerModel)
    PowerModels.variable_bus_voltage(pm)
    PowerModels.variable_gen_power(pm)
    PowerModels.variable_branch_power(pm)
    PowerModels.variable_dcline_power(pm)
    PowerModels.objective_min_fuel_and_flow_cost(pm)
    PowerModels.constraint_model_voltage(pm)
    # Distributed slack: weighted angle-sum = 0
    bus_ids = collect(PowerModels.ids(pm, :bus))
    va_expr = sum(weight_i * PowerModels.var(pm, :va, i) for i in bus_ids)
    JuMP.@constraint(pm.model, va_expr == 0.0)
    # ... standard bus/branch constraints ...
end
result = PowerModels.solve_model(data, DCPPowerModel, HiGHS.Optimizer,
    build_distributed_slack_opf; setting=Dict("output"=>Dict("duals"=>true)))

```

## Notes

- Custom build function requires reproducing all standard OPF constraints manually (~30 lines of boilerplate)
- The `constraint_theta_ref` function is not easily overridable; must replace entire build function
- For lossy DC OPF (A-10), distributed slack could produce different LMPs

## Test Script

See `evaluations/powermodels/tests/expressiveness/A11_distributed_slack_opf.jl`
