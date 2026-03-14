---
test_id: A-1
tool: pandapower
dimension: expressiveness
network: TINY
status: pass
workaround_class: null
blocked_by: null
protocol_version: "v10"
skill_version: "v1"
test_hash: "05bc255c"
wall_clock_seconds: 1.45
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 138
solver: null
timestamp: "2026-03-13T00:00:00Z"
---

# A-1: Solve DCPF

## Result: PASS

## Approach

Loaded the IEEE 39-bus network using the shared `load_pandapower` loader (which calls `pandapower.converter.matpower.from_mpc` with `f_hz=60`). Ran DC power flow via `pp.rundcpp(net)` with default settings (`trafo_model='t'`).

The converter splits the 46 MATPOWER branches into 35 lines and 11 transformers (branches with non-unity tap ratios). This is pandapower's standard behavior and does not affect DCPF results.

Results are accessed via `net.res_bus` (voltage angles, nodal injections), `net.res_line` (line flows), `net.res_trafo` (transformer flows), `net.res_gen` (generator output), and `net.res_ext_grid` (slack bus output). All are pandas DataFrames.

## Output

| Metric | Value |
|--------|-------|
| Converged | True |
| Buses with nonzero angles | 38 of 39 (only slack bus at 0) |
| Total generation | 6254.23 MW |
| Solve time | 0.426 s |

Bus voltage angles range from -13.46 deg to +7.40 deg. Line flows (P from/to) are lossless (equal magnitude, opposite sign) as expected for DCPF. All results are structured pandas DataFrames with named columns.

**Result tables available after `rundcpp()`:**

| Table | Shape | Key columns |
|-------|-------|-------------|
| `net.res_bus` | (39, 4) | `vm_pu, va_degree, p_mw, q_mvar` |
| `net.res_line` | (35, 14) | `p_from_mw, p_to_mw, loading_percent` |
| `net.res_trafo` | (11, 13) | `p_hv_mw, p_lv_mw, loading_percent` |
| `net.res_gen` | (9, 4) | `p_mw, q_mvar, va_degree, vm_pu` |
| `net.res_ext_grid` | (1, 2) | `p_mw, q_mvar` |

## Workarounds

None required.

## Timing

- **Wall-clock:** 1.45 s (includes network loading; solve-only: 0.43 s)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** N/A (direct linear solve)
- **Convergence residual:** N/A
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a1_dcpf.py`
