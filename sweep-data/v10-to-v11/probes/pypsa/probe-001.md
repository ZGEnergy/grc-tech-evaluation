---
probe_id: probe-001
tool: pypsa
source_test: G-FNM-3
probe_type: convergence_check
classification: claim_debunked
reason: Deviations are non-zero at float64 precision (max bus angle 1.07e-8 deg, max branch flow 5.76e-7 %), but round to 0.0 at 6 decimal places — the reported "0.0" values are display artifacts of the rounding in the result file, not exact zeros
solver_version: pypsa-1.1.2
solver_version_match: true
timeout_seconds: 300
wall_clock_seconds: 18
timestamp: "2026-03-14T00:00:00Z"
---

# Probe-001: G-FNM-3 DCPF Zero-Deviation Claim

## Original Claim

The G-FNM-3 result file (`evaluations/pypsa/results/fnm_ingestion/G-FNM-3_dcpf_verification.md`) states:

> "100% of buses and 100% of branches pass all tolerance thresholds. Zero deviations from the MATPOWER reference solution."

The numeric tables show:

| Metric | Value |
|--------|-------|
| Mean deviation (bus angles) | 0.0 deg |
| Max deviation (bus angles) | 0.0 deg |
| Mean deviation (branch flows) | 0.0% |
| Max deviation (branch flows) | 0.0% |

This covers 27,862 buses and 32,532 branches on the FNM main island (ACTIVSg70k-derived network).

## Validation Report Discrepancy

The `evaluations/pypsa/results/validation-report.md` lists G-FNM-3 as a **FAIL**:

> "G-FNM-3 | DCPF verification failed — systematic impedance conversion differences via MATPOWER fallback"

This contradicts the individual result file's PASS status. The validation report appears to have been generated from an **older version of the test** (before the shared `matpower_loader.load_pypsa()` was introduced with the branch-status patch). The result file itself was updated to PASS but the validation report was not regenerated. The validation report is therefore stale relative to the result file.

## Probe Methodology

1. Read the original test script (`test_g_fnm_3_dcpf_verification.py`) to reproduce the exact methodology.
2. Wrote an independent probe script using the same shared `matpower_loader.load_pypsa()` utility, same input files, and same reference data.
3. Computed all deviations at full float64 precision using `np.float64` arrays and `:.18e` formatting.
4. Checked deviation distributions across multiple thresholds (exact 0.0, 1e-12, 1e-9, 1e-6).
5. Verified PyPSA version inside the devcontainer matches the version reported in the original test (1.1.2).
6. Ran inside devcontainer: `/devcontainer/dc-exec -C /workspace/evaluations/pypsa timeout 300 uv run python probe-001_script.py`

**Input files used:**
- Network: `/workspace/data/fnm/reference/cleaned/fnm_main_island.m`
- Reference buses: `/workspace/data/fnm/reference/dcpf/buses_dcpf.csv`
- Reference branches: `/workspace/data/fnm/reference/dcpf/branches_dcpf.csv`

## Probe Results (Raw Output)

