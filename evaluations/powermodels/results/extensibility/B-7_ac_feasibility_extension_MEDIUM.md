---
test_id: B-7
tool: powermodels
dimension: extensibility
network: MEDIUM
status: pass
wall_clock_seconds: 53.392
timestamp: 2026-03-05
---

# B-7: AC Feasibility Extension Audit [MEDIUM]

## Result: PASS (no workaround needed)

## Summary
Same as TINY: A-4 (AC PF feasibility check on DC OPF dispatch) requires no workaround at 10k-bus scale. The workflow uses only native PowerModels functions:

1. `solve_dc_opf()` with Ipopt -- DC OPF dispatch
2. Set `gen["pg"]` values in fresh data dict
3. `compute_ac_pf!()` -- Newton-Raphson in-place solve
4. `calc_branch_flow_ac()` -- check violations

## Scale Observations
- DC OPF (Ipopt): ~20s on 10k-bus
- AC PF (native NR): ~30s on 10k-bus
- No API changes needed vs TINY

## Timing
- Wall-clock: 53.4s
