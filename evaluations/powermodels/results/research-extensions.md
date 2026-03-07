# powermodels -- Research: Extensions & Architecture

**Tool version:** PowerModels.jl v0.21.5, InfrastructureModels.jl v0.7.8
**Julia version:** 1.10
**Source path in devcontainer:** `/opt/julia-depot/packages/PowerModels/VCmhH`

## Key Findings

- PowerModels.jl is architected around a clean **Problem-Formulation decoupling**: problem specifications (e.g., `build_opf`) define *what* constraints/variables are needed, while formulation files (e.g., `form/acp.jl`, `form/dcp.jl`) define *how* they are mathematically expressed. Julia's multiple dispatch on the abstract type hierarchy is the core extension mechanism.
- **No plugin/callback system in the traditional sense.** Extension is achieved through (1) subtyping `AbstractPowerModel`, (2) defining new methods via multiple dispatch, (3) `ref_extensions` list for pre-computation hooks, and (4) `solution_processors` for post-solve hooks. There are no event-driven hooks or middleware patterns.
- **The `ext` dictionary** on every model instance (`pm.ext::Dict{Symbol,Any}`) provides an escape hatch for storing arbitrary extension data, used internally for SDP decomposition metadata (`pm.ext[:SDconstraintDecomposition]`).
- **InfrastructureModels.jl** is the abstract base layer providing the model lifecycle (`instantiate_model`, `optimize_model!`, `build_ref`), field definitions (`@im_fields`), and multi-infrastructure/multi-network data conventions. PowerModels.jl subtypes `AbstractInfrastructureModel` as `AbstractPowerModel`.
- **No native Graphs.jl or DataFrames.jl integration.** The network is stored as nested `Dict{String,Any}` dictionaries. Graph-based and DataFrame-based access require separate ecosystem packages (PowerModelsAnalytics.jl, PowerPlots.jl).
- **Rich ecosystem of extension packages** demonstrates the extensibility pattern in practice: PowerModelsDistribution.jl, PowerModelsRestoration.jl, PowerModelsSecurityConstrained.jl, GasPowerModels.jl, PowerModelsITD.jl all extend the base via the same type hierarchy + dispatch mechanism.
- The codebase is ~14,000 lines across `core/`, `form/`, and `prob/` directories, with a clear separation: `core/` for infrastructure, `form/` for mathematical formulations, `prob/` for problem specifications, `io/` for parsing.
- **Admittance matrix computation** is built-in (`calc_admittance_matrix`, `calc_susceptance_matrix`) returning a custom `AdmittanceMatrix` struct with sparse matrix and bus-index mappings, but this is not a graph in the Graphs.jl sense.

## Detailed Notes

### Architecture: Three-Layer Separation

PowerModels.jl is organized into three clearly separated layers:

1. **`prob/` -- Problem Specifications**: Define *what* an optimization problem looks like by calling variable, constraint, and objective functions. Example: `build_opf` calls `variable_bus_voltage`, `constraint_power_balance`, `objective_min_fuel_and_flow_cost`, etc. These are formulation-agnostic -- they dispatch on `AbstractPowerModel` and call template functions.

2. **`form/` -- Formulations**: Provide formulation-specific implementations of variables, constraints, and expressions. Each formulation file (e.g., `acp.jl`, `dcp.jl`, `wr.jl`) defines methods dispatched on abstract types like `AbstractACPModel`, `AbstractDCPModel`. For example, `constraint_ohms_yt_from(pm::AbstractDCPModel, ...)` produces a linear constraint `-b*(va_fr - va_to)`, while the same function dispatched on `AbstractACPModel` produces a nonlinear constraint.

3. **`core/` -- Infrastructure**: Contains the type hierarchy (`types.jl`), model lifecycle (`base.jl`), constraint templates (`constraint_template.jl`), variable definitions (`variable.jl`), reference data building (`ref.jl`), data manipulation (`data.jl`), and solution handling (`solution.jl`).

**Source:** `/opt/julia-depot/packages/PowerModels/VCmhH/src/PowerModels.jl` (include order), file line counts from `wc -l`.

### Type Hierarchy and Multiple Dispatch

The type hierarchy is the primary extension mechanism. Key structure:

