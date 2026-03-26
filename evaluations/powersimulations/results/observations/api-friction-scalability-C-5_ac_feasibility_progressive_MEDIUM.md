---
tag: api-friction
source_dimension: scalability
source_test: C-5
tool: powersimulations
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: DCPF/ACPF Return Type Inconsistency at MEDIUM Scale

## Finding

PowerFlows.jl `solve_powerflow` returns different structures for DC vs AC power flow:
- DCPF: `Dict{Union{Char,String}, Dict{String, DataFrame}}` nested under period key `"1"`
- ACPF: `Dict{String, DataFrame}` (flat)

This inconsistency, also observed in SMALL (C-5 SMALL), requires conditional handling at each
scale tier. The pattern `dcpf_result["1"]["bus_results"]` vs `acpf_result["bus_results"]` is
a minor friction point when combining DC warm-start with AC power flow.

## Context

C-5 MEDIUM uses DCPF warm-start angles to initialize ACPF. Accessing DCPF bus angles
requires an extra indexing level compared to ACPF bus voltages.

## Implications

Low severity. Inconvenient but does not block any workflow.
