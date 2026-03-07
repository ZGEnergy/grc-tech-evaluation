---
test_id: A-1
tool: pandapower
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 3.31
peak_memory_mb: null
loc: 88
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# A-1: Solve DCPF

## Result: PASS

## Approach

Loaded ACTIVSg10k (~10,000 buses) from MATPOWER `.m` file using `from_mpc()` with `f_hz=60`. Solved DC power flow using `pp.rundcpp(net)`. Extracted results from `net.res_bus` and `net.res_line` DataFrames.

The MATPOWER import splits 10,701 branches into 9,726 lines and 975 transformers. 4 branches connecting same voltage levels were imported as trafos due to non-unity tap ratio.

## Output

| Metric | Value |
|--------|-------|
| Bus count | 10,000 |
| Lines | 9,726 |
| Transformers | 975 |
| Total branches | 10,701 |
| Generators | 1,727 (+ 1 ext_grid = 1,728) |
| Load time | 1.93 s |
| Solve time | 3.31 s (total including load) |

Voltage angles range: -71.04 to +55.48 degrees.
Max line flow: 1,839.6 MW.

Results accessible as `pandas.DataFrame`:
- `net.res_bus.va_degree` -- voltage angles
- `net.res_bus.p_mw` -- nodal injections
- `net.res_line.p_from_mw` / `p_to_mw` -- line flows

All outputs are structured DataFrames with named columns, not raw solver vectors.

## Workarounds

None required.

## Timing

- **Wall-clock:** 3.31 s (includes network loading + solve)
- **Peak memory:** not measured
- **Solver iterations:** N/A (direct linear solve)

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a1_dcpf_medium.py`
