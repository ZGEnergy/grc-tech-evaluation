# Observation: arch-quality — Two-level API enables clean custom constraint injection

**Tag:** arch-quality
**Dimension:** extensibility
**Test:** B-1
**Severity:** positive

## Finding

PowerModels' `instantiate_model` + `optimize_model!` two-level API provides a clean, documented hook for custom constraint injection. The intermediate `pm.model` object is a standard JuMP `Model`, so any JuMP constraint syntax (`@constraint`, `@objective`, etc.) works directly without any PowerModels-specific adapter.

Dual extraction via `JuMP.dual()` works correctly on custom constraints added this way. The non-binding case produced exactly zero duals; the binding case produced a non-zero dual (900.96) with the correct sign and magnitude.

This design — using JuMP as the constraint model and exposing it directly — means PowerModels inherits all of JuMP's extensibility for free: custom constraints, callback hooks, objective modifications, and dual extraction all work without additional PowerModels-specific API surface.

## Evidence

- B-1 test (binding case): `JuMP.dual(gate_lower) = 900.961`, objective increase = 1,428.07
- B-1 test (non-binding case): `JuMP.dual(gate_upper) = JuMP.dual(gate_lower) = 0.0`
- API call: `pm = instantiate_model(...)` then `@constraint(pm.model, ...)` then `optimize_model!`
- Source: documented in PowerModels quickguide (`https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/`)

## Implication

Positive architecture finding. PowerModels' use of JuMP as the underlying model layer is a force-multiplier for extensibility: any valid JuMP operation works on the PowerModels model. This is a strong design choice that other tools (which wrap solvers more tightly) do not share.
