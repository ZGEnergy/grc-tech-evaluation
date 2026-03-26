---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-4
tool: powermodels
severity: medium
timestamp: "2026-03-24T12:30:00Z"
---

# Observation: ACPF Diverges on 27,862-Bus FNM with ~7 GB Memory Consumption

## Finding

PowerModels' `solve_ac_pf` with Ipopt/MUMPS diverges on the FNM 27,862-bus case,
consuming approximately 7 GB of memory. Ipopt's MUMPS linear solver required 4 memory
reallocation attempts (icntl[13] from 1000 to 16000) before continuing to diverge.
The 67,206-variable NLP with 380,065 Jacobian nonzeros is tractable in terms of
problem construction but the solver cannot find a feasible point.

## Context

G-FNM-4 applied DCPF warm start (VM=1.0, VA from DCPF) before attempting ACPF.
The ACPF reference data itself shows divergent values (bus VM up to 379,646 p.u.),
confirming the FNM case is inherently difficult for ACPF convergence even in MATPOWER.
The convergence difficulty is likely related to missing switched shunt modeling,
generator Q-limit handling, and transformer tap optimization that are lost in the
MATPOWER PPC conversion.

## Implications

The memory consumption pattern (~7 GB for MUMPS factorization on a 28k-bus network)
provides a data point for scalability assessment. Memory requirements grow with network
size and MUMPS workspace management becomes a limiting factor. The convergence failure
is informational for this test but indicates that PowerModels requires careful network
preparation for ACPF on utility-scale cases.
