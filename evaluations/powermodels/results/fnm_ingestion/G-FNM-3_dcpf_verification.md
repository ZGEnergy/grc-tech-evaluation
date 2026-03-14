---
test_id: G-FNM-3
tool: powermodels
dimension: fnm_ingestion
network: LARGE
protocol_version: v10
skill_version: v1
test_hash: 52baae11
status: fail
workaround_class: null
blocked_by: null
wall_clock_seconds: 8.72
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: 12904
loc: 421
solver: HiGHS 1.13.1
input_path: matpower
timestamp: "2026-03-13T01:30:00Z"
---

# G-FNM-3: DCPF Verification

## Result: FAIL

PowerModels' `solve_dc_pf` with `DCPPowerModel` produces DCPF results with systematic
deviations from the MATPOWER reference. Bus angle pass rate is 2.43% (need >=95%) and branch
flow pass rate is 78.88% (need >=90%). This is a hard fail: >20% of buses fail the angle
tolerance. The deviations are caused by a documented formulation difference --
`DCPPowerModel` uses a simplified B-matrix that ignores transformer tap ratios, while the
MATPOWER reference uses the full B-matrix incorporating taps.

## Approach

1. Loaded the cleaned FNM case (`data/fnm/reference/cleaned/fnm_main_island.m`) via
   `PowerModels.parse_file` (27,862 buses, 32,606 branches, baseMVA=100).
2. Applied zero-reactance preprocessing (0 fixes needed -- no zero-reactance branches
   in the cleaned case). No rate fixes needed either.
3. Solved DCPF using `PowerModels.solve_dc_pf(data, HiGHS.Optimizer)` which internally
   uses `DCPPowerModel`. The task specification calls for `solve_dc_pf` rather than
   `compute_dc_pf` (which uses full complex admittance instead of DCPF approximation).
4. Extracted bus voltage angles (radians from PowerModels, converted to degrees) and
   computed branch flows from angles using `pf = (va_from - va_to - shift) / (br_x * tap)`.
5. Compared against reference solution from `data/fnm/reference/dcpf/buses_dcpf.csv` and
   `branches_dcpf.csv`.
6. The excluded buses from `excluded_buses.json` are not relevant because the reference
   CSV contains only the 27,862 main-island buses (post-exclusion).

## Output

### Solver Output

| Metric | Value |
|--------|-------|
| Solver | HiGHS 1.13.1 |
| Model | DCPPowerModel (simplified B-matrix) |
| Termination | OPTIMAL |
| Simplex iterations | 12,904 |
| Solve time | 8.72 s |
| HiGHS wall time | 6.43 s |
| Nonzero VA buses | 27,858 / 27,862 |

### Bus Angle Comparison

| Metric | Value | Pass Condition |
|--------|-------|----------------|
| Non-excluded buses | 27,862 | -- |
| Passing (|dev| < 1.0 deg) | 678 (2.43%) | >= 95% |
| Failing | 27,184 | -- |
| Mean deviation | 5.098 deg | -- |
| Median deviation | ~4.6 deg | -- |
| P95 deviation | 9.937 deg | -- |
| Max deviation | 62.213 deg | -- |

### Branch Flow Comparison

| Metric | Value | Pass Condition |
|--------|-------|----------------|
| In-service branches | 32,532 | -- |
| Passing (dev < 10%) | 25,660 (78.88%) | >= 90% |
| Failing | 6,872 | -- |
| Mean deviation | 31.29% | -- |
| P95 deviation | 72.67% | -- |
| Max deviation | 114,050.94% | < 50% (hard fail) |

### Hard-Fail Conditions

| Condition | Threshold | Actual | Triggered |
|-----------|-----------|--------|-----------|
| Bus failing fraction > 20% | 20% | 97.57% | YES |
| Branch failing fraction > 20% | 20% | 21.12% | YES |
| Extreme branch deviation > 50% | 50% | 114,050.94% | YES |

All three hard-fail conditions are triggered.

### Formulation Difference Analysis

The deviations are systematic and attributable to the formulation difference between
PowerModels' `DCPPowerModel` and MATPOWER's DCPF implementation:

- **DCPPowerModel (PowerModels):** Uses a simplified B-matrix that computes branch
  susceptance as `b = -1/x`, ignoring transformer tap ratios. This is documented in
  the cross-tool watchpoints: "DCPPowerModel uses simplified; DCMPPowerModel uses full."
- **MATPOWER reference:** Uses the full B-matrix via `makeBdc()`, which incorporates
  tap ratios and phase shift angles into the admittance matrix construction.

The FNM network has 12,501 transformer-connected buses (out of 27,862 total). On a network
with this many transformers operating at non-unity tap settings, the simplified B-matrix
produces significantly different power flow solutions. The mean angle deviation of 5.1
degrees and the widespread nature of the failures (97.6% of buses) confirm this is a
global formulation effect rather than localized data issues.

PowerModels' `DCMPPowerModel` formulation would incorporate taps into the B-matrix but
is not available through `solve_dc_pf` (which hardcodes `DCPPowerModel`). Using
`solve_pf(data, DCMPPowerModel, optimizer)` could potentially produce results closer
to the MATPOWER reference, but this was not tested because the task specification
explicitly requires `solve_dc_pf`.

### Sample Bus Angles (First 10 Buses)

| Bus | Tool VA (deg) | Reference VA (deg) | Deviation (deg) |
|-----|---------------|--------------------|-----------------:|
| 1 | -169.41 | -166.84 | 2.57 |
| 2 | 295.13 | 289.13 | 6.00 |
| 3 | 239.72 | 234.81 | 4.91 |
| 4 | 178.17 | 174.07 | 4.10 |

The consistent positive offset in deviations suggests the tap-ratio-ignoring formulation
systematically shifts voltage angles across the network.

## Workarounds

None attempted. The pass condition is not met and the formulation difference is
structural to `DCPPowerModel`. A workaround would require using `DCMPPowerModel`
(full B-matrix) via `solve_pf(data, DCMPPowerModel, optimizer)`, but this deviates
from the test specification.

## Timing

- **Wall-clock:** 8.72 s (solve only, excluding JIT warm-up)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** 12,904 (HiGHS dual simplex)

## Test Script

**Path:** `evaluations/powermodels/tests/fnm_ingestion/test_g_fnm_3_dcpf_verification.jl`

Key code:

```julia
result_pf = PowerModels.solve_dc_pf(data, HiGHS.Optimizer)
# Internally uses DCPPowerModel (simplified B-matrix, ignores taps)

# Branch flows computed from bus angles:
pf_pu = (va_f - va_t - shift) / (br_x * tap)
```
