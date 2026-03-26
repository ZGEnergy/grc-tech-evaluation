---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-5
tool: powersimulations
severity: info
timestamp: "2026-03-24T22:10:00Z"
---

# Observation: Supplemental CSV representability is scale-independent

## Finding

G-FNM-5 supplemental CSV representability assessment is a type-system analysis that
does not depend on network scale. The 50%/30%/20% native/extension/external
classification applies equally to any network size because it reflects PowerSystems.jl's
type hierarchy structure, not runtime data handling.

## Context

The assessment was performed via Julia introspection (fieldnames, type hierarchy
traversal) on PowerSystems.jl v4.6.2 types. No network data was loaded. The
classification would remain identical for TINY through LARGE networks.

## Implications

No scale-specific findings for G-FNM-5. The extension mechanism (`ext` dict) has
O(1) per-field access regardless of network size, though the aggregate storage
overhead of extension fields scales linearly with component count.
