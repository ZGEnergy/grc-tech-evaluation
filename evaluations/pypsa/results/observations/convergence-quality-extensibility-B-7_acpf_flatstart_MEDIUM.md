---
tag: convergence-quality
source_dimension: extensibility
source_test: B-7
tool: pypsa
severity: medium
timestamp: 2026-03-11T00:00:00Z
---

# Observation: AC PF non-convergence on 10k-bus network with flat-start initialization

## Finding

`n.pf()` fails to converge on ACTIVSg10k (10,000-bus network) when initialized from a flat start (all voltages = 1.0 pu, all angles = 0). The Newton-Raphson solver iterated 65 times and produced NaN residuals (MatrixRankWarning on singular Jacobian row). Final voltage magnitudes ranged 0.9616–1.0814 pu with 62 buses above 1.05 pu.

## Context

Discovered during B-7 MEDIUM (AC feasibility extension). The DC OPF dispatch was applied to a fresh network via `generators_t.p_set` as in test A-4, then `n.pf()` was called. The AC PF ran (not a silent failure) and iterated extensively, moving voltages from flat start to near-nominal values but did not reach the convergence tolerance.

Key detail: PyPSA's `n.pf()` on the full 10,000-bus network has no built-in warm-start from DC voltage angles. The DC OPF result provides P dispatch but not voltage initialization (V, δ). This is a workflow design gap, not a PyPSA API limitation — a warm-start from approximate DC angles and reactive power estimates would likely achieve convergence.

## Implications

For the Extensibility dimension (B-7), this is a qualified pass: the API workflow (DC OPF → AC PF via `p_set` injection) is fully functional, but AC convergence at 10k scale with flat start is unreliable. Practitioners implementing AC feasibility workflows should:
1. Initialize voltages from DC angle results before calling `n.pf()`
2. Pre-condition reactive power dispatch using generator Q limits

The Scalability dimension (C-tests) should note that AC PF convergence degrades with network size without a proper warm-start strategy. This is expected behavior for Newton-Raphson methods and is not specific to PyPSA.