```

AbstractInfrastructureModel (InfrastructureModels.jl)
  AbstractPowerModel (PowerModels.jl)
    AbstractActivePowerModel
      AbstractDCPModel
        DCPPowerModel (concrete, @pm_fields)
        AbstractDCMPPModel -> DCMPPowerModel
        AbstractNFAModel -> NFAPowerModel
        AbstractDCPLLModel -> DCPLLPowerModel
    AbstractACPModel -> ACPPowerModel
    AbstractACRModel -> ACRPowerModel
      AbstractIVRModel -> IVRPowerModel
    AbstractACTModel -> ACTPowerModel
    AbstractLPACModel -> AbstractLPACCModel -> LPACCPowerModel
    AbstractConicModel
      AbstractWRConicModel -> AbstractSOCWRConicModel -> SOCWRConicPowerModel
      AbstractWRMModel -> AbstractSDPWRMModel -> SDPWRMPowerModel, SparseSDPWRMPowerModel
    AbstractWRModel
      AbstractSOCWRModel -> SOCWRPowerModel
      AbstractQCWRModel -> ...
    AbstractBFModel
      AbstractBFAModel -> BFAPowerModel
      AbstractBFQPModel -> AbstractSOCBFModel -> SOCBFPowerModel
      AbstractBFConicModel -> AbstractSOCBFConicModel -> SOCBFConicPowerModel

```

To add a new formulation, a user:
1. Defines a new abstract type subtying any existing abstract type
2. Defines a concrete mutable struct using the `@pm_fields` macro
3. Implements the required dispatch methods (variables, constraints)

Example pattern:

```julia

abstract type AbstractMyModel <: AbstractACPModel end
mutable struct MyPowerModel <: AbstractMyModel @pm_fields end
# Then override specific constraint/variable methods

```

**Source:** `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/types.jl`

### Constraint Template Pattern (Data-Formulation Bridge)

Constraint templates (in `core/constraint_template.jl`, 984 lines) serve as the bridge between network data and mathematical formulations:

1. **Template function**(dispatched on `AbstractPowerModel`): Extracts data from `ref` dict, passes named parameters.
2. **Formulation function**(dispatched on specific abstract types like `AbstractACPModel`): Receives pre-extracted parameters, builds JuMP constraints.

Example: `constraint_thermal_limit_from(pm::AbstractPowerModel, i; nw)` extracts `rate_a` and indices from `ref`, then calls `constraint_thermal_limit_from(pm, nw, f_idx, rate_a)` which dispatches to the formulation-specific version.

Templates should "always be defined over `AbstractPowerModel` and should never refer to model variables" (per source comments). This is the documented convention for ensuring extensibility.

**Source:** `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/constraint_template.jl` (lines 1-15 comment header), `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/constraint.jl`

### Extension Point: ref_extensions

The `ref_extensions` parameter on `solve_model` and `instantiate_model` accepts a list of functions with signature `(ref::Dict{Symbol,Any}, data::Dict{String,Any}) -> nothing` (mutating `ref` in-place). These run after the core `ref_add_core!` function during model instantiation.

Use cases:
- Adding precomputed data (e.g., susceptance matrices for PTDF formulations: `ref_add_sm!`, `ref_add_sm_inv!`)
- Adding connected component information (`ref_add_connected_components!`)
- Adding bounds for on/off variables (`ref_add_on_off_va_bounds!`)
- Extension packages add their own ref data (e.g., `GasPowerModels._GM.ref_add_ne!`)

Example from PowerModels PTDF OPF:

```julia

solve_opf_ptdf(file, model_type, optimizer;
    ref_extensions=[ref_add_connected_components!, ref_add_sm!])

```

**Source:** `/opt/julia-depot/packages/InfrastructureModels/C2xBM/src/core/base.jl` (lines 350-375), `/opt/julia-depot/packages/PowerModels/VCmhH/src/prob/opf.jl` (lines 163-170)

### Extension Point: solution_processors

The `solution_processors` parameter on `solve_model` is passed through to `optimize_model!` in InfrastructureModels. These are functions that post-process the result dictionary after solving. PowerModels also has a `solution_preprocessor` method (dispatched via InfrastructureModels) that adds `per_unit` and `baseMVA` to solutions.

Additionally, each formulation can implement `sol_data_model!(pm, solution)` to convert solution values into the data model's standard space (e.g., polar voltages, rectangular power).

**Source:** `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/solution.jl`, `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/base.jl` (line 20, `solve_model`)

### Extension Point: ext Dictionary

Every model instance has an `ext::Dict{Symbol,Any}` field (defined in `@im_fields`). This is explicitly documented as an "Extension dictionary" where "Extensions should define a type to hold information particular to their functionality, and store an instance of the type in this dictionary keyed on an extension-specific symbol."

In PowerModels itself, it is used for SDP constraint decomposition data in `form/wrm.jl` (lines 137, 146, 242).

**Source:** `/opt/julia-depot/packages/InfrastructureModels/C2xBM/src/core/base.jl` (lines 36-42)

### Extension Point: Custom Problem Specifications (build_method)

