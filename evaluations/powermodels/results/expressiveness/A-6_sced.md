---
test_id: A-6
tool: powermodels
network: TINY
status: pass
timestamp: 2026-03-05T21:00:00Z
---

# A-6: Security-Constrained Economic Dispatch (SCED) on case39

## Result: PASS (with workaround)

## Metrics

- **Wall clock:** ~1.4 s (HiGHS QP solver)
- **Lines of code:** ~50 lines of custom JuMP code beyond PowerModels API
- **Workarounds:** 1 (no built-in SCED)
- **Depends on:** A-5 (SCUC commitment schedule)

## Details

- **Network:** 39 buses, 10 generators, 24 periods
- **Solver:** HiGHS (continuous QP -- no binary variables since commitment is fixed)
- **Objective:** 682,850.02 (matches A-5 objective, confirming UC/ED consistency)
- **Termination status:** OPTIMAL
- **Commitment source:** A-5 result (all 10 generators committed for all 24 hours)

### UC/ED Separation

- **UC and ED cleanly separable:** Yes
- **Separation method:** Commitment fixed as parameter (not decision variable), ED solved as continuous QP
- The A-5 SCUC objective (682,850) exactly matches the A-6 ED objective, confirming that fixing the commitment schedule and re-solving dispatch produces a consistent result.

### Ramp Constraints

- **Ramp constraints enforced:** Yes (0 violations)
- **Ramp constraints added:** 460 (2 per generator per inter-period transition, 10 gens x 23 transitions x 2 directions)
- **Ramp limits:** Based on `ramp_10` field scaled to hourly; most generators have ramp limits equal to pmax (generous limits in case39)
- **Max observed ramp:** 0.964 pu (gen 1,3,4,6,7,8,9,10) -- well within limits

### Dispatch Pattern

Generators track the load profile smoothly. At peak periods (hours 10-11), generators 5, 7, 8 hit their pmax limits. At off-peak (hours 3-4), all generators dispatch proportionally near 3.1 pu.

## Workaround

**PowerModels has no built-in SCED formulation.** Required custom JuMP code after `instantiate_model()` to:
1. Fix commitment via pmin/pmax bounds (trivial for all-committed case)
2. Add inter-period ramp constraints (~20 lines)
3. Use HiGHS for continuous QP solve (vs SCIP for MIP in A-5)

This is the same pattern as A-5 but simpler since no binary variables are needed.

## API Pattern

```julia
mn_data = PowerModels.replicate(data, 24)
pm = PowerModels.instantiate_model(mn_data, DCPPowerModel, PowerModels.build_mn_opf)
pg_vars[(t,g)] = PowerModels.var(pm, t, :pg, g)
# Fix commitment (pmin/pmax bounds)
@constraint(model, pg >= pmin * u)
@constraint(model, pg <= pmax * u)
# Add ramp constraints
@constraint(model, pg_t - pg_tm1 <= ramp_limit)
@constraint(model, pg_tm1 - pg_t <= ramp_limit)
set_optimizer(model, HiGHS.Optimizer)
optimize!(model)

```

## Notes

- HiGHS solves the continuous QP in 0.16s (much faster than SCIP MIP in A-5)
- The dispatch schedule is identical to A-5 because all generators stay committed and ramp limits are non-binding
- Case39 ramp data (`ramp_10`) is generous enough that ramp constraints are not binding in this test

## Test Script

See `evaluations/powermodels/tests/expressiveness/A6_sced.jl`
