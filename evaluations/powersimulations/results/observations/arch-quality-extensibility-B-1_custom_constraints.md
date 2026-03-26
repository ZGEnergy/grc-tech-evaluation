---
tag: arch-quality
source_dimension: extensibility
source_test: B-1
tool: powersimulations
severity: low
timestamp: 2026-03-24T00:00:00Z
---

# Observation: JuMP model access is a genuine architectural strength

## Finding

PowerSimulations.jl exposes the underlying JuMP optimization model via `PSI.get_jump_model()`,
enabling arbitrary constraint addition and dual extraction through standard JuMP API.

## Context

During B-1 (custom constraints), a flow gate constraint was added to a DCOPF model using
`@constraint` on the JuMP model, and duals were extracted via `JuMP.dual()`. This required
no internal access or workarounds -- the JuMP model is a documented, first-class extension point.

## Implications

This architectural pattern means PSI inherits the full expressiveness of JuMP/MathOptInterface
for custom extensions. Any optimization constraint or objective modification expressible in
JuMP can be layered onto a PSI model after `build!()`. This is a positive maturity signal
for the Maturity audit (D-dimension).
