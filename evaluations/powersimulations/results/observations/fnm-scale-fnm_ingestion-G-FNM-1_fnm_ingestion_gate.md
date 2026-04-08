---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: powersimulations
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: MATPOWER fallback loads ~28,000-bus main island in 12s

## Finding

PowerSystems.jl loaded the ~28,000-bus MATPOWER fallback file in 12.03 seconds with
847 MB peak RSS. This demonstrates the tool can handle LARGE-tier networks via
MATPOWER ingestion, though 2,445 isolated buses (8.1% of total) are excluded from the
cleaned fallback file.

## Context

The full FNM has ~30,000 buses, ~34,000 branches (~24,000 lines + ~9,700 transformers),
~5,800 generators, and ~15,000 loads. The MATPOWER fallback contains only the main
connected island: ~28,000 buses, ~33,000 branches, ~5,700 generators, ~12,000 loads.
Load time of 12s includes Julia's PowerModels-derived MATPOWER parser and System
construction overhead.

## Implications

For scalability assessment, the 12-second load time for a ~28,000-bus network is
acceptable for G-FNM-3/4/5 downstream tests. The missing 2,445 buses are isolated
(IDE=4) and disconnected island fragments that do not participate in power flow, so
their absence does not affect DCPF/ACPF verification accuracy.
