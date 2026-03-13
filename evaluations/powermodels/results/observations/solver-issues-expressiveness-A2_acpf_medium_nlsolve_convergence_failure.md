---
tag: solver-issues
source_dimension: expressiveness
source_test: A-2
network: MEDIUM
tool: powermodels
severity: high
timestamp: 2026-03-11T05:15:00Z
---

# Solver Issue: compute_ac_pf NLsolve fails to converge on ACTIVSg 10k-bus network

## Observation

`PowerModels.compute_ac_pf(data)` uses NLsolve's Newton-Raphson implementation internally and fails to converge on the ACTIVSg 10000-bus network under both flat start and DC warm-start initialization strategies.

- **Flat start (vm=1.0, va=0.0):** 581.85s, `termination_status=false`
- **DC warm-start (DC angles, vm=1.0):** 621.57s, `termination_status=false`
- **Total elapsed:** 1261.51s (~21 minutes)
- **Peak memory during run:** ~672 MB

Neither attempt produced a converged voltage solution. The `termination_status` returned by `compute_ac_pf` is a Bool (`true`/`false`) — there is no iteration count, residual, or diagnostic message to understand how close the solver got or why it diverged.

## Impact

A-2 (ACPF MEDIUM) fails. The ACPF capability at MEDIUM scale is not functional via the standard `compute_ac_pf` API.

**Root cause:** NLsolve's Newton-Raphson is not well-suited for large-scale AC power flow. The NLsolve approach lacks the specialized convergence features (predictor-corrector, adaptive damping, sparsity optimizations) used in production ACPF solvers. It works for TINY (39-bus) but fails at MEDIUM (10,000-bus) scale.

**What would work:** The JuMP-based path using Ipopt (`solve_ac_opf` or `instantiate_model(ACPPowerModel)` + `optimize_model!` with Ipopt) would likely converge on this network, as Ipopt uses interior-point methods with MUMPS sparse linear algebra — well-suited for large NLP problems. However, `solve_ac_opf` is AC OPF (optimizes generation), not pure ACPF (given dispatch). There is no direct Ipopt-backed ACPF in the standard PowerModels API.

## Implications

This finding caps the expressiveness grade for ACPF at MEDIUM scale to fail. The tool cannot solve AC power flow on operationally realistic transmission networks via its primary ACPF API function. This is a significant limitation for energy systems practitioners who need ACPF for voltage security and reactive power analysis on full-scale models.

## Version

PowerModels.jl v0.21.5, Julia 1.10, NLsolve 4.5 (dependency).