```
PyPSA version: 1.1.2
NumPy version: 2.3.5
Pandas version: 2.3.3

Excluded buses: 2445
Reference buses: 27862
Reference branches: 32532

Loading MATPOWER case via shared matpower_loader.load_pypsa()...
  Load time: 0.73s
  Buses: 27862
  Lines: 23125
  Transformers: 9481
  Generators: 5741
  MATPOWER total branches: 32606, active: 32532

Running DCPF (net.lpf())...
  Solve time: 17.16s

======================================================================
BUS VOLTAGE ANGLE COMPARISON (float64 precision)
======================================================================
Buses compared (non-excluded): 27862
  Max deviation (deg):  1.073351540981093422e-08
  Mean deviation (deg): 3.316293917875641802e-09
  Min deviation (deg):  0.000000000000000000e+00
  Std deviation (deg):  2.369635338727692015e-09
  P50 deviation (deg):  2.923016495515184943e-09
  P95 deviation (deg):  7.940541024709091620e-09
  P99 deviation (deg):  9.055444820660341462e-09
  Buses with dev > 1e-6 deg:  0
  Buses with dev > 1e-9 deg:  22427
  Buses with dev > 1e-12 deg: 27851
  Buses with dev > 0.0 (exact): 27858
  No outlier buses with dev > 1e-6 deg.

  Distribution of nonzero deviations (27858 buses):
    Max: 1.073351540981093422e-08
    Min: 2.344791028008330613e-13
    Mean: 3.316770089017558105e-09

======================================================================
BRANCH FLOW COMPARISON (float64 precision)
======================================================================
Branches compared: 32532
  Max deviation (%):    5.757743807042548304e-07
  Mean deviation (%):   1.175349767552511295e-08
  Min deviation (%):    0.000000000000000000e+00
  P95 deviation (%):    4.589095774355148793e-08
  P99 deviation (%):    2.370491861436153432e-07
  Branches with dev > 1e-6 %:  0
  Branches with dev > 1e-9 %:  15646
  Branches with dev > 0.0 (exact): 26892

  Lines: 23056 compared
    Max dev (%): 5.757743807042548304e-07
    Mean dev (%): 1.244668512309947464e-08

  Transformers: 9476 compared
    Max dev (%): 4.956535848421594892e-07
    Mean dev (%): 1.006690736407783267e-08

======================================================================
SUMMARY
======================================================================
Bus angle max dev:    1.073351540981093422e-08 deg
Bus angle mean dev:   3.316293917875641802e-09 deg
Branch flow max dev:  5.757743807042548304e-07 %
Branch flow mean dev: 1.175349767552511295e-08 %

Claim: 0.0 mean and max deviation across all buses and branches
Claim supported (exact float64 zero): False
Claim supported (rounded to 0.0 at 6 decimal places): True

Total wall clock: 17.9s (load: 0.7s, solve: 17.2s)
```

## Analysis

### The "0.0" Values Are Rounding Artifacts

The original test script computes deviations correctly as float64, but then formats results with `round(..., 6)` (6 decimal places) before storing them in the result dictionary. For example:

```python
"max_deviation_deg": round(float(np.max(va_deviations)), 6)
"mean_deviation_deg": round(float(np.mean(va_deviations)), 6)
```

The actual maximum bus angle deviation is **1.07e-8 degrees** — this rounds to 0.000000 at 6 decimal places. Similarly, the maximum branch flow deviation is **5.76e-7 percent** — also rounds to 0.000000. So the reported "0.0" values in the result file are correct as 6-decimal display values, but they misrepresent the actual float64 deviations.

### Magnitude of Actual Deviations

| Metric | Probe Result | Claimed |
|--------|-------------|---------|
| Bus angle max deviation | 1.07e-8 deg | 0.0 deg |
| Bus angle mean deviation | 3.32e-9 deg | 0.0 deg |
| Branch flow max deviation | 5.76e-7 % | 0.0% |
| Branch flow mean deviation | 1.18e-8 % | 0.0% |

The deviations are sub-nanodegree for bus angles and sub-micron-percent for branch flows. These are **numerical floating-point rounding errors intrinsic to the DCPF linear algebra**, not physically meaningful discrepancies. All 27,862 buses and 32,532 branches pass the 1.0-degree / 10% tolerance thresholds by an enormous margin. The PASS grade is fully warranted.

### The Nature of the Deviations

These are consistent with floating-point round-trip errors in the B-matrix assembly and sparse linear solve — expected when comparing two independently computed solutions that use equivalent but not identical code paths. The deviations (~1e-8 to 1e-7 magnitude) are at the limit of float64 precision for values of this scale, not evidence of a formulation difference.

### Validation Report vs. Result File Discrepancy

The validation report lists G-FNM-3 as FAIL with reason "systematic impedance conversion differences via MATPOWER fallback." This reflects the state **before** the branch-status patch was introduced. The individual result file (`G-FNM-3_dcpf_verification.md`) was updated to PASS after the shared loader fixed the bug, but the validation report was not regenerated. The probe independently confirms the result file's PASS conclusion is accurate.

## Classification Rationale

Classification: **claim_debunked** — the deviations are not exactly 0.0 at float64 precision.

However, this is a **weak debunking**: the deviations are at the level of floating-point noise (~1e-8 to 1e-7), far below any physically meaningful threshold. The PASS grade and the engineering conclusion that "PyPSA matches MATPOWER exactly" are both correct. The claim of "0.0" is a rounding artifact from the 6-decimal-place display format used in the result file, not an error in the test methodology or an inflated performance claim.

The validation report discrepancy (FAIL vs PASS) is a stale artifact — the probe confirms the result file's PASS assessment is accurate.
