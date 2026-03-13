---
tag: api-friction
source_dimension: expressiveness
source_test: A-10
tool: powermodels
severity: medium
timestamp: 2026-03-11T00:00:00Z
---

# Observation: DCPLLPowerModel Requires Ipopt — HiGHS Silently Incompatible

## Finding

`DCPLLPowerModel` cannot be solved with HiGHS. The solver rejects the model with `UnsupportedConstraint{ScalarQuadraticFunction{Float64}, GreaterThan{Float64}}` at the point of solve. Ipopt must be used instead. This is not documented in the PowerModels.jl API or the `DCPLLPowerModel` docstring.

## Context

Test A-10 (lossy DC OPF with LMP decomposition) requires `DCPLLPowerModel` to incorporate linearized branch loss terms. When HiGHS (the standard LP/QP solver) is used, it throws `UnsupportedConstraint` because DCPLLPowerModel introduces quadratic *constraints* (not just a quadratic objective). HiGHS supports QP objectives but not QCQP. Switching to Ipopt resolves the issue.

## Implications

- **Accessibility dimension (D-3/D-4):** New users will likely default to HiGHS and encounter a cryptic error with no guidance in the documentation. The error message does not mention "use Ipopt instead."
- **Scalability dimension (C-3):** Ipopt is an NLP solver and may be significantly slower than HiGHS for large networks. This is a performance concern for the SMALL/MEDIUM tier A-10 grade run.
- **Extensibility dimension:** Any user building a lossy DC OPF formulation on top of DCPLLPowerModel must be aware of this solver incompatibility.
