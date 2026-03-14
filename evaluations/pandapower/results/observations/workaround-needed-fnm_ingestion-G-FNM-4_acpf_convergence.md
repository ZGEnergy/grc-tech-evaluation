---
tag: workaround-needed
source_dimension: fnm_ingestion
source_test: G-FNM-4
tool: pandapower
severity: medium
timestamp: 2026-03-13T12:00:00Z
---

# Observation: MATPOWER fallback path loses AC-critical transformer data

## Finding

The MATPOWER PPC import path used for FNM ingestion flattens
transformer-specific AC data (tap control modes, winding impedance
details, switched shunt discrete steps) into the generic branch
matrix format. This data loss likely contributes to ACPF
non-convergence on the FNM.

## Context

pandapower has no native CSV import, so the FNM must be loaded via
the MATPOWER `.m` / `.mat` fallback path. The PPC format represents
all branches (lines and transformers) in a single matrix with limited
columns, discarding PSS/E fields such as transformer tap control mode
(COD1), voltage band (VMA1/VMI1), and impedance correction tables.
Additionally, switched shunts lose their discrete step definitions
and are reduced to a single Bs value.

For DCPF (G-FNM-3), this data loss is largely inconsequential because
DCPF does not use resistance, reactive power, or voltage magnitude
data. For ACPF (G-FNM-4), the lost data is critical for reactive
power balance, voltage regulation, and switched shunt step control —
all necessary for NR convergence on large networks.

## Implications

This workaround limitation means pandapower's ACPF performance on
the FNM cannot be evaluated independently of the ingestion path. A
native CSV or PSS/E import path (if one existed) might produce
different convergence results. The workaround is classified as
stable (public APIs used throughout) but with the caveat that it
systematically degrades AC model fidelity.
