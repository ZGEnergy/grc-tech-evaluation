# powermodels — Research: Extensions & Architecture

## Key Findings

- PowerModels is built on a **two-level extension model**: (1) subtype `AbstractPowerModel` to add a new mathematical formulation, and (2) write a custom `build_*` function that calls variable/constraint templates. No plugin registration or callback registry is needed — Julia multiple dispatch is the extension mechanism.
- The `instantiate_model(data, ModelType, build_fn; ref_extensions=[...])` function accepts a `ref_extensions` array of functions that are called during reference-data preprocessing, providing a clean hook point for adding derived data structures (e.g., custom arc mappings, extra indexed sets) before the JuMP model is constructed.
- The **two-level API** (`instantiate_model` → `optimize_model!`) gives direct access to `pm.model` (the underlying JuMP model) between construction and solve. Custom JuMP constraints can be appended with `@constraint(pm.model, ...)` without any patching. Dual values are extractable via `JuMP.dual()`.
- There is **no native Graphs.jl integration**. Network graph structure must be built manually from `data["branch"]["f_bus"]` / `"t_bus"` fields. PowerModelsAnalytics.jl adds visualization (Vega-based) and exposes `build_network_graph`, but is a separate package not installed in the evaluation environment.
- **DataFrame interoperability is trivial**: results are plain Julia `Dict`s with string keys. Constructing a `DataFrame` from result dicts takes 3–4 lines per component type; no custom serialization is required.
- The **`ref_add_core!`** function (source: `src/core/base.jl`) is the canonical reference-data builder. It populates `:bus`, `:gen`, `:branch`, `:arcs_from`, `:arcs_to`, `:arcs`, `:bus_arcs`, `:buspairs`, and related lookup tables. Custom `ref_extensions` functions receive the same `ref` dict and can add arbitrary keys.
- **Constraint templates** (`src/core/constraint_template.jl`) decouple data extraction from mathematical formulation: each template function is defined over `AbstractPowerModel` and passes named scalar arguments to a formulation-specific method. Adding a custom constraint requires implementing only the formulation-specific method (or reusing the template pattern for a new formulation).
- **No distributed-slack support** in the native API. Implementing load-proportional distributed slack requires ~150 lines of manual JuMP code using `calc_basic_ptdf_matrix` as a building block.
- The **PTDF matrix is a first-class API**: `make_basic_network` + `calc_basic_ptdf_matrix` returns a dense `(branches × buses)` matrix. A single-row variant `calc_basic_ptdf_row(data, l)` is also available for memory-efficient access.
- The ecosystem follows the **InfrastructureModels.jl** pattern: `AbstractPowerModel <: _IM.AbstractInfrastructureModel`. Extension packages (PowerModelsDistribution, PowerModelsSecurityConstrained, PowerModelsAnnex, etc.) all subtype this hierarchy, enabling multi-infrastructure co-optimization through InfrastructureModels.

## Detailed Notes

### Extension via Julia Multiple Dispatch (Custom Formulations)

PowerModels uses Julia's type system as its extension mechanism. There is no plugin registry, no hook list, and no callback API. Instead:

1. Define a new abstract type: `abstract type MyModel <: AbstractPowerModel end` (or subtype an existing intermediate like `AbstractDCPModel`).
2. Define a concrete struct: `mutable struct MyPowerModel <: MyModel; @pm_fields; end`
3. Dispatch new variable/constraint methods on `MyModel` or `MyPowerModel` where the built-in implementations differ.
4. Write a `build_my_problem(pm::AbstractPowerModel)` function that composes variable and constraint calls.
5. Call: `instantiate_model(data, MyPowerModel, build_my_problem)`.

The `@pm_fields` macro (defined in `base.jl` via `_IM.@def`) injects the five standard fields: `model`, `data`, `setting`, `solution`, `ref`. Source: `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/base.jl`.

