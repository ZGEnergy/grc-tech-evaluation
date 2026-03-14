---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-5
tool: powermodels
severity: medium
timestamp: "2026-03-13T01:30:00Z"
---

# Observation: PowerModels 39% Native Coverage Reflects Power Flow Tool Domain Boundary

## Finding

PowerModels.jl achieves 39% native coverage across 44 supplemental CSV fields. Market-layer
concepts (trading hubs, generator distribution factors) and operational concepts
(contingency definitions, interfaces, outage schedules) are 100% tool-external. The dict-based
data model enables simple Extension-representable storage (18% of fields) via arbitrary dict
keys, but these are not semantically interpreted by any PowerModels function.

## Context

G-FNM-5 assessed each supplemental CSV field's representability in PowerModels' data model.
The tool's native strengths are 3 thermal rating tiers (RATE_A/B/C) and standard network
element identifiers. The 100% external classification for INTERFACE.csv (5 fields) is the
most consequential gap -- PowerModels has no interface/flowgate concept, meaning congestion
corridor analysis requires entirely external implementation.

## Implications

For extensibility evaluation: PowerModels' dict-based data model is pragmatically extensible
(add any key to any component dict) but semantically shallow (the tool ignores custom keys).
This pattern produces good Extension-representable coverage but poor Native coverage for
domain concepts beyond power flow. The interface gap is shared with PyPSA, pandapower, and
GridCal (all 100% external for INTERFACE.csv), differentiating only from PowerSimulations.jl
and MATPOWER which have native interface support.
