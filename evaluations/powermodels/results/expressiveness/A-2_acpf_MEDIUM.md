---
test_id: A-2
tool: powermodels
dimension: expressiveness
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

# A-2: Solve ACPF on MEDIUM (ACTIVSg 10000-bus)

## Result: FAIL

## Approach

Followed convergence protocol: flat start first, then DC warm start fallback.

1. `PowerModels.parse_file("case_ACTIVSg10k.m")`
2. **Attempt 1 (flat start):** `PowerModels.compute_ac_pf(data)` -- converged: false, time: 33.88s
3. **Attempt 2 (DC warm start):** Solved DCPF first with `compute_dc_pf`, merged angles into data via `update_data!`, then `compute_ac_pf(data)` -- converged: false, time: 33.12s

Both attempts returned `termination_status = false`, indicating Newton-Raphson (NLsolve) failed to converge within its default iteration limit.

## Analysis

The ACTIVSg 10,000-bus case is a challenging network for Newton-Raphson power flow. PowerModels' `compute_ac_pf` uses NLsolve.jl with default settings (trust region method). The network has:

- 10,000 buses with varied voltage levels
- 12,706 branches (many with zero angmin/angmax needing default widening)
- 2,485 generators

The DC warm start did not help because it only initializes voltage angles, not magnitudes. PowerModels does not expose NLsolve iteration count or convergence diagnostics through its API, making it difficult to diagnose whether the solver is diverging, oscillating, or simply needs more iterations.

Note: An AC OPF formulation (using Ipopt) would likely find a feasible operating point, but `compute_ac_pf` specifically tests the Newton-Raphson power flow solver.

## Workarounds

None attempted beyond the DC warm start. Potential approaches that were not available:
- Adjusting NLsolve tolerance or iteration limits (not exposed by `compute_ac_pf` API)
- Using a different NR algorithm variant (e.g., decoupled fast NR)
- Voltage magnitude initialization from the case file (already present but insufficient)

## Timing

- Wall-clock: 66.99s total (both attempts)
- Attempt 1 (flat start): 33.88s
- Attempt 2 (DC warm start): 33.12s
- Peak memory: not measured (failed before measurement)

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a2_acpf_medium.jl`
Batch runner: `evaluations/powermodels/tests/test_medium_all.jl`
