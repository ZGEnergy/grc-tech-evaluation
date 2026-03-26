---
tag: fnm-scale
source_dimension: fnm_ingestion
source_test: G-FNM-1
tool: powersimulations
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: MATPOWER fallback loads 27,862-bus main island in 12s

## Finding

PowerSystems.jl loaded the 27,862-bus MATPOWER fallback file in 12.03 seconds with
847 MB peak RSS. This demonstrates the tool can handle LARGE-tier networks via
MATPOWER ingestion, though 2,445 isolated buses (8.1% of total) are excluded from the
cleaned fallback file.

## Context

The full FNM has 30,307 buses, 33,840 branches (24,117 lines + 9,723 transformers),
5,768 generators, and 15,062 loads. The MATPOWER fallback contains only the main
connected island: 27,862 buses, 32,606 branches, 5,741 generators, 11,734 loads.
Load time of 12s includes Julia's PowerModels-derived MATPOWER parser and System
construction overhead.

## Implications

For scalability assessment, the 12-second load time for a 27,862-bus network is
acceptable for G-FNM-3/4/5 downstream tests. The missing 2,445 buses are isolated
(IDE=4) and disconnected island fragments that do not participate in power flow, so
their absence does not affect DCPF/ACPF verification accuracy.
