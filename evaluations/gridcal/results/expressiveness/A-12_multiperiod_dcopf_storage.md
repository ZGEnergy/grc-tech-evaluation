---
test_id: A-12
tool: gridcal
dimension: expressiveness
network: TINY
status: fail
workaround_class: blocking
blocked_by: null
protocol_version: "v10"
skill_version: v1
test_hash: "4b7e1360"
wall_clock_seconds: 1.57
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 434
solver: "HiGHS"
timestamp: "2026-03-14T03:15:00Z"
---

# A-12: 24-hour multi-period DCOPF with storage and congestion

## Result: FAIL

All three pass conditions failed. The root cause is a sign error in GridCal's battery
energy balance formulation in `linear_opf_ts.py`, which causes the optimizer to treat
battery discharge as free energy creation rather than energy depletion. This cascades
into failures of arbitrage timing and suppresses congestion signal.

## Approach

Used GridCal's native `Battery` device type and `OptimalPowerFlowTimeSeriesDriver` for
multi-period DCOPF. Setup steps:

1. Loaded case39 via `load_gridcal()` (shared MATPOWER loader)
2. Applied differentiated generator costs from `gen_temporal_params.csv` (c2 = c1 * 0.001)
3. Applied 70% branch derating (multiply all branch rates by 0.70)
4. Added a `Battery` at bus 5 with: Pmax=150 MW, Pmin=-150 MW, Enom=600 MWh,
   min_soc=0.10, max_soc=0.90, soc_0=0.50, charge_efficiency=0.92,
   discharge_efficiency=0.95, Cost=0
5. Set 24-hour load profiles from `load_24h.csv` via `P_prof.set()`
6. Configured `OptimalPowerFlowOptions(solver=LINEAR_OPF, mip_solver=HIGHS)`
7. Ran `OptimalPowerFlowTimeSeriesDriver` over 24 time indices

The OPF converged for all 24 hours. Battery power, energy, LMPs, and branch overloads
were extracted from `ts_results`.

## Output

### Battery Dispatch (all hours discharge at Pmax)

| Hour | Battery P (MW) | Battery E (MWh) | Bus 5 LMP ($/MWh) |
|------|---------------|-----------------|-------------------|
| 1    | 150.0         | 300.000         | 29.48             |
| 2    | 150.0         | 300.119         | 29.48             |
| ...  | 150.0         | ...             | ...               |
| 18   | 150.0         | 302.415         | 75.28             |
| 24   | 150.0         | 303.285         | 29.48             |

The battery discharges at maximum power (150 MW) for all 24 hours with no charging.
Stored energy **increases** from 300.0 to 303.3 MWh despite continuous discharge.

### Root Cause: Formulation Sign Error

In `VeraGridEngine/Simulations/OPF/Formulations/linear_opf_ts.py` (line ~1776):

```python
prob.add_cst(cst=(batt_vars.e[t, k] == batt_vars.e[t - 1, k]
                  + dt * (batt_data_t.discharge_efficiency[k] * p_pos
                          - batt_data_t.charge_efficiency[k] * p_neg)),
             name=join("batt_energy_", [t, k], "_"))
```

Where `p = p_pos - p_neg` (p_pos = discharge power, p_neg = charge power).

**The bug:** When discharging (p_pos > 0), the formula adds `eta_dis * p_pos * dt` to
energy, causing stored energy to *increase*. Correct physics requires energy to
*decrease* during discharge: `E[t] = E[t-1] - P_dis * dt / eta_dis`.

Additionally, the efficiency factor is in the wrong position: `eta_dis` should divide
P_dis (you lose more stored energy than you deliver to the grid), not multiply it.

**Impact:** The optimizer sees no cost to discharging (energy grows rather than depletes),
so it dispatches the battery at Pmax continuously. This produces:

- No arbitrage behavior (always discharging, never charging)
- 150 MW of "free" generation suppressing congestion
- Energy trajectory that violates physical energy balance

### Pass Condition Results

| Check | Result | Details |
|-------|--------|---------|
| PC1: Congestion (>=2 hours with >=2 binding branches) | **FAIL** | 0 qualifying hours (only HR 18-19 had 1 congested branch each) |
| PC2: BESS arbitrage (discharge LMP > charge LMP) | **FAIL** | 24 discharge hours, 0 charge hours — no arbitrage |
| PC3: SoC feasibility (bounds + energy balance < 1 MWh) | **FAIL** | Energy balance error = 158 MWh/timestep |

### System Summary

- Total generation: 4087-6104 MW (follows load profile correctly)
- LMP range: $3.46-$84.38/MWh (differentiated costs produce spread)
- Congestion: minimal due to 150 MW free battery injection flattening flows

## Workarounds

- **What:** The battery energy balance formulation in `linear_opf_ts.py` has a sign error
  that makes the battery model physically incorrect. No workaround was found that could
  fix this through the public API alone.
- **Why:** The formulation `E[t] = E[t-1] + eta_dis*P_dis*dt` (energy increases during
  discharge) is hardcoded in the OPF constraint builder. There is no user-facing API to
  override or correct individual OPF constraints.
- **Durability:** blocking -- would require patching the source code in
  `linear_opf_ts.py` to fix the sign and efficiency placement.
- **Grade impact:** Multi-period storage optimization produces incorrect results. This
  is a formulation bug, not a missing feature. The Battery device type, time-series
  driver, and SoC tracking infrastructure all exist; only the energy balance sign is wrong.

## Timing

- **Wall-clock:** 1.57 seconds
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver:** HiGHS (LP, all 24 hours converged)

## Test Script

**Path:** `evaluations/gridcal/tests/expressiveness/test_a12_multiperiod_dcopf_storage.py`

Key code for battery setup:
```python
batt = grid.add_battery(bus=bess_bus)
batt.Pmax = 150.0
batt.Pmin = -150.0
batt.Enom = 600.0
batt.min_soc = 0.10
batt.max_soc = 0.90
batt.soc_0 = 0.50
batt.charge_efficiency = 0.92
batt.discharge_efficiency = 0.95
batt.Cost = 0.0
batt.enabled_dispatch = True
```