The type hierarchy defined in `src/core/types.jl` includes:
- `AbstractActivePowerModel <: AbstractPowerModel` (DC/active-only models)
- `AbstractConicModel <: AbstractPowerModel` (for SDP/conic solvers)
- `AbstractBFModel <: AbstractPowerModel` (branch-flow models)
- `AbstractACPModel <: AbstractPowerModel`, `AbstractDCPModel <: AbstractActivePowerModel`, etc.

### `ref_extensions` — Pre-Build Hook

`instantiate_model` delegates to `_IM.instantiate_model(data, model_type, build_method, ref_add_core!, _pm_global_keys, pm_it_sym; kwargs...)`. The `ref_extensions` keyword accepts an array of functions with signature `(ref::Dict{Symbol,Any}) -> nothing`. These are called after `ref_add_core!` populates the standard sets, allowing extensions to add custom lookup tables before any variables or constraints are built.

Example usage pattern (from PowerModelsDistribution):

```julia

pm = PowerModels.instantiate_model(data, ACPPowerModel, build_opf;
    ref_extensions=[my_custom_ref_fn!])

```

This is the documented hook for packages that extend PowerModels (e.g., PowerModelsDistribution uses `ref_add_arcs_trans!`). Source: `base.jl` line `_IM.instantiate_model(...)`.

### Two-Level API: `instantiate_model` + `optimize_model!`

The high-level `solve_*` functions (e.g., `solve_dc_opf`) are thin wrappers over `solve_model`, which calls `instantiate_model` then `optimize_model!`. Using the two-level API directly:

```julia

pm = PowerModels.instantiate_model(data, DCPPowerModel, PowerModels.build_opf)
jump_model = pm.model            # access the JuMP model
flow_var = PowerModels.var(pm, :p)[(br_idx, f_bus, t_bus)]
gate_con = @constraint(jump_model, flow_var <= gate_limit)
result = PowerModels.optimize_model!(pm; optimizer=optimizer)
dual_val = JuMP.dual(gate_con)   # dual extraction works

```

This pattern was confirmed working in test B-1 (`test_b1_custom_constraints.jl`): a flow gate constraint was added post-instantiation and its dual correctly reflected binding status.

Accessor functions on the `pm` object (all defined in `base.jl`, forwarding to `_IM`):
- `var(pm, key)` / `var(pm, nw, key)` — variable dictionary access
- `con(pm, key)` — constraint dictionary access
- `ref(pm, key)` — reference data access
- `sol(pm, key)` — solution data access
- `ids(pm, key)` — component ID iterator
- `nw_ids(pm)` — network IDs (for multi-network models)

### Build Function Architecture

A `build_*` function receives a typed `pm::AbstractPowerModel` argument and calls the compositional variable/constraint API. The canonical example from `src/prob/opf.jl`:

```julia

function build_opf(pm::AbstractPowerModel)
    variable_bus_voltage(pm)
    variable_gen_power(pm)
    variable_branch_power(pm)
    ...
    for i in ids(pm, :ref_buses)
        constraint_theta_ref(pm, i)
    end
    for i in ids(pm, :bus)
        constraint_power_balance(pm, i)
    end
    for i in ids(pm, :branch)
        constraint_ohms_yt_from(pm, i)
        ...
    end
end

```

A custom `build_*` function can call any subset of these, reorder them, or add custom JuMP constraints inline. There is no required superclass method or decorator.

### Constraint Template Pattern

Templates in `src/core/constraint_template.jl` are the indirection layer between data and math. A template:
1. Accepts `pm::AbstractPowerModel` and component index `i`.
2. Looks up parameters from `ref(pm, :branch, i)` or similar.
3. Calls the formulation-specific implementation passing scalar values.

```julia

function constraint_ohms_yt_from(pm::AbstractPowerModel, i::Int; nw=nw_id_default)
    branch = ref(pm, nw, :branch, i)
    g, b = calc_branch_y(branch)
    # ... extract more params ...
    constraint_ohms_yt_from(pm, nw, i, f_bus, t_bus, g, b, ...)
end

```

The formulation-specific implementation (e.g., for `DCPPowerModel`) is dispatched by type. To add a custom constraint for a new formulation type, only the formulation-specific method needs to be added — the template method is inherited.

