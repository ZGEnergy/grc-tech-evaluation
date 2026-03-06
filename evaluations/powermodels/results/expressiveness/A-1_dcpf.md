---
test_id: A-1
tool: powermodels
network: TINY
status: pass
timestamp: 2026-03-05T19:00:00Z
---

# A-1: DC Power Flow on case39

## Result: PASS

## Metrics

- **Wall clock:** ~2.1 s (includes Julia compilation; subsequent calls ~0.01 s)
- **Lines of code:** 3 API calls (`parse_file`, `compute_dc_pf`, `calc_branch_flow_dc`)
- **Output format:** Nested `Dict{String,Any}` with string keys (not typed structs)
- **Workarounds:** None required

## Details

- **Network:** 39 buses, 46 branches, 10 generators
- **Method:** `compute_dc_pf(data)` -- native non-JuMP solver (direct PTDF computation)
- **Reference bus:** bus 31 (bus_type == 3), angle = 0.0 rad
- **Non-zero voltage angles:** 38 of 39 buses (all except reference)
- **Branch flows:** All 46 branches have non-trivial `pf`/`pt` values via `calc_branch_flow_dc(data)`
- **Nodal injections:** Computed manually from gen/load data (not a built-in API call)

## API Pattern

```julia
data = PowerModels.parse_file(network_file)
result_dc = PowerModels.compute_dc_pf(data)
PowerModels.update_data!(data, result_dc["solution"])
branch_flows = PowerModels.calc_branch_flow_dc(data)

```

## Notes

- `compute_dc_pf` returns a result dict; it does NOT mutate `data` in-place (unlike `compute_ac_pf!`)
- Must call `update_data!` before `calc_branch_flow_dc` to propagate solution angles into the data dict
- All results are `Dict{String,Any}` with string keys -- requires manual type handling
- No DataFrame or tabular output; user must extract fields from nested dicts

## Test Script

See `evaluations/powermodels/tests/expressiveness/A1_dcpf.jl`
