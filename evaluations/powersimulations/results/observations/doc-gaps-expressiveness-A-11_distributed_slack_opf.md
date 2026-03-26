---
tag: doc-gaps
source_dimension: expressiveness
source_test: A-11
tool: powersimulations
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Misleading "use_slacks" terminology in PTDFPowerModel

## Finding

PSI's `PTDFPowerModel` has a `use_slacks` parameter that adds feasibility slack variables
(penalty-based soft constraints), not distributed slack for power balance. The naming conflicts
with standard power systems terminology where "slack" refers to the reference bus.

## Context

A-11 investigates distributed slack formulation support. The PSI namespace contains 30+ symbols
with "slack" in the name, all pertaining to constraint feasibility relaxation (e.g.,
`SystemBalanceSlackDown`, `FlowActivePowerSlackUpperBound`). None relate to distributing the
power balance reference across multiple buses.

## Implications

This is relevant to the Accessibility audit (D-4). Users searching for distributed slack
formulation support may mistakenly believe `use_slacks=true` provides this capability. The
documentation does not clarify the distinction between feasibility slack and distributed
power balance slack.
