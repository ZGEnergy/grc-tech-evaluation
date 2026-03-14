---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-5
tool: pypsa
severity: medium
timestamp: 2026-03-13T00:00:00Z
---

# Observation: PyPSA achieves 82% in-model representability for supplemental CSVs via extension mechanism

## Finding

PyPSA can represent 82.2% of supplemental CSV fields within its data model: 20.5% natively
and 61.6% via extension (custom DataFrame columns, extra_functionality callbacks, PTDF
constraints). Only 17.8% of fields (13 out of 73) require external data structures.
The extension mechanism (custom columns on component DataFrames) was empirically verified.

Three v10 reclassifications expanded PyPSA's extension coverage: CONTINGENCY
(extra_functionality + BODF), INTERFACE (PTDF + extra_functionality), and TRADING_HUB
(custom bus attributes + PTDF-weighted LMP averaging). These are complex patterns
requiring 50-100 lines of custom code each.

## Context

G-FNM-5 assessed all 7 supplemental CSVs from the FNM Annual S01 variant against
PyPSA's data model. The high extension-representable percentage (61.6%) reflects
PyPSA's flexible DataFrame-based architecture: any column can be added to any component
DataFrame. However, extension-representable fields are not semantically interpreted by
PyPSA's solvers -- they require custom post-processing code.

The universally tool-external fields (OUTAGE schedule data, generator distribution factors,
APNode identifiers) represent market-layer and temporal scheduling concepts outside all
power flow tools' domain models.

## Implications

PyPSA's high extension-representability score benefits from its DataFrame-centric
architecture, which makes custom attribute storage trivial. This is relevant to the
Extensibility dimension (data model flexibility) and contrasts with tools that use
fixed struct/matrix formats (MATPOWER, PowerModels.jl). The Accessibility dimension
should note that while storage is easy, semantic interpretation of extended fields
requires significant custom code.
