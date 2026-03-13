---
test_id: G-FNM-3
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v9
skill_version: v1
test_hash: e4c07e71
status: fail
workaround_class: stable
blocked_by: null
wall_clock_seconds: 39.505
timing_source: measured
peak_memory_mb: 16289.4
convergence_residual: null
convergence_iterations: null
loc: 485
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# G-FNM-3: DCPF Verification

## Result: FAIL

Hard-fail triggered on both bus angle and branch flow metrics.

## Approach

1. Parsed the pre-cleaned MATPOWER `.m` case file (`fnm_main_island.m`) with a
   regex-based parser (the `.mat` variant is Octave text format, not
   scipy-compatible, and PyPSA has no native MATPOWER reader).
2. Imported into PyPSA via `import_from_pypower_ppc(ppc)`. PyPSA classified
   32,606 branches into 23,125 lines and 9,481 transformers based on voltage
   level mismatch, non-unity tap ratio, or nonzero phase shift.
3. Solved DCPF using `n.lpf()` (linear power flow).
4. Extracted bus voltage angles (radians, converted to degrees) and branch
   active power flows (MW) from time-series output.
5. Compared against the MATPOWER DCPF reference solution using v9 pass
   conditions: >=95% buses within 1.0 deg, >=90% branches within 10% (floor 1 MW).
6. Excluded the 2,445 buses in `excluded_buses.json` from bus angle metrics.

## Output

### Bus Voltage Angles (v9: >=95% within 1.0 deg)

| Metric | Value |
|--------|-------|
| Non-excluded buses matched | 27,862 |
| Buses passing (within 1.0 deg) | 2,517 |
| Fraction passing | 9.03% |
| Required fraction | 95% |
| Mean deviation | 3.95 deg |
| Median deviation | 2.10 deg |
| P95 deviation | 6.89 deg |
| P99 deviation | 34.10 deg |
| Max deviation | 61.05 deg |
| **Pass** | **NO — hard fail (91% fail rate > 20% threshold)** |

### Branch Power Flows (v9: >=90% within 10% relative, floor 1 MW)

| Metric | Value |
|--------|-------|
| Matched branches | 32,532 |
| Branches passing | 30,910 |
| Fraction passing | 95.01% |
| Required fraction | 90% |
| Mean deviation | 18.55% |
| Median deviation | 0.0% |
| P95 deviation | 9.95% |
| P99 deviation | 89.79% |
| Max deviation | 87,054.5% |
| **Pass** | **NO — hard fail (max deviation 87,054% > 50% threshold)** |

Note: Branch flow fraction passing (95.0%) technically meets the 90% threshold,
but the max deviation hard-fail condition is triggered by extreme outliers on
transformers with very low reference flows.

### Deviation Breakdown by Component Type

| Component | Count | Mean dev | Max dev |
|-----------|-------|----------|---------|
| Lines | 23,056 | 11.59% | 52,032.0% |
| Transformers | 9,476 | 35.47% | 87,054.5% |

### Transformer Tap Analysis

| Property | Value |
|----------|-------|
| Total transformers | 9,481 |
| Tap = 1.0 (or 0.0 → 1.0) | 7,123 |
| Tap != 1.0 | 2,358 |
| Tap range | 0.7894 to 1.4165 |

### Power Balance

| Quantity | Value (MW) |
|----------|------------|
| Pre-solve gen (sum of Pg) | 155,511.04 |
| Load (sum of Pd) | 165,491.55 |
| Reference post-solve gen | 165,491.55 |

## Root Cause Analysis

The DCPF results diverge systematically because **PyPSA and MATPOWER use
different transformer models in the DC approximation**:

- **MATPOWER** DCPF (`makeBdc`): susceptance `b = 1/x` for all branches,
  ignoring the tap ratio entirely. Only the phase shift enters the DCPF
  formulation.
- **PyPSA** DCPF (`lpf`): susceptance `b = 1/(x * tap_ratio)` for
  transformers. The tap ratio modifies the effective reactance.

On the ERCOT FNM, 2,358 transformers have non-unity tap ratios (range
0.79–1.42). These produce different susceptance values between the two tools,
which propagate through the entire network as angle and flow deviations.

This is not a bug in either tool — it reflects a legitimate modeling choice.
PyPSA's approach is arguably more physically accurate for the DC approximation,
but it produces results that differ from the MATPOWER reference.

The extreme max deviation values (52K–87K%) arise on branches where the
reference flow is near zero but the PyPSA solution has a small nonzero flow —
the percentage formula amplifies small absolute differences on near-zero flows.

## Workarounds

- **What:** Parsed `.m` file with regex instead of using `.mat` file or a
  native reader.
- **Why:** The `.mat` file is in Octave text format (not scipy-loadable) and
  PyPSA has no native MATPOWER file reader.
- **Durability:** stable — regex parsing of MATPOWER format is straightforward.
- **Grade impact:** Minor — this is an I/O convenience issue, not a modeling limitation.
- **Version tested:** PyPSA 1.1.2

## Timing

- **Wall-clock (total):** 39.505 s
- **Wall-clock (solve only):** 37.944 s
- **Timing source:** measured
- **Peak memory:** 16,289.4 MB (tracemalloc)
- **CPU cores used:** 1 (PyPSA lpf is single-threaded)

The solve time of ~38 seconds is significantly slower than the MATPOWER
reference (0.13 s), a factor of ~292x. This is consistent with PyPSA's
Python-based sparse linear algebra versus MATPOWER's optimized Octave routines.

## Test Script

**Path:** `evaluations/pypsa/tests/fnm_ingestion/test_g_fnm_3_dcpf_verification.py`
