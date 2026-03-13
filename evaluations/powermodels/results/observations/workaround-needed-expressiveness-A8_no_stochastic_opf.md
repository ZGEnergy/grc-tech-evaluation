---
tag: workaround-needed
dimension: expressiveness
test_id: A-8
observed: 2026-03-11
tool: powermodels
version: 0.21.5
---

# Missing Feature: No Native Stochastic OPF

## Observation

PowerModels.jl v0.21.5 has no support for scenario-indexed stochastic optimization. The `replicate(data, T)` multi-network facility creates T-period coupling (time steps), not scenario branching. There is no:

- Scenario tree representation
- Two-stage stochastic program formulation (`build_stochastic_opf`)
- Non-anticipativity constraint support
- Probability-weighted expected-value objective
- Dedicated stochastic data model

## Impact

Test A-8 is a **blocking fail**. The pass condition explicitly requires native stochastic structure as part of the optimization formulation. A loop over 600 independent deterministic solves (50 scenarios × 12 hours) does not constitute a stochastic program:

- Each scenario's dispatch is independent (no first-stage here-and-now coupling)
- Non-anticipativity is not enforced
- The resulting "policy" is 600 different dispatches, not one policy robust to uncertainty

## Workaround Durability

A loop-based workaround is stable (uses documented `solve_dc_opf` and deepcopy), but it is not equivalent to stochastic OPF. No extension package in the ecosystem at v0.21.5 fills this gap.

## Note for Grading

This is an intentional design boundary — PowerModels.jl is a deterministic steady-state OPF library. Stochastic programming extensions would require a separate framework (e.g., built on JuMP's stochastic programming capabilities or a dedicated package like `StochasticPrograms.jl`). The tool's scope is explicitly deterministic.
