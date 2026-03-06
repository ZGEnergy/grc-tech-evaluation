# PowerModels.jl -- Research: Extensions & Architecture

## Key Findings

- PowerModels v0.21.5 is architected around a **strict separation of problem specifications from formulation details**, enabled by Julia's multiple dispatch on a deep abstract type hierarchy rooted at `AbstractPowerModel <: InfrastructureModels.AbstractInfrastructureModel`.
- Extension via **new formulations** requires only: (1) define an abstract type and concrete struct with `@pm_fields`, (2) implement formulation-specific constraint/variable methods that dispatch on your new type. No registration or plugin API needed -- Julia's type system IS the plugin system.
- Extension via **new problem types** requires writing a `build_<problem>(pm::AbstractPowerModel)` function that calls variable/constraint/objective functions, then passing it to `solve_model` or `instantiate_model`.
- The **constraint template pattern** (two-layer design) separates data extraction from mathematical formulation: templates defined on `AbstractPowerModel` extract network parameters, then call formulation-specific constraint implementations that dispatch on concrete types.
- **Full JuMP model access** is available via `pm.model` after `instantiate_model()`, enabling arbitrary inspection, modification, or addition of JuMP constraints/variables before solving.
- **`ref_extensions`** and **`solution_processors`** are callback arrays passed to `solve_model`/`instantiate_model`, allowing injection of custom reference data computation and solution post-processing without modifying PowerModels source.
- The **`ext` dictionary** (`pm.ext::Dict{Symbol,Any}`) on every model instance provides a typed extension point for storing arbitrary per-model state (used e.g., by `SparseSDPWRMPowerModel` for SDP decomposition data).
- **No Graphs.jl integration** exists. PowerModels implements its own graph algorithms (connected components via DFS) using adjacency lists built from the network data dictionary. Network topology is stored as bus/branch dictionaries, not graph objects.
- **No DataFrames.jl integration** exists. Results are returned as nested `Dict{String,Any}` structures. Conversion to DataFrames is trivial but manual.
- **PTDF matrix** is natively supported via `calc_basic_ptdf_matrix()` and `calc_basic_ptdf_row()`, plus incidence, admittance, susceptance, and Jacobian matrices. These require `make_basic_network()` preprocessing.

## Detailed Notes

### Architecture: Separation of Concerns

PowerModels has a clean four-layer architecture reflected in the source directory structure:

| Layer | Directory | Responsibility |

|-------|-----------|---------------|

| **I/O** | `src/io/` | Parsing MATPOWER `.m`, PSS/E `.raw`, JSON files |

| **Data/Ref** | `src/core/data.jl`, `ref.jl`, `data_basic.jl` | Network data validation, transformation, reference dict construction |

| **Formulations** | `src/form/` | Formulation-specific variable/constraint implementations (one file per formulation family) |

| **Problems** | `src/prob/` | Problem specifications that compose variables, constraints, and objectives |

The core modeling infrastructure (`base.jl`, `types.jl`, `variable.jl`, `constraint_template.jl`, `constraint.jl`, `objective.jl`, `solution.jl`) lives in `src/core/`.

