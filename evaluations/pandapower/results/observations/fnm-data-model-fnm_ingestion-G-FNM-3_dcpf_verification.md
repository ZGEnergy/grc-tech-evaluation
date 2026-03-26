---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: pandapower
severity: medium
timestamp: 2026-03-24T12:00:00Z
---

# Observation: MATPOWER PPC import path produces localized DCPF angle deviations on FNM

## Finding

pandapower's MATPOWER PPC import path (`from_ppc`) produces a cluster of ~101 buses with
systematic voltage angle deviations of 14-21 degrees in a connected sub-region of the FNM
subtransmission/distribution network (69-138 kV), triggering the hard-fail condition for
extreme branch flow deviation (596.6% > 50% threshold).

## Context

G-FNM-3 loaded the pre-cleaned 27,862-bus FNM main island via `matpowercaseframes.CaseFrames`
+ `from_ppc` (MATPOWER fallback path, since pandapower lacks native CSV ingestion). The DCPF
converges and the aggregate metrics are strong (99.64% buses pass, 99.67% branches pass), but
a localized cluster of outliers in the 69-138 kV sub-network causes the worst-case branch
flow deviation to exceed the hard-fail threshold. The deviations are not correlated with
transformer tap ratios (0% transformer adjacency), ruling out formulation difference.

The bus injection power balance check passes with machine-precision accuracy (max mismatch
8.6e-11 p.u.), confirming the solution is internally consistent. The issue is in data
ingestion fidelity, not solver correctness.

## Implications

The PPC import path flattens transformer-specific data (tap control modes, winding impedance
details) that may affect impedance calculations in the sub-region containing the outlier
buses. This data model limitation also contributes to the ACPF non-convergence observed in
G-FNM-4. Tools that can ingest the full intermediate CSV format (preserving all PSS/E v31
fields) may avoid this issue.
