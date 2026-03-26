---
test_id: G-FNM-3
tool: pandapower
dimension: fnm_ingestion
network: LARGE
protocol_version: "v11"
skill_version: "v2"
test_hash: "6ef3dee2"
status: fail
workaround_class: stable
blocked_by: null
wall_clock_seconds: 23.64
timing_source: measured
peak_memory_mb: 139.0
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 587
solver: null
ingestion_path: matpower_raw
input_path: matpower
timestamp: 2026-03-24T12:00:00Z
---

# G-FNM-3: DCPF Verification Against Reference Solution on FNM

## Result: FAIL

DCPF converges successfully and aggregate thresholds are met (99.64% of buses
pass VA tolerance, 99.67% of branches pass flow tolerance). The v11 bus
injection power balance cross-reference check passes with max mismatch of
8.602342e-11 p.u. (well within the 1e-4 p.u. tolerance). However, the
hard-fail condition is triggered: the maximum branch flow deviation of
5.966459e+02% exceeds the 50% threshold. The extreme deviations are
concentrated in a localized sub-region of ~101 buses and are not correlated
with transformer adjacency, so they cannot be classified as a formulation
difference.

## Approach

1. Loaded the pre-cleaned MATPOWER case (`fnm_main_island.m`, 27,862-bus main
   island) using `matpowercaseframes.CaseFrames` + `from_ppc` (MATPOWER
   fallback since pandapower has no native CSV import).
2. Applied zero RATE_A workaround (set to 9999 before `from_ppc`).
3. Solved DCPF using `pandapower.rundcpp(net)`.
4. Compared bus voltage angles against reference (`buses_dcpf.csv`).
5. Compared branch active power flows against reference (`branches_dcpf.csv`).
6. Applied pass conditions from `pass_conditions.json` DCPF section.
7. Excluded 2,445 buses per `excluded_buses.json`.
8. Performed v11 bus injection power balance cross-reference check.

## Output

### Bus Angle Comparison

| Metric | Value |
|--------|-------|
| Total non-excluded buses | 27,862 |
| Passing (VA dev < 1.0 deg) | 27,761 (99.64%) |
| Failing | 101 (0.36%) |
| Threshold | >= 95% |
| **Aggregate gate** | **PASS** |

| Statistic | Value |
|-----------|-------|
| Max deviation | 2.160477e+01 deg |
| Mean deviation | 4.545689e-02 deg |
| Median deviation | 2.001058e-02 deg |
| P95 deviation | 5.204895e-02 deg |
| P99 deviation | 2.382426e-01 deg |

### Voltage Level Breakdown

| Tier | Buses | Passing | Fraction | Max Dev (deg) | Mean Dev (deg) |
|------|-------|---------|----------|---------------|----------------|
| Transmission (230+ kV) | 4,317 | 4,316 | 99.98% | 1.351836e+00 | 2.615651e-02 |
| Subtransmission (69-229 kV) | 11,338 | 11,291 | 99.59% | 2.160477e+01 | 5.530872e-02 |
| Distribution (< 69 kV) | 12,207 | 12,154 | 99.57% | 2.160477e+01 | 4.313197e-02 |

### Branch Flow Comparison

| Metric | Value |
|--------|-------|
| Total in-service branches | 32,532 |
| Matched to tool | 32,532 (100%) |
| Passing (dev < 10%) | 32,424 (99.67%) |
| Failing | 108 (0.33%) |
| Threshold | >= 90% |
| **Aggregate gate** | **PASS** |

| Statistic | Value |
|-----------|-------|
| Max deviation (%) | 5.966459e+02 |
| Mean deviation (%) | 1.981888e-01 |
| Median deviation (%) | 1.181483e-09 |
| P95 deviation (%) | 4.789568e-02 |
| P99 deviation (%) | 8.630734e-01 |
| Max absolute deviation | 1.658578e+02 MW |

### Bus Injection Power Balance (v11)

| Metric | Value |
|--------|-------|
| Buses checked | 27,862 |
| Max mismatch (p.u.) | 8.602342e-11 |
| Max mismatch (MW) | 8.602342e-09 |
| Tolerance (p.u.) | 1.000000e-04 |
| Violations | 0 |
| **Check** | **PASS** |

The power balance check confirms that pandapower's DCPF solution is internally
consistent: the sum of branch flows at every bus equals the net injection
(generation minus load) to within machine-precision tolerance.

