---
tag: workaround-needed
dimension: extensibility
test_id: B-7
observed: 2026-03-11
tool: powermodels
version: 0.21.5
---

# Workaround Needed: compute_ac_pf omits branch flows — stable workaround

## Observation

`PowerModels.compute_ac_pf(data)` does not populate `result["solution"]["branch"]` with AC
branch flows. This is consistent across A-2, A-4, and B-7 tests. To obtain AC branch flows for
thermal violation detection, the following two-step post-processing is required:

```julia

PowerModels.update_data!(data, ac_result["solution"])
flow_data = PowerModels.calc_branch_flow_ac(data)

```

## Classification

**Durability: stable.** `calc_branch_flow_ac` is a documented public API present since v0.18.3.
No undocumented internals accessed. Pattern confirmed in three independent test contexts (A-2,
A-4, B-7).

## Effort Impact

2 extra lines of public API calls. Not a capability gap — AC branch flows are fully accessible.
The workaround is documented in the official API reference.

## See Also

Prior observations:
- `api-friction-expressiveness-A2_acpf_branch_flows_require_post_processing.md`
- `api-friction-expressiveness-A4_acpf_branch_flows_require_post_processing.md`

This B-7 observation confirms the pattern persists across the full AC feasibility extension
workflow and classifies its durability as stable for grading purposes.
