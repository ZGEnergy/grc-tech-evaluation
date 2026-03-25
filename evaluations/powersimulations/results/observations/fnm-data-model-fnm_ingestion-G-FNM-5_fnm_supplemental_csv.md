---
tag: fnm-data-model
source_dimension: fnm_ingestion
source_test: G-FNM-5
tool: powersimulations
severity: low
timestamp: "2026-03-24T22:10:00Z"
---

# Observation: PowerSystems.jl achieves highest native supplemental CSV coverage (50%)

## Finding

PowerSystems.jl v4.6.2 achieves 50% native, 30% extension, 20% external coverage
across 44 fields in 7 supplemental CSVs. This is the highest native coverage among
the six evaluated tools. The lead is driven by two differentiating type constructs:
`TransmissionInterface` (unique among all tools for native interface support) and the
`Contingency` type hierarchy (matching GridCal's 83% native contingency coverage).

## Context

The `ext::Dict{String,Any}` field on every PowerSystems.jl component type serves as
the extension mechanism for all E-tier fields (13 of 44). This is a documented,
stable API that survives serialization. However, extension-tier data is not
semantically interpreted by PowerSimulations.jl solvers -- enforcing multi-tier
thermal ratings or emergency interface limits requires custom JuMP constraint
formulation. The 9 external fields (20%) are universally external across all tools
(trading hubs, outage schedules, market participation factors).

## Implications

PowerSimulations.jl's native interface and contingency support positions it well for
Phase 2 congestion analysis, where interface flow limits and N-1 contingency
definitions are critical inputs. The ext-dict extension mechanism is adequate for
carrying additional rating tiers but adds custom code burden for enforcement.
