---
test_id: A-2
tool: pandapower
dimension: expressiveness
network: TINY
status: pass
workaround_class: null
blocked_by: null
protocol_version: "v10"
skill_version: "v1"
test_hash: "fca7353e"
wall_clock_seconds: 2.02
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: 4
loc: 190
solver: null
timestamp: "2026-03-13T00:00:00Z"
---

# A-2: Solve ACPF (Newton-Raphson)

## Result: PASS

## Approach

Loaded the IEEE 39-bus network using the shared `load_pandapower` loader. Ran AC power flow via `pp.runpp(net, algorithm='nr', init='flat', tolerance_mva=1e-8, max_iteration=10, calculate_voltage_angles=True)`.

The flat start (`init='flat'`) initializes all voltage magnitudes to 1.0 pu and all angles to 0.0 degrees, per the convergence protocol. pandapower's Newton-Raphson solver converged in 4 iterations without requiring a DC warm start.

Convergence diagnostics extracted from `net._ppc`:
- Iteration count: accessible via `net._ppc["iterations"]` (returns 4)
- Success flag: `net._ppc["success"]` (returns True)

**Note on tolerance_mva:** pandapower documents this parameter as MVA but internally compares against per-unit mismatches (known bug #2750, unfixed in v3.4.0). The solver converges to this tolerance regardless of the unit interpretation.

## Output

| Metric | Value |
|--------|-------|
| Converged | True |
| DC warm start needed | No |
| NR iterations | 4 |
| Buses differing from flat start | 100% (39/39) |
| Vm range | 0.982 - 1.064 pu |
| Vm mean / std | 1.026 / 0.022 pu |
| Total P losses | 43.64 MW |
| Total Q losses | -112.16 Mvar |
| Solve time | 1.03 s |

All 39 buses have voltage magnitudes differing from the 1.0 pu flat start, satisfying the >95% threshold. Bus results include both voltage magnitudes and angles. Line results include P/Q flows and losses (`pl_mw`, `ql_mvar`).

**Result tables available after `runpp()`:**

| Table | Key columns |
|-------|-------------|
| `net.res_bus` | `vm_pu, va_degree, p_mw, q_mvar` |
| `net.res_line` | `p_from_mw, q_from_mvar, p_to_mw, q_to_mvar, pl_mw, ql_mvar, loading_percent` |
| `net.res_trafo` | `p_hv_mw, q_hv_mvar, p_lv_mw, q_lv_mvar, pl_mw, ql_mvar, loading_percent` |
| `net.res_gen` | `p_mw, q_mvar, va_degree, vm_pu` |

## Workarounds

None required.

**Diagnostic quality note:** The convergence residual (final power mismatch) is not directly accessible as a scalar from the public API. The solver converges when the mismatch falls below `tolerance_mva`, but the final residual value is not stored in a result attribute. Iteration count is accessible via the internal `net._ppc["iterations"]` attribute, which uses a private (underscore-prefixed) attribute. This is a minor diagnostic quality limitation but does not affect the pass condition since convergence is verified through voltage profile divergence from flat start.

## Timing

- **Wall-clock:** 2.02 s (includes network loading; solve-only: 1.03 s)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** 4
- **Convergence residual:** below 1e-8 (tolerance_mva setting; exact value not extractable)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a2_acpf.py`
