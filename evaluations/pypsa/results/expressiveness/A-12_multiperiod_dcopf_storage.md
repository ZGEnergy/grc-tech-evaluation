---
test_id: A-12
tool: pypsa
dimension: expressiveness
network: TINY
protocol_version: v11
skill_version: v2
test_hash: bb8a8930
status: qualified_pass
workaround_class: fragile
blocked_by: null
wall_clock_seconds: 7.32
timing_source: measured
peak_memory_mb: 123.89
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 433
solver: HiGHS
timestamp: 2026-03-24T00:00:00Z
---

# A-12: Solve 24-hour multi-period DCOPF with storage and congestion on TINY

## Result: QUALIFIED PASS

All three pass conditions met. Branch shadow price extraction required a fragile workaround (linopy model internals) because PyPSA v1.1.2 does not populate `n.lines_t.mu_upper`/`mu_lower` after `n.optimize()`.

## Approach

Applied the full Modified Tiny recipe to the IEEE 39-bus network:

1. Loaded `case39.m` via shared `matpower_loader.load_pypsa()` (applies transformer b-fix and gencost import).
2. Set 24 hourly snapshots (`pd.date_range`, `n.set_snapshots()`).
3. Replaced generator costs with differentiated values from `gen_temporal_params.csv`: hydro $5, nuclear $10, coal $25, gas CC $40/MWh. Applied quadratic cost coefficients (`marginal_cost_quadratic = c1 * 0.001`).
4. Loaded time-varying demand from `load_24h.csv` for all 21 load buses, set via `n.loads_t.p_set`.
5. Derated all branch ratings to 70% (`n.lines.s_nom *= 0.7`).
6. Added BESS at bus 16: 50 MW / 200 MWh, `efficiency_store=0.92`, `efficiency_dispatch=0.95`, `cyclic_state_of_charge=True`.
7. Solved with `n.optimize(solver_name="highs")` using HiGHS v1.13.1 in QP mode (single thread, 300s time limit).

HiGHS correctly identified the problem as a QP (quadratic costs present) and solved via the ASM (Active Set Method) algorithm. The solver reported `Optimal` with 845 simplex iterations and 538 QP ASM iterations.

## Output

**Solver:** HiGHS 1.13.1, QP mode, objective = $3,126,428.06

**Pass Condition 1 -- Congestion Reporting:**

All 24 hours had at least 2 branches with non-zero shadow prices. Hours 7-12 and 20-21 had 4 binding branches; peak-adjacent hours (13-19) had 3; off-peak hours had 2.

| Metric | Value |
|--------|-------|
| Hours with >=2 binding branches | 24/24 |
| Shadow price range | $2.21 - $16.37/MWh (hourly mean) |
| Shadow price std range | $9.16 - $60.13/MWh |

**Pass Condition 2 -- BESS Arbitrage Timing:**

| Metric | Value |
|--------|-------|
| Charge hours | 5 (h01-h05) |
| Discharge hours | 4 (h16-h19) |
| Mean LMP at bus 16 during discharge | $109.10/MWh |
| Mean LMP at bus 16 during charge | $40.22/MWh |
| Total charged | 217.4 MWh |
| Total discharged | 190.0 MWh |

The BESS charges during low-cost nighttime hours and discharges during the evening peak, confirming correct arbitrage behavior.

**Pass Condition 3 -- SoC Feasibility:**

| Metric | Value |
|--------|-------|
| SoC range | [0.0, 200.0] MWh |
| Energy capacity | 200.0 MWh |
| Max energy balance error | 0.000000 MWh |
| Cyclic SoC | Yes (SoC[0] = SoC[23] = 0) |

SoC stays within [0, 200] MWh at all timesteps. The energy balance trajectory is perfectly consistent (max error < 1e-6 MWh), confirming correct inter-temporal coupling with the specified charge/discharge efficiencies.

**LMP Statistics:**

| Metric | Value |
|--------|-------|
| Mean LMP | $57.69/MWh |
| Min LMP | -$0.14/MWh |
| Max LMP | $229.19/MWh |

LMPs show strong spatial and temporal variation, with negative prices at off-peak and high prices at congested buses during peak load.

## Workarounds

- **What:** Branch shadow prices extracted from linopy model constraint duals (`n.model.constraints['Line-fix-s-upper'].dual`) instead of the documented `n.lines_t.mu_upper`/`mu_lower` attributes.
- **Why:** `n.lines_t.mu_upper` and `n.lines_t.mu_lower` are empty after `n.optimize()` in PyPSA v1.1.2. The solver log confirms shadow prices were computed but "were not assigned to the network", indicating a PyPSA post-solve assignment bug [tool-specific].
- **Durability:** fragile -- depends on the internal linopy constraint naming convention (`Line-fix-s-upper`), which is not part of PyPSA's public API and could change in future versions.
- **Grade impact:** The workaround only affects shadow price extraction for pass condition 1. The BESS arbitrage (condition 2) and SoC feasibility (condition 3) use standard public API attributes (`n.buses_t.marginal_price`, `n.storage_units_t.p`, `n.storage_units_t.state_of_charge`). Status is qualified_pass rather than pass due to the fragile workaround.

## Timing

- **Wall-clock:** 7.32s (total), 1.91s (solve only)
- **Timing source:** measured
- **Peak memory:** 123.89 MB
- **Solver iterations:** 845 simplex + 538 QP ASM
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/expressiveness/test_a12_multiperiod_dcopf_storage.py`
