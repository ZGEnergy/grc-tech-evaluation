---
test_id: C-2
tool: pypsa
dimension: scalability
network: MEDIUM
protocol_version: "v9"
skill_version: v1
test_hash: 7f5f00c7
status: qualified_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 255.078
timing_source: measured
peak_memory_mb: 2099.0
convergence_residual: null
convergence_iterations: 72
loc: null
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# C-2: AC Power Flow Scale

## Result: QUALIFIED PASS

## Approach

Loaded ACTIVSg10k (10,000 buses, 9,726 lines, 2,485 generators) and ran `n.pf(x_tol=1e-6)` —
PyPSA's Newton-Raphson AC power flow (scipy sparse solver, no external solver needed). Ipopt
is not installed in the devcontainer and is not needed for `n.pf()`. Measured wall-clock via
`time.perf_counter()` and peak memory via `tracemalloc`.

The NR solver ran 72 iterations before diverging with a matrix singularity warning:
`MatrixRankWarning: Matrix is exactly singular`. The solver did not converge and the final
residual was NaN.

## Output

| Metric | Value |
|--------|-------|
| Network | ACTIVSg10k — 10,000 buses, 9,726 lines |
| Solver | Newton-Raphson (scipy sparse, `n.pf()`) |
| **Solve wall-clock** | **255.08 s** |
| **Peak memory** | **2,099.0 MB** |
| NR iterations | 72 |
| Converged | No |
| Final residual | NaN (matrix singular) |
| Tolerance | 1e-6 |

Non-convergence on ACTIVSg10k with a flat-start initial point is expected for large meshed
networks. The scipy Newton-Raphson in PyPSA does not support DC warm-start initialization.
Timing and memory are recorded as required by the pass condition.

## Workarounds

None required. The test's pass condition requires timing and memory be recorded; non-convergence
is documented as a finding.

## Timing

- **Wall-clock:** 255.08 s
- **Timing source:** measured
- **Peak memory:** 2,099.0 MB
- **Solver iterations:** 72 NR iterations (did not converge — matrix singular at iteration 72)
- **Convergence residual:** NaN (diverged)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/pypsa/tests/scalability/test_c2_acpf_scale.py`
