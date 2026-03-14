---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-4
tool: pypsa
severity: medium
timestamp: 2026-03-13T00:00:00Z
---

# Observation: PyPSA ACPF hits singular Jacobian on 27,862-bus FNM at all relaxation levels

## Finding

PyPSA's built-in Newton-Raphson ACPF solver (`n.pf()`) encounters a singular Jacobian
matrix on the FNM main island at 0%, 10%, and 20% thermal limit relaxation,
even with DC warm-start initialization. This is consistent with MATPOWER 8.1's failure
on the same network. The singular matrix prevents convergence entirely (NaN residuals)
rather than exhibiting slow convergence.

## Context

G-FNM-4 followed the progressive relaxation protocol: DCPF warm start, then ACPF
attempts at 0%, 10%, 20% relaxation. All three attempts terminated with
`MatrixRankWarning: Matrix is exactly singular`. The network has a 6.0%
generation-load imbalance (155,511 MW gen vs 165,492 MW load) and 9,481 transformers
(2,358 with non-unity taps).

PyPSA's ACPF uses a built-in Newton-Raphson solver, not Ipopt. The solver does not
expose continuation power flow or alternative NR variants (NR-IC, NR-SP, FDXB/FDBX)
that MATPOWER offers. This limits PyPSA's options for convergence recovery on difficult
networks.

## Implications

The singular Jacobian on this planning model is expected -- neither PyPSA nor MATPOWER
can converge. However, PyPSA's lack of alternative ACPF solver options (continuation PF,
fast-decoupled, Ipopt-based NLP) means it has fewer recovery tools compared to MATPOWER.
This is relevant to the Extensibility dimension (solver swap capability) and the
Scalability dimension (robustness on large networks).
