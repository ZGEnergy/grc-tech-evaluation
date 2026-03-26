---
test_id: A-2
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "eb349d9c"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 17.23
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: 4
convergence_evidence_quality: iteration_count_reported
loc: 181
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# A-2: Solve ACPF (Newton-Raphson) on TINY (case39)

## Result: PASS

## Approach

Loaded the IEEE 39-bus network using the shared `load_pandapower` loader. Ran AC power flow via `pp.runpp(net, algorithm='nr', init='flat', tolerance_mva=1e-8, max_iteration=10, calculate_voltage_angles=True)`.

The flat start (`init='flat'`) initializes all voltage magnitudes to 1.0 pu and all angles to 0.0 degrees, per the convergence protocol. pandapower's Newton-Raphson solver converged in 4 iterations without requiring a DC warm start.

**Convergence diagnostics:**
- Iteration count: accessible via `net._ppc["iterations"]` (returns 4). This uses a private attribute but provides the actual NR iteration count.
- Success flag: `net._ppc["success"]` (returns True).
- Public convergence flag: `net.converged` (returns True).
- Convergence evidence quality: `iteration_count_reported` -- iteration count extracted from `net._ppc["iterations"]`.

**Note on tolerance_mva:** pandapower documents this parameter as MVA but internally compares against per-unit mismatches. The solver converges to this tolerance. The final residual scalar is not directly accessible as a stored result attribute.

## Output

| Metric | Value |
|--------|-------|
| Converged | True |
| DC warm start needed | No |
| NR iterations | 4 |
| Buses differing from flat start | 100% (39/39) |
| Vm range | 0.982 -- 1.064 pu |
| Vm mean / std | 1.026 / 0.022 pu |
| Total P losses | 43.64 MW |
| Total Q losses | -112.16 Mvar |
| Solve time | 8.84 s |

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

**Diagnostic quality note:** The convergence residual (final power mismatch scalar) is not directly accessible from the public API. The solver converges when the mismatch falls below `tolerance_mva`, but the final residual value is not stored in a result attribute. Iteration count is accessible via the internal `net._ppc["iterations"]` attribute (private, underscore-prefixed). This is a minor diagnostic quality limitation (convergence evidence quality = `iteration_count_reported`), not a test failure. Convergence is additionally verified through 100% voltage profile divergence from flat start.

## Timing

- **Wall-clock:** 17.23 s (includes network loading; solve-only: 8.84 s)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** 4
- **Convergence residual:** below 1e-8 (tolerance_mva setting; exact value not extractable)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a2_acpf.py`
