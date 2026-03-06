---
test_id: A-3
tool: powermodels
network: TINY
status: pass
timestamp: 2026-03-05T19:00:00Z
---

# A-3: DC OPF with Generation Costs and Line Flow Limits on case39

## Result: PASS

## Metrics

- **Wall clock:** ~1.5 s
- **Lines of code:** 2 API calls (`parse_file`, `solve_dc_opf`)
- **Output format:** Nested `Dict{String,Any}` with string keys
- **Workarounds:** None required for primary solve

## Details

- **Network:** 39 buses, 10 generators
- **Solver:** HiGHS (primary), GLPK (secondary)
- **Objective (HiGHS):** 41263.94 $/hr
- **Termination status:** OPTIMAL
- **LMP extraction:** Via `setting = Dict("output" => Dict("duals" => true))`, bus duals at key `lam_kcl_r`
- **LMP range:** Uniform across all buses (~-1356.8 to -1356.8) -- no congestion on case39
- **Congested branches:** 0 (case39 has sufficient capacity for optimal dispatch)
- **Branch duals:** `mu_sm_fr` and `mu_sm_to` available for all branches (all zero = no congestion)

### GLPK Secondary Solver

- GLPK fails on case39 because the cost model is quadratic (model=2, ncost=3) and GLPK only supports linear objectives
- Error: `MathOptInterface.UnsupportedAttribute`
- This is expected behavior, not a PowerModels bug

## API Pattern

```julia
data = PowerModels.parse_file(network_file)
result = solve_dc_opf(data, HiGHS.Optimizer;
    setting = Dict("output" => Dict("duals" => true)))
lmps = Dict(bid => bus["lam_kcl_r"] for (bid, bus) in result["solution"]["bus"])

```

## Notes

- Dual extraction requires explicit `setting` parameter -- not enabled by default
- LMP sign convention: negative values (cost interpretation, not price)
- GLPK incompatibility with quadratic costs is a solver limitation, not a tool limitation
- case39 has no binding branch constraints at optimal dispatch, so LMPs are uniform

## Test Script

See `evaluations/powermodels/tests/expressiveness/A3_dcopf.jl`
