---
tag: api-friction
source_dimension: expressiveness
source_test: A-6
tool: powersimulations
severity: high
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: No built-in UC-to-ED handoff mechanism

## Finding

PowerSimulations.jl has no API for transferring commitment decisions from a UC model to an
ED model. The two-stage UC-then-ED workflow requires manual extraction of binary commitment
variables via internal PSI APIs and re-application as JuMP variable fixes.

## Context

A-6 tests the ability to fix commitment from a SCUC solve and solve ED as a separate LP/QP.
PSI provides `ThermalStandardUnitCommitment` for UC and `ThermalDispatchNoMin` for ED, but
no mechanism to connect them. The evaluator had to: (1) extract `OnVariable__ThermalStandard`
from PSI's internal variable containers, (2) fix decommitted generators to P=0 via
`JuMP.fix()`, and (3) manually add ramp constraints via `@constraint` since
`ThermalDispatchNoMin` does not include ramp enforcement.

## Implications

This is a significant API gap for the Accessibility audit (D-4). A user attempting a standard
two-stage production cost simulation workflow would need to understand PSI's internal variable
naming conventions, JuMP constraint manipulation, and PSI's internal container structure.
The lack of a documented handoff API is a barrier to adoption for users familiar with other
PST tools where UC-to-ED feedforward is built-in.
