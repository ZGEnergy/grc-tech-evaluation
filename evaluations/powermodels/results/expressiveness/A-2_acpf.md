---
test_id: A-2
tool: powermodels
network: TINY
status: pass
timestamp: 2026-03-05T19:00:00Z
---

# A-2: AC Power Flow (Newton-Raphson) on case39

## Result: PASS

## Metrics

- **Wall clock:** ~0.6 s
- **Lines of code:** 3 API calls (`parse_file`, `compute_ac_pf!`, `calc_branch_flow_ac`)
- **Output format:** Nested `Dict{String,Any}` with string keys
- **Workarounds:** None required

## Details

- **Network:** 39 buses
- **Method:** `compute_ac_pf!(data)` -- native Newton-Raphson solver (non-JuMP, mutates data in-place)
- **Convergence:** Yes
- **Voltage magnitude range:** 0.982 to 1.080 pu (all within normal operating bounds)
- **Total real power losses:** ~0.45 pu across all branches
- **Branch flows:** All 46 branches have P and Q flows (pf, pt, qf, qt)
- **Branch losses:** Computed as pf + pt per branch (positive = loss)

## API Pattern

```julia
data = PowerModels.parse_file(network_file)
PowerModels.compute_ac_pf!(data)  # mutates data in-place
branch_flows = PowerModels.calc_branch_flow_ac(data)

```

## Notes

- `compute_ac_pf!` mutates `data` in-place (note the `!` suffix) -- unlike `compute_dc_pf` which returns a result dict. This API inconsistency is a minor friction point.
- Full AC solution with voltage magnitudes, angles, and P/Q branch flows
- Losses are not a first-class output; must be computed manually as `pf + pt` per branch
- Fallback path via `solve_ac_pf(data, Ipopt.Optimizer)` available if native NR fails

## Test Script

See `evaluations/powermodels/tests/expressiveness/A2_acpf.jl`
