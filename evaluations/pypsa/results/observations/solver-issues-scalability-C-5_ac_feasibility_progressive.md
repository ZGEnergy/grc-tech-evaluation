---
tag: solver-issues
source_dimension: scalability
source_test: C-5
tool: pypsa
severity: low
timestamp: 2026-03-24T22:00:00Z
---

# Observation: PyPSA NR solver converges robustly on SMALL AC network

## Finding

PyPSA's internal Newton-Raphson AC power flow solver converges on ACTIVSg2000
(2,000 buses) at all relaxation levels (0%, 10%, 20%) with DC warm start,
requiring only 4 iterations with residuals in the 1e-9 range.

## Context

C-5 tests progressive AC feasibility relaxation on SMALL. PyPSA's `n.pf()` uses
an internal scipy-based Newton-Raphson solver, not Ipopt. The solver converges
in 4 iterations at 0% relaxation (no relaxation needed), with a residual of
5.13e-09 (well below the 1e-6 tolerance). Peak memory: 84 MB. Wall-clock: 4.1s
per ACPF attempt plus 1.0s for DCPF warm start.

93.95% of buses have non-flat voltages (1,879 of 2,000), confirming a genuine
converged solution. The remaining 121 buses at exactly 1.0 pu are PV generator
buses holding their voltage setpoints.

## Implications

This is a positive finding for PyPSA's AC PF scalability. The internal NR
solver handles 2,000-bus networks comfortably without relaxation. However, for
AC *OPF* (optimization, not just power flow), PyPSA would need Ipopt or another
NLP solver, which is a different capability.
