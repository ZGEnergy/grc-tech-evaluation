---
tag: workaround-needed
dimension: expressiveness
test_id: A-5
tool: powersimulations
timestamp: "2026-03-07T04:30:00Z"
---

# Workaround Needed: MATPOWER Data Lacks UC Parameters

## Observation

MATPOWER case39.m generators have `ramp_up=0.0`, `ramp_down=0.0`,
`min_up_time=null`, `min_down_time=null`, and `Pmin=0.0`. PSI's
`ThermalStandardUnitCommitment` formulation requires non-zero values for these
parameters. Manual initialization is required before SCUC can solve.

## Workaround

Set ramp rates (50% Pmax), min up/down times (2h), and Pmin (30% Pmax) using
PowerSystems setter APIs (`set_ramp_limits!`, `set_time_limits!`,
`set_active_power_limits!`).

## Classification

**Stable** — uses documented public API. The values chosen are reasonable engineering
defaults. This is a data limitation (MATPOWER format) not a tool limitation.
