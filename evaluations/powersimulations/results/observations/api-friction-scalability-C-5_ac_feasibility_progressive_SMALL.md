---
tag: api-friction
source_dimension: scalability
source_test: C-5
tool: powersimulations
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: DCPowerFlow and ACPowerFlow return inconsistent result structures

## Finding

`solve_powerflow(DCPowerFlow(), sys)` returns a nested structure
`Dict{Union{Char,String}, Dict{String, DataFrame}}` with results under a period key "1",
while `solve_powerflow(ACPowerFlow(), sys)` returns a flat `Dict{String, DataFrame}`.
This inconsistency requires different extraction code for each power flow type.

## Context

Discovered during C-5 (AC feasibility progressive relaxation) when applying DCPF warm-start
angles. The DCPF result must be accessed as `dcpf_result["1"]["bus_results"]` while the ACPF
result is accessed directly as `acpf_result["bus_results"]`. This difference is not documented
in PowerFlows.jl's API reference and was discovered empirically via `KeyError`.

## Implications

Minor API friction that affects code clarity and debugging time. Not a functional limitation --
both power flow types produce correct results. This is a documentation and API consistency gap
in PowerFlows.jl v0.9.0 that may be addressed in newer versions.
