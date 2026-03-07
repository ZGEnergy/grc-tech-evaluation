---
tag: api-friction
dimension: expressiveness
test_id: A-4
tool: powersimulations
timestamp: "2026-03-07T04:30:00Z"
---

# API Friction: Dispatch Unit Mismatch Between PSI and PowerFlows

## Observation

The `ActivePowerVariable` values returned by `read_variables()` from a PSI
`DecisionModel` are not in the same unit basis as the `System` component limits
(`get_active_power_limits()`). Dispatch values appear ~100x larger than Pmax,
making direct transfer to PowerFlows for ACPF validation impossible without
unit conversion.

## Impact

The DCOPF-to-ACPF workflow (A-4) fails because `set_active_power!(gen, dispatch_value)`
sets physically unrealistic values on the System, causing ACPF non-convergence.
Users must understand PSI's internal unit conventions (which differ from
PowerSystems.jl's component accessors) to correctly interpret optimization results.

## Severity

High — this is a workflow-breaking issue for the DCOPF->ACPF pipeline. The mismatch
is not documented and requires either source code investigation or trial-and-error
to discover.
