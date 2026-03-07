---
test_id: A-2
tool: pandapower
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.203
peak_memory_mb: null
loc: 123
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# A-2: Solve ACPF (Newton-Raphson)

## Result: PASS

## Approach

Loaded IEEE 39-bus network via `from_mpc()`. Solved AC power flow using `pp.runpp(net, algorithm="nr", init="flat")` per the convergence protocol (flat start first).

Flat start converged successfully on the first attempt. No DC warm start fallback was needed.

## Output

| Metric | Value |
|--------|-------|
| Voltage magnitude range | 0.982 - 1.064 pu |
| Voltage angle range | -14.54 to +4.47 degrees |
| Total active power losses (lines) | 31.06 MW |
| Total reactive power losses (lines) | -692.65 Mvar |
| Transformer active losses | 12.58 MW |

Results accessible as `pandas.DataFrame`:
- `net.res_bus.vm_pu` -- voltage magnitudes
- `net.res_bus.va_degree` -- voltage angles
- `net.res_bus.p_mw`, `q_mvar` -- nodal P/Q injections
- `net.res_line.p_from_mw`, `q_from_mvar`, `p_to_mw`, `q_to_mvar` -- line P/Q flows
- `net.res_line.pl_mw`, `ql_mvar` -- line losses
- `net.res_trafo` -- transformer results (same column structure)

All outputs are structured DataFrames. Losses are directly available as columns (`pl_mw`, `ql_mvar`).

## Workarounds

None required.

## Timing

- **Wall-clock:** 1.203 s (flat start, solve only)
- **Peak memory:** not measured
- **Solver iterations:** not extracted (pandapower's internal NR does not easily expose iteration count)

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a2_acpf.py`
