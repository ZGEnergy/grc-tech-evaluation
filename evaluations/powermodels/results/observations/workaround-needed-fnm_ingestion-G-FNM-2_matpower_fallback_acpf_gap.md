---
tag: workaround-needed
source_dimension: fnm_ingestion
source_test: G-FNM-2
tool: powermodels
severity: medium
timestamp: "2026-03-13T23:15:00Z"
---

# Observation: MATPOWER fallback workaround from G-FNM-1 causes systemic ACPF field loss

## Finding

The MATPOWER fallback workaround used in G-FNM-1 (blocking-class) propagates into G-FNM-2
as a systemic data model limitation: 218 of 237 ACPF-critical fields and 76 of 87
Informational fields are absent from the PowerModels data model. This is not a PowerModels
limitation per se but a consequence of the MATPOWER PPC format being the only viable
ingestion path.

## Context

G-FNM-2 passes its primary pass condition (19/19 DCPF-critical fields present) because the
MATPOWER PPC format preserves all fields needed for DC power flow. However, the field
coverage audit reveals that ACPF-critical coverage is only 8.0%. Key absent capabilities
include ZIP load models, generator remote voltage regulation topology, transformer tap
control parameters, HVDC line data, FACTS devices, and switched shunt discrete steps.

## Implications

For Extensibility assessment, if a user needed to extend PowerModels to handle the full
FNM with ACPF fidelity, they would need to either (a) fix the PSS/E v31 parser to handle
the FNM's header format, or (b) write a custom CSV-to-PowerModels-JSON converter covering
all 17 intermediate schema tables. Option (b) is feasible but substantial, requiring
mapping of approximately 350 fields across 17 tables to PowerModels' internal dictionary
schema. This is a significant integration effort that other tools (e.g., those with native
PSS/E v31 or CSV support) do not require.
