---
test_id: F-5
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "6108ab51"
status: informational
workaround_class: null
timestamp: "2026-03-14T00:00:00Z"
---

# F-5: Code Inspectability

## Result: INFORMATIONAL

## Summary

The full execution path from `DecisionModel` construction through `build!` and
`solve!` to solver invocation is traceable through open-source Julia code. The only
opaque steps are inside the compiled solver binaries (HiGHS, Ipopt, GLPK, SCIP),
which are the mathematical optimization engines. All orchestration, model
construction, and result extraction code is inspectable Julia source.

## Execution Path Trace

### 1. Model Construction

```
DecisionModel(template, sys; optimizer=HiGHS.Optimizer)
```

**Module:** `PowerSimulations` (`/opt/julia-depot/packages/PowerSimulations/89s3Q/src/operation/decision_model.jl`)

- Constructs the optimization container
- Stores the system data reference and problem template
- All Julia source, fully inspectable

### 2. Build Phase

```
build!(model; output_dir=...)
```

**Module:** `PowerSimulations` (`src/operation/decision_model.jl:364`)

- Iterates over template device formulations
- Calls device-specific `construct_device!` methods
- Each device formulation adds variables, constraints, and objectives to a JuMP model
- Network formulation adds power balance and flow constraints

**Sub-modules traversed:**
- `PowerSimulations/src/devices/` -- device formulation constructors (thermal, renewable, storage, etc.)
- `PowerSimulations/src/network_models/` -- network formulations (PTDF, copperplate, etc.)
- `PowerSimulations/src/services/` -- ancillary service formulations
- `PowerSystems` -- data model queries (generators, buses, branches)
- `InfrastructureSystems` -- time series management
- `JuMP` -- algebraic modeling layer

All modules are pure Julia. No compiled extensions in the build path.

### 3. Solve Phase

```
solve!(model)
```

**Module:** `PowerSimulations` (`src/operation/decision_model.jl:461`)

Calls `JuMP.optimize!(model)` internally. The call chain:

```
PowerSimulations.solve!
  -> JuMP.optimize!(jump_model)
    -> MathOptInterface.optimize!(backend)
      -> HiGHS.Optimizer (or other solver MOI wrapper)
        -> ccall into libhighs.so (compiled binary)
```

**Modules in the solve path:**

| Layer | Module | Source Available | Language |
|-------|--------|-----------------|----------|
| Orchestration | PowerSimulations | Yes | Julia |
| Algebraic modeling | JuMP v1.29.4 | Yes | Julia |
| Solver abstraction | MathOptInterface v1.49.0 | Yes | Julia |
| Solver wrapper | HiGHS.jl v1.21.1 | Yes | Julia |
| Solver engine | libhighs.so (HiGHS_jll) | Source available, binary opaque | C++ |

### 4. Result Extraction

After `solve!`, results are extracted via:

```
PowerSimulations result accessors
  -> JuMP.value() / JuMP.dual()
    -> MathOptInterface.get(attr)
      -> solver wrapper get method
        -> ccall into solver library
```

All result extraction code is Julia source. The solver returns numerical values
via its C API, which the Julia wrapper retrieves via `ccall`.

## Module Inventory

All modules in the critical path from model definition to solved results:

| Module | Version | License | Inspectable |
|--------|---------|---------|-------------|
| PowerSimulations | 0.30.2 | BSD-3-Clause | Yes, pure Julia |
| PowerSystems | 4.6.2 | BSD-3-Clause | Yes, pure Julia |
| InfrastructureSystems | 2.6.0 | BSD-3-Clause | Yes, pure Julia |
| PowerFlows | 0.9.0 | BSD-3-Clause | Yes, pure Julia |
| PowerNetworkMatrices | 0.12.1 | BSD-3-Clause | Yes, pure Julia |
| JuMP | 1.29.4 | MPL-2.0 | Yes, pure Julia |
| MathOptInterface | 1.49.0 | MIT | Yes, pure Julia |
| HiGHS.jl | 1.21.1 | MIT | Yes, Julia wrapper |
| GLPK.jl | 1.2.1 | GPL-3.0 | Yes, Julia wrapper |
| Ipopt.jl | 1.14.1 | MIT | Yes, Julia wrapper |
| SCIP.jl | 0.12.8 | MIT | Yes, Julia wrapper |

## Opaque Binary Steps

The **only** opaque steps in the entire execution path are the solver engines
themselves:

1. **HiGHS** (`libhighs.so`) -- simplex/IPM LP/MILP/QP solver
2. **Ipopt** (`libipopt.so`) -- interior-point NLP solver
3. **GLPK** (`libglpk.so`) -- simplex LP/MILP solver
4. **SCIP** (`libscip.so`) -- branch-and-cut MILP solver

These are industry-standard, peer-reviewed optimization solvers with publicly
available source code. The binary artifacts are compiled from pinned source
commits via Yggdrasil (see F-4). The solver internals implement well-documented
mathematical algorithms (simplex, interior point, branch-and-bound).

No other binary step exists in the path. Julia's JIT compilation of the Julia
source code is transparent -- users can inspect any method via `@code_lowered`,
`@code_typed`, or `@code_native` macros at the REPL.

## Inspectability Assessment

- **Fully inspectable (source-level):** 100% of Julia code in the path (~95% of code volume)
- **Source available but compiled:** Solver engines (~5% of code volume)
- **Proprietary/closed:** None (MKL is optional and not in the solve path)
