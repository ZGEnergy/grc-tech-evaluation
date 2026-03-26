---
tag: formulation-difference
source_dimension: fnm_ingestion
source_test: G-FNM-5
tool: powersimulations
severity: info
timestamp: "2026-03-24T22:10:00Z"
---

# Observation: No formulation differences in supplemental CSV representability

## Finding

G-FNM-5 is a type-system representability assessment with no solver formulation
component. No formulation differences apply. The classifications (N/E/X) are
determined by the tool's data model structure, not by any power flow or optimization
formulation.

## Context

Included for observation tag completeness. The only formulation-relevant finding is
that extension-tier fields (e.g., multi-tier thermal ratings stored in `ext` dict)
are not automatically incorporated into PowerSimulations.jl's optimization formulations.
An analyst must write custom JuMP constraints to enforce extension-tier data, which
represents a formulation gap rather than a formulation difference.

## Implications

No formulation-difference impact from G-FNM-5.