### Graph Access

PowerModels has **no native Graphs.jl integration** (confirmed by test B-2 comment and `native_graph_api = false`). The `data` dict exposes topology through:
- `data["bus"]` — dict of bus dicts with voltage/type info
- `data["branch"]` — dict of branch dicts, each with `"f_bus"` and `"t_bus"` integer fields
- `PowerModels.calc_connected_components(data)` — returns array of connected component bus sets
- `PowerModels.connected_components(data)` (alias)
- `ref[:arcs]`, `ref[:bus_arcs]` — preprocessed arc tuples `(branch_id, from_bus, to_bus)`

For graph algorithms (BFS, shortest path, etc.), the adjacency structure must be built manually from branch endpoint data (~15 lines of Julia). The test B-2 implementation demonstrates this is straightforward.

**PowerModelsAnalytics.jl** (separate package, not installed) wraps network data into a graph structure and provides `build_network_graph` and `plot_network` via Vega.jl. It does not appear to expose a Graphs.jl-compatible interface based on available documentation. Source: <https://lanl-ansi.github.io/PowerModelsAnalytics.jl/stable/>

### DataFrame / CSV Interoperability

Results are returned as nested Julia `Dict{String,Any}` (test B-5). Converting to DataFrames requires only the standard `DataFrame(; col=[...])` constructor syntax — no custom serialization, no special adapters. Export pattern from `test_b5_interoperability.jl`:

```julia

bus_df = DataFrame(;
    bus_id=[parse(Int, id) for id in keys(sol["bus"])],
    va_rad=[bus["va"] for bus in values(sol["bus"])],
)
CSV.write(path, bus_df)

```

Assessment: "3–4 lines each (DataFrame constructor + sort + CSV.write). Custom serialization needed: false."

### Multi-Network / Stochastic Wrapping

`PowerModels.replicate(data, T)` deep-copies a single-network dict into a multi-network structure with `T` time periods accessible at `mn_data["nw"]["1"]` through `mn_data["nw"][string(T)]`. Each period's data can be mutated independently before calling `solve_mn_opf`. This is the documented approach for multi-period and stochastic problems (test B-4). No native stochastic decomposition (Benders, L-shaped) is provided.

### PTDF Matrix API

`PowerModels.calc_basic_ptdf_matrix(basic_data)` returns a dense `Float64` matrix of shape `(branches, buses)`. Prerequisite: `basic_data = PowerModels.make_basic_network(data)` which renumbers buses to contiguous 1:N. A row-level accessor `calc_basic_ptdf_row(data, l)` is also provided for memory-efficient single-row access. Confirmed working in test B-9 with max flow prediction error < 1e-6.

### Reference Bus Configuration

Single-slack reference bus change is trivial via data dict mutation (`bus_type` field: 3 = slack, 2 = PV). No model reconstruction. Distributed slack is not natively supported and requires ~150 lines of manual PTDF-based OPF via JuMP (test B-8).

### Ecosystem Extension Packages

Built on `InfrastructureModels.jl` (`AbstractPowerModel <: _IM.AbstractInfrastructureModel`). Known extension packages following the same pattern:

| Package | Scope |
|---|---|
| PowerModelsDistribution.jl | Unbalanced distribution networks |
| PowerModelsSecurityConstrained.jl | N-1 security constrained OPF |
| PowerModelsAnalytics.jl | Visualization (Vega-based) |
| PowerModelsAnnex.jl | Exploratory/experimental formulations |
| PowerModelsONM.jl | Outage management (depends on PMD) |
| GasPowerModels.jl | Gas+power co-optimization |
| PowerWaterModels.jl | Power+water co-optimization |

All extension packages create new `AbstractPowerModel` subtypes and use the same `instantiate_model` / `build_*` / `ref_extensions` API.

## Sources

