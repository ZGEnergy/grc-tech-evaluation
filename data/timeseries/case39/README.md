# Augmented IEEE 39-Bus Test Case (TINY)

This directory contains an augmented version of the IEEE 39-bus (New England)
test case. The canonical `case39.m` ships with 10 identical-cost generators,
no renewables, no storage, and no time-varying data — it was designed for
single-snapshot power flow, not for exercising OPF, unit commitment, or
market-clearing functionality. This augmented dataset adds the missing
pieces so that evaluation tests can probe those capabilities.

## What changed vs. the canonical case

| Aspect | Canonical case39 | This augmented version |
|--------|------------------|------------------------|
| Generator costs | $0.30/MWh for all 10 | Fuel-type costs: hydro $5, nuclear $10, coal $25–32, gas CC $40, gas CT $55 |
| Fuel types | Unlabeled | Classified: 1 hydro, 5 nuclear, 2 coal, 2 gas CC |
| Temporal params | None | Ramp rates, min-up/down, startup costs per technology |
| Renewables | None | 5 units: 3 wind (732 MW) + 2 solar (488 MW), 20% penetration |
| Storage | None | 1 BESS: 150 MW / 600 MWh, 87% round-trip efficiency |
| Demand response | None | 1 DR bus: 25 MW curtailment at bus 20 |
| Load profile | Single snapshot | 24-hour profile across 21 load buses |
| Reserves | None | Spinning + non-spinning requirements, per-unit eligibility |
| Stochastic scenarios | None | 50 correlated scenarios for renewable output |
| Flowgates | None | 3 flowgates derived from DC OPF congestion analysis |
| Congestion | Uncongested at nominal ratings | Congested at 70% branch derating with diverse RE placement |

## File inventory

### Network definition

- **`case39.m`** — Cleaned MATPOWER case file. Generator `Pg`/`Qg` reset to
  zero (dispatch is a solver output, not an input), voltage angles
  normalized, hydro Pmin set for reservoir operation. The base topology,
  impedances, and ratings are unchanged from the original IEEE case.

- **`cleanup_manifest.json`** — Provenance log of every modification applied
  during cleanup, with rule names and counts.

### Generator augmentation

- **`gen_classification.csv`** — Fuel type and RTS-GMLC technology class for
  each of the 10 generators.

  | Column | Description |
  |--------|-------------|
  | `gen_index` | 0-based index matching MATPOWER gen row order |
  | `bus_id` | Generator bus number |
  | `fuel_category` | High-level fuel: `hydro`, `nuclear`, `ng` |
  | `rts_gmlc_class` | Technology class: `Hydro`, `Nuclear`, `Coal/Steam`, `Gas/CC` |
  | `pmax_mw`, `pmin_mw` | Capacity bounds (MW) |

- **`gen_temporal_params.csv`** — Unit commitment parameters derived from
  RTS-GMLC technology medians, scaled by capacity ratio.

  | Column | Description |
  |--------|-------------|
  | `gen_uid` | Unique ID, e.g. `case39_bus30_gen1` |
  | `tech_class_key` | Key for cost lookup: `hydro`, `nuclear`, `coal_large`, `gas_CC` |
  | `ramp_rate_mw_per_min` | Ramp capability (MW/min) |
  | `min_up_time_hr`, `min_down_time_hr` | Minimum run/down time (hours) |
  | `startup_cost_cold_dollar` | Cold start cost ($); warm and hot also provided |
  | `no_load_cost_dollar_per_hr` | No-load cost ($/hr) |

  **How to use for OPF cost curves:** The MATPOWER `gencost` rows in `case39.m`
  are the original homogeneous values. Replace them with quadratic cost curves
  using the `tech_class_key` field:

  ```
  tech_class_key     c1 ($/MWh)    Suggested c2 ($/MW^2h)
  hydro                 5.0         0.005
  nuclear              10.0         0.010
  coal_large           25.0         0.025
  gas_CC               40.0         0.040
  ```

  The `c2` coefficient produces a marginal cost that increases with output,
  which is necessary for QP-based OPF to produce scenario-differentiated
  LMPs and shadow prices. With `c2 = c1 * 0.001`, marginal cost increases
  roughly 40% from zero to typical dispatch levels.

