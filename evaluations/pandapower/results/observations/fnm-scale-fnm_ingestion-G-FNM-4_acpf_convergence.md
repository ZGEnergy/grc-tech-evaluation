---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-4
tool: pandapower
severity: high
timestamp: 2026-03-13T12:00:00Z
---

# Observation: ACPF infeasible on 27,862-bus FNM via MATPOWER import path

## Finding

pandapower's Newton-Raphson ACPF solver fails to converge on the
27,862-bus FNM main island network at all relaxation levels (0%, 10%,
20%). Five different algorithms were attempted (nr, iwamoto_nr, fdbx,
fdxb, gs); none converged.

## Context

G-FNM-4 loads the pre-cleaned FNM main island MATPOWER case via
`matpowercaseframes` + `from_ppc` and attempts ACPF with DCPF
warm-start. The DCPF converges successfully but the ACPF diverges
regardless of algorithm choice, tolerance relaxation, or thermal limit
relaxation. The Iwamoto-NR algorithm showed step-length multipliers
decaying to 1e-25, confirming numerical ill-conditioning.

Contributing factors include: (1) the MATPOWER PPC import path loses
transformer-specific AC data (tap control modes, winding impedance
details, switched shunt discrete steps), (2) the localized cluster of
~101 buses with 14-21 degree systematic DCPF deviations identified in
G-FNM-3 likely creates Jacobian ill-conditioning, and (3) pandapower
uses its internal NR implementation (not Ipopt) for ACPF, which may
have less robust convergence on ill-conditioned large-scale networks.

## Implications

This finding establishes that pandapower cannot solve ACPF on the LARGE
(FNM) network via the MATPOWER import path. For the scalability
dimension, this means AC power flow scalability cannot be assessed at
the LARGE tier for pandapower. The limitation is primarily an ingestion
fidelity issue (MATPOWER format loses AC-critical data) rather than a
solver weakness, since the DCPF solves successfully on the same network.
