---
tag: api-friction
source_dimension: expressiveness
source_test: A-3
tool: powersimulations
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Single-snapshot OPF requires time series boilerplate

## Finding

PowerSimulations.jl's `DecisionModel` requires the `System` to contain deterministic
forecast data even for single-snapshot optimization. Without time series, the constructor
throws `"The System does not contain any forecast data"`. Users must add synthetic 1-step
forecasts with multiplier 1.0 for all loads as boilerplate before any OPF solve.

## Context

Discovered during A-3 (DCOPF) evaluation. The time series value is a multiplier on
`max_active_power` (not the absolute MW value), which was discovered empirically.
The required boilerplate is approximately:

```julia
timestamps = [DateTime("2024-01-01"), DateTime("2024-01-01") + Hour(1)]
for load in get_components(PowerLoad, sys)
    add_time_series!(sys, load, SingleTimeSeries("max_active_power", TimeArray(timestamps, [1.0, 1.0])))
end
transform_single_time_series!(sys, Hour(1), Hour(1))
```

This adds ~5 lines per test. The workaround is stable (uses documented public API) but
represents friction for users performing one-off OPF analyses.

## Implications

For Accessibility audit: this architectural decision (PowerSimulations is a simulation
framework, not a standalone OPF solver) creates friction for the common use case of
single-snapshot power flow optimization. Users coming from MATPOWER, PyPSA, or pandapower
expect to load a network and solve immediately.