### Renewable generators

- **`renewable_units.csv`** — 5 variable renewable generators to add to the
  network. These are *not* in the `.m` file — they must be added as new
  generators (or equivalent component) by the tool under test.

  | Column | Description |
  |--------|-------------|
  | `gen_uid` | Unit ID: `WIND_1`, `WIND_2`, `WIND_3`, `SOLAR_1`, `SOLAR_2` |
  | `bus_id` | Connection bus (2, 5, 6, 16, 19) |
  | `type` | `wind` or `solar` |
  | `pmax_mw` | Nameplate capacity (243.88 MW each) |

  Buses were selected for transmission headroom (sum of connected branch
  ratings) and area diversity to spread renewables across the network.

- **`wind_forecast_24h.csv`**, **`solar_forecast_24h.csv`** — Day-ahead
  forecast profiles (MW) for each renewable unit, 24 hours. These are the
  expected dispatch levels to use as `p_max_pu` (normalized by `pmax_mw`)
  or as fixed injection for must-take renewables.

- **`wind_actual_24h.csv`**, **`solar_actual_24h.csv`** — Realized output
  (MW). The difference from forecast represents forecast error. Solar
  profiles are zero outside hours 7–18.

- **`renewable_placement.json`** — Provenance: placement algorithm details,
  total penetration (20% of peak load), per-unit bus selection rationale.

### Load profile

- **`load_24h.csv`** — Hourly load (MW) at each of 21 load buses, 24 hours.
  Row = bus, column = `HR_1` through `HR_24`. The profile peaks at HR 18
  (6,254 MW system total) and troughs at HR 4 (5,028 MW). Loads at non-load
  buses (generators-only stubs) are zero and omitted.

  **How to use:** Set each bus's `Pd` to the value for the hour being solved.
  For single-snapshot studies, HR 18 (peak) is the most congested hour.

- **`load_metadata.json`** — System peak, hourly shape multipliers, bus
  coverage.

### Energy storage

- **`bess_units.csv`** — One 4-hour lithium-ion battery.

  | Field | Value |
  |-------|-------|
  | `unit_id` | `BESS_1` |
  | `bus_id` | 5 (co-located with SOLAR_1 for midday arbitrage) |
  | `power_mw` | 150 (charge and discharge limit) |
  | `energy_mwh` | 600 |
  | `efficiency` | 0.874 (round-trip: 92% charge × 95% discharge) |
  | `min_soc` | 0.10 (60 MWh floor) |
  | `max_soc` | 0.90 (540 MWh ceiling) |
  | `init_soc` | 0.50 (300 MWh) |

  **How to use:** Add as a `StorageUnit` (PyPSA), `storage` element
  (pandapower), or equivalent. For multi-period OPF, enforce the
  inter-temporal SoC constraint:
  `SoC(t) = SoC(t-1) + η_ch·Pch(t)·Δt − Pdis(t)·Δt/η_dis`

  For single-period studies, the BESS can be modeled as a generator with
  `Pmin = −150` (charging) and `Pmax = 150` (discharging), ignoring SoC.

### Demand response

- **`dr_buses.csv`** — One DR-eligible bus.

  | Field | Value |
  |-------|-------|
  | `bus_id` | 20 (680 MW peak load) |
  | `max_curtailment_mw` | 25 |
  | `max_recovery_mw` | 25 |
  | `curtailment_cost` | $200/MWh |
  | `recovery_cost` | $50/MWh |
  | `max_hours` | 4 |

  **How to use:** Model as a dispatchable load reduction. In OPF, add a
  "generator" at bus 20 with `Pmax = 25`, `Pmin = 0`, `marginal_cost = 200`.
  It will only dispatch when the LMP exceeds its curtailment cost.

