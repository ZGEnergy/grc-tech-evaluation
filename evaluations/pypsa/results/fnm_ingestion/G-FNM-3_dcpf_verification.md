---
test_id: G-FNM-3
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v10
skill_version: v1
test_hash: 96876ab1
status: pass
failure_reason: null
workaround_class: stable
blocked_by: null
wall_clock_seconds: 31.3
timing_source: measured
peak_memory_mb: 16288.7
convergence_residual: null
convergence_iterations: null
loc: 446
solver: null
input_path: matpower
timestamp: 2026-03-13T00:00:00Z
---

# G-FNM-3: DCPF verification against reference solution on LARGE

## Result: PASS

100% of buses and 100% of branches pass all tolerance thresholds. Zero deviations
from the MATPOWER reference solution. No hard-fail conditions triggered.

## Approach

Loaded the pre-cleaned 27,862-bus FNM main island from
`data/fnm/reference/cleaned/fnm_main_island.m` via the shared
`matpower_loader.load_pypsa()` utility (MATPOWER fallback, since G-FNM-1 failed
with `psse_parse_error`). The loader applies three correctness patches:

1. **Branch status** — `import_from_pypower_ppc` ignores MATPOWER BR_STATUS
   (column 10), importing all branches as active. The loader deactivates 74
   branches that have `status=0` in the MATPOWER data.
2. **Transformer susceptance** — resets `b = 1/x` (MATPOWER DC convention).
3. **Generator marginal costs** — populates from gencost table (N/A for FNM).

Solved DCPF using `n.lpf()` and compared bus voltage angles and branch active
power flows against the MATPOWER reference solution.

### Root Cause of Previous Failure

The original run (without the shared loader) produced 91% bus angle failures and
87,054% max branch flow deviation. Investigation revealed that `import_from_pypower_ppc`
imports the MATPOWER `BR_STATUS` column as a custom `status` attribute but does NOT
map it to PyPSA's `active` flag. All 32,606 branches were treated as active, but only
32,532 should be (74 inactive). The 74 phantom branches distorted the B-matrix globally,
producing the observed deviations.

## Output

### Bus Voltage Angle Comparison

| Metric | Value |
|--------|-------|
| Non-excluded buses compared | 27,862 |
| Tolerance | 1.0 deg |
| Buses passing | 27,862 (100.0%) |
| Required passing fraction | 95% |
| Mean deviation | 0.0 deg |
| Max deviation | 0.0 deg |

### Bus Angle Deviation by Voltage Tier

| Voltage Tier | Count | Passing | Fraction | Mean Dev (deg) | Max Dev (deg) |
|--------------|-------|---------|----------|----------------|---------------|
| >= 230 kV | 4,317 | 4,317 | 100.0% | 0.0 | 0.0 |
| 69-230 kV | 11,338 | 11,338 | 100.0% | 0.0 | 0.0 |
| < 69 kV | 12,207 | 12,207 | 100.0% | 0.0 | 0.0 |

### Branch Flow Comparison

| Metric | Value |
|--------|-------|
| Branches compared | 32,532 |
| Tolerance | 10% (floor 1 MW) |
| Branches passing | 32,532 (100.0%) |
| Required passing fraction | 90% |
| Mean deviation | 0.0% |
| Max deviation | 0.0% |

### Branch Flow by Component Type

| Type | Count | Mean Dev (%) | Max Dev (%) |
|------|-------|-------------|-------------|
| Lines | 23,056 | 0.0 | 0.0 |
| Transformers | 9,476 | 0.0 | 0.0 |

### Transformer Tap Analysis

- Total transformers: 9,481
- Tap = 1.0: 7,123
- Tap != 1.0: 2,358
- Tap range: [0.7894, 1.4165]

With the branch status patch applied, transformer susceptance values are correctly
computed and the DCPF B-matrix matches the reference exactly.

### Power Balance

| Metric | PyPSA (pre-solve) | Reference |
|--------|-------------------|-----------|
| Total generation | 155,511 MW | 165,492 MW |
| Total load | 165,492 MW | 165,492 MW |

The 9,981 MW generation-load imbalance (6.0%) is absorbed at the slack bus (bus 29421).

### Hard-Fail Conditions

1. **excessive_bus_failing_fraction**: 0.0% fail < 20% threshold -- OK
2. **excessive_branch_failing_fraction**: 0.0% fail < 20% threshold -- OK
3. **extreme_branch_flow_deviation**: 0.0% < 50% threshold -- OK

## Workarounds

- **What:** MATPOWER fallback path via shared `matpower_loader.load_pypsa()`
- **Why:** G-FNM-1 failed -- PyPSA cannot parse PSS/E intermediate CSV format
- **Durability:** stable -- matpowercaseframes is a documented third-party package;
  the three correctness patches in the loader are deterministic and version-pinned
- **Grade impact:** No additional grade impact beyond G-FNM-1 failure. The loader
  patches are necessary due to bugs in `import_from_pypower_ppc` (branch status
  ignored, gencost ignored), not fundamental tool limitations.

## Timing

- **Wall-clock:** 31.3s (total), 29.3s (solve only)
- **Timing source:** measured
- **Peak memory:** 16,289 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/fnm_ingestion/test_g_fnm_3_dcpf_verification.py`
