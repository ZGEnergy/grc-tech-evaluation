---
tag: doc-gaps
source_dimension: expressiveness
source_test: A-3
tool: powersimulations
severity: medium
timestamp: "2026-03-07T01:30:00Z"
---

# Observation: Time series value semantics underdocumented, causes silent infeasibility

## Finding

The `max_active_power` time series values in PowerSimulations are multipliers on the
component's `max_active_power` attribute, not absolute power values. This semantic is
not clearly documented, and using absolute values (e.g., passing `get_active_power(load)`
as the time series value) produces a model that builds successfully but is silently
infeasible -- the solver returns INFEASIBLE with no diagnostic indicating the unit mismatch.

## Context

During A-3 development, the initial approach used `get_active_power(load)` as time series
values for loads. With loads having `active_power=62.54` (system base) and
`max_active_power=62.54`, the model multiplied these together in the power balance
constraint, producing a RHS of ~311 instead of ~62.5. The build succeeded, but HiGHS
returned INFEASIBLE. Diagnosing this required printing the JuMP model constraints directly.

## Implications

This should be noted in Accessibility (D-2, D-4). The lack of input validation on time
series values and the absence of a clear error message when the resulting model is
infeasible make this a significant usability gap. New users are likely to encounter this
issue when working with MATPOWER data.
