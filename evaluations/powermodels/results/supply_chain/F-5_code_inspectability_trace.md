---
test_id: F-5
tool: powermodels
dimension: supply_chain
status: pass
timestamp: 2026-03-05
---

# F-5: Code Inspectability Trace

## Finding

The full code path from `solve_dc_opf()` through JuMP to HiGHS is entirely inspectable in pure Julia source code down to the solver JLL boundary. All intermediate layers are open-source Julia packages with readable source.

## Evidence

**Call trace for `solve_dc_opf("case3.m", HiGHS.Optimizer)`**:

1. **PowerModels.jl** (`src/prob/opf.jl`): `solve_dc_opf(file, optimizer)` calls `solve_opf(file, DCPPowerModel, optimizer)`
2. **PowerModels.jl** (`src/prob/opf.jl`): `solve_opf()` calls `solve_model(data, model_type, optimizer, build_opf)`
3. **PowerModels.jl** (`src/core/base.jl`): `solve_model()` instantiates `JuMP.Model(optimizer)`, calls `build_opf(pm)` to add variables/constraints/objective
4. **PowerModels.jl** (`src/prob/opf.jl`): `build_opf(pm)` calls:
   - `variable_bus_voltage(pm)` -- DC voltage angles
   - `variable_gen_power(pm)` -- generator dispatch variables
   - `variable_branch_power(pm)` -- branch flow variables
   - `constraint_*` functions -- Kirchhoff's laws, thermal limits, etc.
   - `objective_min_fuel_and_flow_cost(pm)` -- cost objective
5. **JuMP.jl** (`src/JuMP.jl`): Model receives variables, constraints, and objective via MathOptInterface (MOI) abstraction
6. **MathOptInterface.jl**: Translates JuMP model to solver-specific representation
7. **HiGHS.jl** (`src/HiGHS.jl`): Julia wrapper calling into HiGHS_jll via `ccall`
8. **HiGHS_jll**: Pre-compiled HiGHS C++ library (MIT licensed, source at github.com/ERGO-Code/HiGHS)

**All modules in the trace**:

| Layer | Package | License | Source Available |

|-------|---------|---------|-----------------|

| Problem | PowerModels.jl | BSD-3 (LANL) | Yes (Julia) |

| Data model | InfrastructureModels.jl | BSD (LANL) | Yes (Julia) |

| Optimization | JuMP.jl | MPL-2.0 | Yes (Julia) |

| Interface | MathOptInterface.jl | MIT | Yes (Julia) |

| Solver wrapper | HiGHS.jl | MIT | Yes (Julia) |

| Solver binary | HiGHS_jll | MIT | Yes (C++, Yggdrasil build) |

Source: PowerModels.jl source code, JuMP.jl documentation

## Implications

The entire stack from user-facing API to solver call is inspectable. The only opaque boundary is the HiGHS_jll binary itself, which is built from open source via Yggdrasil with reproducible build recipes. This is an excellent inspectability profile -- comparable to or better than Python alternatives where C extensions are common.
