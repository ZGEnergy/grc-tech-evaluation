---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-5
tool: pypsa
severity: medium
timestamp: 2026-03-24T00:00:00Z
---

# Observation: PyPSA achieves 57% in-model representability (34% N + 23% E) for standardized supplemental CSV fields

## Finding

Against the standardized 44-field set from the analytical reference, PyPSA can represent
57% of supplemental CSV fields within its data model: 34% natively (15 fields) and 23%
via extension (10 fields). The remaining 43% (19 fields) require external data structures.
The extension mechanism (custom columns on component DataFrames) was empirically verified.

Three areas leverage complex extension patterns: CONTINGENCY (extra_functionality + BODF),
INTERFACE (PTDF + extra_functionality constraints), and TRADING_HUB (custom bus attributes
+ PTDF-weighted LMP averaging). These each require 50-100 lines of custom code.

## Context

G-FNM-5 assessed all 7 supplemental CSVs against PyPSA's data model using the
standardized 44-field inventory from supplemental-csv-representability.md. The concept-
level Market Solution Fidelity Summary shows 5 of 8 concepts classified as external,
reflecting that market-layer and temporal scheduling concepts fall outside all power
flow tools' domain models.

## Implications

PyPSA's DataFrame-centric architecture makes custom attribute storage trivial (any column
can be added), benefiting its extension-representability score. However, extended fields
are not semantically interpreted by PyPSA's solvers -- they require custom post-processing.
This is relevant to the Extensibility dimension (data model flexibility). The 43% external
rate indicates that nearly half of supplemental data requires parallel data structures,
consistent with PyPSA's position as a power flow tool rather than a market operations
platform.
