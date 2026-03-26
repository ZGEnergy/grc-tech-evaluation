---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-5
tool: powermodels
severity: high
timestamp: 2026-03-24T12:00:00Z
---

# Observation: PowerModels has no native SCUC -- recorded as fail

## Finding

PowerModels.jl v0.21.5 has no native SCUC support. No `build_uc`, `build_scuc`, `solve_uc`, or equivalent functions exist. The tool focuses on single-period steady-state power network optimization and unit commitment is entirely outside its scope. A-5 is recorded as `fail` with `failure_reason: unsupported_in_installed_version`.

## Context

Test A-5 required a 24-hour SCUC with cycling. While a user could assemble a complete MILP using JuMP (PowerModels only for data parsing), this tests JuMP's capabilities rather than PowerModels' expressiveness. The v11 protocol records this as a straightforward unsupported capability rather than a workaround-based pass.

## Implications

This is an expressiveness gap inherent to the tool's architecture. For the Extensibility audit, this confirms that PowerModels is architecturally limited to steady-state single-period optimization. For Accessibility, users requiring SCUC need to use a different tool (e.g., PowerSimulations.jl) or build the formulation from scratch in JuMP.
