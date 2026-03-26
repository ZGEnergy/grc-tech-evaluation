---
tag: cascaded-failure
source_dimension: scalability
source_test: C-10
tool: powermodels
severity: medium
timestamp: 2026-03-24T22:00:00Z
---

# Observation: C-10 distributed slack scalability blocked by A-11 expressiveness failure

## Finding

C-10 (distributed slack DC OPF scale on MEDIUM) cannot be executed because its prerequisite A-11 (distributed slack OPF) failed with a blocking workaround classification. PowerModels.jl v0.21.5 does not natively support distributed slack formulations. [tool-specific]

## Context

A-11 confirmed that PowerModels.jl has no distributed slack API: no `build_*` function, formulation type, or API parameter supports it. The workaround requires ~150 lines of custom JuMP PTDF-based DC OPF code, bypassing PowerModels' problem specification API entirely. This was classified as a blocking workaround in A-11.

While the custom approach could theoretically be scaled to MEDIUM (10k buses), the blocking classification from A-11 prevents C-10 from proceeding.

## Implications

The distributed slack capability gap cascades from expressiveness (A-11) to scalability (C-10), affecting both dimension grades for PowerModels.jl. This is an architectural limitation, not a scale-dependent one.
