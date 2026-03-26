---
test_id: A-12
tool: gridcal
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: v2
test_hash: "bb8a8930"
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: 1.28
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 418
solver: "HiGHS"
cpu_threads_used: null
cpu_threads_available: null
ingestion_path: null
sced_mode: null
test_category: null
timestamp: "2026-03-24T12:00:00Z"
---

# A-12: 24-hour multi-period DCOPF with storage and congestion

## Result: FAIL

All three pass conditions failed. The root cause is a sign error in GridCal's battery
energy balance formulation in `linear_opf_ts.py`, which causes the optimizer to treat
battery discharge as free energy creation rather than energy depletion. This is a
formulation bug [tool-specific], not a solver limitation.

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

### Solver QP vs LP watchpoint

GridCal's battery cost formulation uses only the linear cost term (`cost_1 * p_pos + cost_0`).
The quadratic cost term (`Cost2`) is not included in the battery objective function
in `add_linear_battery_formulation()`. Generator costs do include `Cost2` via
`add_linear_simple_generation_formulation()`, so the overall problem is QP when
generator quadratic costs are nonzero. However, the battery itself is formulated as LP
within the larger QP. This is acceptable since battery marginal cost is set to zero for
A-12 (arbitrage behavior is driven by LMP differentials, not battery cost curves).

### Cyclic SoC watchpoint

GridCal's `add_linear_battery_formulation()` does not implement a cyclic SoC constraint
(SoC[0] == SoC[T]). The A-12 spec calls for "cyclic SoC: initial = final, value chosen
by optimizer." This is a secondary failure mode that would remain even if the energy
balance sign error were fixed.

### Storage sign convention

GridCal uses: `p = p_pos - p_neg` where `p_pos >= 0` (discharge) and `p_neg >= 0` (charge).
Net battery power `batt_power` reports positive values for discharge, negative for charge.
This convention is consistent with PyPSA and is correctly handled in the test script.

## Output

### Battery Dispatch (all hours discharge at Pmax)

| Hour | Battery P (MW) | Battery E (MWh) | Bus 5 LMP ($/MWh) |
|------|---------------|-----------------|-------------------|
| 1    | 150.0         | 300.000         | 29.48             |
| 2    | 150.0         | 300.119         | 29.48             |
| 3    | 150.0         | 300.277         | 29.48             |
| 4    | 150.0         | 300.435         | 29.48             |
| 5    | 150.0         | 300.554         | 29.48             |
| 6    | 150.0         | 300.713         | 29.48             |
| 7    | 150.0         | 300.831         | 29.48             |
| 8    | 150.0         | 300.990         | 29.48             |
| 9    | 150.0         | 301.148         | 29.48             |
| 10   | 150.0         | 301.267         | 29.48             |
| 11   | 150.0         | 301.425         | 29.48             |
| 12   | 150.0         | 301.544         | 29.48             |
| 13   | 150.0         | 301.702         | 29.48             |
| 14   | 150.0         | 301.860         | 29.48             |
| 15   | 150.0         | 301.979         | 29.48             |
| 16   | 150.0         | 302.138         | 29.48             |
| 17   | 150.0         | 302.256         | 29.48             |
| 18   | 150.0         | 302.415         | 75.28             |
| 19   | 150.0         | 302.573         | 29.48             |
| 20   | 150.0         | 302.692         | 29.48             |
| 21   | 150.0         | 302.850         | 29.48             |
| 22   | 150.0         | 302.969         | 29.48             |
| 23   | 150.0         | 303.127         | 29.48             |
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

Where `p = p_pos - p_neg` (p_pos = discharge power >= 0, p_neg = charge power >= 0).

**The bug:** When discharging (p_pos > 0), the formula adds `eta_dis * p_pos * dt` to
energy, causing stored energy to *increase*. Correct physics requires energy to
*decrease* during discharge: `E[t] = E[t-1] - P_dis * dt / eta_dis`.

Additionally, the efficiency factor is in the wrong position: `eta_dis` should divide
P_dis (you lose more stored energy than you deliver to the grid), not multiply it.

**Correct formulation should be:**
```
E[t] = E[t-1] + dt * (charge_efficiency * p_neg - p_pos / discharge_efficiency)
```

**Impact:** The optimizer sees no cost to discharging (energy grows rather than depletes),
so it dispatches the battery at Pmax continuously. This produces:

- No arbitrage behavior (always discharging, never charging)
- 150 MW of "free" generation suppressing congestion
- Energy trajectory that violates physical energy balance

### Pass Condition Results

| Check | Result | Details |
|-------|--------|---------|
| PC1: Congestion (>=2 hours with >=2 binding branches) | **FAIL** | 0 qualifying hours. Only HR 18-19 had 1 congested branch each. Congestion suppressed by 150 MW free battery injection. |
| PC2: BESS arbitrage (discharge LMP > charge LMP) | **FAIL** | 24 discharge hours, 0 charge hours. No charging occurred. |
| PC3: SoC feasibility (bounds + energy balance < 1 MWh) | **FAIL** | Max energy balance error = 1.580531e+02 MWh/timestep (textbook convention). Energy increased during discharge. |

### System Summary

- Total generation: 4,087 - 6,104 MW (follows 24-hour load profile correctly)
- LMP range: $3.46 - $84.38/MWh (differentiated costs produce meaningful spread)
- LMP mean: $30.57/MWh
- Congestion: minimal due to 150 MW free battery injection flattening flows
- All 24 hours converged

## Workarounds

- **What:** The battery energy balance formulation in `linear_opf_ts.py` has a sign error
  that makes the battery model physically incorrect. No workaround was found that could
  fix this through the public API alone.
- **Why:** The formulation `E[t] = E[t-1] + eta_dis*P_dis*dt` (energy increases during
  discharge) is hardcoded in the OPF constraint builder. There is no user-facing API to
  override or correct individual OPF constraints. Additionally, there is no cyclic SoC
  constraint (SoC[0] == SoC[T]) in the formulation.
- **Durability:** blocking -- would require patching the source code in
  `linear_opf_ts.py` to fix the sign and efficiency placement. [tool-specific: battery
  energy balance sign error in OPF formulation]
- **Grade impact:** Multi-period storage optimization produces physically impossible
  results. This is a formulation bug, not a missing feature. The Battery device type,
  time-series driver, and SoC tracking infrastructure all exist; only the energy balance
  constraint is incorrect.

## Timing

- **Wall-clock:** 1.28 seconds
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver:** HiGHS (LP/QP, all 24 hours converged)
- **CPU cores used:** 1 (single-threaded)

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