### Reserve requirements

- **`reserve_requirements_24h.csv`** — Hourly spinning and non-spinning
  reserve requirements (MW). Currently 550 MW flat for both products
  (approximately 9% of system peak).

- **`reserve_eligibility.csv`** — Per-generator eligibility and maximum
  contribution fraction for each reserve product. Nuclear units contribute
  up to 5% of capacity for spinning reserves; gas CC units contribute up
  to 17%.

  **How to use:** These are constraints in unit commitment / SCUC
  formulations. For simpler OPF studies, they can be ignored.

### Stochastic scenarios

- **`scenarios/scenario_multipliers_50x24.csv`** — 50 correlated weather
  scenarios, each providing a multiplier per renewable unit per hour.

  | Column | Description |
  |--------|-------------|
  | `scenario` | Scenario ID (1–50) |
  | `gen_uid` | Renewable unit (`WIND_1`, ..., `SOLAR_2`) |
  | `HR_1`–`HR_24` | Multiplier on forecast output for that hour |

  Multipliers are centered near 1.0 with ±10–15% variation. They preserve
  spatial correlation (nearby wind units covary) via Iman-Conover rank
  reordering over Student-t marginals.

  **How to use:** For scenario `s`, hour `h`, unit `u`:
  `actual_MW = forecast_MW[u][h] × multiplier[s][u][h]`, clamped to
  `[0, pmax_mw]`. This produces 50 plausible renewable realizations for
  stochastic OPF or Monte Carlo congestion studies.

- **`scenarios/stochastic_metadata.json`** — Generation parameters, achieved
  correlation matrix, KS test results.

### Flowgates

- **`flowgates.csv`** — 3 monitored flowgates derived from DC OPF congestion
  analysis at peak, shoulder (75%), and valley (55%) load levels.

  | Flowgate | Branches | Limit (MW) | Peak loading |
  |----------|----------|------------|--------------|
  | FG_01 | 2→3, 2→30 | 475 | 131% |
  | FG_02 | 6→11 | 456 | 67% |
  | FG_03 | 10→32 | 855 | 68% |

  **How to use:** These define aggregate transfer constraints. The flowgate
  flow is `Σ weight_k × flow_k` for the constituent branches, and must
  not exceed `limit_mw`. FG_01 is the primary congestion corridor —
  it binds in 100% of scenario-hours under 70% branch derating.

- **`flowgate_metadata.json`** — Derivation parameters, corridor clustering
  details.

### Congestion analysis outputs (reference, not input)

The `scenario_congestion/` subdirectory contains pre-computed results from
running DC OPF across all 50 scenarios × 24 hours. These are *reference
outputs*, not inputs — they document the congestion behavior of the
augmented network and can be used to validate that a tool's OPF produces
similar patterns.

- `diverse_tight/dcopf_statistics.json` — With 70% branch derating and
  diverse renewable placement: 7 binding branches, LMP spread mean
  $87/MWh (σ=$50), shadow prices varying continuously across scenarios.
- `diverse_tight/lmp_summary.csv` — Bus-level LMPs for all scenario-hours.
- `diverse_tight/shadow_prices.csv` — Branch shadow prices for binding
  branches.

## Producing congestion

The canonical case39 is uncongested under normal conditions. Two
modifications are needed to produce meaningful congestion for OPF testing:

1. **Derate branch ratings to 70%** — Multiply all `rateA` values in the
   branch data by 0.70 before solving. This tightens thermal limits enough
   to bind without making the system infeasible.

2. **Place renewables at diverse buses** — The default placement
   (`renewable_units.csv`) puts generation at buses with headroom. For
   maximum congestion variability across scenarios, place renewables at
   buses behind different bottleneck branches (e.g., buses 1, 12, 18, 24,
   27 with 300 MW wind / 250 MW solar). See `scenario_dcopf.py`
   `DIVERSE_PLACEMENTS` for the tested configuration.

