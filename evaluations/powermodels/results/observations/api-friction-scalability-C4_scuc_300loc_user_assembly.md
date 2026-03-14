---
tag: api-friction
source_dimension: scalability
source_test: C-4
tool: powermodels
severity: high
timestamp: 2026-03-13T22:30:00Z
---

# Observation: SCUC at 2000-bus scale requires ~300 LOC of custom JuMP code

## Finding

Scaling SCUC from TINY (39-bus, ~250 LOC) to SMALL (2000-bus, ~300 LOC) required the same fundamental user-assembly effort. PowerModels provides no SCUC capability at any scale. The resulting model has 100K variables (13K binary) and 340K constraints, all hand-constructed. The model formulation complexity (commitment bounds, startup/shutdown logic, min up/down time, ramp rates, nodal DC power balance, thermal limits) does not change with network size, but model build time becomes significant at scale.

## Context

A-5 TINY established the ~250 LOC user-assembled MILP. C-4 SMALL uses the same approach but on a 2000-bus network. The model structure is solver-agnostic (JuMP), but the complete absence of any PowerModels SCUC abstraction means every deployment at any scale requires the same hand-written formulation.

## Implications

This is relevant to both Accessibility (API friction for a standard industry workflow) and Extensibility (can the tool be extended for UC). The blocking workaround is identical across scales, confirming that the SCUC gap is architectural, not a scale-dependent limitation.
