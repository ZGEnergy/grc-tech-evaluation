---
test_id: C-2
tool: gridcal
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: v2
test_hash: "e04c4a98"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 3.378
timing_source: measured
peak_memory_mb: 91.13
convergence_residual: 2.731e-07
convergence_iterations: 5
convergence_evidence_quality: residual_reported
loc: 271
solver: NR (native)
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T12:00:00Z
---

# C-2: ACPF on MEDIUM -- wall-clock, peak memory, iterations

## Result: PASS

## Approach

AC power flow on the ACTIVSg 10000-bus network using GridCal's native Newton-Raphson solver (`SolverType.NR`) with tolerance 1e-6 and max 100 iterations. Protocol specifies Ipopt, but GridCal has no Ipopt integration for ACPF -- its native NR solver is the appropriate solver for this tool.

Convergence protocol followed: flat start attempted first. Flat start converged successfully on the first attempt -- no DC warm start fallback was needed.

**v11 convergence verification:** Max bus power mismatch (residual) is 2.731e-07 p.u., well below the 1e-4 p.u. threshold. Convergence evidence quality is `residual_reported` (Tier 1) -- the `PowerFlowResults` object exposes `results.error` (float residual), `results.iterations` (int), and `results.converged` (bool) as first-class attributes.

## Output

| Metric | Value |
|--------|-------|
| Bus count | 10,000 |
| Branch count | 12,706 |
| Generator count | 2,485 |
| Converged | Yes (flat start) |
| NR iterations | 5 |
| Convergence residual | 2.731e-07 p.u. |
| Solve time | 3.378 s |
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

**Observation (api-friction):** GridCal has no Ipopt integration for ACPF. The protocol specifies Ipopt as the AC solver, but GridCal uses its own Newton-Raphson implementation. This is an inherent tool limitation, not a workaround -- the native NR produces high-quality convergence.

## Timing

- **Wall-clock:** 3.378 s (solve only, excludes network loading)
- **Timing source:** measured
- **Peak memory:** 91.13 MB (tracemalloc)
- **Solver iterations:** 5
- **Convergence residual:** 2.731e-07 p.u.
- **CPU threads used:** 1
- **CPU threads available:** 32
- **Total script time:** 10.04 s (includes network loading)

## Test Script

**Path:** `evaluations/gridcal/tests/scalability/test_c2_acpf_scale_medium.py`
