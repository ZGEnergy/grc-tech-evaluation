---
test_id: A-2
tool: pandapower
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.27
peak_memory_mb: null
loc: 139
solver: Newton-Raphson
timestamp: 2026-03-06T00:00:00Z
---

# A-2: Solve ACPF (Newton-Raphson)

## Result: PASS

## Approach

Loaded ACTIVSg10k (~10,000 buses) and solved ACPF using `pp.runpp(net)` with Newton-Raphson. Followed convergence protocol: flat start first, DC warm start fallback if needed.

**Flat start failed** after 100 iterations (expected for a 10k-bus network). DC warm start succeeded.

## Output

| Metric | Value |
|--------|-------|
| Bus count | 10,000 |
| Flat start converged | No (100 iterations) |
| DC warm start converged | Yes |
| DC warm start time | 0.27 s |
| Voltage magnitude range | 0.868 -- 1.081 pu |
| Voltage angle range | -92.41 -- +15.69 deg |
| Total P losses (lines) | 2,446.3 MW |
| Total Q losses (lines) | -82,571.7 Mvar |
| Total P losses (trafos) | 152.4 MW |

Results accessible as `pandas.DataFrame`:
- `net.res_bus[["vm_pu", "va_degree", "p_mw", "q_mvar"]]`
- `net.res_line[["p_from_mw", "q_from_mvar", "p_to_mw", "q_to_mvar", "pl_mw", "ql_mvar"]]`

## Workarounds

None required. DC warm start fallback is per convergence protocol and expected for large networks.

## Timing

- **Wall-clock:** 0.27 s (DC warm start solve only; flat start attempt took 4.93 s)
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pandapower/tests/expressiveness/test_a2_acpf_medium.py`
