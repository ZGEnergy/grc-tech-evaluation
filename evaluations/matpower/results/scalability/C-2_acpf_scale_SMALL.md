---
test_id: C-2
tool: matpower
dimension: scalability
network: SMALL
protocol_version: v10
skill_version: v1
test_hash: c3429117
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.165
timing_source: measured
peak_memory_mb: 1.8
convergence_residual: 7.358e-12
convergence_iterations: 5
loc: 168
solver: NR
timestamp: 2026-03-14T00:00:00Z
---

# C-2: ACPF on SMALL — wall-clock time, peak memory, iterations

## Result: PASS

## Approach

Ran `runpf(mpc, mpopt)` on ACTIVSg 2000-bus network using Newton-Raphson (NR) with
flat start (VM=1.0 pu, VA=0.0 deg on all buses) per convergence protocol. Tolerance
set to 1e-8. No DC warm start or tolerance relaxation was needed.

## Output

| Metric | Value |
|--------|-------|
| Buses | 2000 |
| Branches | 3206 |
| Generators | 544 |
| Solver | Newton-Raphson (built-in) |
| Wall clock | 0.165 s |
| Peak memory (VmHWM) | 1.8 MB |
| NR iterations | 5 |
| Convergence residual | 7.358e-12 |
| DC warm start needed | No |
| Total generation | 68,740.87 MW |
| Total load | 67,109.21 MW |
| Total P losses | 1,631.66 MW (2.37%) |
| Total Q losses | 10,367.86 MVAr |
| VM range | [0.9723, 1.0400] pu |
| VA range | [-73.95, 0.00] deg |
| VM differs from flat start | 95.1% of buses |

### Convergence Quality

The Newton-Raphson solver converged from flat start in 5 iterations with a final
residual of 7.358e-12, well below the 1e-8 tolerance. The convergence trajectory
shows rapid progress:

```
it    max residual        max dx
 0    5.495e+01
 1    3.904e+00        7.722e-01
 2    4.430e+00        7.673e-01
 3    7.461e-02        4.512e-02
 4    3.196e-05        1.044e-03
 5    7.358e-12        5.255e-07
```

95.1% of buses have VM differing from the flat-start default of 1.0 pu, meeting the
>95% threshold. The remaining ~5% of buses have VM at exactly 1.04 pu, which is the
voltage setpoint of their connected generators (PV bus behavior, not flat-start defaults).

## Workarounds

None required. Flat start converged without any fallback needed.

## Timing

- **Wall-clock:** 0.165 s
- **Timing source:** measured
- **Peak memory:** 1.8 MB
- **Solver iterations:** 5 (NR)
- **Convergence residual:** 7.358e-12
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/matpower/tests/scalability/test_c2_acpf_scale_SMALL.m`
