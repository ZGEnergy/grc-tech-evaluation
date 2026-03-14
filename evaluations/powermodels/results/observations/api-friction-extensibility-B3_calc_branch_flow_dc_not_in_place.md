---
tag: api-friction
source_dimension: extensibility
source_test: B-3
tool: powermodels
severity: low
timestamp: 2026-03-14T00:47:28Z
---

# Observation: calc_branch_flow_dc returns a dict, not in-place

## Finding

`PowerModels.calc_branch_flow_dc(data)` returns a new dictionary with branch flow results rather than modifying `data` in-place. Additionally, `compute_dc_pf` results must be merged back into the data dict via `update_data!` before calling `calc_branch_flow_dc`. The private function `_calc_branch_flow_dc` exists but does not reliably populate branch `pf` fields. This pattern is not immediately obvious from the function name or documentation.

## Context

Discovered while implementing B-3 (N-M contingency sweep) and B-9 (PTDF validation). Initial implementation used `_calc_branch_flow_dc(data)` expecting in-place mutation, which silently produced zero flows. The correct pattern is:

```julia
pf_result = PowerModels.compute_dc_pf(data)
PowerModels.update_data!(data, pf_result["solution"])
flow_dict = PowerModels.calc_branch_flow_dc(data)
# Access flows via: flow_dict["branch"][br_id]["pf"]
```

## Implications

Minor API friction. The three-step pattern (solve, merge, compute flows) is documented but not emphasized. Users expecting a single-call flow computation will encounter silent zeros on their first attempt. This should be noted in the Accessibility audit as a discoverability issue.
