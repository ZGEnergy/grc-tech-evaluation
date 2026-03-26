---
tag: workaround-needed
source_dimension: fnm_ingestion
source_test: G-FNM-3
tool: pandapower
severity: low
timestamp: 2026-03-24T12:00:00Z
---

# Observation: MATPOWER fallback required for FNM ingestion in pandapower

## Finding

pandapower has no native capability to ingest the intermediate CSV format tables.
Both G-FNM-3 and G-FNM-4 used the pre-cleaned MATPOWER case file via
`matpowercaseframes.CaseFrames` + `from_ppc` as a stable workaround. A secondary
workaround (zero RATE_A values set to 9999) was also required due to a pandapower 3.4.0
bug in `_from_ppc_branch`.

## Context

The MATPOWER fallback path is classified as a stable workaround because
`matpowercaseframes`, `from_ppc`, and `rundcpp`/`runpp` are all public, documented APIs.
However, the PPC format inherently flattens transformer-specific data (tap control modes,
winding impedance details, switched shunt discrete steps), which reduces data fidelity
compared to direct CSV ingestion.

## Implications

The MATPOWER fallback is a stable workaround with grade impact limited to field fidelity
reduction. The zero RATE_A fix is a deterministic pre-processing step that compensates for
a specific pandapower bug. Both workarounds should be noted in the Extensibility narrative
as evidence of pandapower's reliance on MATPOWER-format intermediaries for non-native
data sources.
