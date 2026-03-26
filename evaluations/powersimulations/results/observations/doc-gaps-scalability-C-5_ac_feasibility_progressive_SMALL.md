---
tag: doc-gaps
source_dimension: scalability
source_test: C-5
tool: powersimulations
severity: low
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: PowerFlows.jl return type inconsistency undocumented

## Finding

PowerFlows.jl v0.9.0 API documentation does not describe the return type difference between
`DCPowerFlow` (nested Dict with period key) and `ACPowerFlow` (flat Dict). Users must
discover this empirically or by reading source code.

## Context

See companion api-friction observation for technical details. The documentation gap is minor
but compounds with other PowerFlows.jl diagnostic limitations (no residual reporting,
iteration count only via log capture).

## Implications

Low severity. Affects developer experience but not correctness. Newer PowerFlows.jl versions
(up to v0.16.0) may have addressed this.
