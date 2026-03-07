---
test_id: A-8
tool: powermodels
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 0.0
peak_memory_mb: null
loc: 132
solver: HiGHS
timestamp: "2026-03-06T00:00:00Z"
---

# A-8: Stochastic Timeseries DCOPF on SMALL (ACTIVSg 2000-bus)

## Result: FAIL

Same outcome as TINY. PowerModels.jl does **not natively support scenario-indexed stochastic optimization**. This is an architectural limitation independent of network size.

The multi-network framework (`replicate()` + `solve_mn_opf()`) supports multi-period (temporal) optimization but not multi-scenario. There is no scenario indexing, probability weighting, recourse structure, or chance constraints in core PowerModels.

Per the test protocol: "A passing grade on A-8 requires that the tool's optimization formulation is aware of multiple scenarios simultaneously." PowerModels fails this requirement at any network scale.

## Why No Re-Run Is Needed

The TINY test (A-8_stochastic_timeseries_TINY.md) conclusively established that:

1. PowerModels' `replicate()` framework is one-dimensional (time periods only, no scenario dimension)
2. No native probability weighting, recourse structure, or chance constraints exist
3. StochasticPowerModels.jl is a separate external package (not installed, not part of core PowerModels)
4. Manual JuMP assembly does not satisfy the pass condition per protocol

These are design-level limitations that do not change with network size. Running the 2000-bus network would only demonstrate the same multi-period DCOPF capability already shown on TINY, without addressing the fundamental missing stochastic features.

## Workarounds

No viable workaround exists within the scope of this test's pass condition. The limitation is architectural.

## Test Script

Not executed for SMALL. TINY script: `evaluations/powermodels/tests/expressiveness/test_a8_stochastic_timeseries.jl`
