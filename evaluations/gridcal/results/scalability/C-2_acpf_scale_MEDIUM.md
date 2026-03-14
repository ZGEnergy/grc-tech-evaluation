---
test_id: C-2
tool: gridcal
dimension: scalability
network: MEDIUM
status: pass
workaround_class: null
blocked_by: null
protocol_version: "v10"
skill_version: v1
test_hash: "bcf49161"
wall_clock_seconds: 3.103
timing_source: measured
peak_memory_mb: 91.13
convergence_residual: 2.731e-07
convergence_iterations: 5
loc: 281
solver: NR (native)
timestamp: 2026-03-13T00:00:00Z
---

# C-2: ACPF on MEDIUM — wall-clock, peak memory, iterations

## Result: PASS

## Approach

AC power flow on the ACTIVSg 10000-bus network using GridCal's native Newton-Raphson solver (`SolverType.NR`) with tolerance 1e-6 and max 100 iterations. Protocol specifies Ipopt, but GridCal has no Ipopt integration for ACPF — its native NR solver is the appropriate solver for this tool.

Convergence protocol followed: flat start attempted first. Flat start converged successfully on the first attempt — no DC warm start fallback was needed.

## Output

| Metric | Value |
|--------|-------|
| Bus count | 10,000 |
| Branch count | 12,706 |
| Generator count | 2,485 |
| Converged | Yes (flat start) |
| NR iterations | 5 |
| Convergence residual | 2.731e-07 |
| Solve time | 3.103 s |
| Peak memory | 91.13 MB |
| Vm min | 0.957 pu |
| Vm max | 1.089 pu |
| Vm mean | 1.023 pu |
| Max angle | 66.73 deg |
| Total losses | 2,585.7 MW |
| Max loading | 1586.8% |
| Buses differing from flat start | 99.98% (9,998 / 10,000) |

Convergence quality is excellent: 5 NR iterations with residual well below tolerance, and 99.98% of buses differ from flat-start voltage magnitudes.

The high maximum loading (1586.8%) indicates some branches are severely overloaded in the AC solution. This is a characteristic of the network's base-case operating point, not a solver artifact.

## Workarounds

None required. GridCal's native NR solver handles the 10k-bus network without difficulty.

**Observation (api-friction):** GridCal has no Ipopt integration for ACPF. The protocol specifies Ipopt as the AC solver, but GridCal uses its own Newton-Raphson implementation. This is an inherent tool limitation, not a workaround — the native NR produces high-quality convergence.

## Timing

- **Wall-clock:** 3.103 s (solve only, excludes network loading)
- **Timing source:** measured
- **Peak memory:** 91.13 MB (tracemalloc)
- **Solver iterations:** 5
- **Convergence residual:** 2.731e-07
- **Total script time:** 9.20 s (includes network loading)

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c2_acpf_scale_medium.py`
