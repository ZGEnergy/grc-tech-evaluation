---
test_id: G-FNM-3
tool: pypsa
dimension: fnm_ingestion
network: LARGE
protocol_version: v11
skill_version: v2
test_hash: 64141acc
status: pass
workaround_class: stable
blocked_by: null
ingestion_path: matpower
input_path: matpower
wall_clock_seconds: 43.544
timing_source: measured
peak_memory_mb: 16288.7
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 570
solver: null
timestamp: 2026-03-24T00:00:00Z
---

# G-FNM-3: DCPF verification against reference solution on LARGE

## Result: PASS

100% of buses and 100% of branches pass all tolerance thresholds. All deviations
are at float64 machine-precision level. No hard-fail conditions triggered. Bus
injection power balance check passes on all 27,862 buses.

## Approach

Loaded the pre-cleaned 27,862-bus FNM main island from
`data/fnm/reference/cleaned/fnm_main_island.m` via the shared
`matpower_loader.load_pypsa()` utility (MATPOWER fallback, since G-FNM-1 failed
with `psse_parse_error`). The loader applies three correctness patches:

1. **Branch status** -- `import_from_pypower_ppc` ignores MATPOWER BR_STATUS
   (column 10), importing all branches as active. The loader deactivates 74
   branches that have `status=0` in the MATPOWER data.
2. **Transformer susceptance** -- resets `b = 1/x` (MATPOWER DC convention).
3. **Generator marginal costs** -- populates from gencost table (N/A for FNM).

Solved DCPF using `n.lpf()` and compared bus voltage angles and branch active
power flows against the MATPOWER reference solution. Added bus injection power
balance verification using post-solve generator dispatch values.

## Output

### Bus Voltage Angle Comparison

| Metric | Value |
|--------|-------|
| Non-excluded buses compared | 27,862 |
| Tolerance | 1.0 deg |
| Buses passing | 27,862 (100.0%) |
| Required passing fraction | 95% |
| Mean deviation | 3.316294e-09 deg |
| Max deviation | 1.073352e-08 deg |
| Median deviation | 2.923016e-09 deg |
| P95 deviation | 7.940541e-09 deg |
| P99 deviation | 9.055445e-09 deg |

### Bus Angle Deviation by Voltage Tier

| Voltage Tier | Count | Passing | Fraction | Mean Dev (deg) | Max Dev (deg) |
|--------------|-------|---------|----------|----------------|---------------|
| >= 230 kV | 4,317 | 4,317 | 100.0% | 3.340458e-09 | 9.670032e-09 |
| 69-230 kV | 11,338 | 11,338 | 100.0% | 3.242921e-09 | 1.021766e-08 |
| < 69 kV | 12,207 | 12,207 | 100.0% | 3.375898e-09 | 1.073352e-08 |

### Branch Flow Comparison

| Metric | Value |
|--------|-------|
| Branches compared | 32,532 |
| Tolerance | 10% (floor 1 MW) |
| Branches passing | 32,532 (100.0%) |
| Required passing fraction | 90% |
| Mean deviation | 1.175350e-08 % |
| Max deviation (pct) | 5.757744e-07 % |
| Max deviation (MW) | 5.773336e-08 MW |
| Median deviation | 8.130470e-10 % |
| P95 deviation | 4.589096e-08 % |
| P99 deviation | 2.370492e-07 % |

### Branch Flow by Component Type

| Type | Count | Mean Dev (%) | Max Dev (%) |
|------|-------|-------------|-------------|
| Lines | 23,056 | 1.244669e-08 | 5.757744e-07 |
| Transformers | 9,476 | 1.006691e-08 | 4.956536e-07 |

### Transformer Tap Analysis

- Total transformers: 9,481
- Tap = 1.0: 7,123
- Tap != 1.0: 2,358
- Tap range: [0.7894, 1.4165]

With the branch status patch applied, transformer susceptance values are correctly
computed and the DCPF B-matrix matches the reference exactly (deviations are float64
numerical noise only).

### Bus Injection Power Balance

| Metric | Value |
|--------|-------|
| Buses checked | 27,862 |
| Tolerance | 1.000000e-03 MW |
| Buses balanced | 27,862 (100.0%) |
| Buses imbalanced | 0 |
| Max mismatch | 1.317039e-07 MW |
| Mean mismatch | 6.748134e-11 MW |
| Balance pass | true |

Power balance verified using post-solve generator dispatch (including slack bus
absorption of the 9,981 MW generation-load deficit).

### Power Balance (System-Level)

| Metric | PyPSA (pre-solve) | Reference |
|--------|-------------------|-----------|
| Total generation | 155,511 MW | 165,492 MW |
| Total load | 165,492 MW | 165,492 MW |

The 9,981 MW generation-load imbalance (6.0%) is absorbed at the slack bus (bus 29421).

### Hard-Fail Conditions

1. **excessive_bus_failing_fraction**: 0.0% fail < 20% threshold -- OK
2. **excessive_branch_failing_fraction**: 0.0% fail < 20% threshold -- OK
3. **extreme_branch_flow_deviation**: 5.757744e-07% < 50% threshold -- OK

## Workarounds

- **What:** MATPOWER fallback path via shared `matpower_loader.load_pypsa()`
- **Why:** G-FNM-1 failed -- PyPSA cannot parse PSS/E intermediate CSV format
- **Durability:** stable -- matpowercaseframes is a documented third-party package;
  the three correctness patches in the loader are deterministic and version-pinned
- **Grade impact:** No additional grade impact beyond G-FNM-1 failure. The loader
  patches are necessary due to bugs in `import_from_pypower_ppc` (branch status
  ignored, gencost ignored), not fundamental tool limitations.

## Timing

- **Wall-clock:** 43.5s (total), 40.1s (solve only)
- **Timing source:** measured
- **Peak memory:** 16,289 MB
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/fnm_ingestion/test_g_fnm_3_dcpf_verification.py`