Source: [PowerModels.jl main module](https://github.com/lanl-ansi/PowerModels.jl/blob/master/src/PowerModels.jl)

### Type Hierarchy and Multiple Dispatch

The type hierarchy is the primary extension mechanism. The full hierarchy (from `src/core/types.jl`):

```

AbstractInfrastructureModel  (InfrastructureModels.jl)
  +-- AbstractPowerModel  (src/core/base.jl)
        +-- AbstractActivePowerModel
        |     +-- AbstractDCPModel

        |           +-- DCPPowerModel (concrete)

        |           +-- AbstractDCMPPModel -> DCMPPowerModel

        |           +-- AbstractNFAModel -> NFAPowerModel

        |           +-- AbstractDCPLLModel -> DCPLLPowerModel

        +-- AbstractACPModel -> ACPPowerModel
        +-- AbstractACRModel -> ACRPowerModel
        |     +-- AbstractIVRModel -> IVRPowerModel

        +-- AbstractACTModel -> ACTPowerModel
        +-- AbstractLPACModel
        |     +-- AbstractLPACCModel -> LPACCPowerModel

        +-- AbstractWRModel (quadratic relaxations)
        |     +-- AbstractSOCWRModel -> SOCWRPowerModel

        |     +-- AbstractQCWRModel -> QCRMPowerModel, QCLSPowerModel

        +-- AbstractConicModel
        |     +-- AbstractSOCWRConicModel -> SOCWRConicPowerModel

        |     +-- AbstractWRMModel (SDP)

        |           +-- AbstractSDPWRMModel -> SDPWRMPowerModel

        |                 +-- AbstractSparseSDPWRMModel -> SparseSDPWRMPowerModel

        +-- AbstractBFModel (branch flow)
              +-- AbstractBFAModel -> BFAPowerModel
              +-- AbstractBFQPModel
              |     +-- AbstractSOCBFModel -> SOCBFPowerModel

              +-- AbstractBFConicModel
                    +-- AbstractSOCBFConicModel -> SOCBFConicPowerModel

```

Each concrete type is a `mutable struct` containing the standard fields injected by `@pm_fields` (which expands to `@im_fields` from InfrastructureModels): `model`, `data`, `setting`, `solution`, `ref`, `var`, `con`, `sol`, `sol_proc`, `ext`.

Source: [src/core/types.jl](https://github.com/lanl-ansi/PowerModels.jl/blob/master/src/core/types.jl), [src/core/base.jl](https://github.com/lanl-ansi/PowerModels.jl/blob/master/src/core/base.jl)

### How to Add a Custom Formulation (External Package)

To create a new formulation in a downstream package:

```julia
import PowerModels
import PowerModels: @pm_fields, AbstractPowerModel

# 1. Define type hierarchy
abstract type AbstractMyCustomModel <: AbstractPowerModel end
mutable struct MyCustomPowerModel <: AbstractMyCustomModel
    PowerModels.@pm_fields  # must be explicitly qualified for downstream packages
end

# 2. Implement formulation-specific methods via dispatch
function PowerModels.variable_bus_voltage(pm::AbstractMyCustomModel; kwargs...)
    # custom variable definitions using JuMP via pm.model
end

function PowerModels.constraint_ohms_yt_from(pm::AbstractMyCustomModel, n::Int, f_bus, t_bus, f_idx, t_idx, g, b, g_fr, b_fr, tr, ti, tm)
    # custom Ohm's law constraint
    p_fr = PowerModels.var(pm, n, :p, f_idx)
    JuMP.@constraint(pm.model, p_fr == ...)
end

# 3. Use with existing problem specs
result = PowerModels.solve_opf("case.m", MyCustomPowerModel, optimizer)

```

No registration step is needed. Julia's method dispatch automatically selects the most specific implementation.

Source: [PowerModels formulations documentation](https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/), [PowerModelsITD style guide](https://lanl-ansi.github.io/PowerModelsITD.jl/stable/developer/style.html)

### How to Add a Custom Problem Specification

```julia
function build_my_custom_opf(pm::AbstractPowerModel)
    PowerModels.variable_bus_voltage(pm)
    PowerModels.variable_gen_power(pm)
    PowerModels.variable_branch_power(pm)

    PowerModels.objective_min_fuel_and_flow_cost(pm)
    PowerModels.constraint_model_voltage(pm)

    for i in PowerModels.ids(pm, :ref_buses)
        PowerModels.constraint_theta_ref(pm, i)
    end
    for i in PowerModels.ids(pm, :bus)
        PowerModels.constraint_power_balance(pm, i)
    end
    for i in PowerModels.ids(pm, :branch)
        PowerModels.constraint_ohms_yt_from(pm, i)
        PowerModels.constraint_ohms_yt_to(pm, i)
        # Add custom constraints here:
        my_custom_constraint(pm, i)
    end
end

# Solve with any formulation
result = PowerModels.solve_model("case.m", ACPPowerModel, optimizer, build_my_custom_opf)

```

Source: [src/prob/opf.jl](https://github.com/lanl-ansi/PowerModels.jl/blob/master/src/prob/opf.jl) (reference implementation of `build_opf`)

### Constraint Template Pattern (Two-Layer Design)

**Layer 1 -- Template** (formulation-agnostic, extracts data):

```julia
# From constraint_template.jl -- dispatches on AbstractPowerModel
function constraint_power_balance(pm::AbstractPowerModel, i::Int; nw::Int=nw_id_default)
    bus = ref(pm, nw, :bus, i)
    # ... extract bus_arcs, bus_gens, bus_loads, bus_shunts, pd, qd, gs, bs ...
    constraint_power_balance(pm, nw, i, bus_arcs, bus_arcs_dc, bus_arcs_sw, bus_gens, bus_storage, bus_loads, bus_gs, bus_bs)
end

```

**Layer 2 -- Formulation** (formulation-specific, uses JuMP variables):

```julia
# From form/dcp.jl -- dispatches on AbstractDCPModel
function constraint_power_balance(pm::AbstractDCPModel, n::Int, i, bus_arcs, ...)
    p = var(pm, n, :p)
    pg = var(pm, n, :pg)
    # ... build JuMP constraint using pm.model ...
    JuMP.@constraint(pm.model, sum(p[a] for a in bus_arcs) == sum(pg[g] for g in bus_gens) - sum(pd ...))
end

```

Source: [constraint_template.jl](https://github.com/lanl-ansi/PowerModels.jl/blob/master/src/core/constraint_template.jl), [Constraints documentation](https://lanl-ansi.github.io/PowerModels.jl/stable/constraints/)

### ref_extensions Callback API

The `ref_extensions` parameter accepts an array of functions with signature `f(ref::Dict{Symbol,Any}, data::Dict{String,Any})`. These are called during model instantiation to inject additional pre-computed data into the `ref` dictionary.

Built-in examples:
- `ref_add_connected_components!` -- computes network connected components and adds `:components` key
- `ref_add_sm!` / `ref_add_sm_inv!` -- computes susceptance matrix (or its inverse) and adds `:sm` key

Usage:

```julia
result = solve_model(data, DCPPowerModel, optimizer, build_opf;
    ref_extensions=[ref_add_connected_components!, my_custom_ref_extension!])

```

Source: [src/core/base.jl](https://github.com/lanl-ansi/PowerModels.jl/blob/master/src/core/base.jl) lines 21-35, [src/prob/opf.jl](https://github.com/lanl-ansi/PowerModels.jl/blob/master/src/prob/opf.jl) `solve_opf_ptdf`

### solution_processors Callback API

The `solution_processors` parameter accepts an array of functions passed to `optimize_model!` from InfrastructureModels. These functions post-process the solution dictionary after optimization completes.

Usage:

```julia
result = solve_model(data, ACPPowerModel, optimizer, build_opf;
    solution_processors=[my_solution_postprocessor])

```

Source: [src/core/base.jl](https://github.com/lanl-ansi/PowerModels.jl/blob/master/src/core/base.jl) line 35

### ext Dictionary for Per-Model State

Every PowerModels instance has an `ext::Dict{Symbol,Any}` field (inherited from InfrastructureModels' `@im_fields`). This is the designated extension point for storing arbitrary per-model data.

Example from PowerModels itself (SDP decomposition in `src/form/wrm.jl`):

```julia
pm.ext[:SDconstraintDecomposition] = _SDconstraintDecomposition(groups, lookup_index, ordering)
# ... later accessed as:
decomp = pm.ext[:SDconstraintDecomposition]

```

Source: [InfrastructureModels base.jl](https://github.com/lanl-ansi/InfrastructureModels.jl/blob/master/src/core/base.jl), [src/form/wrm.jl](https://github.com/lanl-ansi/PowerModels.jl/blob/master/src/form/wrm.jl) lines 137, 146, 242

### JuMP Model Access

The underlying JuMP model is directly accessible:

```julia
pm = instantiate_model(data, ACPPowerModel, PowerModels.build_opf)
print(pm.model)  # inspect the full JuMP model

# Add custom JuMP constraints directly:
JuMP.@constraint(pm.model, sum(pm.var[:p][a] for a in some_arcs) <= limit)

# Or pass a pre-built JuMP model:
m = JuMP.Model()
result = solve_opf(data, DCPPowerModel, solver; jump_model=m)
println(m)  # inspect after solve

```

Source: [Getting Started guide](https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/), [tutorial notebook](https://github.com/lanl-ansi/tutorial-grid-science/blob/master/Class%20III%20-%20An%20introduction%20to%20PowerModels.jl.ipynb)

### InfrastructureModels.jl Relationship

PowerModels.jl depends on InfrastructureModels.jl (v0.6 or v0.7) as its foundational framework. InfrastructureModels provides:

- `AbstractInfrastructureModel` -- root type for all infrastructure models
- `@im_fields` / `@def` macros -- standard field injection for model structs
- `InitializeInfrastructureModel()` -- constructor for model instances
- `instantiate_model()` -- model building pipeline (ref construction, build method invocation)
- `optimize_model!()` -- solve + solution extraction pipeline
- `ref_initialize()` -- multi-infrastructure/multi-network ref dict construction
- Accessor functions: `ids()`, `ref()`, `var()`, `con()`, `sol()`, `nw_ids()`, `nws()`
- Multi-infrastructure data format support (the `"it"` key convention)

PowerModels delegates nearly all core infrastructure operations to InfrastructureModels. The `pm`-prefixed accessor functions in PowerModels (e.g., `ref(pm, :bus)`) are thin wrappers that inject the `pm_it_sym` infrastructure type symbol.

Source: [InfrastructureModels.jl](https://github.com/lanl-ansi/InfrastructureModels.jl), [src/core/base.jl](https://github.com/lanl-ansi/PowerModels.jl/blob/master/src/core/base.jl)

### Network Graph Access

PowerModels does **not** use Graphs.jl (or its predecessor LightGraphs.jl). It has zero dependency on any graph library. Instead:

- Network topology is stored as `Dict{String, Any}` with `"bus"`, `"branch"`, `"dcline"`, `"switch"` entries
- The `ref_add_core!` function pre-computes adjacency structures: `:arcs_from`, `:arcs_to`, `:arcs`, `:bus_arcs`, `:buspairs`
- Connected component analysis uses a custom DFS implementation in `calc_connected_components()` (in `src/core/data.jl`)
- Graph algorithms for SDP decomposition (chordal extension, maximal cliques, Prim's algorithm) are implemented inline in `src/form/wrm.jl`

To get a Graphs.jl graph from PowerModels data, you would need to manually construct it:

```julia
using Graphs
data = PowerModels.parse_file("case.m")
n_bus = length(data["bus"])
g = SimpleGraph(n_bus)
for (_, branch) in data["branch"]
    add_edge!(g, branch["f_bus"], branch["t_bus"])
end

```

Source: [src/core/data.jl](https://github.com/lanl-ansi/PowerModels.jl/blob/master/src/core/data.jl) lines 2476-2560

### PTDF and Network Matrix Utilities

PowerModels provides "basic" matrix utilities (require `make_basic_network()` preprocessing which enforces sequential 1-to-n numbering, single connected component, etc.):

| Function | Returns |

|----------|---------|

| `calc_basic_incidence_matrix(data)` | Sparse incidence matrix (+1 from, -1 to) |

| `calc_basic_admittance_matrix(data)` | Sparse complex admittance (Y-bus) matrix |

| `calc_basic_susceptance_matrix(data)` | Sparse real susceptance (B) matrix |

| `calc_basic_branch_susceptance_matrix(data)` | Sparse branch-to-bus susceptance matrix |

| `calc_basic_ptdf_matrix(data)` | Dense PTDF matrix (branches x buses) |

| `calc_basic_ptdf_row(data, branch_idx)` | Single PTDF row for one branch |

| `calc_basic_jacobian_matrix(data)` | AC power flow Jacobian matrix |

| `compute_basic_dc_pf(data)` | DC power flow solution via linear solve |

The PTDF implementation computes `B * B_inv` where `B` is the branch susceptance matrix and `B_inv` is the bus susceptance matrix inverse. For large networks (10,000+ buses), the dense matrix inverse can be slow; `calc_basic_ptdf_row()` provides a per-branch alternative.

Source: [Basic Data Utilities documentation](https://lanl-ansi.github.io/PowerModels.jl/stable/basic-data-utilities/), [src/core/data_basic.jl](https://github.com/lanl-ansi/PowerModels.jl/blob/master/src/core/data_basic.jl), [GitHub issue #728](https://github.com/lanl-ansi/PowerModels.jl/issues/728)

### DataFrames.jl Interoperability

There is **no built-in DataFrames.jl integration**. PowerModels results are returned as nested dictionaries:

```julia
result = solve_ac_opf("case.m", optimizer)
result["solution"]["bus"]["1"]["vm"]  # voltage magnitude at bus 1
result["solution"]["gen"]["1"]["pg"]  # active power output of gen 1

```

Manual conversion is straightforward:

```julia
using DataFrames
bus_df = DataFrame(
    bus_id = parse.(Int, keys(result["solution"]["bus"])),
    vm = [b["vm"] for b in values(result["solution"]["bus"])],
    va = [b["va"] for b in values(result["solution"]["bus"])]
)

```

### Ecosystem Extension Packages

The LANL-ANSI ecosystem builds on PowerModels via the same type dispatch mechanism:

| Package | Purpose | Extends |

|---------|---------|---------|

| [PowerModelsDistribution.jl](https://github.com/lanl-ansi/PowerModelsDistribution.jl) | Unbalanced (multi-phase) distribution network optimization | PowerModels type hierarchy for multi-conductor models |

| [PowerModelsAnnex.jl](https://github.com/lanl-ansi/PowerModelsAnnex.jl) | Exploratory/preliminary methods (relaxed quality standards) | PowerModels formulations and problems |

| [PowerModelsITD.jl](https://github.com/lanl-ansi/PowerModelsITD.jl) | Integrated transmission-distribution co-optimization | PowerModels + PowerModelsDistribution via multi-infrastructure |

| [PowerModelsONM.jl](https://github.com/lanl-ansi/PowerModelsONM.jl) | Networked microgrid operations under contingencies | PowerModelsDistribution |

| [PowerModelsGMD.jl](https://github.com/lanl-ansi/powermodelsgmd.jl) | Geomagnetically induced current (GMD) problems | PowerModels formulations |

| [PowerModelsStability.jl](https://github.com/lanl-ansi/PowerModelsStability.jl) | Small signal stability analysis | PowerModelsDistribution |

All ecosystem packages follow the same pattern: subtype the abstract hierarchy, implement dispatch methods, compose with existing problem specifications.

Source: [PowerModels README](https://github.com/lanl-ansi/PowerModels.jl), [PowerModelsITD style guide](https://lanl-ansi.github.io/PowerModelsITD.jl/stable/developer/style.html)

## Sources

1. [PowerModels.jl GitHub repository](https://github.com/lanl-ansi/PowerModels.jl) -- v0.21.5
2. [PowerModels.jl documentation (stable)](https://lanl-ansi.github.io/PowerModels.jl/stable/)
3. [PowerModels Quick Start Guide](https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/)
4. [PowerModels Formulations](https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/)
5. [PowerModels Constraints](https://lanl-ansi.github.io/PowerModels.jl/stable/constraints/)
6. [PowerModels Basic Data Utilities](https://lanl-ansi.github.io/PowerModels.jl/stable/basic-data-utilities/)
7. [PowerModels Problem Specifications](https://lanl-ansi.github.io/PowerModels.jl/stable/specifications/)
8. [InfrastructureModels.jl GitHub](https://github.com/lanl-ansi/InfrastructureModels.jl)
9. [PowerModelsDistribution.jl GitHub](https://github.com/lanl-ansi/PowerModelsDistribution.jl)
10. [PowerModelsAnnex.jl GitHub](https://github.com/lanl-ansi/PowerModelsAnnex.jl)
11. [PowerModelsITD.jl Style Guide](https://lanl-ansi.github.io/PowerModelsITD.jl/stable/developer/style.html)
12. [LANL-ANSI Grid Science Tutorial Notebook](https://github.com/lanl-ansi/tutorial-grid-science/blob/master/Class%20III%20-%20An%20introduction%20to%20PowerModels.jl.ipynb)
13. [GitHub Issue #728 -- PTDF matrix](https://github.com/lanl-ansi/PowerModels.jl/issues/728)
14. [Julia Discourse -- PTDF computation](https://discourse.julialang.org/t/calculating-power-transfer-distribution-factor-ptdf-matrix-using-powermodels-jl/42668)
15. Source code inspection: `/opt/julia-depot/packages/PowerModels/VCmhH/src/` (v0.21.5 installed in devcontainer)
16. Source code inspection: `/opt/julia-depot/packages/InfrastructureModels/*/src/core/base.jl`

## Gaps and Uncertainties

- **No formal extension/plugin documentation**: PowerModels does not have a dedicated "How to Extend" guide. The extension pattern must be inferred from the type hierarchy, ecosystem packages, and source code. A forthcoming tutorial on extending PowerModels was referenced in the Grid Science tutorial notebook but does not appear to have been published.
- **solution_processors API details**: The exact function signature and available arguments for solution processor callbacks are not well-documented; they are defined in InfrastructureModels internals.
- **Callback/hook API beyond ref_extensions**: There is no event-based callback system (e.g., pre-solve hooks, iteration callbacks). The only extension points are ref_extensions, solution_processors, the ext dictionary, and Julia's method dispatch.
- **DataFrames/Graphs interop**: Confirmed absent. No adapters, traits, or conversion utilities exist. These would need to be user-implemented.
- **PTDF scalability**: The `calc_basic_ptdf_matrix` function performs a dense matrix inverse, which is O(n^3) and impractical for networks with 10,000+ buses. The per-row `calc_basic_ptdf_row` uses sparse factorization and scales better but is undocumented for large-scale use.
- **Multi-infrastructure extension pattern**: How exactly InfrastructureModels coordinates multiple infrastructure types (e.g., PowerModelsITD coupling transmission and distribution) involves the `"it"` key convention in data dicts, but the detailed mechanics are spread across InfrastructureModels internals and not centrally documented.
