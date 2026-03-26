---
tag: api-friction
source_dimension: extensibility
source_test: B-3
tool: powersimulations
severity: medium
timestamp: 2026-03-24T00:00:00Z
---

# Observation: No built-in contingency analysis in PSI ecosystem

## Finding

PowerSimulations.jl has no built-in N-1 or N-M contingency analysis pipeline. Users must
assemble LODF screening, branch adjacency graphs, and combinatorial enumeration from
separate packages (PowerNetworkMatrices.jl, PowerFlows.jl, Combinatorics.jl) plus custom code.

## Context

During B-3 (N-M contingency sweep), the complete pipeline required: (1) base-case DCPF via
PowerFlows.jl, (2) LODF matrix from PowerNetworkMatrices.jl, (3) manual branch adjacency
graph construction for graph-distance pruning, (4) Combinatorics.jl for enumeration. This
is architecturally clean but requires significant domain knowledge from the user.

## Implications

For the Accessibility audit: the assembly burden is high -- a user must understand LODF
theory, know which companion packages to use, and implement the glue code. Legacy N-1/G-1
contingency code was removed in v0.33.0, suggesting this capability was never fully mature.
