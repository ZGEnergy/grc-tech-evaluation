---
test_id: C-2
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: 66.99
peak_memory_mb: null
loc: 127
solver: NLsolve
timestamp: 2026-03-07T00:00:00Z
---

# C-2: ACPF Scalability on MEDIUM (ACTIVSg 10000-bus)

## Result: FAIL

## Metrics

| Metric | Value |
|--------|-------|
| Attempt 1 (flat start) | 33.88s, did not converge |
| Attempt 2 (DC warm start) | 33.12s, did not converge |
| Total wall-clock | 66.99s |
| Peak memory | Not measured (failed before) |
| Iterations | Not exposed by PowerModels API |

## Analysis

PowerModels' `compute_ac_pf` uses NLsolve.jl (trust region Newton-Raphson). The solver failed to converge on the ACTIVSg 10,000-bus network under both flat start and DC warm start conditions.

The ~33s per attempt suggests the solver is running its full iteration budget before giving up. PowerModels does not expose NLsolve configuration (iteration limit, tolerance, algorithm variant) through the `compute_ac_pf` API, limiting the ability to tune convergence.

This is a scalability limitation: the same `compute_ac_pf` function converges on TINY (39-bus) and SMALL (2000-bus) networks but fails on MEDIUM (10,000-bus). The Newton-Raphson implementation may need:
- More iterations than the default limit
- Better initial point construction
- A decoupled or accelerated NR variant

## Methodology

- JIT warm-up: solved case39 ACPF before timing
- Convergence protocol: flat start first, DC warm start fallback
- Timing: `time()` calls around each attempt

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a2_acpf_medium.jl`
Batch runner: `evaluations/powermodels/tests/test_medium_all.jl`
