---
tag: convergence-quality
dimension: expressiveness
test_id: A-2
network: MEDIUM
timestamp: 2026-03-11T00:00:00Z
---

# Observation: AC Power Flow Non-Convergence on ACTIVSg10k

## Finding

PyPSA's Newton-Raphson ACPF solver fails to converge on the ACTIVSg10k (10,000-bus) network from both flat start and DC warm start. The `scipy.sparse.linalg.spsolve` call inside PyPSA's NR loop raises `MatrixRankWarning: Matrix is exactly singular` at some NR iteration, halting progress after 72 iterations with NaN residual.

## Evidence

- **Flat start:** 72 iterations, residual = NaN, `MatrixRankWarning: Matrix is exactly singular`
- **DC warm start:** 72 iterations, residual = NaN, same warning
- PyPSA consistency checker flagged: transformer T18 has zero resistance (`r=0`), which can cause singularity in the admittance matrix
- Base-case DCPF shows max voltage angle of 104.9° — unusually large for NR initialization
- Only 17.1% of buses show non-flat voltages after the failed flat-start attempt (vs >95% expected)

## Root Cause Assessment

Two likely contributing factors:

1. **Zero-resistance transformer:** T18 has `r=0` which PyPSA flags as potentially breaking the linear load flow. In the full NR Jacobian, a branch with zero resistance and nonzero reactance can create a rank deficiency in certain configurations.

2. **Large voltage angle range:** DCPF angles up to 104.9° suggest the operating point is far from flat start, making the Newton-Raphson iteration path longer and more susceptible to ill-conditioning.

The ACTIVSg10k network is a synthetic dataset not all tools can solve in ACPF; MATPOWER (Octave) would need to be checked as a reference to determine if the network is genuinely ill-conditioned or if this is a PyPSA-specific limitation.

## Implications

- A-2 MEDIUM: FAIL (both flat start and DC warm start fail)
- A-4 MEDIUM: QUALIFIED PASS (same-model-context expressiveness test passes; AC PF convergence is the limitation)
- The DCPF and DCOPF work correctly at MEDIUM scale — this is specifically an ACPF solver issue
- Grade cap: per convergence protocol, MEDIUM non-convergence "may cap grade" but does not automatically fail the criterion
