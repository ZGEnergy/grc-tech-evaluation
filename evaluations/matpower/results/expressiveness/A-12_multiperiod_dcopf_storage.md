---
test_id: A-12
tool: matpower
dimension: expressiveness
network: TINY
protocol_version: v10
skill_version: v1
test_hash: "4b7e1360"
status: qualified_pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.71
timing_source: measured
peak_memory_mb: 1.8
convergence_residual: null
convergence_iterations: null
loc: 279
solver: GLPK
timestamp: 2026-03-13T00:00:00Z
---

# A-12: 24hr multi-period DCOPF with storage, renewables, quadratic costs, congestion

## Result: QUALIFIED PASS

## Approach

MATPOWER's MOST (MATPOWER Optimal Scheduling Tool, v1.3.1) provides native multi-period
DCOPF with storage as a core capability. The test was set up using MOST's documented API:

1. **Base case:** IEEE 39-bus loaded via `loadcase()`.
2. **Differentiated costs:** Linear costs applied (hydro $5, nuclear $10, coal $25, gas $40
   $/MWh). Quadratic costs could not be used because MIPS (the only available QP solver
   in MOST) encounters numerical issues (singular matrix) on this problem size, and GLPK
   only handles LP.
3. **Branch derating:** 70% applied to all RATE_A/B/C values to produce congestion.
4. **Renewables:** 5 variable generators (3 wind + 2 solar, 732 + 488 MW nameplate) added
   from `renewable_units.csv` with time-varying Pmax profiles from forecast CSVs.
5. **Storage:** 150 MW / 600 MWh BESS at bus 5 added via `addstorage()` with:
   - Charge efficiency: 0.92, Discharge efficiency: 0.95
   - SoC bounds: [60, 540] MWh (10%-90% of 600 MWh)
   - Initial SoC: 300 MWh (50%)
   - Cyclic SoC constraint enabled (`most.storage.cyclic = 1`)
6. **Load profile:** 24-hour from `load_24h.csv` (4,237-6,254 MW).
7. **Solver:** GLPK (LP).

The `addstorage()` function properly integrates the BESS generator, xGenData, and
StorageData into the MOST data structures, including the storage unit index mapping.

## Output

### BESS Dispatch and SoC

| Hour | Dispatch (MW) | SoC (MWh) | Status |
|------|--------------|-----------|--------|
| HR01 | -0.00 | 300.0 | idle |
| HR03 | -43.8 | 340.3 | charge |
| HR04 | -94.1 | 426.9 | charge |
| HR05 | -61.5 | 483.4 | charge |
| HR06 | -61.5 | 540.0 | charge |
| HR15 | 12.5 | 526.8 | discharge |
| HR17 | 75.4 | 447.5 | discharge |
| HR18 | 144.2 | 295.8 | discharge |
| HR19 | 144.2 | 144.0 | discharge |
| HR20 | 79.8 | 60.0 | discharge |
| HR23 | -110.9 | 162.0 | charge |
| HR24 | -150.0 | 300.0 | charge |

BESS charges during low-price early morning hours and discharges during high-price
afternoon/evening hours. SoC returns to 300 MWh at HR24 (cyclic constraint).

### Condition 1: Congestion (PASS)

11 of 24 hours have >= 2 branches with non-zero shadow prices (threshold: 2).
Peak congestion at HR18 with 5 binding branches and mean shadow price $25.0/MWh.

### Condition 2: BESS Arbitrage (PASS)

| Metric | Value |
|--------|-------|
| Discharge hours | HR15, HR17-20 |
| Charge hours | HR3-6, HR23-24 |
| Mean LMP during discharge | $20.09/MWh |
| Mean LMP during charge | $9.95/MWh |
| Arbitrage spread | $10.14/MWh |

The BESS correctly arbitrages between low-price and high-price hours, discharging when
LMPs are approximately 2x higher than during charging periods.

### Condition 3: SoC Feasibility (PASS)

| Metric | Value |
|--------|-------|
| SoC range | [60.0, 540.0] MWh |
| SoC bounds | [60.0, 540.0] MWh |
| Max energy balance error | 0.0000 MWh |
| Cyclic SoC | Yes (HR24 = HR00 = 300 MWh) |

Energy balance is exactly consistent at all timesteps (error < 1e-10 MWh).

### LMP Summary

LMP spread ranges from $5-6/MWh during off-peak to $42.9/MWh during peak hours (HR13-20),
driven by congestion from 70% branch derating and differentiated generator costs.

## Workarounds

- **What:** Used linear costs instead of quadratic costs (c2 = c1 * 0.001 as specified in
  the test parameters). This required using GLPK (LP solver) instead of a QP solver.
- **Why:** MIPS (the only QP-capable solver available in MOST on Octave) encounters
  singular matrix numerical issues on this problem size (16 generators x 24 periods with
  storage constraints). GLPK can solve LP but rejects QP. HiGHS is not available for MOST
  in the Octave devcontainer. With commercial solvers (CPLEX, Gurobi, MOSEK) or MATLAB,
  quadratic costs would work.
- **Durability:** stable -- The MOST API for multi-period DCOPF with storage (`addstorage`,
  `loadmd`, `most`) is fully documented and works correctly. The limitation is solver
  availability on Octave, not a formulation issue. Linear costs produce valid but non-unique
  shadow prices (LP degeneracy), which is why the test specification prefers quadratic costs.
  Despite linear costs, all three behavioral pass conditions are met.
- **Grade impact:** Minor. The multi-period storage formulation is a core MOST capability
  demonstrated successfully. The quadratic cost limitation affects LMP uniqueness but not the
  correctness of BESS arbitrage behavior or SoC feasibility.

## Timing

- **Wall-clock:** 0.71 s
- **Timing source:** measured
- **Peak memory:** 1.8 MB
- **Solver:** GLPK
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/expressiveness/test_a12_multiperiod_dcopf_storage.m`

Key API calls for multi-period DCOPF with storage:

```matlab
%% Add storage via MOST's addstorage() API
[iess, mpc, xgd, sd] = addstorage(storage, mpc, xgd);

%% Build multi-period data and solve
md = loadmd(mpc, nt, xgd, sd, [], profiles);
mpopt = mpoption('most.dc_model', 1, 'most.storage.cyclic', 1);
mdo = most(md, mpopt);

%% Extract results
ms = most_summary(mdo);
dispatch = ms.Pg(:, :, 1, 1);           % generator dispatch
lmps = ms.lamP(:, :, 1, 1);             % nodal prices
shadow = ms.muF(:, :, 1, 1);            % branch shadow prices
soc = mdo.Storage.ExpectedStorageState;  % state of charge
```
