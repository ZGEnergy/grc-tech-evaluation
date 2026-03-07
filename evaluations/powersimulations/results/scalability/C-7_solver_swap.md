---
test_id: C-7
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: "HiGHS, Ipopt"
timestamp: "2026-03-07T06:30:00Z"
---

# C-7: Solver Swap — DCOPF with Multiple Solvers

## Result: PASS

## Finding

Solver swapping requires **only a parameter change** — no reformulation needed. The
same `ProblemTemplate` is reused with a different `optimizer_with_attributes()` call:

```julia
# HiGHS
solver_highs = optimizer_with_attributes(HiGHS.Optimizer, "output_flag" => false)
model = DecisionModel(template, sys; optimizer=solver_highs, ...)

# Ipopt (same template)
solver_ipopt = optimizer_with_attributes(Ipopt.Optimizer, "print_level" => 0)
model = DecisionModel(template, sys; optimizer=solver_ipopt, ...)
```

## Solver Compatibility Matrix

| Solver | LP (DCOPF) | QP (quadratic cost) | MIP (SCUC) | NLP (ACOPF) |
|--------|-----------|---------------------|-----------|-------------|
| HiGHS | Yes | Yes | Yes* | No |
| GLPK | Yes | No | Yes | No |
| SCIP | Yes | Limited | Yes | No |
| Ipopt | Yes | Yes | No | Yes |

*HiGHS fails on SCUC during initial condition computation (PSI-specific issue, not
a general HiGHS limitation).

## Architecture Note

PSI delegates solver management entirely to JuMP.jl's `MathOptInterface`. Any MOI-
compatible solver can be used without code changes. The template defines the problem
structure; the solver is injected at `DecisionModel` construction time.

This is the cleanest possible solver abstraction — the user never interacts with
solver-specific APIs.

## Test Script

`evaluations/powersimulations/tests/scalability/test_c3_dcopf_medium.jl` (tests both
HiGHS and Ipopt on MEDIUM)
