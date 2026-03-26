---
tag: workaround-needed
source_dimension: extensibility
source_test: B-8
tool: powersimulations
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Distributed slack not supported in DCPPowerModel OPF formulation

## Finding

DCPPowerModel (angle-based DC OPF) does not support distributed slack. The reference bus
angle is fixed to zero and PowerSimulations.jl does not expose a distributed slack
weighting option. PowerNetworkMatrices.jl supports distributed slack for PTDF computation
(via `dist_slack` parameter), but this capability does not propagate to PSI's OPF formulation.

## Context

B-8 tested reference bus configurability with three single-slack configurations. The
`set_bustype!` API is clean and documented, but changing the reference bus requires full
System reconstruction. Distributed slack would require switching to PTDFPowerModel, which
is a different network model choice rather than a parameter on the existing model.

## Implications

Users needing distributed slack for more accurate LMP decomposition must use PTDFPowerModel
instead of DCPPowerModel. This is a formulation-level choice, not a simple parameter change.
The Accessibility audit should note that the relationship between network model choice and
slack formulation is not well-documented.
