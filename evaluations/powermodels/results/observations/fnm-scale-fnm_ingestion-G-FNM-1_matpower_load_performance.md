---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: powermodels
severity: low
timestamp: "2026-03-13T00:00:00Z"
---

# Observation: MATPOWER Fallback Load Performance at LARGE Scale

## Finding

PowerModels loaded the 27,862-bus MATPOWER fallback file in 2.97 seconds. This confirms
that PowerModels' MATPOWER parser handles LARGE-scale networks without difficulty, though
the actual FNM (30,307 buses) could not be tested due to PSS/E parser incompatibility.

## Context

The MATPOWER fallback (`fnm_main_island.m`) contains 27,862 buses, 32,606 branches,
5,741 generators, and 8,624 loads. PowerModels parsed this file without errors (warnings
about angle limits and branch orientation reversals were handled automatically). The
2.97-second load time is well within acceptable bounds for a network of this scale.

## Implications

PowerModels has no scalability concerns for MATPOWER-format network loading at the LARGE
tier. The performance bottleneck is format compatibility (PSS/E and CSV formats), not
parsing speed. This is relevant for Scalability dimension assessments of ingestion
overhead.
