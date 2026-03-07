# Observation: Workaround Needed -- B-4 Stochastic Scenarios

**Tag:** workaround-needed
**Test:** B-4 (Stochastic Scenario Wrapping)
**Dimension:** extensibility

## Observation

PowerSystems.jl time series are immutable after `transform_single_time_series!`.
This forces a full System reload from file for each scenario, adding ~2-3s of
overhead per scenario for file parsing and time series construction.

The `transform_single_time_series!` API signature is also error-prone. It takes
`(sys, horizon, interval)` but the parameter names are not obvious from the function
signature. The original test script passed them in the wrong order
(`(sys, resolution, Hour(n_hours))` instead of `(sys, Hour(n_hours), resolution)`),
which produced the error: "TimeSeries: max_active_power interval = 12 hours is bigger
than the max of 1 hour". The error message was clear enough to diagnose, but the API
could benefit from keyword arguments.

Additionally, 2 of 5 scenarios failed with FAILED solve status due to infeasible
load/generation combinations. This is a data characteristic (case39 has tight thermal
limits), not a tool limitation.

## Impact

The System reload overhead is manageable for small networks (~3s per scenario) but
would become significant for large systems (potentially minutes per reload). For
production stochastic optimization, an in-place time series update API would be
valuable. The workaround is stable but adds unnecessary I/O overhead.
