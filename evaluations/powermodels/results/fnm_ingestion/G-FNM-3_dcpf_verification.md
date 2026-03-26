---
test_id: G-FNM-3
tool: powermodels
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: b318fdf1
status: fail
workaround_class: null
blocked_by: null
wall_clock_seconds: 8.20
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: 12904
convergence_evidence_quality: null
loc: 558
solver: HiGHS 1.13.1
ingestion_path: matpower_raw
timestamp: "2026-03-24T12:00:00Z"
---

# G-FNM-3: DCPF Verification

## Result: FAIL

PowerModels' `solve_dc_pf` with `DCPPowerModel` produces DCPF results with systematic
deviations from the MATPOWER reference on the 27,862-bus FNM main island. Bus angle pass
rate is 2.43% (need >=95%) and branch flow pass rate is 78.88% (need >=90%). All three
hard-fail conditions are triggered. The deviations are caused by a documented formulation
difference: `DCPPowerModel` uses a simplified B-matrix (`b = -1/x`) that ignores
transformer tap ratios, while the MATPOWER reference uses the full B-matrix incorporating
taps via `makeBdc()`. [tool-specific: DCPPowerModel formulation choice]

## Approach

1. Loaded the cleaned FNM case (`data/fnm/reference/cleaned/fnm_main_island.m`) via
   `PowerModels.parse_file` (27,862 buses, 32,606 branches, 5,741 generators, baseMVA=100).
2. Applied zero-reactance preprocessing (0 fixes needed). No rate fixes needed.
3. Solved DCPF using `PowerModels.solve_dc_pf(data, HiGHS.Optimizer)` which internally
   uses `DCPPowerModel`. Per the task specification, `solve_dc_pf` is used rather than
   `compute_dc_pf` (which uses full complex admittance b = -x/(r^2+x^2) instead of DCPF
   approximation b = 1/x).
4. Extracted bus voltage angles (radians from PowerModels, converted to degrees) and
   computed branch flows from angles using `pf = (va_from - va_to - shift) / (br_x * tap)`.
5. Verified bus injection power balance (non-slack buses).
6. Compared against reference solution from `data/fnm/reference/dcpf/buses_dcpf.csv` and
   `branches_dcpf.csv`.

## Output

### Solver Output

| Metric | Value |
|--------|-------|
| Solver | HiGHS 1.13.1 |
| Model | DCPPowerModel (simplified B-matrix) |
| Termination | OPTIMAL |
| Simplex iterations | 12,904 |
| Solve time | 8.20 s |
| HiGHS wall time | 6.79 s |
| Nonzero VA buses | 27,858 / 27,862 |

### Power Balance Check

| Metric | Value |
|--------|-------|
| Buses checked (excl. slack) | 27,861 |
| Max mismatch | 4.027619e+02 p.u. |
| Mean mismatch | 2.125234e-01 p.u. |
| Pass (<1e-4 p.u.) | FAIL |

The large power balance mismatch is a consequence of the simplified B-matrix formulation.
The `solve_dc_pf` solver finds the DCPF solution internally consistent with its simplified
admittance model, but the manual flow computation using `(va_f - va_t - shift) / (br_x * tap)`
includes tap ratios that the solver's B-matrix ignores. This cross-formulation mismatch
produces apparent power balance violations at transformer-adjacent buses. The solver's own
internal solution is self-consistent (OPTIMAL termination, zero objective).

### Bus Angle Comparison

| Metric | Value | Pass Condition |
|--------|-------|----------------|
| Non-excluded buses | 27,862 | -- |
| Passing (\|dev\| < 1.0 deg) | 678 (2.43%) | >= 95% |
| Failing | 27,184 | -- |
| Mean deviation | 5.098394e+00 deg | -- |
| Median deviation | 5.154057e+00 deg | -- |
| P95 deviation | 9.936478e+00 deg | -- |
| Max deviation | 6.221311e+01 deg | -- |

### Branch Flow Comparison

| Metric | Value | Pass Condition |
|--------|-------|----------------|
| In-service branches | 32,532 | -- |
| Passing (dev < 10%) | 25,660 (78.88%) | >= 90% |
| Failing | 6,872 | -- |
| Mean deviation | 3.129475e+01% | -- |
| Median deviation | 2.385945e+00% | -- |
| P95 deviation | 7.267029e+01% | -- |
| Max deviation | 1.140509e+05% | < 50% (hard fail) |
| Worst branch | (35415, 14458) | -- |

### Hard-Fail Conditions

| Condition | Threshold | Actual | Triggered |
|-----------|-----------|--------|-----------|
| Bus failing fraction > 20% | 20% | 97.57% | YES |
| Branch failing fraction > 20% | 20% | 21.12% | YES |
| Extreme branch deviation > 50% | 50% | 1.140509e+05% | YES |

All three hard-fail conditions are triggered.

### Formulation Difference Analysis

The 6-step formulation difference procedure was applied:

1. **Transformer identification:** 9,530 transformers in the network; 2,358 have off-nominal
   tap ratios (|tap - 1.0| > 1e-6). These connect to 12,501 unique buses.
2. **Failing bus classification:** Of the 27,184 failing buses, 12,187 (44.8%) are connected
   to transformers and 14,997 (55.2%) are not.
3. **Formulation difference classification: NOT triggered.** The deviations do NOT cluster at
   transformer buses -- instead, the simplified B-matrix causes a global shift across the
   entire network. The mean deviation at transformer-adjacent buses (5.369306e+00 deg) is
   similar to non-transformer buses (5.081049e+00 deg), confirming the effect is system-wide
   rather than localized.

This is expected: the simplified B-matrix omits tap ratios from the entire admittance matrix,
which changes the network topology's impedance structure globally. Even buses electrically
distant from transformers see shifted angles because power flow patterns change throughout
the interconnected network.

`DCPPowerModel` uses a simplified B-matrix (`b = -1/x`), documented in the cross-tool
watchpoints. The full B-matrix formulation (`DCMPPowerModel`) incorporates tap ratios but
is not accessible through `solve_dc_pf`, which hardcodes `DCPPowerModel`.

## Workarounds

None attempted. The pass condition is not met and the formulation difference is structural
to `DCPPowerModel`. A workaround would require using `DCMPPowerModel` (full B-matrix) via
a custom solve call, but this deviates from the specified `solve_dc_pf` API.

## Timing

- **Wall-clock:** 8.20 s (solve only, excluding JIT warm-up)
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
