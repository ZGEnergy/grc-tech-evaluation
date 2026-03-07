---
test_id: F-5
tool: powermodels
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-06T00:00:00Z
---

# F-5: Code Inspectability Trace

## Result: PASS

## Finding

The full execution path from API call to solver invocation is traceable through pure Julia source code. No opaque steps exist between the user-facing API and the solver call. The only opaque boundary is the solver binary itself (e.g., libhighs.so), which is expected and standard.

## Evidence

**Traced execution path for `solve_dc_opf(data, HiGHS.Optimizer)`:**

1. **`PowerModels.solve_dc_opf()`** -- convenience wrapper, dispatches to `solve_opf()` with `DCPPowerModel` formulation type.

2. **`PowerModels.solve_opf(data, DCPPowerModel, optimizer)`** -- calls `solve_model()`.

3. **`PowerModels.solve_model()`** -- calls `instantiate_model()` then `optimize_model!()`.

4. **`PowerModels.parse_file(io)`** -- `/src/io/common.jl:17`. Detects file type (.m or .raw), dispatches to `parse_matpower()` or `parse_psse()`. Returns a `Dict{String, Any}` network data dictionary. All parsing logic is pure Julia.

5. **`PowerModels.instantiate_model(data, DCPPowerModel, build_opf)`** -- `/src/core/base.jl:47`. Creates a JuMP model, builds variables/constraints/objective per the formulation type. Key sub-calls:
   - `ref` computation (`/src/core/ref.jl`) -- builds reference dictionaries
   - `variable_*` functions (`/src/core/variable.jl`) -- creates JuMP decision variables
   - `constraint_*` functions (`/src/core/constraint_template.jl`, `/src/form/dcp.jl`) -- adds DC power flow constraints
   - `objective_*` functions (`/src/core/objective.jl`) -- sets cost objective

6. **`InfrastructureModels.optimize_model!(pm; optimizer=HiGHS.Optimizer)`** -- `/InfrastructureModels/src/core/base.jl:378`. Sets the optimizer on the JuMP model, calls `JuMP.optimize!()`.

7. **`JuMP.optimize!(model)`** -- translates JuMP model to MathOptInterface (MOI) representation, passes to solver-specific MOI wrapper.

8. **`HiGHS.Optimizer`**(MOI wrapper) -- pure Julia, calls `ccall` into `libhighs.so` to solve the LP/MIP.

9. **Solver binary**(`libhighs.so`) -- the only opaque step. Pre-compiled C++ binary. Source available at github.com/ERGO-Code/HiGHS.

**Module trace summary:**

| Step | Module | Source Location | Inspectable? |
|------|--------|-----------------|--------------|
| Parse | PowerModels | `/src/io/common.jl`, `/src/io/matpower.jl` | Yes (pure Julia) |
| Build model | PowerModels | `/src/core/base.jl`, `/src/form/dcp.jl` | Yes (pure Julia) |
| Optimize | InfrastructureModels | `/src/core/base.jl` | Yes (pure Julia) |
| JuMP dispatch | JuMP | JuMP/src/optimizer_interface.jl | Yes (pure Julia) |
| MOI bridge | MathOptInterface | MOI/src/ | Yes (pure Julia) |
| Solver wrapper | HiGHS.jl | HiGHS/src/ | Yes (pure Julia + ccall) |
| Solver engine | libhighs.so | Binary | Source available, not directly inspectable at runtime |

**Verified via live execution:**

```

result = PowerModels.solve_dc_opf(data, HiGHS.Optimizer)
# Termination: OPTIMAL
# Objective: 17613.21587795645

```

## Implications

The entire path from data parsing through model construction to solver invocation is implemented in inspectable Julia source code. The only opaque component is the solver binary, which is an expected boundary. Users can inspect and modify any part of the modeling pipeline. Julia's multiple dispatch makes it straightforward to trace which method is called at each step using `methods()` and `@which`.