Users can write entirely custom `build_method` functions that compose existing or new variable/constraint/objective functions. The `build_method` is a plain Julia function taking `pm::AbstractPowerModel`, giving full access to add JuMP variables and constraints via `pm.model`.

Example composability -- `build_opf` is ~25 lines calling high-level functions:

```julia

function build_opf(pm::AbstractPowerModel)
    variable_bus_voltage(pm)
    variable_gen_power(pm)
    variable_branch_power(pm)
    variable_dcline_power(pm)
    objective_min_fuel_and_flow_cost(pm)
    constraint_model_voltage(pm)
    for i in ids(pm, :ref_buses) ... end
    for i in ids(pm, :bus) ... end
    for i in ids(pm, :branch) ... end
    for i in ids(pm, :dcline) ... end
end

```

**Source:** `/opt/julia-depot/packages/PowerModels/VCmhH/src/prob/opf.jl` (lines 11-45)

### InfrastructureModels.jl Relationship

InfrastructureModels.jl (v0.7.8) provides:

- **`AbstractInfrastructureModel`** root type with standard fields via `@im_fields` macro (model, data, setting, solution, ref, var, con, sol, sol_proc, ext)
- **`instantiate_model`** lifecycle: initialize model -> `ref_add_core!` -> ref_extensions -> build_method
- **`optimize_model!`** lifecycle: optional integrality relaxation -> set optimizer -> JuMP.optimize! -> build_result with solution_processors
- **Multi-infrastructure data format**(`data["it"]["pm"]` for power, `data["it"]["gm"]` for gas, etc.)
- **Multi-network support**(`data["nw"]["1"]`, `data["nw"]["2"]`, etc. for time series)
- **Ref initialization** from data dictionaries (string keys to symbol keys, component keys to integers)

PowerModels re-exports key IM functions: `ids`, `ref`, `var`, `con`, `sol`, `nw_ids`, `nws`, `optimize_model!`, `nw_id_default`.

**Source:** `/opt/julia-depot/packages/InfrastructureModels/C2xBM/src/InfrastructureModels.jl`, `/opt/julia-depot/packages/InfrastructureModels/C2xBM/src/core/base.jl`

### Data Model: Nested Dictionaries (No Native DataFrame/Graph)

The internal data model is a nested `Dict{String,Any}`:

```

data["bus"]["1"]["bus_type"] = 3
data["gen"]["1"]["pg"] = 1.5
data["branch"]["1"]["f_bus"] = 1

```

This structure is designed for MATPOWER compatibility and JSON serialization. It does **not** use DataFrames.jl or Graphs.jl natively.

**Accessing graph-like information:** The `ref` dictionary precomputes adjacency-like structures:
- `:arcs_from`, `:arcs_to`, `:arcs` -- tuples of `(branch_id, from_bus, to_bus)`
- `:bus_arcs` -- mapping from bus to connected arcs
- `:bus_gens`, `:bus_loads`, `:bus_shunts`, `:bus_storage` -- bus-to-component mappings
- `:buspairs` -- parameters for connected bus pairs

The `AdmittanceMatrix` struct provides sparse matrix access with bus-index mappings, but is not a Graphs.jl graph.

