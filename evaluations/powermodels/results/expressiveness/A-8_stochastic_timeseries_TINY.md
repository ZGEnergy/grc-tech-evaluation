---
test_id: A-8
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 2.515
peak_memory_mb: null
loc: 132
solver: HiGHS
timestamp: "2026-03-06T00:00:00Z"
---

# A-8: Stochastic Timeseries DCOPF on TINY (IEEE 39-bus)

## Result: FAIL

PowerModels.jl does **not natively support scenario-indexed stochastic optimization**. The multi-network framework (`replicate()` + `solve_mn_opf()`) supports multi-period (temporal) optimization but not multi-scenario. There is no scenario indexing, probability weighting, recourse structure, or chance constraints in core PowerModels.

Per the test protocol: "A passing grade on A-8 requires that the tool's optimization formulation is aware of multiple scenarios simultaneously -- e.g., co-optimizing across scenarios with recourse decisions, or enforcing chance constraints across a scenario set." PowerModels fails this requirement.

## Approach

The test demonstrates what PowerModels CAN and CANNOT do:

### What Works: Multi-Period Deterministic DCOPF
- `PowerModels.replicate(data, 12)` creates a 12-period multi-network structure
- Load profiles applied per period by modifying `mn_data["nw"][t]["load"]`
- `solve_mn_opf(mn_data, DCPPowerModel, HiGHS.Optimizer)` solves successfully
- Result: OPTIMAL, objective = 363,865.20

### What Does NOT Work: Stochastic Optimization
- **No scenario indexing:** The multi-network framework has a single dimension (periods). There is no second dimension for scenarios.
- **No probability weighting:** No mechanism to assign scenario probabilities or compute expected cost.
- **No recourse structure:** No first-stage/second-stage decision variable separation.
- **No chance constraints:** No mechanism to enforce constraints across a probability-weighted scenario set.

### External Package
StochasticPowerModels.jl (KU Leuven/Electa, 24 GitHub stars, last pushed 2025-10-14) provides stochastic AC-OPF using polynomial chaos expansion. This is a separate external package, NOT part of core PowerModels.jl, and NOT installed in this evaluation environment.

### Manual Assembly
A user could manually assemble a two-stage stochastic program using JuMP (scenario-indexed variables, non-anticipativity constraints, expected-cost objective). However, this uses JuMP directly and PowerModels provides no structural support. The test protocol explicitly states: "A tool that only supports deterministic solves but can be wrapped in a Monte Carlo loop is tested under Extensibility (B-4), not here."

## Output

- **Multi-period DCOPF:** OPTIMAL (12 periods, HiGHS)
- **Stochastic formulation:** NOT ATTEMPTED (no native support)

## Workarounds

No viable workaround exists within the scope of this test's pass condition. The limitation is architectural -- PowerModels' multi-network framework is one-dimensional (time periods) with no second dimension for scenarios.

## Timing

- Wall-clock: 2.52s (multi-period DCOPF demonstration, excludes JIT)
- Peak memory: not measured

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a8_stochastic_timeseries.jl`
