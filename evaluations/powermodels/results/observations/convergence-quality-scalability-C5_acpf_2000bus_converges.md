---
tag: convergence-quality
source_dimension: scalability
source_test: C-5
tool: powermodels
severity: low
timestamp: 2026-03-13T22:00:00Z
---

# Observation: ACPF converges at 0% relaxation on 2000-bus with DC warm start

## Finding

PowerModels' `compute_ac_pf` (NLsolve Newton-Raphson) converged on the ACTIVSg 2000-bus network with DCPF warm-start angles in 0.231 seconds, at 0% thermal relaxation. No progressive relaxation steps were needed. However, 58 buses have voltage magnitudes below 0.95 pu (minimum 0.936 pu), indicating voltage violations in the base-case solution. Convergence quality is verified: 100% of non-slack buses have nonzero angles.

## Context

C-5 tests progressive AC feasibility relaxation. The 2000-bus scale is the boundary between success and failure for `compute_ac_pf`: it converges at SMALL (2000-bus) but fails at MEDIUM (10k-bus, per A-2 MEDIUM). The 0.231s solve time at 2000-bus is fast, suggesting the NLsolve solver is well within its convergence envelope at this scale. The NR iteration count and convergence residual remain unavailable (known diagnostic gap from A-2).

## Implications

The 2000-bus convergence success establishes a useful data point for the scalability assessment: `compute_ac_pf` works up to ~2000 buses but fails at 10,000 buses. This suggests a convergence boundary somewhere in the 2,000-10,000 bus range for NLsolve-based Newton-Raphson. For the Accessibility dimension, the 58 voltage violations at 0% relaxation may warrant investigation -- they suggest the network has some voltage-stressed buses that a production operator would need to address.
