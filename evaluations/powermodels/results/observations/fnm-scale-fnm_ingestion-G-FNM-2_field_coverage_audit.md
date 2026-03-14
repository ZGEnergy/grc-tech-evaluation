---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-2
tool: powermodels
severity: medium
timestamp: "2026-03-13T23:15:00Z"
---

# Observation: MATPOWER fallback carries 27,862 buses and 32,606 branches successfully

## Finding

PowerModels successfully loaded and indexed the 27,862-bus, 32,606-branch MATPOWER fallback
of the regional FNM in approximately 3 seconds. The data model correctly represents all core
network elements (buses, loads, generators, branches including transformer-as-branch, and
fixed shunts) at this scale.

## Context

G-FNM-2 audited field coverage on the MATPOWER fallback case. While the primary finding
concerns field-level coverage (100% DCPF, 8% ACPF), the scale dimension is also relevant:
PowerModels' dictionary-based internal representation handled the large network without
issue. The 3,110 fixed shunts (converted from MATPOWER's shunt data) are also present and
correctly represented with bus, conductance, susceptance, and status fields.

## Implications

For scalability assessment, PowerModels can handle FNM-scale networks for DCPF and DCOPF
analysis. The 3-second parse time is acceptable for production workflows. The scale
limitation is in field coverage (ACPF fidelity), not in the tool's ability to handle
large bus counts.
