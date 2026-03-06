---
test_id: A-8
tool: powermodels
network: TINY
status: pass
timestamp: 2026-03-05T19:00:00Z
---

# A-8: Multi-Period Stochastic DC OPF on case39

## Result: PASS (qualified -- no native stochastic support)

## Metrics

- **Wall clock:** ~2.3 s
- **Lines of code:** ~60 lines
- **Output format:** Nested `Dict{String,Any}`
- **Workarounds:** 1 (significant)

## Details

- **Network:** 39 buses, 10 generators
- **Periods:** 24 (hourly, diurnal load profile 0.50-1.00 of base)
- **Scenarios:** 3 (multipliers: 1.0, 1.05, 0.95; probabilities: 0.5, 0.3, 0.2)
- **Solver:** Ipopt (HiGHS fails on large multi-network quadratic problems)
- **Total networks:** 72 (3 scenarios x 24 periods)

### Results

- **Multi-network objective (all 72 networks):** 2,053,062.66
- **Deterministic objectives per scenario:** [682,850.02, 753,193.20, 617,019.43]
- **Expected cost (probability-weighted deterministic):** 690,786.86
- **MN vs deterministic sum difference:** ~7e-10 (numerically identical, confirming independence)
- **Termination status:** LOCALLY_SOLVED

### Key Finding

The multi-network solve is mathematically equivalent to independent deterministic solves because:
1. DC OPF without commitment has no first-stage (here-and-now) decisions
2. All dispatch is recourse (second-stage), so scenarios decouple naturally
3. No non-anticipativity constraints are needed for pure dispatch problems

## Workaround

**PowerModels has NO native stochastic programming support.** Specifically missing:
- Probability weights on scenarios
- Scenario tree structure
- Non-anticipativity constraints for first-stage variables
- Two-stage stochastic programming formulation

The multi-network infrastructure (`replicate()` + `solve_mn_opf()`) provides scenario indexing but not stochastic structure. For dispatch-only problems, this reduces to independent scenario solves within a single JuMP model. For SCUC with commitment (binary first-stage decisions), non-anticipativity constraints on commitment variables would require manual JuMP-level construction (~20 additional lines).

## API Pattern

```julia
total_nw = nscenarios * nperiods  # 72
mn_data = PowerModels.replicate(data, total_nw)
# Modify loads per scenario-period
for s in 1:nscenarios, t in 1:nperiods
    nw_idx = (s-1) * nperiods + t
    mn_data["nw"]["$nw_idx"]["load"][lid]["pd"] = base_pd * profile[t] * multiplier[s]
end
result = solve_mn_opf(mn_data, DCPPowerModel, solver)

```

## Notes

- `replicate()` creates N independent copies with no coupling -- stochastic coupling must be added manually
- HiGHS fails with OTHER_ERROR on 72-network quadratic problems; Ipopt handles this correctly
- The flat scenario x period indexing scheme works but is not ergonomic for scenario tree structures
- Probability weighting of the objective must be done manually via JuMP objective replacement

## Test Script

See `evaluations/powermodels/tests/expressiveness/A8_stochastic_timeseries.jl`
