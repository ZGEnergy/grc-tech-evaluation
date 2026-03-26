---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-6
tool: pandapower
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Multi-period dispatch requires manual sequential OPF with bound manipulation

## Finding

pandapower has no native multi-period economic dispatch. To approximate SCED (A-6), the evaluator ran 24 sequential single-period DC OPF calls, manually adjusting generator Pmin/Pmax bounds between periods to enforce ramp constraints. This produces a greedy (not globally optimal) dispatch because each hour is optimized independently without temporal look-ahead.

## Context

A-6 requires a two-stage workflow: fix UC commitment schedule (from A-5), then solve multi-period economic dispatch with ramp constraints. pandapower failed at both stages: A-5 (SCUC) is unsupported, and the ED stage lacks temporal coupling. The sequential OPF approach is a fragile workaround that (a) does not produce a globally optimal dispatch, (b) relies on manual Pmin/Pmax manipulation that is not a documented pattern, and (c) cannot enforce forward-looking constraints like ramp-down requirements at end of horizon.

## Implications

This finding affects the Extensibility dimension -- pandapower's time series module (`pp.timeseries.run_timeseries()`) runs sequential power flows but does not support OPF or temporal constraints. The tool's architecture treats each time step as independent, which limits its applicability for market simulation workflows.
