---
test_id: C-2
tool: gridcal
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 12.70
peak_memory_mb: 91.12
loc: 55
solver: "GridCal built-in Newton-Raphson"
timestamp: 2026-03-06T04:00:00Z
---

# C-2: ACPF Scale (Grade: MEDIUM)

## Result: PASS

## Network

ACTIVSg10k -- 10,000 buses, 12,706 branches, 2,485 generators.

## Approach

Newton-Raphson with convergence protocol (flat start first, DC warm start fallback, auto-retry fallback). Converged on first attempt (flat start).

## Output

| Metric | Value |
|--------|-------|
| Converged | Yes (attempt 1, flat start) |
| Convergence error | 2.73e-07 |
| Solve time | 12.70s |
| Peak memory (solve) | 91.12 MB |
| File load time | 11.10s |
| Vm range | 0.9572 to 1.0890 pu |
| Va range | -41.01 to 66.73 deg |
| P flow range (MW) | -1720.65 to 2774.92 |
| Total P losses (MW) | 2585.73 |
| Losses nonzero | Yes |

## Scaling

NR converges on 10k-bus network in 12.7s with flat start (no warm-start needed). Convergence protocol was not necessary -- NR converged on the first attempt with error 2.73e-07 (well within 1e-6 tolerance).

## Workarounds

None required (convergence protocol available but not needed).

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c2_acpf_scale.py`
