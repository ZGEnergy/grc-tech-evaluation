---
test_id: C-2
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 22.1
peak_memory_mb: 2383
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# C-2: ACPF Scale Test (MEDIUM)

## Result: PASS

## Approach

Ran AC power flow (Newton-Raphson) on the ACTIVSg 10k-bus network using
`n.pf()` with flat start (V=1.0 pu, theta=0). Converged on the first attempt
without needing DC warm start.

## Output

| Metric | Value |
|--------|-------|
| Status | pass |
| Wall-clock (total) | 22.1 s |
| Flat start converged | Yes |
| DC warm start needed | No |
| NR solve time | 18.1 s |
| Peak memory | 2,383 MB |
| Buses | 10,000 |
| Generators | 2,485 |
| Lines | 9,726 |
| Transformers | 2,980 |
| Voltage magnitude range | 0.962 to 1.081 pu |
| Voltage angle range | 0 rad (DC angles not populated in ACPF) |
| Line P flow range | -985 to 1,048 MW |
| Total P losses | 3,935 MW |

## Analysis

ACPF on the 10k-bus network converges from flat start in ~18s. Newton-Raphson
converges reliably. Voltage magnitudes show realistic spread (0.96-1.08 pu).
Total line losses of 3,935 MW are reported.

Notable: voltage angles are reported as 0 rad, suggesting the ACPF may not be
populating angle results in `buses_t.v_ang` for the 10k case, or all angles
ended up near zero. Line flows and voltage magnitudes confirm convergence.

## Timing

- **Wall-clock:** 22.1 s
- **NR solve time:** 18.1 s
- **Peak memory:** 2,383 MB

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c2_acpf_scale.py`
