---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-2
tool: pandapower
severity: medium
timestamp: 2026-03-14T04:00:00Z
---

# Observation: ACPF-critical field coverage limited by PPC import path

## Finding

pandapower achieves 100% DCPF-critical field coverage but only 55.8% ACPF-critical
coverage (29/52 fields) when ingesting the FNM via the MATPOWER/PYPOWER PPC import
path. The missing ACPF-critical fields include area interchange controls, switched
shunt discrete step parameters, remote regulation bus assignments, and asymmetric
line shunt conductances.

## Context

G-FNM-2 audited pandapower's data model against the field-criticality-matrix (v10)
after importing the 30,307-bus FNM via `scipy.io.loadmat` + `from_ppc`. The PPC
format is a lossy intermediate: it flattens transformer I/O codes into impedance
values, aggregates per-bus shunts, and drops area interchange parameters entirely.

## Implications

The 55.8% ACPF-critical coverage means G-FNM-4 (ACPF convergence) may face
additional challenges beyond solver limitations. Missing switched shunt control
parameters and area interchange data could affect voltage profile accuracy. This
is a data model fidelity finding relevant to the expressiveness and scalability
dimensions when evaluating pandapower's suitability for full ACPF on the FNM.
