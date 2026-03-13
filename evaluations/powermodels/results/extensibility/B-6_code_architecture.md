---
test_id: B-6
tool: powermodels
dimension: extensibility
network: N/A
protocol_version: "v9"
skill_version: v1
test_hash: 0f337d8d
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# B-6: Code Architecture Audit

## Result: PASS

## Approach

Source code audit of PowerModels.jl v0.21.5, tracing the DCPF solve path from API call to solver
invocation. Sources examined:

- `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/base.jl` — solve_model, instantiate_model, optimize_model!, ref_add_core!
- `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/types.jl` — AbstractPowerModel type hierarchy
- `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/constraint_template.jl` — constraint template pattern
- `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/variable.jl` — variable template pattern
- `/opt/julia-depot/packages/PowerModels/VCmhH/src/prob/opf.jl` — solve_opf, build_opf canonical implementations
- `/opt/julia-depot/packages/PowerModels/VCmhH/src/form/dcp.jl` — DCPPowerModel formulation-specific methods

## Abstraction Layers

PowerModels.jl has **four clearly separated abstraction layers**:

| Layer | File(s) | Responsibility |
|-------|---------|----------------|
| 1. Public API | `prob/opf.jl`, `prob/pf.jl` | One-line entry points (`solve_dc_opf`, `solve_ac_pf`). Dispatch on formulation type and delegate to `solve_model`. |
| 2. Model Lifecycle | `core/base.jl` | `solve_model` → `instantiate_model` → `optimize_model!`. Owns the solve-result pipeline, ref preprocessing, and solution processor hooks. |
| 3. Formulation (Build) | `prob/opf.jl` (`build_opf`), `core/constraint_template.jl`, `form/*.jl` | `build_opf` composes variable/constraint templates. Templates (Layer 3a) extract data from `ref`; formulation-specific methods (Layer 3b, dispatched by type) translate to JuMP math. |
| 4. Solver | JuMP / MOI | `optimize_model!` calls `JuMP.optimize!`. Solver identity is hidden behind MOI — any MOI-compliant solver is pluggable. |

### DCPF Solve Path (traced from API to solver)

```

1. solve_dc_opf(data, optimizer)          ← Layer 1 public API
     │
     └─ solve_opf(data, DCPPowerModel, optimizer)
          │
          └─ solve_model(data, DCPPowerModel, optimizer, build_opf)  ← Layer 2
               │
               ├─ instantiate_model(data, DCPPowerModel, build_opf)
               │    ├─ _IM.instantiate_model(...)  — calls ref_add_core!
               │    │    └─ ref_add_core!           — builds ref[:bus], ref[:gen],
               │    │                                  ref[:branch], ref[:arcs], etc.
               │    └─ build_opf(pm::DCPPowerModel)  ← Layer 3 build function
               │         ├─ variable_bus_voltage(pm)   — creates θ variables (DCP)
               │         ├─ variable_gen_power(pm)     — creates pg variables
               │         ├─ variable_branch_power(pm)  — creates p_br variables
               │         ├─ objective_min_fuel_and_flow_cost(pm)
               │         ├─ constraint_theta_ref(pm, ref_bus)
               │         ├─ constraint_power_balance(pm, i) for each bus
               │         └─ constraint_ohms_yt_from/to(pm, i) for each branch
               │              │
               │              └─ constraint_template.jl:           ← Layer 3a template
               │                   constraint_ohms_yt_from(pm::AbstractPowerModel, i)
               │                   → extracts g, b, tap, shift from ref(pm, :branch, i)
               │                   → calls constraint_ohms_yt_from(pm, nw, i, f_bus, t_bus, g, b, ...)
               │                        │
               │                        └─ form/dcp.jl:            ← Layer 3b formulation
               │                             constraint_ohms_yt_from(pm::AbstractDCPModel, ...)
               │                             → @constraint(pm.model, p_fr == (b+b_fr)/tap*(va_fr-va_to))
               │
               └─ optimize_model!(pm, optimizer=optimizer)          ← Layer 4 solver
                    └─ JuMP.optimize!(pm.model)
                         └─ MOI interface → HiGHS/Ipopt/GLPK/...

```

## Separation of Concerns

### Network model / problem formulation / solver interface / results are all separated:

| Concern | Mechanism | Separation Quality |
|---------|-----------|-------------------|
| Network data model | Parsed `Dict{String,Any}` + `ref` preprocessing in `ref_add_core!` | Clean — data never has formulation-specific types |
| Problem formulation | `build_opf` function + formulation type (e.g., `DCPPowerModel`) | Clean — `build_opf` is formulation-agnostic; dispatch handles differences |
| Solver interface | JuMP / MOI abstraction in `optimize_model!` | Clean — solver is a constructor argument; no solver-specific code in PowerModels |
| Results | `solution_processors` post-process `pm.solution`; `result` dict returned | Clean — result extraction happens after solve, not interleaved |

