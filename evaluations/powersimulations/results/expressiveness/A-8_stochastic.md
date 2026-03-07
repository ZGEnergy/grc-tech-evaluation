---
test_id: A-8
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 47.60
peak_memory_mb: null
loc: 348
solver: HiGHS
timestamp: "2026-03-07T05:00:00Z"
---

# A-8: Stochastic Timeseries (12hr multi-period DCOPF with scenarios)

## Result: FAIL

PSI does not natively support stochastic optimization. The `DecisionModel` solves deterministic problems only. While `PowerSystems.jl` has a `Scenarios` time series type for data storage, PSI's optimization formulations do not consume it -- there are no scenario-indexed decision variables, non-anticipativity constraints, or probability-weighted objectives.

## Approach

### Test 1: Native Scenario Support (FAIL)

Attempted to add `Scenarios` time series to loads and build a `DecisionModel`. The `Scenarios` type can be added to `PowerSystems.System`, but it is not used by PSI's optimization formulations. The resulting model is deterministic regardless.

### Test 2: Manual Scenario Loop Workaround (PASS, but not stochastic)

Solved 3 independent deterministic 12-hour DCOPFs, one per scenario (high/medium/low load), and computed expected cost as a probability-weighted sum. All three scenarios solved successfully.

## Output

### Scenario Loop Results

| Scenario | Probability | Objective | Weighted Cost |
|----------|------------|-----------|---------------|
| High     | 0.30       | 240.51    | 72.15         |
| Medium   | 0.50       | 201.33    | 100.67        |
| Low      | 0.20       | 163.47    | 32.69         |
| **Expected** | | | **205.51** |

### Why This Is Not Stochastic Optimization

The manual scenario loop is Monte Carlo simulation, not stochastic optimization. Key missing elements:

- **No scenario-indexed decision variables** (e.g., `x[scenario, time, generator]`)
- **No non-anticipativity constraints** linking first-stage decisions across scenarios
- **No scenario tree structure** (e.g., two-stage: commit now, dispatch per scenario)
- **No probability weights in the objective function** within a single optimization

Each scenario is solved independently -- there are no linking constraints between scenarios. A true stochastic program would require first-stage commitment decisions that must be identical across all scenarios.

### PSI Gap

PSI's `DecisionModel` is deterministic only. The `Scenarios` type in `PowerSystems.jl` is for data storage, not used in optimization formulations. There is no mechanism to build a stochastic program within PSI's framework.

## Workarounds

Manual scenario loop (solve independent deterministic DCOPFs per scenario and compute expected cost). This is NOT stochastic optimization -- no linking constraints between scenarios. Classified as **blocking** because no amount of scripting can replicate true stochastic optimization within PSI's framework.

## Timing

- Wall clock: 47.6 seconds (includes JIT compilation for 3 separate model builds)

## Test Script

`evaluations/powersimulations/tests/expressiveness/test_a8_stochastic.jl`
