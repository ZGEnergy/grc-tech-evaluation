---
test_id: C-1
tool: pandapower
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.795
peak_memory_mb: 322.9
loc: 88
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# C-1: DCPF at scale

## Result: PASS

## Approach

Loaded the ACTIVSg10k (~10,000-bus) MEDIUM network from MATPOWER `.m` file using `from_mpc()` with `f_hz=60`. Solved DC power flow using `pp.rundcpp(net)`. Measured wall-clock time, peak memory (via `resource.getrusage`), and CPU utilization.

The MATPOWER import splits 12,706 total branches into 9,726 lines and 975 transformers.

## Output

| Metric | Value |
|--------|-------|
| Bus count | 10,000 |
| Lines | 9,726 |
| Transformers | 975 |
| Generators | 1,727 (+ 1 ext_grid) |
| Loads | 4,170 |
| Converged | Yes |
| Max voltage angle | 55.48 deg |
| Min voltage angle | -71.04 deg |
| Max line flow | 1,839.6 MW |

## Workarounds

None required.

## Timing

- **Wall-clock:** 0.795 s (total including load), solve-only: 0.529 s
- **Network load time:** 0.266 s
- **Peak memory:** 322.9 MB
- **Memory delta for solve:** 65.0 MB
- **CPU user time:** 4.45 s
- **Solver iterations:** N/A (direct linear solve)

## Test Script

**Path:** `evaluations/pandapower/tests/scalability/test_c1_dcpf_scale.py`