With both modifications, the QP-based DC OPF produces:
- 7 binding branches (out of 46)
- LMP spread of $30–$220/MWh depending on the scenario
- Shadow prices that vary continuously across the 50 scenarios
  (σ = $20–60/MWh on binding branches)

Without the 70% derating, only branch 2→3 binds, and shadow prices are
nearly identical across all scenarios.

## Reference implementation

**[`example_pypsa_dcopf.py`](example_pypsa_dcopf.py)** — Standalone PyPSA script
that loads the augmented case39 data and runs 6 progressively harder DCOPF
analyses (differentiated costs → 24h multi-period → BESS → DR → congestion →
stochastic scenarios). Run directly (`python example_pypsa_dcopf.py`) or as
pytest tests (`python example_pypsa_dcopf.py test`). The `chart` subcommand
generates a 3-panel timeseries chart (LMPs, BESS dispatch, SoC) — use
`plot_congestion_results()` from your own evaluation scripts to produce the
same visualization for any solved network.

## Quick-start: building a network from these files

The general recipe for any tool:

1. **Load the base network** from `case39.m` (MATPOWER format). All 6
   evaluation tools can ingest this directly or via a converter.

2. **Replace generator costs.** The `.m` file has homogeneous `gencost`
   rows. Read `gen_temporal_params.csv` and set each generator's cost
   curve using the `tech_class_key` → cost mapping above. Use quadratic
   costs (`c2 > 0`) if the tool supports QP-based OPF.

3. **Add renewable generators.** For each row in `renewable_units.csv`,
   add a generator at the specified bus with `Pmax = pmax_mw`, `Pmin = 0`,
   `marginal_cost = 0`. Attach the hourly forecast profile from
   `wind_forecast_24h.csv` or `solar_forecast_24h.csv` as the time-varying
   maximum output.

4. **Add the BESS.** Read `bess_units.csv` and add a storage unit at
   bus 5 (co-located with SOLAR_1). For multi-period: set power, energy, efficiency, and SoC bounds
   as specified. For single-period: model as a dispatchable generator with
   `Pmin = −150`, `Pmax = 150`.

5. **Set hourly loads.** For multi-period or time-series studies, read
   `load_24h.csv` and set each bus's `Pd` for each hour. For
   single-snapshot: use HR 18 (peak) for maximum stress.

6. **Derate branches** (optional but recommended). Multiply all `rateA`
   by 0.70 to produce binding congestion.

7. **Solve.** Run DCPF, ACPF, or OPF as appropriate for the test.

### Tool-specific notes

**PyPSA:** Use `import_from_pypower_ppc(ppc)` for the base case, then
`network.add("Generator", ...)` for renewables with
`network.generators_t.p_max_pu` for time series. BESS maps to
`network.add("StorageUnit", ...)`. Branch derating: `network.lines.s_nom *= 0.7`.

**pandapower:** Use `from_mpc()` or `from_ppc()` for ingestion. Renewables
via `create_sgen()`. BESS via `create_storage()`. Branch derating:
`net.line["max_i_ka"] *= 0.7`.

**GridCal:** Import MATPOWER via `FileOpen`. Add generators and storage
through the grid model API.

**PowerModels.jl:** Parse with `PowerModels.parse_file("case39.m")`. Modify
the dict directly: add generator entries, adjust `rate_a` values, set cost
curves.

**PowerSimulations.jl:** Build a `System` from MATPOWER data, add
`RenewableDispatch` and `EnergyReservoirStorage` components. Attach
`SingleTimeSeries` for profiles.

**MATPOWER/Octave:** Modify the `mpc` struct directly in Octave. Add rows
to `mpc.gen`, `mpc.gencost`. Scale `mpc.branch(:,6)` for derating. No
native storage model — must be formulated as custom constraints or as a
generator pair.