### Hard-Fail Conditions

| Condition | Threshold | Actual | Triggered |
|-----------|-----------|--------|-----------|
| Excessive bus failing fraction | > 20% | 0.36% | NO |
| Excessive branch failing fraction | > 20% | 0.33% | NO |
| Extreme branch flow deviation | > 50% | 5.966459e+02% | **YES** |

### Formulation Difference Classification

pandapower uses MATPOWER-equivalent full B-matrix construction that
incorporates tap ratios and phase shift angles. The 101 failing buses are
concentrated in a connected sub-region of the subtransmission/distribution
network (69-138 kV), not scattered across transformer-adjacent buses. The
deviation pattern is systematic (~14-21 degrees) in a connected cluster,
indicating a data ingestion issue rather than a formulation difference.

### Top Bus Outliers

| Bus | Base kV | VA Ref (deg) | VA Tool (deg) | Deviation (deg) |
|-----|---------|-------------|---------------|-----------------|
| 30707 | 69.0 | -133.94 | -112.33 | 2.160477e+01 |
| 148401 | 69.0 | -137.31 | -115.71 | 2.160477e+01 |
| 14543 | 12.5 | -141.90 | -120.29 | 2.160477e+01 |
| 14102 | 138.0 | -133.91 | -112.30 | 2.160477e+01 |
| 48022 | 138.0 | -132.72 | -118.20 | 1.452089e+01 |

### Top Branch Outliers

| From | To | Ref (MW) | Tool (MW) | Deviation (%) |
|------|----|----------|-----------|---------------|
| 14102 | 48022 | -20.0 | 99.3 | 5.966459e+02 |
| 76431 | 5666 | -1.1 | 2.0 | 2.793116e+02 |
| 31202 | 31200 | -2.4 | -8.6 | 2.619815e+02 |
| 36520 | 25254 | -0.06 | -2.2 | 2.106104e+02 |
| 27219 | 35466 | 2.4 | 7.3 | 2.042020e+02 |

## Analysis of Failure

The hard-fail is caused by a localized cluster of ~101 buses with systematic
angle deviations of 14-21 degrees. These buses form a connected sub-region in
the subtransmission/distribution network (69-138 kV). The outlier buses have
zero load and zero generation, sitting in a radial network topology where small
impedance differences cause large angle swings.

The deviations are not correlated with transformer tap ratios, ruling out
formulation difference classification. They likely stem from differences in how
the MATPOWER PPC import path handles specific impedance or topology details
compared to the reference solver's ingestion of the same cleaned case file.

Importantly, the aggregate performance is strong:
- 99.64% of buses pass the 1.0-degree VA tolerance
- 99.67% of branches pass the 10% flow tolerance
- Mean deviations are very small (4.545689e-02 deg for buses, 1.981888e-01% for branches)
- Bus injection power balance check passes with machine-precision accuracy

The failure is attributable to a small number of localized outliers that
trigger the hard-fail ceiling, not to a systematic pandapower solver or
ingestion deficiency. [tool-specific: localized MATPOWER PPC import path
impedance handling difference]

## Workarounds

1. **MATPOWER fallback** (stable):
   - **What:** Used pre-cleaned `fnm_main_island.m` via `matpowercaseframes.CaseFrames` and `from_ppc` instead of intermediate CSVs.
   - **Why:** pandapower has no native CSV import capability. The MATPOWER PPC
     format is the standard programmatic entry point.
   - **Durability:** stable -- `matpowercaseframes`, `from_ppc`, and `rundcpp`
     are all public, documented APIs.
   - **Grade impact:** Reduces field fidelity (PPC format flattens transformer data)
     but does not affect DCPF correctness for the fields that are preserved.

2. **Zero RATE_A fix** (stable):
   - **What:** Set zero RATE_A values to 9999 before `from_ppc` (same as G-FNM-1).
   - **Why:** pandapower 3.4.0 bug in `_from_ppc_branch`.
   - **Durability:** stable -- deterministic pre-processing.

## Timing

- **Wall-clock:** 23.64 s (load: 1.94 s + solve: 2.90 s + comparison: ~18.8 s)
- **Timing source:** measured (time.perf_counter)
- **Peak memory:** 139.0 MB
- **Solver iterations:** N/A (DCPF is a direct linear solve)
- **Convergence residual:** N/A
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/fnm_ingestion/test_g_fnm_3_dcpf_verification.py`
