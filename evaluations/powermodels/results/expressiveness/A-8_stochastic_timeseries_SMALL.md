---
test_id: A-8
tool: powermodels
dimension: expressiveness
network: SMALL
status: fail
workaround_class: blocking
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "513931f7"
wall_clock_seconds: null
timing_source: null
---

# A-8: stochastic_timeseries — SMALL

## Result: FAIL

## Reason

PowerModels.jl v0.21.5 has no native support for scenario-indexed stochastic OPF formulations; it cannot represent a scenario tree, two-stage stochastic program, or coupled multi-scenario dispatch as a single optimization. This limitation was confirmed at the TINY functional tier and is identical at SMALL scale.

## Evidence

- **TINY result:** See `evaluations/powermodels/results/expressiveness/A-8_stochastic_timeseries_TINY.md` for the same failure documented at the functional tier.
- **Capability:** PowerModels.jl v0.21.5 does not support native stochastic/scenario-indexed OPF. [Source: research-version.md capability table]

## Implications

Stochastic dispatch formulations are architecturally absent from PowerModels.jl. At SMALL scale the only available workaround — independent deterministic solves per scenario in a loop — does not satisfy the pass condition requiring stochastic structure to be part of the optimization formulation, confirming a blocking expressiveness gap.
