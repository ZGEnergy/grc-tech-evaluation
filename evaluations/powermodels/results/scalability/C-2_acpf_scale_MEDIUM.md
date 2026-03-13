---
test_id: C-2
tool: powermodels
dimension: scalability
network: MEDIUM
status: fail
workaround_class: blocking
blocked_by: A-2
wall_clock_seconds: 1261.51
timing_source: measured
peak_memory_mb: 672.0
convergence_residual: null
convergence_iterations: null
loc: 165
solver: "NLsolve (Newton-Raphson)"
protocol_version: "v9"
skill_version: v1
test_hash: c2fc9715
timestamp: 2026-03-11T08:00:00Z
---

# C-2: ACPF Scale MEDIUM

## Result: FAIL

## Approach

This test is a cascaded failure from A-2 MEDIUM (expressiveness dimension). A-2 MEDIUM established by direct measurement that `PowerModels.compute_ac_pf(data)` — which uses NLsolve's Newton-Raphson internally — cannot converge on the ACTIVSg 10,000-bus network within practical time limits.

Two initialization strategies were attempted in A-2 MEDIUM:

1. **Flat start (vm=1.0 pu, va=0.0 rad):** Ran to completion in 581.85s. `termination_status=false` (did not converge).
2. **DC warm-start fallback (angles from DCPF, vm=1.0 pu):** Ran to completion in 621.57s. `termination_status=false` (did not converge).

Total measured wall-clock: **1,261.51s (~21 minutes)**. Both attempts failed.

Timing data is sourced from `evaluations/powermodels/tests/expressiveness/test_a2_acpf_medium.jl` (measured). The C-2 script (`test_c2_acpf_scale_medium.jl`) documents this finding without re-running the 21-minute test.

## Output

| Metric | Value |
|--------|-------|
| Buses | 10,000 |
| Branches | 12,706 |
| Generators | 2,485 |
| Flat start solve time | 581.85s |
| Flat start result | failed (Bool=false) |
| DC warm-start solve time | 621.57s |
| DC warm-start result | failed (Bool=false) |
| **Total wall-clock** | **1,261.51s (~21 min)** |
| Peak memory (process monitor) | ~672 MB |
| NR iterations | not available (diagnostic gap) |
| Convergence residual | not available (diagnostic gap) |
| Converged voltage solution | none |

## Workarounds

No workaround available for the standard `compute_ac_pf` API path at MEDIUM scale.

**What would be needed:** An Ipopt-backed ACPF path using `instantiate_model(data, ACPPowerModel, optimizer)` + `optimize_model!` with fixed (non-optimized) generation dispatch. PowerModels.jl does support this approach via the JuMP interface, but it is not exposed as a simple `compute_ac_pf`-equivalent function. Using `solve_ac_opf` is not equivalent to ACPF — it optimizes generation dispatch rather than computing power flow for a given dispatch.

This limitation is classified as **blocking** because there is no simple parameter change or minor workaround that enables ACPF at MEDIUM scale via the public API.

## Timing

- **Wall-clock:** 1,261.51s (flat start: 581.85s + DC warm-start: 621.57s; both timed out without convergence)
- **Timing source:** measured (from A-2 MEDIUM expressiveness test execution)
- **Peak memory:** ~672 MB (process monitor during run)
- **Solver iterations:** not available (NLsolve does not expose iteration count through PowerModels API)
- **Convergence residual:** not available (NLsolve diagnostic gap — `termination_status` is Bool only)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/scalability/test_c2_acpf_scale_medium.jl`

Full execution script:
**Path:** `evaluations/powermodels/tests/expressiveness/test_a2_acpf_medium.jl`

Key API calls from A-2 MEDIUM:

```julia

data = PowerModels.parse_file("case_ACTIVSg10k.m")
apply_medium_preprocessing!(data)

# Flat start
for (_, bus) in data["bus"]; bus["vm"] = 1.0; bus["va"] = 0.0; end
result = PowerModels.compute_ac_pf(data)
# termination_status = false (did not converge after 581.85s)

# DC warm-start fallback
dc_result = PowerModels.compute_dc_pf(data_dc)
PowerModels.update_data!(data_dc, dc_result["solution"])
result2 = PowerModels.compute_ac_pf(data_dc)
# termination_status = false (did not converge after 621.57s)

```

## Observations

- [solver-issues observation](../observations/solver-issues-scalability-C2_acpf_medium_nlsolve_convergence_failure.md)
- [cascaded-failure observation](../observations/cascaded-failure-scalability-C2_acpf_medium_blocked_by_A2.md)
