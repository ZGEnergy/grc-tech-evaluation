---
tag: api-friction
source_dimension: expressiveness
source_test: A-2
tool: powermodels
severity: low
timestamp: 2026-03-12T03:24:30Z
---

# API Friction: compute_ac_pf does not populate branch flows in result dict

## Observation

`PowerModels.compute_ac_pf(data)` returns a result dict with `"solution"` containing `"bus"` (vm, va) and `"gen"` (pg, qg) — but no `"branch"` key. To obtain AC branch P/Q flows, the caller must:

1. Create a fresh copy of the data dict
2. Merge solution voltages into it: `data_copy["bus"][id]["vm"] = sol["vm"]`
3. Call `PowerModels.calc_branch_flow_ac(data_copy)`

The `calc_branch_flow_ac` function computes exact AC power flows from the voltage solution using the full admittance matrix.

## Code that triggers this

```julia

result = PowerModels.compute_ac_pf(data)
# result["solution"]["branch"]  -- key does not exist

```

## Workaround

```julia

data_for_flows = PowerModels.parse_file(network_file)
for (bus_id, sol) in result["solution"]["bus"]
    data_for_flows["bus"][bus_id]["vm"] = sol["vm"]
    data_for_flows["bus"][bus_id]["va"] = sol["va"]
end
flow_data = PowerModels.calc_branch_flow_ac(data_for_flows)
pf_mw = flow_data["branch"][br_id]["pf"] * base_mva

```

`calc_branch_flow_ac` is a documented public function, so this is a stable workaround.

## Impact

Low friction — `calc_branch_flow_ac` is clean and works correctly. The two-step process is counterintuitive but functional. Losses can be computed from `pf + pt` for each branch.

## Version

PowerModels.jl v0.21.5, Julia 1.10
