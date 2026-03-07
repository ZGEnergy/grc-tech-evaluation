---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-5
tool: pandapower
severity: high
timestamp: 2026-03-06T00:00:00Z
---

# Observation: pandapower has no unit commitment / MILP capability

## Finding

pandapower is a steady-state power system analysis tool with no SCUC, no MILP solver interface, no temporal optimization, and no binary commitment variables. This is a fundamental architectural limitation, not a missing feature.

## Context

Test A-5 required solving a 24-hour unit commitment problem with min up/down times, startup costs, ramp rates, and reserve requirements. pandapower provides only single-period OPF (DC and AC) using PYPOWER's continuous interior point solver. No search of `dir(pandapower)` found any commit/schedule/MILP-related modules. The `pandapower.timeseries` module provides sequential power flow simulation but not optimization.

## Implications

This represents a blocking capability gap. For extensibility evaluation, note that pandapower's architecture cannot be extended to support SCUC without fundamental restructuring (adding a MILP solver backend and temporal constraint framework). For accessibility evaluation, the documentation correctly does not claim SCUC support.