Key evidence:

1. **Data/formulation separation**: `constraint_ohms_yt_from(pm::AbstractPowerModel, i)` (template) receives only the `pm` handle and integer index `i`. It calls `ref(pm, :branch, i)` to extract data, then calls the formulation-specific implementation. The template never names `DCPPowerModel` — the formulation receives scalar parameters, not data dicts.

2. **Formulation/solver separation**: `optimize_model!` is a single generic function in `base.jl`. It calls `JuMP.optimize!(pm.model)` regardless of which `AbstractPowerModel` subtype `pm` is. Changing solver requires only changing the optimizer argument, not any model code.

3. **Results separation**: Solution extraction happens via `PowerModels._IM.sol_component_value` in `solution.jl` after `JuMP.optimize!`. The `result` dict is assembled separately from the optimization model.

## Internal Interface Documentation Quality

### Assessment: Good — primarily docstring coverage, formalization varies.

| Interface | Documentation | Quality |
|-----------|---------------|---------|
| `solve_model` | Full docstring with parameter descriptions | Good |
| `instantiate_model` | Full docstring | Good |
| `optimize_model!` | Full docstring | Good |
| `ref_add_core!` | Full docstring listing all populated ref keys (`:bus`, `:gen`, `:branch`, `:arcs_from`, etc.) | Excellent |
| `build_opf` | Empty docstring (`""`) — function signature only | Poor |
| Constraint templates (`constraint_ohms_yt_from`) | Brief docstring referencing IEEE formulation | Good |
| Formulation-specific implementations (`form/dcp.jl`) | No docstrings on most methods | Poor |
| `@pm_fields` macro | Source comment noting `_IM.@def` usage; no formal docstring | Minimal |

The internal doc gap is concentrated in `form/*.jl` — formulation-specific constraint methods have no docstrings. Developers extending PowerModels find the template-method split through source code reading, not documentation. The quickguide at <https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/> covers the two-level API but not how to write new formulation-specific methods.

## Extensibility Points

PowerModels exposes four documented extension hooks:

| Hook | Mechanism | Use case |
|------|-----------|----------|
| New formulation type | `abstract type MyModel <: AbstractPowerModel end` + `mutable struct MyPowerModel; @pm_fields; end` | Full new math model (e.g., new relaxation, AC variant) |
| Pre-build ref extensions | `instantiate_model(data, type, build_fn; ref_extensions=[fn!])` | Add derived data (custom arc sets, adjacency, pre-computed constants) before JuMP model is built |
| Custom build function | Write `build_my_problem(pm::AbstractPowerModel)` and pass to `instantiate_model` | Compose variable/constraint calls differently or add custom JuMP constraints |
| Post-instantiation JuMP access | `pm.model` (direct JuMP model handle) + `var(pm, :p)`, `con(pm, :ohms)` | Inject ad-hoc constraints or objectives after `instantiate_model`, before `optimize_model!` |

The fourth hook (direct JuMP model access) is the most powerful and the most commonly needed for one-off customizations. It was verified in test B-1 (custom flow gate constraint with dual extraction).

The extension pattern is idiomatic Julia — no plugin registry, no callback hooks, no inheritance-based override mechanism. Julia multiple dispatch is the extension mechanism. New formulations are added by defining new methods dispatched on the new type; existing methods are inherited without modification.

## Architecture Quality Summary

| Criterion | Assessment |
|-----------|------------|
| Number of abstraction layers | 4 (public API → model lifecycle → formulation build → solver) |
| Network model / formulation separated | Yes — data dict is formulation-agnostic; dispatch handles formulation differences |
| Formulation / solver interface separated | Yes — JuMP/MOI abstraction completely separates formulation code from solver selection |
| Results separated from model | Yes — solution extraction in post-solve pipeline, not in build_opf |
| Internal interfaces documented | Partially — public API well documented; formulation-specific methods lack docstrings |
| Extension via dispatch | Yes — idiomatic Julia; no plugin registry needed |
| `build_opf` docstring | Missing (empty string `""`) |
| `form/dcp.jl` method docstrings | Absent on most methods |

**Overall architecture quality: High.** The four-layer design is clean and consistent. Separation of concerns is well-enforced by the type system and dispatch mechanism. The main gap is docstring coverage on formulation-specific methods, which requires source code reading to understand the template-method split — mitigated by the well-maintained official documentation and academic paper.

## Test Script

**Path:** N/A — this is a documentation/source audit, not a functional test.

Source files audited:
- `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/base.jl`
- `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/types.jl`
- `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/constraint_template.jl`
- `/opt/julia-depot/packages/PowerModels/VCmhH/src/form/dcp.jl`
- `/opt/julia-depot/packages/PowerModels/VCmhH/src/prob/opf.jl`
