---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-5
tool: gridcal
severity: medium
timestamp: 2026-03-13T00:00:00Z
---

# Observation: GridCal has native contingency model but no interface/flowgate model

## Finding

GridCal's data model natively supports contingency definitions (83% native on
CONTINGENCY.csv) via `ContingencyGroup` and `Contingency` classes, but has zero
interface/flowgate representation (100% external on INTERFACE.csv). Overall
supplemental CSV representability is 39% native, 23% extension, 38% external.

## Context

G-FNM-5 classified all 44 fields across 7 supplemental CSVs. GridCal's native
contingency support (`ContingencyGroup`, `Contingency`, `ContingencyAnalysisDriver`)
makes it one of only two tools (with PowerSimulations.jl) that can natively define
and consume contingency scenarios. However, the absence of any interface/flowgate
concept means transmission corridor monitoring and SCOPF with interface constraints
require entirely external implementation.

## Implications

The contingency model strength is relevant to extensibility grading -- GridCal does
not need external scripting for basic N-1 analysis. The interface model gap is
relevant to Phase 2 congestion analysis readiness: flowgate-constrained dispatch
and transmission corridor monitoring cannot be implemented within GridCal's data
model.
