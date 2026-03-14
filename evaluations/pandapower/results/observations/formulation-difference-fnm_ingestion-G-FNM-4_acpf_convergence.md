---
tag: formulation-difference
source_dimension: fnm_ingestion
source_test: G-FNM-4
tool: pandapower
severity: medium
timestamp: 2026-03-13T12:00:00Z
---

# Observation: pandapower uses internal NR for ACPF, not Ipopt

## Finding

pandapower's `runpp()` uses its own internal Newton-Raphson
implementation (inherited from PYPOWER) for AC power flow, not an
external NLP solver like Ipopt. The G-FNM-4 methodology specifies
Ipopt as the solver, but pandapower has no Ipopt integration for
power flow — only for OPF via the PandaModels.jl Julia bridge.

## Context

This formulation difference means pandapower's ACPF convergence
behavior cannot be directly compared with tools that use Ipopt for
ACPF. pandapower offers six internal algorithms (nr, iwamoto_nr,
fdbx, fdxb, gs, bfsw) but none achieved convergence on the FNM.
Ipopt's interior-point method with MUMPS linear solver may have
different convergence properties on ill-conditioned large-scale
networks.

## Implications

When comparing ACPF convergence results across tools in the synthesis
phase, pandapower's infeasible result should be contextualized by its
use of internal NR rather than Ipopt. A tool using Ipopt may converge
where pandapower's NR does not (or vice versa), and this reflects
solver algorithm differences rather than data model or formulation
differences.
