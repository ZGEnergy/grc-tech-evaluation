---
test_id: F-5
tool: powermodels
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: "2026-03-11T00:00:00Z"
protocol_version: "v9"
skill_version: v1
test_hash: "6108ab51"
---

# F-5: Trace execution path from API call to solver invocation; identify all modules

## Finding

The call chain from `solve_ac_opf(data, ACPPowerModel, Ipopt.Optimizer)` to the solver invocation is fully traceable through open-source Julia code with no opaque steps. Every module in the path is readable pure Julia, with the exception of the final `Ipopt.optimize!` call that invokes the compiled `libipopt.so` via `ccall`. That C library has publicly available source.

## Evidence

### Full call chain (source file references in `/opt/julia-depot/packages/`):

1. **`PowerModels.solve_ac_opf(data, optimizer)`**
   File: `PowerModels/VCmhH/src/prob/opf.jl:2`
   → delegates to `solve_opf(file, ACPPowerModel, optimizer)`

2. **`PowerModels.solve_opf(data, ACPPowerModel, optimizer, build_opf)`**
   File: `PowerModels/VCmhH/src/prob/opf.jl:10`
   → calls `solve_model(data, model_type, optimizer, build_opf)`

3. **`PowerModels.solve_model(data, model_type, optimizer, build_method)`**
   File: `PowerModels/VCmhH/src/core/base.jl:20`
   → calls `instantiate_model(...)` then `optimize_model!(pm, ...)`

4. **`PowerModels.instantiate_model`**
   File: `PowerModels/VCmhH/src/core/base.jl:44`
   → delegates to `InfrastructureModels.instantiate_model(...)` which constructs the JuMP model and populates it via `build_opf(pm)`

5. **`build_opf(pm::AbstractPowerModel)`**
   File: `PowerModels/VCmhH/src/prob/opf.jl:16`
   → calls `variable_bus_voltage`, `variable_gen_power`, `variable_branch_power`, etc. (all in `PowerModels/VCmhH/src/core/` and `form/`) to add JuMP variables and constraints

6. **`InfrastructureModels.optimize_model!(aim; optimizer)`**
   File: `InfrastructureModels/C2xBM/src/core/base.jl:378`
   → calls `JuMP.set_optimizer(aim.model, optimizer)` then `JuMP.optimize!(aim.model)`

7. **`JuMP.optimize!(model)`**
   File: `JuMP/7eD71/src/optimizer_interface.jl` (pure Julia)
   → dispatches through `MathOptInterface` to `Ipopt.jl`'s MOI bridge

8. **`Ipopt.jl` MOI bridge**
   File: `Ipopt/uSJxP/src/MOI_wrapper/MOI_wrapper.jl`
   → calls `Ipopt.solve(prob)` which invokes `ccall((:IpoptSolve, libipopt), ...)` in `libipopt.so`

9. **`libipopt.so` (C++ compiled binary)**
   Source: <https://github.com/coin-or/Ipopt> (EPL 2.0)
   → Interior-point NLP solve, calls `libmumps_seq.so` for sparse linear algebra

#### Module summary:

| Module | Language | Opaque? |
|--------|----------|---------|
| PowerModels | Pure Julia | No |
| InfrastructureModels | Pure Julia | No |
| JuMP | Pure Julia | No |
| MathOptInterface | Pure Julia | No |
| Ipopt.jl (wrapper) | Pure Julia | No |
| Ipopt_jll / libipopt.so | C++ compiled | No — source available |
| MUMPS_seq_jll / libmumps.so | Fortran/C compiled | No — source available |

**No opaque binary steps** identified. The transition from pure Julia to compiled code at the `Ipopt.jl ccall` boundary is fully documented and the underlying binary source is publicly available under EPL 2.0.

## Implications

The complete execution path is readable and inspectable. Any evaluation team member can trace model construction through JuMP, follow the MOI translation layer, and see exactly how the NLP problem is handed to Ipopt. The architecture is well-separated: PowerModels builds the optimization model as JuMP code, JuMP/MOI translates it to solver format, and the solver executes it. This is an excellent result for code inspectability.
