---
tag: solver-issues
source_dimension: scalability
source_test: C-7
tool: powermodels
severity: medium
timestamp: 2026-03-13T12:00:00Z
---

# Observation: SCIP crashes on dual extraction in PowerModels DC OPF

## Finding

SCIP.jl v0.11.6 does not support `MathOptInterface.ConstraintDual` attribute extraction. When PowerModels/InfrastructureModels attempts to build the solution result dict after SCIP has solved optimally, it unconditionally tries to extract dual values, causing a `MathOptInterface.GetAttributeNotAllowed` error. The `duals` output setting in PowerModels' solve settings does not prevent this crash.

## Context

During C-7 (solver swap on MEDIUM 10k-bus network), SCIP successfully solved the DC OPF to optimality (obj=$2,401,337.08 per solver log, 25.89s). However, the `PowerModels.solve_dc_opf` call crashes during `build_solution` → `build_solution_values` when InfrastructureModels tries to call `dual()` on JuMP constraint references backed by SCIP.

The crash occurs at `InfrastructureModels/src/core/solution.jl:164` in `build_solution_values`, which calls `dual(con_ref)` unconditionally. Even setting `Dict("output" => Dict("duals" => false))` does not prevent this because the dual extraction is part of the general solution building pipeline in InfrastructureModels v0.7.8.

## Implications

1. **Solver swap is not fully transparent for SCIP:** While the solver swap mechanism itself is a one-line parameter change (no reformulation needed), SCIP cannot be used as a drop-in replacement for HiGHS/GLPK/Ipopt with the standard `solve_dc_opf` API. Users must use the two-level API (`instantiate_model` + `optimize_model!` with custom solution extraction) to avoid the crash.

2. **Accessibility impact:** Users who try to swap to SCIP will encounter an opaque error with no guidance on the workaround. The error message mentions `ConstraintDual` but does not suggest disabling duals or using a different API path.

3. **This is a compatibility gap between SCIP.jl and InfrastructureModels**, not a PowerModels design flaw per se. However, it means the "parameter-only solver swap" claim from JuMP/MOI has a practical exception.
