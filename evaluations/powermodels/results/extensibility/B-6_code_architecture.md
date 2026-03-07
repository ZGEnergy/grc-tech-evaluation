---
test_id: B-6
tool: powermodels
dimension: extensibility
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-07T00:00:00Z
---

# B-6: Code Architecture Review

## Result: PASS

## Finding

PowerModels.jl exhibits a cleanly layered architecture with five distinct abstraction layers separating network model, problem formulation, solver interface, and results. Internal interfaces are partially documented: type definitions carry academic citations and docstrings, template functions have inline docstrings, but many formulation methods use only single-line string docs. The separation of concerns is exemplary for extensibility -- each layer can be replaced or extended independently via Julia's multiple dispatch.

## Evidence

### DCPF Solve Path Trace (JuMP-based path)

The call chain for `solve_dc_pf(file, optimizer)` traverses five layers across two packages (PowerModels.jl and InfrastructureModels.jl):

**Layer 1: API Entry (prob/pf.jl:7-8)**

```

solve_dc_pf(file, optimizer) → solve_pf(file, DCPPowerModel, optimizer)

```

Convenience function that binds the formulation type `DCPPowerModel` and delegates to the generic `solve_pf`.

**Layer 2: Lifecycle Orchestration (prob/pf.jl:12-13 → core/base.jl:15-39)**

```

solve_pf(file, model_type, optimizer) → solve_model(file, model_type, optimizer, build_pf)

```

`solve_model` (core/base.jl:20-39) is the universal lifecycle driver. It:
1. Calls `instantiate_model(data, model_type, build_method; ref_extensions=...)` (line 31)
2. Calls `optimize_model!(pm; optimizer=optimizer, solution_processors=...)` (line 35)

**Layer 3: Model Instantiation (core/base.jl:47-49 → InfrastructureModels/src/core/base.jl:350-375)**
`instantiate_model` delegates to `_IM.instantiate_model` which:
1. Creates the typed model object via `InitializeInfrastructureModel(model_type, data, global_keys, it)` -- this constructs a `DCPPowerModel` instance with an empty JuMP model
2. Builds the `ref` dictionary by calling `ref_add_core!` (core/base.jl:87-186) -- filters inactive components, builds arc/bus lookup tables
3. Runs any user-supplied `ref_extensions`
4. Calls `build_method(imo)` -- i.e., `build_pf(pm)` from prob/pf.jl:17

**Layer 4: Problem Specification + Formulation Dispatch (prob/pf.jl:17-73 + form/dcp.jl + form/apo.jl)**

`build_pf(pm::AbstractPowerModel)` is formulation-agnostic. It calls template functions that dispatch on `pm`'s concrete type:

- `variable_bus_voltage(pm)` -- template in core/variable.jl; dispatches to **form/dcp.jl:6-9** for `AbstractDCPModel`, which calls `variable_bus_voltage_angle` (creates JuMP `va` variables) and sets `vm` fixed to 1.0
- `variable_gen_power(pm)` -- creates `pg` variables (active power only for DC)
- `expression_branch_power_ohms_yt_from(pm, i)` -- template in core/expression_template.jl:67-90 extracts branch parameters (`g`, `b`, `tr`, `ti`, `g_fr`, `b_fr`, `tm`), then dispatches to **form/dcp.jl:55-61** which creates the expression `p[f_idx] = -b*(va_fr - va_to)`
- `constraint_power_balance(pm, i)` -- template in core/constraint_template.jl:171-188 extracts bus data, then dispatches to **form/apo.jl:58-80** for `AbstractActivePowerModel`, which adds the JuMP constraint: `sum(p[arcs]) == sum(pg[gens]) - sum(pd) - sum(gs)`
- `constraint_theta_ref(pm, i)` -- fixes voltage angle at reference bus
- `constraint_voltage_magnitude_setpoint` -- **no-op** for `AbstractDCPModel` (form/dcp.jl:30)

The template layer (constraint_template.jl, expression_template.jl) extracts data from `ref`, while the formulation layer (form/dcp.jl, form/apo.jl) builds JuMP expressions/constraints. This is a clean two-tier dispatch.

**Layer 5: Solve + Solution Extraction (InfrastructureModels/src/core/base.jl:378-420 + solution.jl:2-33)**

