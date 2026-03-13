#=
Test C-2: ACPF Scale — MEDIUM grade assessment
Dimension: scalability
Network: MEDIUM (ACTIVSg 10000-bus, case_ACTIVSg10k.m)
Pass condition: Wall-clock time, peak memory, and iterations recorded.
Tool: PowerModels.jl v0.21.5
Solver: NLsolve (compute_ac_pf internal) — FAILS at MEDIUM scale

This test is a CASCADED FAILURE from A-2 MEDIUM (expressiveness).
A-2 MEDIUM established that compute_ac_pf cannot converge on 10k-bus networks.
This script documents that finding for the scalability dimension.

Result: FAIL — NLsolve Newton-Raphson does not converge on 10,000-bus ACPF.
        Both flat-start and DC warm-start attempts failed after ~21 minutes total.

Note:
  The standard API `compute_ac_pf` uses NLsolve internally. An alternative
  Ipopt-backed path (instantiate_model + optimize_model! with ACPPowerModel)
  was considered in A-4 but not implemented for pure ACPF — solve_ac_opf uses
  Ipopt but optimizes generation dispatch, not pure ACPF.

Timing data is taken from A-2 MEDIUM measured results:
  - Flat start:       581.85s, termination_status=false (did not converge)
  - DC warm-start:    621.57s, termination_status=false (did not converge)
  - Total wall-clock: 1261.51s (~21 minutes)
  - Peak memory:      ~672 MB
=#

# This script documents the cascaded failure rather than re-running the 21-minute test.
# The full timed execution is in: evaluations/powermodels/tests/expressiveness/test_a2_acpf_medium.jl

println("C-2: ACPF Scale MEDIUM — Cascaded failure from A-2 MEDIUM")
println("")
println("A-2 MEDIUM (expressiveness) established:")
println("  - compute_ac_pf (NLsolve Newton-Raphson) fails on 10,000-bus ACPF")
println("  - Flat start:      581.85s, termination_status=false")
println("  - DC warm-start:   621.57s, termination_status=false")
println("  - Total:           1261.51s (~21 minutes)")
println("  - Peak memory:     ~672 MB")
println("  - NR iterations:   not available (NLsolve diagnostic gap)")
println("  - Residual:        not available (NLsolve diagnostic gap)")
println("")
println("C-2 STATUS: FAIL")
println("  Cascaded failure — blocked by A-2 MEDIUM FAIL")
println("  Root cause: NLsolve not suitable for 10k-bus AC power flow")
println("  An Ipopt-backed path is available but requires AC OPF formulation,")
println("  not a pure ACPF (fixed dispatch) computation.")
