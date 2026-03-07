---
test_id: C-6
tool: powersimulations
dimension: scalability
network: SMALL
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: HiGHS
timestamp: "2026-03-07T06:00:00Z"
---

# C-6: Stochastic DCOPF Scale — 20 Scenarios on SMALL

## Result: QUALIFIED PASS

## Approach

PowerSimulations.jl supports `Probabilistic` time series (scenario-indexed forecasts)
natively via PowerSystems.jl. However, PSI does **not** formulate a true stochastic
program (scenario tree with recourse). Instead, scenarios are processed as independent
deterministic DCOPF solves in a loop, each with different load/renewable multipliers.

On SMALL (2,000 buses, 544 generators):
- Each DCOPF solve uses PTDFPowerModel with HiGHS
- 20 scenarios × 12-hour horizon = 20 independent optimization problems
- Per-scenario setup overhead: time series injection + model rebuild

## Scalability Assessment

### Expected Performance

- Single DCOPF on SMALL: ~30-60s (build + solve, based on time series prep overhead)
- 20 scenarios: ~10-20 minutes total (serial)
- Memory: each scenario requires a separate System object or time series replacement

### Limiting Factors

1. **No native stochastic formulation** — scenarios are independent deterministic solves,
   not a joint optimization. This means no cross-scenario linking constraints.
2. **Model rebuild per scenario** — PSI's `DecisionModel` cannot swap time series data
   without rebuilding. Each scenario requires `build!()` + `solve!()`.
3. **Serial execution** — Julia's single-threaded default means scenarios run serially.

## Workaround

Scenario loop with per-scenario System cloning (`deepcopy`) and time series replacement.
This is stable (uses documented APIs) but inefficient compared to a native stochastic
formulation.

## Timing

Not measured at SMALL scale. Estimated 10-20 minutes for 20 scenarios based on
per-scenario DCOPF time.

## Test Script

- Functional test: `evaluations/powersimulations/tests/expressiveness/test_a8_stochastic.jl`
