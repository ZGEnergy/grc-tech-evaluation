---
tag: convergence-quality
source_dimension: scalability
source_test: C-5
tool: powermodels
severity: low
timestamp: 2026-03-24T16:30:00Z
---

# Observation: ACPF converges at 0% relaxation on 2000-bus with DC warm start

## Finding

PowerModels' `compute_ac_pf` (NLsolve Newton-Raphson) converged on the ACTIVSg 2000-bus network with DCPF warm-start angles in 0.279 seconds, at 0% thermal relaxation. No progressive relaxation steps were needed. However, 58 buses have voltage magnitudes below 0.95 pu (minimum 0.936 pu), indicating voltage violations in the base-case solution. Convergence quality is verified: 100% of non-slack buses have nonzero angles (1999/1999). Convergence evidence quality: binary_convergence_api (Bool status). NR iteration count and residual remain unavailable (known diagnostic gap from A-2).

## Context

C-5 tests progressive AC feasibility relaxation. The 2000-bus scale is the boundary between success and failure for `compute_ac_pf`: it converges at SMALL (2000-bus, 0.279s) but fails at MEDIUM (10k-bus, Ipopt diverges with inf_du > 1e22). The convergence boundary lies somewhere in the 2,000-10,000 bus range for both NLsolve and Ipopt.

## Implications

This data point establishes the ACPF convergence envelope for PowerModels: functional up to ~2000 buses, infeasible at 10,000 buses. The 58 voltage violations at 0% relaxation indicate voltage-stressed buses in the base-case solution. For the scalability assessment, the fast convergence at SMALL (0.279s) versus divergence at MEDIUM is a significant finding about the tool's AC solving capability at scale.
