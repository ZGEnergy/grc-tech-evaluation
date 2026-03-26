---
test_id: F-5
tool: powermodels
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: "2026-03-13T23:01:54Z"
protocol_version: v10
skill_version: v1
test_hash: "6108ab51"
---

# F-5: Trace execution path from API call to solver invocation

## Finding

The call chain from `solve_ac_opf(data, Ipopt.Optimizer)` to the solver invocation is fully traceable through open-source Julia code with no opaque steps. Every module in the path is readable pure Julia source, with the sole transition to compiled code occurring at the Ipopt.jl `ccall` boundary into `libipopt.so`, which has publicly available source.

## Evidence

### Full call chain (representative: AC OPF with Ipopt):

1. **`PowerModels.solve_ac_opf(data, optimizer)`**
   File: `PowerModels/VCmhH/src/prob/opf.jl`
   Delegates to `solve_opf(data, ACPPowerModel, optimizer)`

2. **`PowerModels.solve_opf(data, ACPPowerModel, optimizer, build_opf)`**
   File: `PowerModels/VCmhH/src/prob/opf.jl`
   Calls `solve_model(data, model_type, optimizer, build_opf)`

3. **`PowerModels.solve_model(data, model_type, optimizer, build_method)`**
   File: `PowerModels/VCmhH/src/core/base.jl`
   Calls `instantiate_model(...)` then `optimize_model!(pm, ...)`

4. **`PowerModels.instantiate_model`**
   File: `PowerModels/VCmhH/src/core/base.jl`
   Delegates to `InfrastructureModels.instantiate_model(...)` which constructs the JuMP model and populates it via `build_opf(pm)`

5. **`build_opf(pm::AbstractPowerModel)`**
   File: `PowerModels/VCmhH/src/prob/opf.jl`
   Calls `variable_bus_voltage`, `variable_gen_power`, `variable_branch_power`, etc.
   (implementations in `PowerModels/src/core/variable.jl`, `form/acp.jl`, `form/dcp.jl`, etc.)

6. **`InfrastructureModels.optimize_model!(aim; optimizer)`**
   File: `InfrastructureModels/C2xBM/src/core/base.jl`
   Calls `JuMP.set_optimizer(aim.model, optimizer)` then `JuMP.optimize!(aim.model)`

7. **`JuMP.optimize!(model)`**
   File: `JuMP/7eD71/src/optimizer_interface.jl` (pure Julia)
   Dispatches through MathOptInterface bridging layer

8. **`Ipopt.jl` MOI wrapper**
   File: `Ipopt/uSJxP/src/MOI_wrapper/MOI_wrapper.jl` (pure Julia)
   Calls `ccall((:IpoptSolve, libipopt), ...)` — transition to compiled code

9. **`libipopt.so` (C++ compiled binary)**
   Source: [github.com/coin-or/Ipopt](https://github.com/coin-or/Ipopt) (EPL 2.0)
   Interior-point NLP solver; calls `libmumps_seq.so` for sparse linear algebra

### Module summary:

| Module | Language | Source Location | Opaque? |
|--------|----------|-----------------|---------|
| PowerModels 0.21.5 | Pure Julia | `/opt/julia-depot/packages/PowerModels/VCmhH/src/` | No |
| InfrastructureModels 0.7.8 | Pure Julia | `/opt/julia-depot/packages/InfrastructureModels/` | No |
| JuMP 1.29.4 | Pure Julia | `/opt/julia-depot/packages/JuMP/7eD71/src/` | No |
| MathOptInterface 1.49.0 | Pure Julia | `/opt/julia-depot/packages/MathOptInterface/` | No |
| Ipopt.jl 1.14.1 (wrapper) | Pure Julia | `/opt/julia-depot/packages/Ipopt/uSJxP/src/` | No |
| libipopt.so (Ipopt_jll) | C++ compiled | JLL artifact | No — source available (EPL 2.0) |
| libmumps_seq.so (MUMPS_seq_jll) | Fortran/C compiled | JLL artifact | No — source available (CeCILL-C) |

### PowerModels source file organization:

The PowerModels package contains 42 Julia source files organized as:
- `core/` (12 files): base.jl, constraint.jl, variable.jl, objective.jl, ref.jl, solution.jl, types.jl, data.jl, admittance_matrix.jl, relaxation_scheme.jl, expression_template.jl, export.jl
- `form/` (11 files): acp.jl, acr.jl, act.jl, apo.jl, bf.jl, dcp.jl, iv.jl, lpac.jl, shared.jl, wr.jl, wrm.jl
- `io/` (5 files): common.jl, json.jl, matpower.jl, psse.jl, pti.jl
- `prob/` (10 files): opf.jl, pf.jl, ots.jl, tnep.jl, opb.jl, and their variants
- `util/` (2 files): flow_limit_cuts.jl, obbt.jl

**No opaque binary steps** identified. The architecture cleanly separates model construction (PowerModels) from optimization dispatch (JuMP/MOI) from solver execution (JLL binaries). Each layer is independently inspectable.

## Implications

The complete execution path is readable and inspectable. An evaluation team member can trace model construction through PowerModels' Julia source, follow the JuMP/MOI translation layer, and see exactly how the optimization problem is handed to the solver. The `ccall` boundary into `libipopt.so` is the only transition to compiled code, and that binary's source is publicly available. This is an excellent result for code inspectability.
