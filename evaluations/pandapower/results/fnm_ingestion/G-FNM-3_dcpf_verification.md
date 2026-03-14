---
test_id: G-FNM-3
tool: pandapower
dimension: fnm_ingestion
network: LARGE
protocol_version: "v10"
skill_version: "v1"
test_hash: "3a7a247d"
status: fail
workaround_class: stable
blocked_by: null
wall_clock_seconds: 1.97
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 423
solver: null
timestamp: 2026-03-14T04:00:00Z
input_path: matpower
---

# G-FNM-3: DCPF Verification Against Reference Solution on FNM

## Result: FAIL

DCPF converges successfully and aggregate thresholds are met (99.6% of buses
pass VA tolerance, 99.7% of branches pass flow tolerance). However, the
hard-fail condition is triggered: the maximum branch flow deviation of 596.6%
exceeds the 50% threshold. The extreme deviations are concentrated in a
localized sub-region of ~101 buses and are not correlated with transformer
adjacency (0% transformer adjacency fraction), so they cannot be classified
as a formulation difference.

## Approach

1. Loaded the pre-cleaned MATPOWER case (`fnm_main_island.m`, 27,862-bus main
   island) using `matpowercaseframes.CaseFrames` + `from_ppc` (same ingestion
   path as G-FNM-1, using MATPOWER fallback since pandapower has no native CSV import).
2. Solved DCPF using `pandapower.rundcpp(net)`.
3. Compared bus voltage angles against reference (`buses_dcpf.csv`).
4. Compared branch active power flows against reference (`branches_dcpf.csv`).
5. Applied pass conditions from `pass_conditions.json` DCPF section.
6. Excluded 2,445 buses per `excluded_buses.json`.

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
| Max deviation | 21.60 deg |
| Mean deviation | 0.045 deg |
| Median deviation | 0.020 deg |
| P95 deviation | 0.052 deg |
| P99 deviation | 0.238 deg |

### Voltage Level Breakdown

| Tier | Buses | Passing | Fraction | Max Dev (deg) | Mean Dev (deg) |
|------|-------|---------|----------|---------------|----------------|
| Transmission (230+ kV) | 4,317 | 4,316 | 99.98% | 1.35 | 0.026 |
| Subtransmission (69-229 kV) | 11,338 | 11,291 | 99.59% | 21.60 | 0.055 |
| Distribution (< 69 kV) | 12,207 | 12,154 | 99.57% | 21.60 | 0.043 |

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
| Max deviation (%) | 596.6% |
| Mean deviation (%) | 0.198% |
| Median deviation (%) | ~0.0% |
| P95 deviation (%) | 0.048% |
| P99 deviation (%) | 0.863% |
| Max absolute deviation | 165.9 MW |

### Hard-Fail Conditions

| Condition | Threshold | Actual | Triggered |
|-----------|-----------|--------|-----------|
| Excessive bus failing fraction | > 20% | 0.36% | NO |
| Excessive branch failing fraction | > 20% | 0.33% | NO |
| Extreme branch flow deviation | > 50% | 596.6% | **YES** |

### Formulation Difference Classification

- Transformer adjacency fraction: **0/101 = 0%**
- The 101 failing buses are NOT adjacent to transformers with non-unity tap ratios
- The deviations are concentrated in a localized sub-network region (buses
  14102, 48022, 30707, 148401, and their downstream neighbors)
- Deviation pattern: systematic bias (~14-21 degrees) in a connected cluster,
  not scattered across the network
- Classification: **data_ingestion_error** (not formulation_difference)

### Top Bus Outliers

| Bus | Base kV | VA Ref (deg) | VA Tool (deg) | Deviation (deg) |
|-----|---------|-------------|---------------|-----------------|
| 30707 | 69.0 | -133.94 | -112.33 | 21.60 |
| 148401 | 69.0 | -137.31 | -115.71 | 21.60 |
| 14543 | 12.5 | -141.90 | -120.29 | 21.60 |
| 14102 | 138.0 | -133.91 | -112.30 | 21.60 |
| 48022 | 138.0 | -132.72 | -118.20 | 14.52 |

### Top Branch Outliers

| From | To | Ref (MW) | Tool (MW) | Deviation (%) |
|------|----|----------|-----------|---------------|
| 14102 | 48022 | -20.0 | 99.3 | 596.6 |
| 76431 | 5666 | -1.1 | 2.0 | 279.3 |
| 31202 | 31200 | -2.4 | -8.6 | 262.0 |
| 36520 | 25254 | -0.06 | -2.2 | 210.6 |
| 27219 | 35466 | 2.4 | 7.3 | 204.2 |

## Analysis of Failure

The hard-fail is caused by a localized cluster of ~101 buses with systematic
angle deviations of 14-21 degrees. These buses form a connected sub-region in
the subtransmission/distribution network (69-138 kV). The outlier buses have
zero load and zero generation, sitting in a radial network topology where small
impedance differences cause large angle swings.

The deviations are not correlated with transformer tap ratios (0% transformer
adjacency), ruling out formulation difference classification. They likely stem
from differences in how the MATPOWER PPC import path handles specific impedance
or topology details compared to the reference solver's ingestion of the same
cleaned case file.

Importantly, the aggregate performance is strong:
- 99.64% of buses pass the 1.0-degree VA tolerance
- 99.67% of branches pass the 10% flow tolerance
- Mean deviations are very small (0.045 deg for buses, 0.198% for branches)

The failure is attributable to a small number of localized outliers that
trigger the hard-fail ceiling, not to a systematic pandapower solver or
ingestion deficiency.

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

- **Wall-clock:** 1.97 s (load: 0.18 s + solve: 0.40 s + comparison: 1.39 s)
- **Timing source:** measured (time.perf_counter)
- **Peak memory:** not measured
- **Solver iterations:** N/A (DCPF is a direct linear solve)
- **Convergence residual:** N/A
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/fnm_ingestion/test_g_fnm_3_dcpf_verification.py`
