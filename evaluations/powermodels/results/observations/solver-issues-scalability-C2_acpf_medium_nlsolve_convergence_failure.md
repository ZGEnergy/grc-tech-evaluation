---
tag: solver-issues
source_dimension: scalability
source_test: C-2
network: MEDIUM
tool: powermodels
severity: high
timestamp: 2026-03-11T08:00:00Z
---

# Solver Issue: compute_ac_pf NLsolve fails to converge on ACTIVSg 10k-bus network (scalability dimension)

## Observation

`PowerModels.compute_ac_pf(data)` uses NLsolve's Newton-Raphson implementation internally and fails to converge on the ACTIVSg 10,000-bus network under both flat-start and DC warm-start initialization strategies.

- **Flat start (vm=1.0, va=0.0):** 581.85s, `termination_status=false`
- **DC warm-start (DC angles, vm=1.0):** 621.57s, `termination_status=false`
- **Total elapsed:** 1,261.51s (~21 minutes)
- **Peak memory during run:** ~672 MB

Neither attempt produced a converged voltage solution. The `termination_status` returned by `compute_ac_pf` is a Bool (`true`/`false`) — there is no iteration count, residual, or diagnostic message to understand how close the solver got or why it diverged.

## Impact

C-2 (ACPF Scale MEDIUM) fails as a direct consequence of this solver failure. ACPF capability at MEDIUM scale is not functional via the standard `compute_ac_pf` API.

**Root cause:** NLsolve's Newton-Raphson is not well-suited for large-scale AC power flow. It lacks the specialized convergence features (predictor-corrector, adaptive damping, sparsity optimizations) used in production ACPF solvers. The approach works for TINY (39-bus) but fails at MEDIUM (10,000-bus) scale.

**What would work:** The JuMP-based path using Ipopt (`instantiate_model(data, ACPPowerModel, optimizer)` + `optimize_model!` with Ipopt) would likely converge on this network, as Ipopt uses interior-point methods with MUMPS sparse linear algebra — well-suited for large NLP problems. However, this requires using `solve_ac_opf` (which optimizes generation dispatch) rather than a pure ACPF computation.

## Implications

This finding confirms that C-2 ACPF Scale MEDIUM fails. PowerModels.jl cannot solve AC power flow on operationally realistic transmission networks via its primary `compute_ac_pf` API function. The scalability grade for ACPF is capped at fail.

The limitation reinforces the A-2 MEDIUM finding from the expressiveness dimension.

## Version

PowerModels.jl v0.21.5, Julia 1.10, NLsolve 4.5 (dependency).
