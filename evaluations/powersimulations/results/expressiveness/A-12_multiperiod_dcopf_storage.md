---
test_id: A-12
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "5661f0de"
status: partial_pass
workaround_class: fragile
blocked_by: null
wall_clock_seconds: 0.114
timing_source: measured
peak_memory_mb: 1188.7
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 681
solver: HiGHS
timestamp: "2026-03-24T00:00:00Z"
---

# A-12: 24-hour Multi-Period DCOPF with Storage

## Result: PARTIAL PASS

## Approach

Built a 24-hour multi-period DCOPF with renewables, branch derating, and battery storage.

**Multi-period DCOPF:** `DecisionModel` with `DCPPowerModel`, `ThermalDispatchNoMin`, and
`RenewableFullDispatch`. 24-hour load profile from Modified Tiny data with hourly resolution.
5 renewable generators (3 wind, 2 solar) with hourly forecast profiles from
`wind_forecast_24h.csv` and `solar_forecast_24h.csv`. 70% branch derating applied.

**Storage (critical finding):** PSI v0.30.2 does **not** have storage device formulations.
`EnergyReservoirStorage` exists as a data type in PowerSystems.jl v4.6.2, but PSI has no
`get_default_time_series_names` method for it -- meaning no formulation can be applied to
storage devices via `set_device_model!()`. [tool-specific: no storage formulation in PSI v0.30.2]

**BESS workaround:** Modeled the 150 MW / 600 MWh BESS by manually adding JuMP variables
and constraints to PSI's optimization model:
- `bess_charge[t]`, `bess_discharge[t]` (0 to 1.5 pu)
- `bess_soc[t]` (0.6 to 5.4 pu, representing 60-540 MWh)
- Energy balance: `SoC(t) = SoC(t-1) + eta_in * Pch(t) - Pdis(t) / eta_out`
- Cyclic SoC: `SoC(24) = SoC(0) = 3.0 pu` (300 MWh)
- Injection via `set_normalized_coefficient()` on nodal balance constraints

**Cost limitation:** Quadratic costs (`c2 = c1 * 0.001`) cause HiGHS to fail on multi-period
models (`OTHER_ERROR`). Single-period QP (A-3) works but 24-period QP does not. Used linear
costs with HiGHS. [solver-specific: HiGHS multi-period QP bug]

## Output

**Solver:** OPTIMAL, objective $1,669,918 (24h total production cost)

### Condition 1: Congestion (PASS)

All 24 hours have >= 2 binding branches. Branch shadow price evidence by hour:

| Hour | Binding Branches | Count |
|------|-----------------|-------|
| 1 | bus-1-bus-2, bus-2-bus-3 | 2 |
| 12 | bus-1-bus-2, bus-16-bus-19, bus-2-bus-3 | 3 |
| 18 (peak) | bus-1-bus-2, bus-6-bus-11, bus-16-bus-19, bus-2-bus-3 | 4 |
| 24 | bus-1-bus-2, bus-2-bus-3 | 2 |

Mean binding branches per hour: 2.7. Peak hour (18) has 4 binding branches. Branches
bus-1-bus-2 and bus-2-bus-3 bind in all 24 hours; bus-16-bus-19 binds during mid-day and
afternoon (hours 9-22).

### Condition 2: BESS Arbitrage (FAIL)

- Average charge LMP at BESS bus (bus-5): $36.61/MWh (24 charging hours)
- Average discharge LMP at BESS bus (bus-5): $35.68/MWh (21 discharging hours)
- Discharge LMP is NOT greater than charge LMP

The BESS charges and discharges simultaneously in most hours because the LP relaxation has
no mutual exclusion constraint (would require binary variables, making it a MIP). With linear
costs, LMPs are non-unique at the margin, and the BESS operates as a net load (total charge
3,324 MWh > total discharge 2,906 MWh) rather than performing price arbitrage. The round-trip
efficiency loss (87.4%) means the optimizer uses the BESS as a "loss sink" to reduce
generation at expensive buses. [solver-specific: linear costs produce non-unique LMPs; HiGHS
multi-period QP bug prevents quadratic costs]

### Condition 3: SoC Feasibility (PASS)

- SoC range: 60.0 - 540.0 MWh (within 10%-90% bounds)
- Cyclic SoC: initial 300 MWh, final 300 MWh (exactly equal)
- Energy balance max imbalance: 0.0 MWh (numerically exact)
- Min SoC: 60.0 MWh (= min_soc × energy_mwh = 0.10 × 600)
- Max SoC: 540.0 MWh (= max_soc × energy_mwh = 0.90 × 600)

### LMP Summary

