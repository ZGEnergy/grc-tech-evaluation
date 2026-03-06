---
test_id: A-5
tool: powermodels
network: TINY
status: pass
timestamp: 2026-03-05T19:00:00Z
---

# A-5: 24-Hour SCUC as MILP on case39

## Result: PASS (with major workaround)

## Metrics

- **Wall clock:** ~45 s (SCIP MIP solver)
- **Lines of code:** ~100 lines of custom JuMP code beyond PowerModels API
- **MIP gap:** 0.65%
- **Output format:** Nested `Dict` with commitment schedule as binary vectors
- **Workarounds:** 1 (critical -- see below)

## Details

- **Network:** 39 buses, 10 generators, 24 periods
- **Solver:** SCIP (HiGHS cannot solve MIQP -- mixed-integer quadratic program)
- **Objective:** 682,850 (total cost over 24 hours)
- **Approach:** Two-stage -- instantiate multi-network DC OPF via PowerModels, then add UC constraints via JuMP model access
- **Generators with off-periods:** 0 (all generators committed for all 24 hours on case39 at tested load levels)

### Custom Constraints Added

1. **Commitment linking:** `pmin * u[t,g] <= pg[t,g] <= pmax * u[t,g]`
2. **Startup/shutdown logic:** `u[t] - u[t-1] = v[t] - w[t]`
3. **Minimum up time:** 3 hours
4. **Minimum down time:** 2 hours
5. **Ramp rate limits:** Based on `ramp_10` data field, scaled to hourly
6. **Startup costs:** Added to objective function

### Load Profile

24-hour diurnal pattern ranging from 0.50 (hour 4) to 1.00 (hours 9-10, 18) of base load.

## Workaround

**PowerModels has NO built-in SCUC formulation.** The entire unit commitment logic (binary commitment variables, startup/shutdown tracking, min up/down times, ramp constraints, startup costs) had to be manually constructed via JuMP model access after calling `instantiate_model()`. This required:

1. Accessing internal PowerModels variables via `PowerModels.var(pm, nw, :pg, gen_id)`
2. Adding ~60 lines of JuMP constraint code
3. Replacing the solver (HiGHS -> SCIP) because HiGHS cannot handle MIQP
4. Deep knowledge of PowerModels' internal variable naming conventions

## API Pattern

```julia
mn_data = PowerModels.replicate(data, 24)
pm = PowerModels.instantiate_model(mn_data, DCPPowerModel, PowerModels.build_mn_opf)
model = pm.model
pg_vars[(t, g)] = PowerModels.var(pm, t, :pg, g)
# ... add binary variables, constraints, startup costs via JuMP ...
set_optimizer(model, SCIP.Optimizer)
optimize!(model)

```

## Notes

- The two-stage approach (PowerModels for network + JuMP for UC) works but is fragile
- Variable access pattern `PowerModels.var(pm, nw, :pg, gen_id)` is not well-documented
- All 10 generators stay committed in case39 because the network needs all generation capacity even at minimum load
- Ramp data (`ramp_10`) in case39 is generous enough that ramp constraints are not binding

## Test Script

See `evaluations/powermodels/tests/expressiveness/A5_scuc.jl`
