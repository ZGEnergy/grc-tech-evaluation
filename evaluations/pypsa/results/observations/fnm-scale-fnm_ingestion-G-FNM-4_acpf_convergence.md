---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-4
tool: pypsa
severity: medium
timestamp: 2026-03-24T00:00:00Z
---

# Observation: PyPSA ACPF hits SuperLU factorization failure on ~28,000-bus FNM at all relaxation levels

## Finding

PyPSA's built-in Newton-Raphson ACPF solver (`n.pf()`) encounters a SuperLU sparse
matrix factorization failure on the FNM main island at 0%, 10%, and 20% thermal limit
relaxation, even with DC warm-start initialization (mean angle 65.6 degrees, max abs
536.9 degrees). This is consistent with MATPOWER 8.1's failure on the same network.
[solver-specific: SuperLU factorization failure on ill-conditioned admittance matrix]

## Context

G-FNM-4 used the shared `matpower_loader.load_pypsa()` with the branch status patch
(deactivating 74 inactive branches) and solved DCPF for warm start (15.1s). All three
ACPF attempts failed with `RuntimeError: failed to factorize matrix` (SuperLU). The
network has a 6.0% generation-load imbalance and structural topology issues that
prevent AC feasibility at full load.

PyPSA's ACPF uses a built-in Newton-Raphson solver, not Ipopt. The solver does not
expose continuation power flow or alternative NR variants (NR-IC, NR-SP, FDXB/FDBX)
that MATPOWER offers. This limits PyPSA's options for convergence recovery on difficult
networks.

## Implications

The factorization failure on this planning model is expected -- neither PyPSA nor MATPOWER
can converge. However, PyPSA's lack of alternative ACPF solver options (continuation PF,
fast-decoupled, Ipopt-based NLP) means it has fewer recovery tools compared to MATPOWER.
This is relevant to the Extensibility dimension (solver swap capability) and the
Scalability dimension (robustness on large networks).
