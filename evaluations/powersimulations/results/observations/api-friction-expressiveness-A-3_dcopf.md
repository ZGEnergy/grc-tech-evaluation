---
tag: api-friction
source_dimension: expressiveness
source_test: A-3
tool: powersimulations
severity: medium
timestamp: "2026-03-07T01:30:00Z"
---

# Observation: PSI requires time series boilerplate for single-period OPF

## Finding

PowerSimulations.jl `DecisionModel` requires forecast/time series data even for
single-period optimization problems. A simple DC OPF on a MATPOWER case file requires
~30 lines of time series setup (creating `SingleTimeSeries`, adding to each component,
transforming to `Deterministic` forecasts) before the model can be built.

## Context

In test A-3 (DCOPF on case39), the system loaded from case39.m had no time series data.
PSI's `build!()` fails without forecasts. The workaround uses multiplier values of `1.0`
on `max_active_power` for all generators and loads, then transforms them to deterministic
forecasts. This is a documented pattern but adds significant friction for users who just
want to run a single-period OPF.

Additionally, the time series values must be multipliers (0.0-1.0 range) on
`max_active_power`, not absolute power values. Using absolute values causes unit
mismatches that produce infeasible models with no helpful error message -- the model
builds but the solver returns INFEASIBLE.

## Implications

This pattern should be noted in Accessibility (D-2 documentation audit, D-4 error quality).
The silent infeasibility from incorrect time series values is particularly problematic for
new users. The tool does not validate that time series values are in the expected range.
