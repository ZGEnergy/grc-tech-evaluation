---
test_id: B-4
tool: powersimulations
dimension: extensibility
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "9eebb1b8"
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 2.534
timing_source: measured
peak_memory_mb: 1284.8
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 297
solver: HiGHS
timestamp: "2026-03-24T00:00:00Z"
---

# B-4: Stochastic Timeseries (20 Scenarios, 12h Multi-Period DCOPF)

## Result: PASS

## Approach

Generated 20 stochastic scenarios by applying correlated renewable multipliers from
`scenarios/scenario_multipliers_50x24.csv` to the base wind/solar forecast profiles.
For each scenario, built a 12-hour multi-period DCOPF with:

- 10 thermal generators with differentiated linear costs (hydro $5, nuclear $10,
  coal $25, gas CC $40/MWh)
- 5 renewable generators (3 wind + 2 solar) with scenario-modified hourly profiles
- 70% branch derating for congestion
- Hourly load profile from Modified Tiny data

Each scenario requires full System reconstruction: `System(network_file)` + cost
application + branch derating + renewable addition with scenario-specific time series +
load profile + `transform_single_time_series!` + model build + solve. Time series data
is immutable once attached to a System, so in-place modification is not possible.

**Solver:** HiGHS with linear costs, single-threaded, presolve on.

## Output

**All 20 scenarios converged** to OPTIMAL status.

**Per-scenario timing:**

| Metric | Value |
|--------|-------|
| Mean time per scenario | 0.127 s |
| Min time per scenario | 0.088 s |
| Max time per scenario | 0.593 s (scenario 1, includes residual JIT) |
| Total wall-clock (20 scenarios) | 2.534 s |

**Cross-scenario results:**

| Metric | Value |
|--------|-------|
| Objective min | $699,386 |
| Objective max | $707,108 |
| Objective mean | $702,980 |
| Objective std dev | $2,291 |
| LMP mean range | $26.37 (identical across scenarios) |
| LMP spread range | $41.65 (identical across scenarios) |

**Observation:** The LMP mean and spread are identical across all 20 scenarios. This
is because linear costs produce flat marginal cost curves, so LMPs are determined
entirely by which branches bind -- and with the same load profile and similar renewable
output across scenarios (multipliers are within +/-15%), the same branches bind in all
cases. The objective varies (~1%) because different renewable output levels shift
the dispatch mix. [solver-specific: HiGHS QP limitations prevent quadratic cost usage
that would differentiate LMPs across scenarios]

**Sample scenario results:**

| Scenario | Objective ($) | Total Gen (MWh) | Status |
|----------|--------------|----------------|--------|
| 1 | 701,029 | 53,517 | OPTIMAL |
| 10 | 701,931 | 53,567 | OPTIMAL |
| 20 | 700,537 | 53,555 | OPTIMAL |

## Workarounds

- **What:** Full System reconstruction required per scenario.
- **Why:** PowerSimulations.jl's time series data is immutable once attached to a
  System via `add_time_series!()`. There is no `set_time_series!()` or
  `update_time_series!()` API. To change renewable profiles for a new scenario,
  the entire System must be rebuilt from the MATPOWER file.
- **Durability:** stable -- the time series immutability is a design choice in
  InfrastructureSystems.jl (the underlying infrastructure layer). The workaround
  (System reconstruction per scenario) is reliable and produces correct results.
  The `add_time_series!` API is documented and stable.
- **Grade impact:** The per-scenario overhead is dominated by System construction
  and model building (~0.09 s), not by the solve (~0.01 s). For larger networks
  or many scenarios, this overhead would be more significant. A `Simulation` with
  `Scenarios` forecast type could potentially handle this natively, but that interface
  was not tested.

## Timing

- **Total wall-clock:** 2.534 s (20 scenarios)
- **Mean per scenario:** 0.127 s (build + solve)
- **Timing source:** measured (after JIT warm-up)
- **Peak memory:** 1284.8 MB (Julia process RSS, single-threaded)

## Test Script

**Path:** `evaluations/powersimulations/tests/extensibility/test_b4_stochastic_timeseries.jl`

Key API pattern:
```julia
# Per-scenario System construction
for s in 1:20
    sys = System(network_file)
    # ... apply costs, derating, add renewables with scenario multipliers ...

    # Scenario-specific renewable profile
    actual_mw = forecast_mw * scenario_multiplier[s, unit, hour]
    multiplier = clamp(actual_mw / pmax_mw, 0, 1)
    add_time_series!(sys, re_gen, SingleTimeSeries("max_active_power", ...))

    transform_single_time_series!(sys, Hour(12), Hour(1))

    # Build and solve
    model = DecisionModel(template, sys; optimizer=solver, initialize_model=false)
    build!(model; output_dir=mktempdir())
    JuMP.optimize!(PSI.get_jump_model(PSI.get_optimization_container(model)))

    # Extract results (LMPs, dispatch, objective)
end
```

## Observations

- **api-friction:** Time series immutability forces full System reconstruction per
  scenario. This is the primary ergonomic cost of stochastic wrapping in PSI. The
  `Simulation` API with `Scenarios` forecast type may avoid this but adds significant
  setup complexity. [tool-specific]
- **api-friction:** The `initialize_model=false` + `JuMP.optimize!()` pattern is
  needed to avoid PSI's internal initialization failures on multi-period models with
  renewables. This bypasses PSI's `solve!()` method and directly calls JuMP.
  [tool-specific]
- **workaround-needed:** The System reconstruction overhead (~90ms per scenario on
  TINY) is acceptable for 20 scenarios but would scale poorly for Monte Carlo studies
  with 1000+ scenarios on larger networks. The lack of in-place time series modification
  is a genuine API limitation. [tool-specific]