1. `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/base.jl` — AbstractPowerModel definition, instantiate_model, var/con/ref/sol accessors, ref_add_core! implementation
2. `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/types.jl` — Abstract type hierarchy (AbstractActivePowerModel, AbstractBFModel, AbstractConicModel, etc.)
3. `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/constraint_template.jl` — Constraint template pattern with AbstractPowerModel dispatch
4. `/opt/julia-depot/packages/PowerModels/VCmhH/src/prob/opf.jl` — build_opf canonical build function structure
5. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b1_custom_constraints.jl` — Two-level API usage, custom constraint addition, dual extraction (v0.21.5)
6. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b2_graph_access.jl` — Graph access pattern, confirmation of no native Graphs.jl API
7. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b3_contingency_loop.jl` — deepcopy + data mutation for N-1 loop
8. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b4_stochastic_wrapping.jl` — replicate() + multi-period OPF
9. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b5_interoperability.jl` — DataFrame/CSV export pattern
10. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b7_ac_feasibility_extension.jl` — Mutable data dict workflow, no model reconstruction needed
11. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b8_reference_bus_config.jl` — Reference bus config via bus_type mutation; distributed slack workaround
12. `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/tests/extensibility/test_b9_ptdf_extraction.jl` — calc_basic_ptdf_matrix, make_basic_network, calc_basic_ptdf_row APIs
13. <https://lanl-ansi.github.io/PowerModels.jl/stable/> — Official documentation (v0.21, August 2025)
14. <https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/> — Type hierarchy, formulation listing
15. <https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/> — Two-level API (instantiate_model, optimize_model!, pm.model)
16. <https://lanl-ansi.github.io/PowerModels.jl/stable/specifications/> — Problem specification listing (build_opf, build_pf, build_tnep, etc.)
17. <https://lanl-ansi.github.io/PowerModels.jl/stable/constraints/> — Constraint template pattern documentation
18. <https://lanl-ansi.github.io/PowerModels.jl/stable/variables/> — Variable definition pattern
19. <https://lanl-ansi.github.io/PowerModels.jl/stable/multi-networks/> — replicate(), multi-network structure
20. <https://github.com/lanl-ansi/PowerModels.jl> — Repository (v0.21.5, 80 releases, 457 stars)
21. <https://github.com/lanl-ansi/InfrastructureModels.jl> — Base abstraction layer
22. <https://github.com/lanl-ansi/PowerModelsAnalytics.jl> — Visualization extension
23. <https://github.com/lanl-ansi/PowerModelsAnnex.jl> — Experimental extension
24. <https://lanl-ansi.github.io/PowerModelsAnalytics.jl/stable/quickguide/> — Analytics quickstart (visualization focus, limited graph API docs)
25. <https://arxiv.org/abs/1711.01728> — PowerModels.jl paper (Coffrin et al., 2018)

## Gaps and Uncertainties

- **Graphs.jl bridge status**: PowerModelsAnalytics.jl documentation focuses on visualization (Vega/plot_network). Whether it exposes a Graphs.jl-compatible type is not confirmed from available docs. This needs a direct source code check of `PowerModelsAnalytics.jl` if graph-algorithm interop matters.
- **`solution_processors` parameter**: `solve_model` accepts `solution_processors=[]` (an array of post-solve functions). The full API for writing custom solution processors was not explored. This could be relevant for automated result transformation.
- **`relax_integrality` parameter**: `optimize_model!` accepts `relax_integrality=true` to solve MIP relaxations. Interaction with custom constraints added post-instantiation was not tested.
- **`@pm_fields` downstream behavior**: Whether `@pm_fields` correctly captures all required fields when used in a downstream package that `import`s (vs `using`) PowerModels is noted in the source code comments as a known scope concern. Not verified empirically.
- **PowerModelsSecurityConstrained.jl activity**: The changelog URL was found but the package's current maintenance status and compatibility with v0.21 was not verified.
- **DataFrames round-trip fidelity**: The B-5 test verifies row counts but not numerical precision of the CSV round-trip. For production use, floating-point serialization precision should be checked.
- **Distributed slack natively**: Whether any recent version or extension package added native distributed slack support was not confirmed. The B-8 test documents it as absent in v0.21.5 but this may exist in PowerModelsAnnex.
