---
tag: api-friction
source_dimension: scalability
source_test: C-7
tool: powersimulations
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: Solver Parameter Name Inconsistency Across JuMP Solvers

## Finding

Solver-specific parameter names are completely different across the four tested solvers:
- HiGHS: `time_limit` (seconds, Float64)
- GLPK: `tm_lim` (milliseconds, Int)
- SCIP: `limits/time` (seconds, Float64)
- Ipopt: `max_wall_time` (seconds, Float64)

JuMP's `optimizer_with_attributes` abstraction handles the dispatch, but users must look up
each solver's documentation for parameter names and unit conventions. No unified parameter
mapping exists.

Additionally, GLPK's inability to handle quadratic objective functions is only discovered at
`build!` time (not at model definition time), requiring cost linearization for cross-solver
portability.

## Context

C-7 tests solver swap on MEDIUM (ACTIVSg 10k). All four solvers produce consistent objective
values ($3,659,662) with timing ranging from 11.6s (HiGHS) to 54.9s (GLPK).

## Implications

Medium severity. The parameter inconsistency is a JuMP/MathOptInterface ecosystem property,
not specific to PowerSimulations.jl. However, PSI does not provide any solver-agnostic
parameter abstraction on top of JuMP.
