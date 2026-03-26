---
test_id: C-1
tool: pandapower
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: "v2"
test_hash: "b0812a45"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.039
timing_source: measured
peak_memory_mb: 31.14
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 100
solver: null
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T00:00:00Z
---

# C-1: DCPF on MEDIUM

## Result: PASS

## Approach

Loaded the ACTIVSg10k network (10,000 buses, 12,706 branches, 2,485 generators) via
the shared `load_pandapower` loader and ran `pp.rundcpp(net)` — pandapower's direct
DC power flow solver. DCPF is a direct linear solve (no iterative solver), so no
solver configuration is needed.

pandapower's `from_mpc` converter promoted 975 branches with non-unity tap ratios to
transformers (LOSSLESS classification). 4 branches were flagged as connecting same
voltage levels despite having non-unity tap ratios.

## Output

| Metric | Value |
|--------|-------|
| Bus count | 10,000 |
| Line count | 9,726 |
| Transformer count | 975 |
| Generator count | 1,727 (+1 ext_grid) |
| Base MVA | 100.0 |
| Solve time | 1.039 s |
| Peak memory | 31.14 MB |
| Converged | Yes |

**Voltage angles:**

| Metric | Value |
|--------|-------|
| Min angle | -71.04 deg |
| Max angle | 55.48 deg |
| Mean angle | -26.22 deg |

**Branch loading:**

| Metric | Value |
|--------|-------|
| Max line loading | 77.02% |
| Mean line loading | 16.19% |
| Max trafo loading | 77.54% |

**Power balance:**

| Metric | Value |
|--------|-------|
| Total gen (gen + ext_grid) | 1.342359e+05 MW |
| Total load | 1.509169e+05 MW |
| Losses (DCPF) | 0.0 MW |

Note: The generation-load imbalance in DCPF is expected because pandapower's ext_grid
acts as the slack bus absorber; the sum of gen + ext_grid does not include all slack
absorption contributions in the DC formulation.

## Workarounds

None required.

## Timing

- **Wall-clock:** 1.039 s (solve only, excluding network loading)
- **Timing source:** measured
- **Peak memory:** 31.14 MB
- **CPU threads used:** 1 (pandapower DCPF is single-threaded)
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/pandapower/tests/scalability/test_c1_dcpf_medium.py`
