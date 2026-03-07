---
test_id: F-5
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# F-5: Code Inspectability Trace

## Method

Traced the execution path from a typical API call (`DecisionModel` build and solve) through to solver invocation.

## Execution Path

A typical DC-OPF solve follows this path:

```
User code (Julia)
  -> PowerSimulations.jl  (problem construction, device formulations)
    -> PowerSystems.jl     (system data model, component iteration)
    -> JuMP.jl             (optimization model construction, variable/constraint creation)
      -> MathOptInterface.jl  (solver-independent optimization interface)
        -> HiGHS.jl / SCIP.jl / Ipopt.jl  (solver-specific wrapper)
          -> HiGHS_jll / SCIP_jll / Ipopt_jll  (compiled solver via ccall)
            -> Solver C/C++ library (actual solve)
  -> PowerSimulations.jl  (result extraction, DataFrame construction)
    -> DataFrames.jl       (tabular result storage)
```

### Module-by-Module Inspectability

| Layer | Language | Source Inspectable | Notes |
|-------|----------|-------------------|-------|
| PowerSimulations.jl | Julia | Yes | All formulation logic, device models, constraints |
| PowerSystems.jl | Julia | Yes | Data parsing, component types |
| InfrastructureSystems.jl | Julia | Yes | Time series, logging, serialization |
| JuMP.jl | Julia | Yes | Model construction, macros (@variable, @constraint) |
| MathOptInterface.jl | Julia | Yes | Bridging, reformulation, solver abstraction |
| HiGHS.jl | Julia | Yes | Thin wrapper, maps MOI interface to C API |
| HiGHS C library | C++ | Yes (source available) | Actual simplex/IPM/MIP algorithms |
| OpenBLAS | C/Fortran | Yes (source available) | Linear algebra kernels |
| MUMPS | Fortran | Yes (source available) | Sparse direct solver (used by Ipopt) |

### Opaque Steps

**None in the Julia layer.** All Julia code is distributed as source and is fully readable. Julia does not use bytecode or compiled-only distribution.

The only non-Julia code in the execution path is the solver C/C++ libraries themselves (HiGHS, SCIP, Ipopt, GLPK). These are called via Julia's `ccall` FFI mechanism. The source for all four solvers is publicly available and auditable.

### Julia-Specific Transparency

Julia's compilation model aids inspectability:
- All packages are distributed as source code (`.jl` files)
- `@code_lowered`, `@code_typed`, `@code_native` macros allow inspecting every compilation stage
- No `.so`/`.dll` precompiled Julia code is distributed -- precompilation happens locally
- Method dispatch is fully traceable via `@which`, `methods()`, `methodswith()`

## Assessment

The entire execution path from API to solver is inspectable. Julia source code is always distributed as readable text. Compiled solver binaries have publicly available source. No opaque or proprietary steps exist in the execution path. **Pass.**
