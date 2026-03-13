---
test_id: A-8
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v9"
skill_version: v1
test_hash: 513931f7
status: fail
workaround_class: blocking
blocked_by: null
failure_reason: no_native_stochastic_api
wall_clock_seconds: 115.9
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 240
solver: HiGHS
timestamp: 2026-03-11T00:00:00Z
---

# A-8: Stochastic Timeseries OPF

## Result: FAIL

## Pass Condition (not met)

> Tool natively supports scenario-indexed timeseries for load, wind, and solar — the stochastic structure is part of the optimization formulation (e.g., scenario tree, two-stage stochastic program), not just independent deterministic solves in a loop.

PowerModels.jl has **no native stochastic OPF support**. There is no:
- Scenario tree data structure
- Two-stage stochastic program formulation
- `build_stochastic_opf` or equivalent function
- Scenario coupling constraints (non-anticipativity)
- Expected-value objective aggregation over scenarios

## Verification

The research API review confirms:

> `PowerModels.replicate(data, T)` creates multi-network coupling for **time periods**, not for scenarios. Each `nw[s]` in a replicated network represents a time step — there is no concept of probability weights or scenario branching.

No stochastic programming extension exists for PowerModels.jl in the ecosystem at v0.21.5.

## What Was Implemented (Loop Workaround)

A 600-solve loop was implemented and executed to establish the "best achievable" result without native stochastic support:

- Load augmented data: `renewable_units.csv`, `wind_forecast_24h.csv`, `solar_forecast_24h.csv`, `load_24h.csv`, `scenarios/scenario_multipliers_50x24.csv`
- For each of 50 scenarios × 12 hours: solve independent DC OPF with scenario-specific wind/solar/load injection
- Extract dispatch and compute expected values and variance across scenarios

### Results from loop-based approach:

| Metric | Value |
|--------|-------|
| Total solves | 600 (50 scenarios × 12 hours) |
| Scenarios | 50 |
| Hours | 12 (first 12 of 24-hour horizon) |
| Successful solves | 600 / 600 |
| Mean total cost ($/day) | 1,106,485.03 |
| Std dev of cost ($/day) | 3,482.80 |
| Cost range | [1,096,831.39, 1,117,438.57] |
| Prices extractable | yes (from dual variables) |
| Wall clock (600 solves) | 115.9s (includes JIT) |

**Prices:** LMP-equivalent shadow prices can be extracted from the dual variable of the power balance constraint, but only per-scenario per-period — there is no single expected LMP that accounts for stochastic uncertainty in a consistent way.

## Why This Is a Blocking Fail

The loop workaround produces independent deterministic solves. It does not:

1. **Optimize over scenarios jointly** — each scenario's dispatch is independent; no coupling of first-stage here-and-now decisions across scenarios
2. **Enforce non-anticipativity** — the dispatch in hour 1 should be the same across all scenarios (first-stage decision), but the loop produces different dispatches per scenario
3. **Minimize expected cost** — the 600 solves minimize cost per-scenario, not E[cost] weighted by scenario probability
4. **Produce a single policy** — a stochastic program produces one dispatch policy valid for all scenarios; the loop produces 600 different policies

This is not equivalent to stochastic OPF. The pass condition requires native stochastic structure as part of the optimization, which PowerModels.jl cannot provide.

## Workaround Assessment

- **What:** No native stochastic OPF API. Implemented as 600 independent deterministic solves (loop over 50 scenarios × 12 hours).
- **Why:** PowerModels.jl `replicate()` creates time-period coupling (multi-network), not scenario coupling. No `JuMPScenarioOPF` or equivalent exists.
- **Durability:** The loop is stable code, but it is not a valid stochastic program.
- **Grade impact:** Blocking. The absence of scenario-indexed formulation makes it impossible to express the key modeling construct (stochastic policy under uncertainty) that the test requires.

## Timing

- **Wall-clock:** 115.9s (first invocation, includes JIT and 600 solves)
- **Per-solve:** ~0.1s/solve after JIT warmup
- **Timing source:** measured
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a8_stochastic_timeseries_tiny.jl`

Key patterns:

```julia

# No native stochastic API — loop over scenarios × hours
for s in 1:n_scenarios, h in 1:horizon_hours
    data_sh = deepcopy(base_data)
    # Apply scenario multipliers to wind/solar/load
    for (gen_id, gen) in data_sh["gen"]
        if gen_type[gen_id] == :wind
            gen["pmax"] = wind_forecast[h] * scenario_mult[s,h]
        end
    end
    result_sh = PowerModels.solve_dc_opf(data_sh, highs_opt)
    # ...collect results...
end
# No joint optimization — no scenario coupling constraints

```

The documentation in the test script explicitly notes that this approach is NOT equivalent to stochastic OPF and explains why.