**Source:** [Network Data Format docs](https://lanl-ansi.github.io/PowerModels.jl/stable/network-data/), `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/base.jl` (ref_add_core!)

### Interoperability: PowerModelsAnalytics.jl and PowerPlots.jl

Graph and DataFrame access require separate packages:

- **PowerModelsAnalytics.jl** provides `InfrastructureGraph` struct containing a `LightGraphs.AbstractGraph` (now Graphs.jl) with metadata mappings. It converts the PowerModels nested dict into a graph structure for analysis and visualization.
- **PowerPlots.jl** converts PowerModels data into DataFrames (one per component type) for VegaLite.jl plotting. After conversion, standard DataFrames.jl operations apply.

Neither package is a dependency of PowerModels.jl; they are separate optional packages.

**Source:** [PowerModelsAnalytics.jl](https://github.com/lanl-ansi/PowerModelsAnalytics.jl), [PowerPlots.jl paper](https://arxiv.org/html/2510.05063v1)

### Direct JuMP Model Access

The `pm.model` field exposes the underlying `JuMP.Model`, allowing users to:
- Add arbitrary JuMP variables and constraints directly
- Access dual values after solving
- Use any JuMP-compatible solver
- Inspect the model programmatically

This is a powerful escape hatch -- any constraint or variable can be added directly to `pm.model` without going through PowerModels' template system.

**Source:** `/opt/julia-depot/packages/InfrastructureModels/C2xBM/src/core/base.jl` (im_fields definition: `model::JuMP.AbstractModel`)

### Ecosystem Extension Packages

The following packages demonstrate the extensibility pattern:

| Package | Purpose | Extension Pattern |
|---------|---------|-------------------|
| [PowerModelsDistribution.jl](https://github.com/lanl-ansi/PowerModelsDistribution.jl) | Unbalanced distribution networks | New types, multi-conductor |
| [PowerModelsRestoration.jl](https://github.com/lanl-ansi/PowerModelsRestoration.jl) | Power system restoration | New problems (MLD), new constraints |
| [PowerModelsSecurityConstrained.jl](https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl) | SCOPF | Contingency constraints, multi-scenario |
| [GasPowerModels.jl](https://github.com/lanl-ansi/GasPowerModels.jl) | Joint gas-power optimization | Multi-infrastructure via IM |
| [PowerModelsITD.jl](https://github.com/lanl-ansi/PowerModelsITD.jl) | Integrated T&D | Coupling constraints |
| [PowerModelsAnnex.jl](https://github.com/lanl-ansi/PowerModelsAnnex.jl) | Exploratory/experimental | Misc extensions |

**Source:** [LANL ANSI Julia packages](https://juliapackages.com/u/lanl-ansi)

### Export Strategy

PowerModels uses an automatic export strategy: all public symbols (those not starting with `_`) are exported. Internal functions are prefixed with `_`. This means the full public API is very large but discoverable.

**Source:** `/opt/julia-depot/packages/PowerModels/VCmhH/src/core/export.jl`

## Sources

1. [PowerModels.jl GitHub repository](https://github.com/lanl-ansi/PowerModels.jl)
2. [PowerModels.jl stable documentation](https://lanl-ansi.github.io/PowerModels.jl/stable/)
3. [Network Formulations docs](https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/)
4. [Network Data Format docs](https://lanl-ansi.github.io/PowerModels.jl/stable/network-data/)
5. [Constraints docs](https://lanl-ansi.github.io/PowerModels.jl/dev/constraints/)
6. [InfrastructureModels.jl GitHub](https://github.com/lanl-ansi/InfrastructureModels.jl)
7. [PowerModelsAnalytics.jl GitHub](https://github.com/lanl-ansi/PowerModelsAnalytics.jl)
8. [PowerModelsAnnex.jl GitHub](https://github.com/lanl-ansi/PowerModelsAnnex.jl)
9. [PowerModelsDistribution.jl GitHub](https://github.com/lanl-ansi/PowerModelsDistribution.jl)
10. [PowerModelsSecurityConstrained.jl GitHub](https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl)
11. [PowerModelsRestoration.jl GitHub](https://github.com/lanl-ansi/PowerModelsRestoration.jl)
12. [PowerModels.jl paper (arXiv:1711.01728)](https://arxiv.org/abs/1711.01728)
13. [PowerPlots.jl paper (arXiv:2510.05063)](https://arxiv.org/html/2510.05063v1)
14. [GasPowerModels quickguide](https://lanl-ansi.github.io/GasPowerModels.jl/stable/quickguide/)
15. Source code: `/opt/julia-depot/packages/PowerModels/VCmhH/src/` (v0.21.5)
16. Source code: `/opt/julia-depot/packages/InfrastructureModels/C2xBM/src/` (v0.7.8)

## Gaps and Uncertainties

- **No formal plugin/hook registry.** Extensions rely entirely on Julia's type dispatch and the `ref_extensions`/`solution_processors` lists. There is no way to register a "plugin" that automatically activates -- extensions must be explicitly wired into each `solve_model` call.
- **PowerModelsAnalytics.jl Graphs.jl migration status unclear.** The package was originally built on LightGraphs.jl (now archived). Whether it has fully migrated to Graphs.jl needs verification.
- **DataFrame interop is indirect.** PowerPlots.jl provides conversion but is a visualization-focused package. There is no first-class "export network to DataFrame" utility in core PowerModels.
- **Documentation of extension patterns is sparse.** The official docs focus on using existing formulations, not on creating new ones. The best documentation of extension patterns is the source code of downstream packages (PowerModelsDistribution, PowerModelsRestoration, etc.) and the Grid Science tutorial notebook.
- **Multi-infrastructure coupling (via InfrastructureModels) complexity.** The `data["it"]["pm"]` nesting adds complexity for simple single-infrastructure use cases. How well this scales to 3+ infrastructure types is not well documented.
- **No event/callback system for mid-solve hooks.** Unlike some optimization frameworks, there is no mechanism to inject callbacks during the solve process (e.g., lazy constraints, user cuts) through PowerModels' API -- users would need to use JuMP's callback mechanism directly on `pm.model`.
- **`sol_data_model!` coverage.** Not all formulations implement this method; the base `AbstractPowerModel` version emits a warning. Needs verification for which formulations properly transform solutions back to data-model space.