`optimize_model!` (InfrastructureModels):
1. Optionally relaxes integrality
2. Sets the JuMP optimizer
3. Calls `JuMP.optimize!(aim.model)` -- the actual solver invocation
4. Calls `build_result(aim, solve_time)` which extracts termination status, objective, and calls `build_solution` to read JuMP variable values back into the PowerModels Dict format
5. `solution_preprocessor` (PowerModels core/solution.jl:1-8) adds `per_unit` and `baseMVA` metadata

### Alternative DCPF Path (matrix-based, no optimizer)

`compute_dc_pf(data)` (prob/pf.jl:88-131) bypasses JuMP entirely:
1. Calls `reference_bus(data)` to find the slack bus
2. Calls `calc_bus_injection_active(data)` for net injection vector
3. Calls `calc_susceptance_matrix(data)` for the B matrix
4. Calls `solve_theta(sm, ref_idx, bi_idx)` -- direct linear solve via Julia's `\` operator
5. Assembles result dict manually

This path has only 2 layers (API + linear algebra) and demonstrates that the architecture does not force users through the JuMP optimization stack.

### Abstraction Layer Count: 5 (JuMP path)

| # | Layer | Location | Responsibility |
|---|-------|----------|----------------|
| 1 | API convenience | `prob/pf.jl` | Bind formulation type, expose user-facing functions |
| 2 | Lifecycle orchestration | `core/base.jl` | Parse, instantiate, optimize, build result |
| 3 | Model instantiation + ref building | `InfrastructureModels/base.jl` + `core/base.jl:ref_add_core!` | JuMP model creation, network data preprocessing |
| 4 | Problem spec + formulation dispatch | `prob/pf.jl:build_pf` + `core/*_template.jl` + `form/dcp.jl` | Variable/constraint/expression creation via type dispatch |
| 5 | Solve + solution extraction | `InfrastructureModels/base.jl:optimize_model!` + `solution.jl` | JuMP.optimize!, result packaging |

### Separation of Concerns Assessment

| Concern | Separated? | Mechanism |
|---------|-----------|-----------|
| Network model (data) | Yes | `ref` dict built by `ref_add_core!`, isolated from formulation |
| Problem formulation | Yes | `build_pf` in `prob/` is formulation-agnostic; specifics in `form/` |
| Solver interface | Yes | JuMP provides solver abstraction; optimizer passed as parameter |
| Results extraction | Yes | `build_result` + `build_solution` + `solution_preprocessor` in dedicated files |
| Data parsing (I/O) | Yes | Separate `io/` directory with format-specific parsers |

### Internal Interface Documentation

- **Type hierarchy**(types.jl): 16 multi-line docstrings with academic citations for each formulation type. Well-documented.
- **ref_add_core!**(base.jl:58-86): Extensive docstring listing all keys in the ref dictionary. This is the primary internal data interface and is well-documented.
- **Template functions**(constraint_template.jl, expression_template.jl): Mix of single-line string docs (`"..."`) and multi-line docstrings. ~32 multi-line docstrings across 984 lines in constraint_template.jl.
- **Formulation methods**(form/dcp.jl): 4 multi-line docstrings across 420 lines. Many functions have only single-line string docs or inline comments explaining the math (e.g., `p[f_idx] == -b*(t[f_bus] - t[t_bus])`).
- **Lifecycle functions**(base.jl): `solve_model`, `instantiate_model` have single-line docs; `ref_add_core!` has full documentation. The `optimize_model!` function in InfrastructureModels has no docstring.
- **Overall**: Partial documentation. Key interfaces (types, ref dict) are well-documented. Mid-level dispatch functions have lightweight docs. Some critical functions like `optimize_model!` lack docstrings.

### Source Code Scale

Key files in the DCPF path total ~4,440 lines across 8 files. The full PowerModels source is approximately 14,000 lines. InfrastructureModels adds ~1,500 lines of framework infrastructure.

## Implications

The five-layer architecture with clean separation via Julia's type dispatch system is a strong indicator of extensibility. Users can:
- Add new formulations by defining a new type and implementing dispatch methods
- Add new problem types by writing a new `build_*` function
- Swap solvers by changing the optimizer parameter
- Extend the ref dictionary via `ref_extensions`
- Post-process solutions via `solution_processors`

The partial documentation is a minor concern -- the type hierarchy and ref dict are well-documented, which are the primary extension points. The formulation dispatch pattern is consistent enough to be learned by example even where docstrings are sparse.
