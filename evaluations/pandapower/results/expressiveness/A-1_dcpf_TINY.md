---
test_id: A-1
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.545
peak_memory_mb: null
loc: 88
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# A-1: Solve DCPF

## Result: PASS

## Approach

Loaded IEEE 39-bus network from MATPOWER `.m` file using `from_mpc()` with `f_hz=60`. Solved DC power flow using `pp.rundcpp(net)`. Extracted results from `net.res_bus` and `net.res_line` DataFrames.

The MATPOWER import splits the 46 branches into 35 lines and 11 transformers (branches with non-unity tap ratio are imported as transformers even when connecting same voltage levels).

## Output

| Metric | Value |
|--------|-------|
| Bus count | 39 |
| Lines | 35 |
| Transformers | 11 |
| Total branches | 46 |
| Generators | 9 (+ 1 ext_grid = 10) |

Voltage angles range: -13.46 to +7.40 degrees.
Max line flow: 608.8 MW.

Results accessible as `pandas.DataFrame`:
- `net.res_bus.va_degree` -- voltage angles
- `net.res_bus.p_mw` -- nodal injections
- `net.res_line.p_from_mw` / `p_to_mw` -- line flows

All outputs are structured DataFrames with named columns, not raw solver vectors.

## Workarounds

None required.

## Timing

- **Wall-clock:** 0.545 s (includes solve only, not network loading)
- **Peak memory:** not measured
- **Solver iterations:** N/A (direct linear solve)

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a1_dcpf.py`
