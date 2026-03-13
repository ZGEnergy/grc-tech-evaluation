---
tag: api-friction
dimension: expressiveness
test_id: A-4
observed: 2026-03-11
tool: powermodels
version: 0.21.5
---

# API Friction: compute_ac_pf omits branch flows — confirmed in A-4 context

## Observation

The `compute_ac_pf` function does not populate `result["solution"]["branch"]` in the AC feasibility check context (A-4), confirming the prior A-2 observation. After fixing generator dispatch to DC OPF values and running `compute_ac_pf`, the branch solution dict is absent from the result.

Branch MVA flows required for thermal violation detection must be computed via:

```julia

PowerModels.update_data!(data, ac_result["solution"])
flow_data = PowerModels.calc_branch_flow_ac(data)

```

## Additional Finding: Thermal Violations Detectable

The AC feasibility check reveals 4 thermal violations not present in the DC OPF solution. The DC OPF honors the 70% derated `rate_a` limits for real power flows, but the ACPF apparent MVA flows (including reactive power) exceed the MVA rating on 4 branches:

| Branch | DC flow (MW) | AC MVA flow | Limit (MVA) |
|--------|------------|-------------|------------|
| 3 | 350.0 (binding) | 350.47 | 350.0 |
| 20 | 630.0 (binding) | 660.04 | 630.0 |
| 27 | 420.0 (binding) | 435.32 | 420.0 |
| 37 | 630.0 (binding) | 639.35 | 630.0 |

This confirms that the DC-to-AC feasibility gap is correctly surfaced by the workflow.

## Workaround

Use `update_data!` + `calc_branch_flow_ac`. This is a stable workaround using documented public API.
