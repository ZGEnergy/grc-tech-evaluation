---
tag: api-friction
source_dimension: expressiveness
source_test: A-1
tool: powersimulations
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Inconsistent power flow result nesting between DC and AC

## Finding

PowerFlows.jl v0.9.0 returns DC and AC power flow results in different Dict structures.
DCPowerFlow nests results under a string key `"1"` (Dict -> Dict -> DataFrame), while
ACPowerFlow returns a flat Dict -> DataFrame. Users must write defensive code to handle
both formats.

## Context

Discovered during A-1 (DCPF) and A-2 (ACPF) evaluation. The DC result structure is
`pf_result["1"]["bus_results"]` while the AC result structure is
`pf_result["bus_results"]`. This inconsistency requires type checking or try/catch logic
in any code that handles both power flow types.

## Implications

Minor API friction for the Accessibility audit. Users writing generic power flow analysis
code must account for format differences. Documentation does not describe the return value
structure for either method.