| Hour | Min $/MWh | Max $/MWh | Spread | Mean |
|------|-----------|-----------|--------|------|
| 1 | 5.00 | 43.89 | 38.89 | 23.74 |
| 4 (valley) | 5.00 | 43.89 | 38.89 | 23.74 |
| 12 | 5.00 | 46.65 | 41.65 | 32.60 |
| 18 (peak) | 5.00 | 46.65 | 41.65 | 32.60 |
| 24 | 5.00 | 43.89 | 38.89 | 23.74 |

### Renewable Dispatch

| Unit | Type | Total MWh | Peak MW |
|------|------|----------|---------|
| WIND_1 | Wind | 2,307 | 141.5 |
| WIND_2 | Wind | 2,244 | 141.5 |
| WIND_3 | Wind | 2,258 | 134.9 |
| SOLAR_1 | Solar | 1,372 | 214.6 |
| SOLAR_2 | Solar | 1,481 | 207.0 |

Total renewable generation: 9,663 MWh (~7.6% of total system energy).

## Workarounds

- **What:** (1) Modeled BESS as manual JuMP variables/constraints injected into PSI's
  optimization model. (2) Used linear costs instead of quadratic (HiGHS QP failure).
  (3) Used `initialize_model=false` + `JuMP.optimize!()`.
- **Why:** (1) PSI v0.30.2 has no storage device formulations -- `EnergyReservoirStorage`
  is a PowerSystems.jl data type with no corresponding PSI formulation. (2) HiGHS fails
  with `OTHER_ERROR` on 24-period QP models (bug). (3) PSI initialization fails on this
  system configuration.
- **Durability:** fragile -- The JuMP-level BESS injection modifies PSI's internal constraint
  containers via `set_normalized_coefficient()`, which depends on PSI's internal naming
  conventions. The `initialize_model=false` bypass is also fragile. Future PSI versions
  (v0.31+) may add native storage support, making this workaround unnecessary.
- **Grade impact:** Multi-period DCOPF itself works natively (24h horizon, hourly resolution,
  renewables with time-varying profiles). The storage modeling limitation is version-specific.
  Two of three behavioral conditions pass (congestion and SoC feasibility). The BESS
  arbitrage condition fails due to linear costs producing non-unique LMPs combined with
  simultaneous charge/discharge in the LP relaxation. Status downgraded from qualified_pass
  to partial_pass under v11 because workaround_class is fragile and one behavioral condition
  fails.

## Timing

- **Wall-clock:** 0.114 s (second run, after JIT warm-up; includes build + solve)
- **Timing source:** measured
- **Peak memory:** 1188.7 MB (Julia process RSS)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a12_multiperiod_dcopf_storage.jl`

Key API pattern:
```julia
# Multi-period setup
timestamps_25 = [start_time + Hour(h-1) for h in 1:25]
add_time_series!(sys, load, SingleTimeSeries("max_active_power", ...))
transform_single_time_series!(sys, Hour(24), Hour(1))

# Renewables via PSI
re_gen = RenewableDispatch(; name=..., bus=bus, rating=pmax_pu, ...)
set_device_model!(template, RenewableDispatch, RenewableFullDispatch)

# Manual BESS (no native storage formulation in PSI v0.30.2)
@variable(jm, 0 <= bess_charge[t in timesteps] <= power_pu)
@variable(jm, 0 <= bess_discharge[t in timesteps] <= power_pu)
@variable(jm, min_soc <= bess_soc[t in timesteps] <= max_soc)
@constraint(jm, bess_soc[t] == bess_soc[t-1] + eta_in*Pch - Pdis/eta_out)
@constraint(jm, bess_soc[end] == init_soc)  # Cyclic SoC
JuMP.set_normalized_coefficient(nodal_cref, bess_discharge[t], 1.0)
JuMP.set_normalized_coefficient(nodal_cref, bess_charge[t], -1.0)
```

## Observations

- **api-friction:** PSI v0.30.2 lacks storage device formulations entirely. The
  `EnergyReservoirStorage` type exists in PowerSystems.jl but PSI cannot use it in
  `DecisionModel`. This is a significant gap for a production simulation framework.
- **solver-issues:** HiGHS fails with `OTHER_ERROR` on 24-period QP models but handles
  single-period QP (A-3) correctly. Ipopt solves the same QP successfully. This limits
  multi-period OPF to linear costs when using HiGHS.
- **workaround-needed:** The manual JuMP BESS injection is a fragile but functional
  workaround. The ability to access and modify PSI's JuMP model (via
  `get_optimization_container` + `get_jump_model` + `get_constraints`) is the key
  extensibility mechanism.
- **convergence-quality:** The LP with linear costs produces non-unique LMPs at the margin,
  which causes the BESS to behave as a net load rather than an arbitrageur. Quadratic costs
  would resolve this but require a different solver.
