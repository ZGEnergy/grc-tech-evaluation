---
tag: solver-issues
source_dimension: scalability
source_test: C-5
tool: pypsa
severity: low
timestamp: 2026-03-14T01:35:00Z
---

# Observation: PyPSA NR solver converges robustly on SMALL and MEDIUM AC networks

## Finding

PyPSA's internal Newton-Raphson AC power flow solver converges on both
ACTIVSg2000 (2,000 buses) and ACTIVSg10k (10,000 buses) at all relaxation
levels (0%, 10%, 20%) with DC warm start, requiring only 4--5 iterations.

## Context

C-5 tests progressive AC feasibility relaxation. PyPSA's `n.pf()` uses an
internal scipy-based Newton-Raphson solver, not Ipopt. The solver converges
in 4 iterations on SMALL and 5 iterations on MEDIUM, with residuals in the
1e-9 range (well below the 1e-6 tolerance). No relaxation was needed on
either network. Peak memory scaled from 84 MB (SMALL) to 2,099 MB (MEDIUM).

## Implications

This is a positive finding for PyPSA's AC PF scalability. The internal NR
solver handles 10,000-bus networks well. However, for AC *OPF* (optimization,
not just power flow), PyPSA would need Ipopt or another NLP solver, which
is a different capability. The robust NR convergence here does not imply
AC OPF would also converge.
