# Observation: doc-gaps — B-4 Stochastic Wrapping

## Tool
PowerModels.jl v0.21.5

## Finding
PowerModels provides `replicate(data, count)` for multi-period network creation and `solve_mn_opf` for multi-network OPF. However:

1. **No timeseries input API**: There is no method to attach load profiles, generation schedules, or renewable output curves as timeseries data. Users must manually iterate over `mn_data["nw"]["$t"]["load"][id]["pd"]` for each period and load. The `make_multinetwork()` function exists but requires a pre-formatted `time_series` data block whose format is not documented in the main docs.

2. **Scenario loop pattern undocumented**: The pattern of `deepcopy(mn_data)` -> modify loads -> `solve_mn_opf()` works but is not shown in any example or tutorial. Users must discover it by reading the source.

3. **No stochastic programming support**: There is no built-in scenario tree, chance constraint, or two-stage stochastic programming capability. All scenario management must be handled externally.

## Impact
- The multi-period infrastructure exists and works well, but the user-facing documentation does not cover stochastic/scenario analysis workflows.
- The `deepcopy` + modify pattern is efficient (0.14s per 24-period scenario solve) but requires familiarity with the internal dict structure.
