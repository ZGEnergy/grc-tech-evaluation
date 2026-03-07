# powersimulations -- Research: Extensions & Architecture

## Key Findings

- **Multiple dispatch is the extension mechanism.** PowerSimulations.jl (PSI) uses Julia's multiple dispatch instead of a plugin/callback API. Custom device formulations are created by subtyping `AbstractDeviceFormulation` and implementing `construct_device!` methods that dispatch on `(container, sys, stage, DeviceModel{MyDevice, MyFormulation}, NetworkModel{...})`. No registration step beyond defining the type and methods is needed.
- **Two-stage build process.** Model building proceeds in two stages: `ArgumentConstructStage` (variables, parameters, expressions) and `ModelConstructStage` (constraints, objective terms). Both stages call `construct_device!` for each device/branch model in the template, enabling clean separation of variable creation from constraint creation.
- **External extension packages exist and prove the pattern.** `StorageSystemsSimulations.jl` and `HydroPowerSimulations.jl` are standalone packages that extend PSI by defining new `AbstractDeviceFormulation` subtypes and implementing `PSI.construct_device!` methods from outside the PSI codebase (source: [StorageSystemsSimulations.jl](https://github.com/NREL-Sienna/StorageSystemsSimulations.jl), [HydroPowerSimulations.jl](https://github.com/NREL-Sienna/HydroPowerSimulations.jl)).
- **Full JuMP model access.** The underlying `JuMP.Model` is accessible via `get_jump_model(model)` on any `DecisionModel` or via `get_jump_model(container)` on the `OptimizationContainer`. Users can pass a pre-built `JuMP.Model` to the `DecisionModel` constructor. The documentation explicitly states: "although we support all of JuMP.jl objects, you need to employ anonymous constraints and variables" and register them into PSI's containers.
- **Custom `DecisionProblem` subtypes.** Users can define `struct MyProblem <: PSI.DecisionProblem end` and implement their own `build_model!(model::DecisionModel{MyProblem})` for fully custom optimization problems, bypassing the template system entirely.
- **Results are DataFrames.** All result accessors (`read_variable`, `read_dual`, `read_parameter`, `read_expression`, `read_realized_variable`, etc.) return `DataFrames.DataFrame` objects. Export to CSV is built in via `export_realized_results`.
- **No Graphs.jl integration.** Neither PowerSimulations.jl, PowerSystems.jl, PowerNetworkMatrices.jl, nor InfrastructureSystems.jl depend on Graphs.jl. Network topology is represented via incidence/PTDF matrices and bus/branch component collections, not as a graph data structure.
- **Clear separation of concerns across packages.** `InfrastructureSystems.jl` (utilities, time series, optimization container base types), `PowerSystems.jl` (data model, device types), `PowerNetworkMatrices.jl` (PTDF, LODF, incidence matrices), `PowerModels.jl` (network formulations imported as types), and `PowerSimulations.jl` (optimization model building, simulation orchestration).
- **No explicit callback/hook/event API.** There are no `on_build`, `before_solve`, `after_solve` callbacks. Extension happens entirely through dispatch and the `build_model!` override mechanism.
- **Template system provides high-level configuration.** `ProblemTemplate` aggregates `NetworkModel`, `DeviceModel`, `ServiceModel`, and branch models. Users compose templates by calling `set_device_model!`, `set_service_model!`, `set_network_model!` to mix and match formulations.

## Detailed Notes

### Package Architecture and Separation of Concerns

PowerSimulations.jl (v0.30.2 installed) is part of NREL's Sienna ecosystem. The package dependencies form a layered architecture:

```
InfrastructureSystems.jl (v2.6.0)
    Provides: time series management, optimization container base types,
              result serialization/deserialization, logging infrastructure

PowerSystems.jl (v4.6.2)
    Provides: device type hierarchy (ThermalGen, RenewableGen, Storage, etc.),
              bus/branch topology data, system construction and I/O
    Depends on: InfrastructureSystems.jl

PowerNetworkMatrices.jl (v0.12.1)
    Provides: PTDF, LODF, Ybus, incidence matrices, radial branch reduction,
              subnetwork detection (find_subnetworks)
    Depends on: PowerSystems.jl, InfrastructureSystems.jl

PowerModels.jl (v0.21.5)
    Provides: network formulation abstract types (ACPPowerModel, DCPPowerModel, etc.)
    Note: PSI imports formulation types from PowerModels but does NOT use
          PowerModels' constraint/variable building machinery

PowerSimulations.jl (v0.30.2)
    Provides: optimization model building, template system, simulation orchestration
    Depends on: all of the above + JuMP.jl
```

Source: `Project.toml` at `/opt/julia-depot/packages/PowerSimulations/89s3Q/Project.toml` and the installed package listing.

The source code is organized into these directories:
- `src/core/` -- abstract types, optimization container, settings, key types
- `src/devices_models/` -- device constructors and device-specific constraints/variables
- `src/feedforward/` -- inter-model data passing
- `src/network_models/` -- network constraint construction
- `src/operation/` -- DecisionModel, EmulationModel, templates, results
- `src/simulation/` -- multi-step simulation orchestration
- `src/parameters/`, `src/initial_conditions/`, `src/services_models/`, `src/utils/`

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/`

### Template System: DeviceModel, ServiceModel, NetworkModel

The template system is the primary user-facing configuration interface.

**DeviceModel** pairs a `PSY.Device` subtype with an `AbstractDeviceFormulation` subtype:

```julia
DeviceModel(ThermalStandard, ThermalStandardUnitCommitment;
    feedforwards = [...],
    use_slacks = false,
    duals = [ActivePowerVariableLimitsConstraint],
    attributes = Dict{String, Any}(),
)
```

Fields: `feedforwards`, `use_slacks`, `duals`, `services`, `time_series_names`, `attributes`, `subsystem`.

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/device_model.jl`

**ServiceModel** pairs a `PSY.Service` subtype with an `AbstractServiceFormulation`:

```julia
ServiceModel(PSY.VariableReserve{PSY.ReserveUp}, RangeReserve)
```

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/service_model.jl`

**NetworkModel** wraps a `PM.AbstractPowerModel` subtype with configuration:

```julia
NetworkModel(PTDFPowerModel; ptdf = ptdf_matrix, reduce_radial_branches = true)
```

Built-in PSI network types: `CopperPlatePowerModel`, `PTDFPowerModel`, `AreaBalancePowerModel`, `AreaPTDFPowerModel`. PSI also re-exports PowerModels types: `ACPPowerModel`, `DCPPowerModel`, `SOCWRPowerModel`, etc.

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/network_model.jl`

**ProblemTemplate** aggregates all of the above:

```julia
template = ProblemTemplate(NetworkModel(CopperPlatePowerModel))
set_device_model!(template, ThermalStandard, ThermalStandardUnitCommitment)
set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
set_service_model!(template, PSY.VariableReserve{PSY.ReserveUp}, RangeReserve)
```

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/operation/problem_template.jl`

### Extension Mechanism 1: Custom Device Formulations

The primary extension path. Users define a new formulation struct and implement `construct_device!` for both build stages:

```julia
# Step 1: Define the formulation type
struct MyCustomFormulation <: PSI.AbstractDeviceFormulation end

# Step 2: Implement ArgumentConstructStage (variables, parameters, expressions)
function PSI.construct_device!(
    container::PSI.OptimizationContainer,
    sys::PSY.System,
    ::PSI.ArgumentConstructStage,
    model::PSI.DeviceModel{PSY.ThermalStandard, MyCustomFormulation},
    network_model::PSI.NetworkModel{<:PM.AbstractPowerModel},
)
    devices = PSI.get_available_components(model, sys)
    PSI.add_variables!(container, PSI.ActivePowerVariable, devices, MyCustomFormulation())
    # ... add more variables, parameters, expressions
end

# Step 3: Implement ModelConstructStage (constraints)
function PSI.construct_device!(
    container::PSI.OptimizationContainer,
    sys::PSY.System,
    ::PSI.ModelConstructStage,
    model::PSI.DeviceModel{PSY.ThermalStandard, MyCustomFormulation},
    network_model::PSI.NetworkModel{<:PM.AbstractPowerModel},
)
    devices = PSI.get_available_components(model, sys)
    # Add constraints using PSI.add_constraints!, PSI.add_constraints_container!, etc.
end
```

The formulation type hierarchy for thermal generation alone includes: `AbstractThermalFormulation > AbstractThermalDispatchFormulation > ThermalBasicDispatch | ThermalStandardDispatch | ThermalCompactDispatch | ThermalDispatchNoMin` and `AbstractThermalUnitCommitment > AbstractStandardUnitCommitment | AbstractCompactUnitCommitment > ...` with 9 concrete formulations.

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/formulations.jl`

This pattern is proven by extension packages:
- `StorageSystemsSimulations.jl` defines `StorageDispatchWithReserves <: AbstractStorageFormulation <: PSI.AbstractDeviceFormulation` and overrides `PSI.construct_device!` for `PSY.Storage` devices ([source](https://github.com/NREL-Sienna/StorageSystemsSimulations.jl/blob/main/src/storage_constructor.jl)).
- `HydroPowerSimulations.jl` does the same for hydro devices ([source](https://github.com/NREL-Sienna/HydroPowerSimulations.jl)).

### Extension Mechanism 2: Custom DecisionProblem

For fully custom optimization problems, users can bypass the template system entirely:

```julia
struct MyCustomProblem <: PSI.DecisionProblem end

function PSI.build_model!(model::PSI.DecisionModel{MyCustomProblem})
    container = PSI.get_optimization_container(model)
    PSI.set_time_steps!(container, 1:24)

    # Directly use PSI.add_variable_container!, get_jump_model(container), etc.
    variable = PSI.add_variable_container!(
        container, PSI.ActivePowerVariable(), PSY.ThermalGeneration, names, steps
    )
    for t in steps, d in devices
        variable[name, t] = JuMP.@variable(get_jump_model(container))
    end
end
```

The `DefaultDecisionProblem` subtype is what the standard template-based build uses. Custom subtypes get their own `build_model!` dispatch.

Note: Issue [#1280](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1280) reported that custom `DecisionProblem` subtypes could not be properly built because some methods dispatched only on `DefaultDecisionProblem`. The resolution was that users must implement their own `validate_time_series` for custom problem types.

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/operation_model_abstract_types.jl`, `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/operation/decision_model.jl`

### JuMP Model Access

The JuMP model is accessible at multiple levels:

```julia
# From a DecisionModel
jump_model = PSI.get_jump_model(model)

# From the OptimizationContainer
container = PSI.get_optimization_container(model)
jump_model = PSI.get_jump_model(container)
```

The `OptimizationContainer` struct holds `JuMPmodel::JuMP.Model` as a field, along with dictionaries for variables, constraints, expressions, parameters, duals, and initial conditions. All are keyed by typed keys (`VariableKey`, `ConstraintKey`, etc.).

Users can also pass a pre-built JuMP model to the `DecisionModel` constructor:

```julia
DecisionModel{GenericOpProblem}(template, sys, custom_jump_model)
```

Though the docs warn: "Use with care" -- and direct mode (`JuMP.direct_model`) conflicts with the externally provided model.

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/optimization_container.jl` (lines 68-87 for the struct definition), `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/operation/operation_model_interface.jl` (line 20 for `get_jump_model`).

### Constraint and Variable Registration API

PSI provides container management functions used internally and by extension packages:

- `add_variable_container!(container, VarType(), DeviceType, axes...)` -- allocates a JuMP variable container
- `add_constraints_container!(container, ConstraintType(), DeviceType, axes...; sparse=false)` -- allocates a constraint container
- `add_variables!(container, VarType, devices, formulation)` -- high-level variable addition with bounds
- `add_constraints!(container, ConstraintType, VarType, devices, model, network_model)` -- high-level constraint addition (many dispatch methods)
- `add_to_expression!(container, ExprType, VarType, devices, model, network_model)` -- adds variable contributions to balance expressions
- `add_parameters!(container, ParamType, devices, model)` -- adds time-series parameters

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/optimization_container.jl`

### Feedforward System

Feedforwards formalize inter-model data flow in multi-stage simulations (e.g., UC to ED):

- `UpperBoundFeedforward` -- constrains variables to upper bounds from another model's results
- `LowerBoundFeedforward` -- constrains variables to lower bounds
- `SemiContinuousFeedforward` -- passes on/off decisions (e.g., `ON * Pmin <= P <= ON * Pmax`)
- `FixValueFeedforward` -- fixes variable values from another model

Custom feedforwards can be created by subtyping `AbstractAffectFeedforward`.

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/feedforward/feedforwards.jl`, `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/abstract_feedforward.jl`

### DataFrame Interoperability

All result values are stored as `DataFrames.DataFrame`:

```julia
# OptimizationProblemResults stores:
#   variable_values::Dict{VariableKey, DataFrames.DataFrame}
#   dual_values::Dict{ConstraintKey, DataFrames.DataFrame}
#   parameter_values::Dict{ParameterKey, DataFrames.DataFrame}
#   expression_values::Dict{ExpressionKey, DataFrames.DataFrame}
#   optimizer_stats::DataFrames.DataFrame

results = OptimizationProblemResults(model)
df = read_variable(results, "ActivePowerVariable__ThermalStandard")  # returns DataFrame
df = read_realized_variable(results, "ActivePowerVariable__ThermalStandard")  # concatenated DataFrame
```

Export functions: `export_realized_results(results, path)` writes CSVs. `export_results` also available.

Source: `/opt/julia-depot/packages/InfrastructureSystems/LEg3t/src/Optimization/optimization_problem_results.jl` (lines 7-12 for the struct definition), [PSI docs](https://nrel-sienna.github.io/PowerSimulations.jl/stable/how_to/read_results/)

### Graph / Network Topology Access

**No Graphs.jl integration exists anywhere in the Sienna stack.** Neither `PowerSimulations.jl`, `PowerSystems.jl`, `PowerNetworkMatrices.jl`, nor `InfrastructureSystems.jl` list Graphs.jl as a dependency.

Network topology is represented via:
1. **Component collections**: `PSY.get_components(PSY.ACBus, sys)`, `PSY.get_components(PSY.Line, sys)` -- iterate buses and branches
2. **Incidence / PTDF / LODF matrices**: via `PowerNetworkMatrices.jl` -- sparse matrices with bus/branch name indexing
3. **Subnetwork detection**: `PNM.find_subnetworks(sys)` returns `Dict{Int, Set{Int}}` mapping reference bus numbers to sets of bus numbers in each island
4. **Radial branch reduction**: `PNM.RadialNetworkReduction(sys)` identifies and removes radial branches

The `NetworkModel` struct stores `subnetworks::Dict{Int, Set{Int}}` and a `bus_area_map::Dict{PSY.ACBus, Int}` for area-based decomposition.

To construct a Graphs.jl graph from PSI data, users would need to manually iterate buses and branches and build the graph themselves. This is straightforward but not provided out of the box.

Source: `/opt/julia-depot/packages/PowerNetworkMatrices/XXeBY/Project.toml` (no Graphs.jl dep), `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/network_model.jl`

### Build Process Internals

The `build_impl!` function in `optimization_container.jl` orchestrates model construction:

1. Initialize system expressions (power balance expressions per subnetwork)
2. For each device model in template: call `construct_device!(container, sys, ArgumentConstructStage(), device_model, network_model)`
3. Construct services (reserves, AGC)
4. For each branch model: call `construct_device!` for `ArgumentConstructStage`
5. For each device model: call `construct_device!` for `ModelConstructStage`
6. Construct network constraints
7. For each branch model: `ModelConstructStage`
8. Construct services `ModelConstructStage`
9. Serialize model

This two-pass design ensures all variables exist before constraints reference them.

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/optimization_container.jl` (lines 641-730)

### Results Storage

Two storage backends:
- **In-memory store**: for single-solve `DecisionModel` results
- **HDF5 store**: for `Simulation` results with inline compression, hierarchical structure, and caching

Source: [arxiv paper](https://arxiv.org/html/2404.03074v1)

## Sources

1. [PowerSimulations.jl GitHub repository](https://github.com/NREL-Sienna/PowerSimulations.jl)
2. [PowerSimulations.jl documentation (stable)](https://nrel-sienna.github.io/PowerSimulations.jl/stable/)
3. [PowerSimulations.jl formulation library introduction](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/Introduction/)
4. [PowerSimulations.jl arXiv paper (2404.03074)](https://arxiv.org/html/2404.03074v1)
5. [StorageSystemsSimulations.jl](https://github.com/NREL-Sienna/StorageSystemsSimulations.jl)
6. [HydroPowerSimulations.jl](https://github.com/NREL-Sienna/HydroPowerSimulations.jl)
7. [InfrastructureSystems.jl](https://github.com/NREL-Sienna/InfrastructureSystems.jl)
8. [PowerSystems.jl](https://github.com/NREL-Sienna/PowerSystems.jl)
9. [PSI documentation: Register a variable](https://nrel-sienna.github.io/PowerSimulations.jl/stable/how_to/register_variable/)
10. [PSI documentation: Read results](https://nrel-sienna.github.io/PowerSimulations.jl/stable/how_to/read_results/)
11. [PSI documentation: Internals API](https://nrel-sienna.github.io/PowerSimulations.jl/stable/api/internal/)
12. [GitHub issue #1280: Custom DecisionProblems build failure](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1280)
13. [GitHub issue #1353: Document extension packages](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1353)
14. Installed source code at `/opt/julia-depot/packages/PowerSimulations/89s3Q/` (v0.30.2)
15. Installed source code at `/opt/julia-depot/packages/InfrastructureSystems/LEg3t/` (v2.6.0)
16. Installed source code at `/opt/julia-depot/packages/PowerNetworkMatrices/XXeBY/` (v0.12.1)

## Gaps and Uncertainties

- **No formal plugin/callback API documentation.** The extension mechanism relies entirely on Julia's multiple dispatch convention. There is no `register_plugin!`, `add_hook!`, or event system. Whether this is sufficient depends on the use case -- for adding new device formulations it works well, but for cross-cutting concerns (e.g., logging every constraint addition, modifying behavior at solve time) there is no hook.
- **Custom constraint types underdocumented.** While users can define new `ConstraintType` subtypes and use `add_constraints_container!`, the documentation for doing so is minimal. The "Register a variable" how-to guide exists but there is no equivalent "Register a constraint" guide.
- **`build_model!` for custom `DecisionProblem` is underdocumented.** The abstract type docstring says `#TODO: Document the required interfaces for custom types`. Issue #1280 shows this pathway has had bugs.
- **No Graphs.jl interop verified.** Users wanting graph algorithms on the network topology must construct graphs manually. No utility function exists to convert a `PSY.System` to a `Graphs.SimpleGraph`.
- **Extension package stability unclear.** `StorageSystemsSimulations.jl` and `HydroPowerSimulations.jl` exist but their maturity/versioning relative to PSI versions is not documented. Issue #1353 (open as of 2025) requests that these be mentioned in the formulation library docs.
- **`ext` field on `DecisionModel`.** The `DecisionModel` struct has an `ext::Dict{String, Any}` field, but no documentation or examples of its intended use were found. It may be for user-attached metadata.
- **Attribute system.** `DeviceModel` has an `attributes::Dict{String, Any}` that can modify formulation behavior (e.g., `StorageDispatchWithReserves` uses attributes like `"reservation"`, `"cycling_limits"`). This provides a lightweight configuration mechanism within formulations, but it is stringly-typed and validation is formulation-specific.
