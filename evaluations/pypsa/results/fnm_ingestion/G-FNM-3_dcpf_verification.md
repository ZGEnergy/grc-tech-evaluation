---
test_id: G-FNM-3
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v10
skill_version: v1
test_hash: 96876ab1
status: fail
workaround_class: null
blocked_by: null
wall_clock_seconds: 30.3
timing_source: measured
peak_memory_mb: 16289.4
convergence_residual: null
convergence_iterations: null
loc: 446
solver: null
input_path: matpower
timestamp: 2026-03-13T00:00:00Z
---

# G-FNM-3: DCPF verification against reference solution on LARGE

## Result: FAIL

Two hard-fail conditions triggered: 91.0% of buses fail the VA tolerance (threshold 20%),
and maximum branch flow deviation of 87,054% exceeds the 50% hard-fail threshold.

## Approach

Loaded the pre-cleaned 27,862-bus FNM main island from
`data/fnm/reference/cleaned/fnm_main_island.m` via `matpowercaseframes` +
`import_from_pypower_ppc` (MATPOWER fallback, since G-FNM-1 failed with
`psse_parse_error`). Solved DCPF using `n.lpf()` and compared bus voltage angles
and branch active power flows against the MATPOWER reference solution.

## Output

### Bus Voltage Angle Comparison

| Metric | Value |
|--------|-------|
| Non-excluded buses compared | 27,862 |
| Tolerance | 1.0 deg |
| Buses passing | 2,517 (9.0%) |
| Required passing fraction | 95% |
| Mean deviation | 3.95 deg |
| Median deviation | 2.10 deg |
| P95 deviation | 6.89 deg |
| P99 deviation | 34.10 deg |
| Max deviation | 61.05 deg |

### Bus Angle Deviation by Voltage Tier

| Voltage Tier | Count | Passing | Fraction | Mean Dev (deg) | Max Dev (deg) |
|--------------|-------|---------|----------|----------------|---------------|
| >= 230 kV | 4,317 | 373 | 8.6% | 3.63 | 61.05 |
| 69-230 kV | 11,338 | 1,234 | 10.9% | 3.83 | 49.07 |
| < 69 kV | 12,207 | 910 | 7.5% | 4.18 | 47.64 |

Deviations are uniformly distributed across all voltage tiers, not concentrated
at any particular voltage level. This pattern is inconsistent with a simple
formulation sophistication difference (which would concentrate at transformer-connected
buses) and suggests a systematic difference in how PyPSA and MATPOWER construct the
DC B-matrix for this network.

### Branch Flow Comparison

| Metric | Value |
|--------|-------|
| Branches compared | 32,532 |
| Tolerance | 10% (floor 1 MW) |
| Branches passing | 30,910 (95.0%) |
| Required passing fraction | 90% |
| Mean deviation | 18.5% |
| Median deviation | 0.0% |
| P95 deviation | 10.0% |
| P99 deviation | 89.8% |
| Max deviation | 87,054% |

### Branch Flow by Component Type

| Type | Count | Mean Dev (%) | Max Dev (%) |
|------|-------|-------------|-------------|
| Lines | 23,056 | 11.6 | 52,032 |
| Transformers | 9,476 | 35.5 | 87,054 |

Transformer branches show systematically higher deviations (mean 35.5%) than lines
(mean 11.6%), consistent with the B-matrix formulation difference for branches with
non-unity tap ratios.

### Transformer Tap Analysis

- Total transformers: 9,481
- Tap = 1.0: 7,123
- Tap != 1.0: 2,358
- Tap range: [0.7894, 1.4165]

Both PyPSA and MATPOWER incorporate tap ratios in the DCPF B-matrix. The deviations
are therefore attributable to differences in how `import_from_pypower_ppc` maps
transformer impedance parameters, not to formulation sophistication differences.

### Power Balance

| Metric | PyPSA (pre-solve) | Reference |
|--------|-------------------|-----------|
| Total generation | 155,511 MW | 165,492 MW |
| Total load | 165,492 MW | 165,492 MW |

The source MATPOWER data has a 9,981 MW generation-load imbalance (6.0%). Both
tools absorb this at the slack bus (bus 29421). The slack bus angle deviation is
exactly 0.0 degrees, confirming correct slack identification.

### Hard-Fail Conditions

1. **excessive_bus_failing_fraction**: 91.0% fail > 20% threshold -- TRIGGERED
2. **excessive_branch_failing_fraction**: 5.0% fail < 20% threshold -- OK
3. **extreme_branch_flow_deviation**: 87,054% > 50% threshold -- TRIGGERED

## Workarounds

- **What:** MATPOWER fallback path used instead of intermediate CSV ingestion
- **Why:** G-FNM-1 failed -- PyPSA cannot parse PSS/E intermediate CSV format
- **Durability:** stable -- matpowercaseframes is a documented third-party package
- **Grade impact:** No additional grade impact beyond G-FNM-1 failure

## Timing

- **Wall-clock:** 30.3s (total), 28.7s (solve only)
- **Timing source:** measured
- **Peak memory:** 16,289 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/fnm_ingestion/test_g_fnm_3_dcpf_verification.py`
