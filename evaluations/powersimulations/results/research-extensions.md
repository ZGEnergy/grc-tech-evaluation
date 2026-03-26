# PowerSimulations.jl — Research: Extensions & Architecture

## Key Findings

- **Julia's multiple dispatch is the extension mechanism.** There is no plugin registry, callback API, or hook system. Users create new `struct` types that subtype abstract formulation types, then define methods (e.g., `construct_device!`) that Julia dispatches on the new type. This is idiomatic Julia and extremely flexible.
- **Three official extension packages** demonstrate the pattern: `StorageSystemsSimulations.jl`, `HydroPowerSimulations.jl`, and `HybridSystemsSimulations.jl` — all maintained by NREL-Sienna, each adding new formulations, variables, constraints, and device constructors.
- **Custom `DecisionProblem` types** allow completely overriding `build_model!` to construct arbitrary JuMP optimization models while reusing PSI's result handling, simulation orchestration, and serialization infrastructure.
- **The architecture has clean separation of concerns**: PowerSystems.jl (data model), PowerSimulations.jl (optimization/simulation), PowerNetworkMatrices.jl (network matrices), InfrastructureSystems.jl (time series and infrastructure), PowerModels.jl (power flow formulations).
- **No Graphs.jl dependency.** Network topology is represented via sparse adjacency/incidence matrices in PowerNetworkMatrices.jl with custom DFS implementations. There is no direct integration with Graphs.jl.
- **Results are returned as DataFrames.** Functions like `read_variable()`, `read_dual()`, `read_realized_variable()` all return `DataFrames.DataFrame` objects. CSV export is built-in via `export_results()` and `export_realized_results()`.
- **JuMP model is fully accessible** via `get_jump_model(model)`, giving users direct access to add arbitrary constraints, variables, and objectives.
- **Two-stage construction pattern**: device construction is split into `ArgumentConstructStage` (variables, parameters, expressions) and `ModelConstructStage` (constraints, objective terms), enabling clean separation of variable declaration from constraint definition.
- **Simulation results stored in HDF5** for multi-step simulations, with an in-memory store option for single-step problems.
- **`ext::Dict{String, Any}` field** on both `DecisionModel` and `Settings` provides a generic extension dictionary for user-defined metadata, but is not used as a formal plugin mechanism.

## Detailed Notes

### Extension via Multiple Dispatch (Formulation Types)

The primary extension mechanism is Julia's type system and multiple dispatch. The abstract type hierarchy is:

```
AbstractDeviceFormulation
├── FixedOutput
├── AbstractBranchFormulation
│   ├── StaticBranch, StaticBranchBounds, StaticBranchUnbounded
│   ├── LossLessLine, PhaseAngleControl
│   └── AbstractTwoTerminalDCLineFormulation
│       ├── HVDCTwoTerminalDispatch, HVDCTwoTerminalLossless, ...
├── AbstractThermalFormulation
│   ├── AbstractThermalDispatchFormulation
│   │   ├── ThermalBasicDispatch, ThermalStandardDispatch, ThermalCompactDispatch, ThermalDispatchNoMin
│   └── AbstractThermalUnitCommitment
│       ├── AbstractStandardUnitCommitment (ThermalBasicUnitCommitment, ThermalStandardUnitCommitment)
│       └── AbstractCompactUnitCommitment (ThermalMultiStartUnitCommitment, ...)
├── AbstractRenewableFormulation → RenewableFullDispatch, RenewableConstantPowerFactor
├── AbstractLoadFormulation → StaticPowerLoad, PowerLoadDispatch, PowerLoadInterruption
├── AbstractRegulationFormulation
└── AbstractConverterFormulation → LossLessConverter
```

To create a custom formulation, you define a new struct subtyping the appropriate abstract type, then implement `construct_device!` methods dispatched on your type. The docstring in `formulations.jl` explicitly shows the pattern:

```julia
struct MyCustomDeviceFormulation <: PSI.AbstractDeviceFormulation end
```

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/formulations.jl`

### Custom Decision Problems

Users can define entirely custom optimization problems by subtyping `DecisionProblem` and overriding `build_model!`:

```julia
struct MyCustomProblem <: PSI.DecisionProblem end

function PSI.build_model!(model::PSI.DecisionModel{MyCustomProblem})
    container = PSI.get_optimization_container(model)
    # ... build custom JuMP model ...
end
```

The `DefaultDecisionProblem` abstract type (parent of `GenericOpProblem`) uses the standard template-based build pipeline. Custom problem types bypass this entirely, giving full control over model construction.

Two levels of customization are available:
- **`PSI.DecisionProblem`**: Full control — fewer checks, fewer validations, maximum flexibility
- **`PSI.DefaultDecisionProblem`**: More structure — uses the standard template-based build pipeline with PSI's validation checks

Optional method overloads for custom problems: `validate_template`, `validate_time_series!`, `reset!`, `solve_impl!`.

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/operation_model_abstract_types.jl`, `/opt/julia-depot/packages/PowerSimulations/89s3Q/docs/src/tutorials/adding_new_problem_model.md`

### Two-Stage Device Construction Pattern

The `build_impl!` function in `optimization_container.jl` (line 641) iterates through all device models in two stages:

1. **`ArgumentConstructStage`**: Adds variables, parameters, and expressions to the optimization container
2. **`ModelConstructStage`**: Adds constraints and objective function contributions

Between these stages, services and network construction are also staged. This pattern allows variables declared by one device to be referenced in constraints of another. Extension packages (e.g., StorageSystemsSimulations.jl) follow the same pattern, implementing `PSI.construct_device!` methods for both stages.

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/optimization_container.jl` (lines 641-780)

### Official Extension Packages (Proof of Extensibility)

Three NREL-maintained packages demonstrate the full extension pattern:

1. **StorageSystemsSimulations.jl** — Adds `StorageDispatchWithReserves` formulation with 8 new variable types, 11 constraint types, custom feedforwards (`EnergyTargetFeedforward`, `EnergyLimitFeedforward`), and a `StorageEnergyOutput` auxiliary variable. Extends `PSI.construct_device!` for both `AbstractPowerModel` and `AbstractActivePowerModel` network variants.

2. **HydroPowerSimulations.jl** — Adds 12 hydro dispatch/commitment formulations, 11 variable types (water spillage, reservoir head/volume, turbine flow), reservoir balance constraints, and a custom `MediumTermHydroPlanning` decision model type.

3. **HybridSystemsSimulations.jl** — Adds hybrid system device models combining storage, generation, and load components.

These packages import PowerSimulations and extend its methods (`PSI.construct_device!`, `PSI.add_variables!`, `PSI.add_constraints!`, etc.) using Julia's multiple dispatch. They do NOT require any registration API or plugin hooks — just method definitions on the appropriate type signatures.

Source: https://github.com/NREL-Sienna/StorageSystemsSimulations.jl, https://github.com/NREL-Sienna/HydroPowerSimulations.jl, https://github.com/NREL-Sienna/HybridSystemsSimulations.jl

### Architecture: Separation of Concerns

The Sienna ecosystem has strong separation across packages:

| Package | Responsibility | Version (installed) |
|---------|---------------|-------------------|
| PowerSystems.jl | Data model (devices, buses, branches, time series) | 4.6.2 |
| InfrastructureSystems.jl | Time series management, serialization, optimization infrastructure | 2.6.0 |
| PowerSimulations.jl | Optimization model construction, simulation orchestration | 0.30.2 |
| PowerNetworkMatrices.jl | PTDF, LODF, Ybus, adjacency matrices | 0.12.1 |
| PowerFlows.jl | Power flow solutions | 0.9.0 |
| PowerModels.jl | Power flow formulations (AC, DC, relaxations) — external dependency | (transitive) |

Within PowerSimulations.jl itself, the source is organized into:
- `core/` — Abstract types, containers (OptimizationContainer, variables, constraints, parameters, expressions)
- `devices_models/device_constructors/` — Per-device-category construction logic
- `devices_models/devices/` — Device-specific variable/constraint implementations
- `network_models/` — Network formulation implementations
- `services_models/` — Ancillary service models
- `feedforward/` — Inter-model parameter passing
- `operation/` — DecisionModel, EmulationModel, problem templates, results
- `simulation/` — Multi-step simulation orchestration

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/`

### JuMP Model Access and Custom Constraints

The underlying JuMP optimization model is accessible via:

```julia
jump_model = PSI.get_jump_model(model)  # Returns JuMP.Model
```

Users can add custom constraints directly to the JuMP model after `build!` but before `solve!`. The `OptimizationContainer` also provides structured access:

- `PSI.get_optimization_container(model)` — Returns the container with all variables, constraints, parameters
- `PSI.add_variable_container!(container, VarType(), DeviceType, names, time_steps)` — Register custom variables
- `PSI.add_constraints_container!(container, ConType(), DeviceType, names, time_steps; meta="ub")` — Register custom constraints (the `meta` kwarg enables reusing a constraint type for e.g. upper/lower bounds)
- `PSI.get_variable(container, VarType(), DeviceType)` — Retrieve previously registered variables for use in constraints

For the "register a variable in a custom operation model" pattern, users override `PSI.build_model!` and use `PSI.get_optimization_container()` to access the container, then use JuMP anonymous variables/constraints registered into PSI's container system.

The PSI docs explicitly require anonymous JuMP variables/constraints (not named ones) registered into PSI's container system for simulation-level features (inter-model coordination, results post-processing) to work.

Source: https://nrel-sienna.github.io/PowerSimulations.jl/latest/how_to/register_variable/, `/opt/julia-depot/packages/PowerSimulations/89s3Q/docs/src/tutorials/adding_new_problem_model.md`

### Network Graph Access

PowerSimulations.jl does **not** use Graphs.jl. Network topology is accessed through:

1. **PowerNetworkMatrices.jl** provides:
   - `AdjacencyMatrix(sys)` — N×N sparse incidence matrix indexed by bus numbers
   - `PTDF(sys)` — Power Transfer Distribution Factor matrix
   - `VirtualPTDF(sys)` — Lazy/virtual PTDF computation
   - `find_subnetworks(M)` — DFS-based connectivity analysis
   - `validate_connectivity(M)` — Check if network is fully connected

2. **PowerSystems.jl** provides component iterators:
   - `get_components(ThermalStandard, sys)` — Typed component queries
   - `get_bus(device)` — Bus connectivity for devices
   - Bus/branch/device relationships via the data model

There is no way to get a `Graphs.SimpleGraph` or similar directly from the Sienna ecosystem. Users would need to construct one manually from the adjacency matrix or bus/branch data.

The `find_subnetworks` function uses a custom DFS implementation operating on `SparseArrays.SparseMatrixCSC` via `SparseArrays.nzrange` and `SparseArrays.rowvals` — it does not depend on any graph library.

Source: `/opt/julia-depot/packages/PowerNetworkMatrices/XXeBY/src/adjacency_matrix.jl`, `/opt/julia-depot/packages/PowerNetworkMatrices/XXeBY/src/common.jl`

### Interoperability: DataFrames and Serialization

**DataFrame output is native.** All result-reading functions return `DataFrames.DataFrame`:

- `read_variable(results, key)` → DataFrame
- `read_dual(results, key)` → DataFrame
- `read_realized_variable(results, key)` → DataFrame (concatenated across simulation steps)
- `read_parameter(results, key)` → DataFrame
- `read_expression(results, key)` → DataFrame

**CSV export:**
- `export_results(results)` — Export all results to CSV
- `export_realized_results(results)` — Export realized (concatenated) results to CSV
- `export_optimizer_stats(results)` — Export solver statistics

**System serialization:**
- PowerSystems.jl supports `to_json(sys, filename)` and `serialize(sys, filename)` for JSON-based serialization
- Simulation results are stored in HDF5 format for multi-step simulations (`HDF5Dataset` in `dataset.jl`)
- `serialize_optimization_model()` and `serialize_problem()` for model persistence

**No direct NetworkX interop** — the ecosystem is Julia-native. Python interop would require manual conversion (e.g., exporting bus/branch data to CSV, then loading in Python).

For simulation results, `read_variable` returns a `SortedDict{DateTime, DataFrame}` with one DataFrame per simulation step. `read_realized_variable` concatenates across steps into a single DataFrame.

Internal conversion from JuMP arrays to DataFrames uses `to_dataframe()` in `utils/dataframes_utils.jl`, supporting both `DenseAxisArray` and `SparseAxisArray` types.

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/utils/dataframes_utils.jl`, `/opt/julia-depot/packages/PowerSimulations/89s3Q/docs/src/modeler_guide/read_results.md`

### Service Model Extension

Similar to device models, ancillary services are extensible:

```julia
abstract type AbstractServiceFormulation end
abstract type AbstractReservesFormulation <: AbstractServiceFormulation end

struct MyCustomReserve <: PSI.AbstractReservesFormulation end
```

Built-in service formulations include `RangeReserve`, `StepwiseCostReserve`, `RampReserve`, `NonSpinningReserve`, `GroupReserve`, and AGC formulations.

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/formulations.jl`

### Feedforward Mechanism

Feedforwards enable parameter passing between models in multi-stage simulations:

- `FixValueFeedforward` — Fix variable values from upstream model
- `SemiContinuousFeedforward` — Semi-continuous variable linking
- `UpperBoundFeedforward` / `LowerBoundFeedforward` — Bound propagation

Extension packages add their own feedforwards (e.g., `EnergyTargetFeedforward` in StorageSystemsSimulations.jl).

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/abstract_feedforward.jl`

### No Formal Plugin/Callback System

There is no `register_plugin()`, `on_before_solve()`, or similar callback API. The "Events" system (`EventType`, `EventKey`, recorder events) is for simulation logging and monitoring, not for user-defined hooks. The extension mechanism is purely Julia's multiple dispatch — define methods on the right type signatures and they are automatically called during model construction.

## Sources

1. PowerSimulations.jl source code: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/`
2. PowerNetworkMatrices.jl source code: `/opt/julia-depot/packages/PowerNetworkMatrices/XXeBY/src/`
3. PowerSystems.jl source code: `/opt/julia-depot/packages/PowerSystems/AHyDB/src/`
4. PSI docs — Modeling Structure: https://nrel-sienna.github.io/PowerSimulations.jl/latest/explanation/psi_structure/
5. PSI docs — Public API: https://nrel-sienna.github.io/PowerSimulations.jl/latest/api/PowerSimulations/
6. PSI docs — Internals: https://nrel-sienna.github.io/PowerSimulations.jl/latest/api/internal/
7. PSI docs — Register Variable: https://nrel-sienna.github.io/PowerSimulations.jl/latest/how_to/register_variable/
8. PSI docs — Problem Templates: https://nrel-sienna.github.io/PowerSimulations.jl/latest/how_to/problem_templates/
9. PSI docs — Read Results: https://nrel-sienna.github.io/PowerSimulations.jl/latest/how_to/read_results/
10. PSI docs — Formulation Library: https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/Introduction/
11. StorageSystemsSimulations.jl: https://github.com/NREL-Sienna/StorageSystemsSimulations.jl
12. HydroPowerSimulations.jl: https://github.com/NREL-Sienna/HydroPowerSimulations.jl
13. HybridSystemsSimulations.jl: https://github.com/NREL-Sienna/HybridSystemsSimulations.jl
14. PowerSimulations.jl GitHub: https://github.com/NREL-Sienna/PowerSimulations.jl (311 stars, 78 forks, BSD-3-Clause)

## Gaps and Uncertainties

- **Custom constraint addition post-build**: While `get_jump_model()` provides access to the JuMP model, it is unclear how well PSI handles constraints added outside its container system (e.g., whether they persist across simulation steps, whether they appear in results).
- **Extension documentation is sparse**: The "register a variable" how-to is described as "pseudo-code" and the developer guidelines page redirects to InfrastructureSystems.jl style guide rather than providing PSI-specific extension documentation.
- **No documented testing pattern for extensions**: The three NREL extension packages exist but there's no public guide for third-party extension development.
- **Graphs.jl interop**: No native integration exists. It's unknown whether anyone has built a bridge between PowerNetworkMatrices adjacency matrices and Graphs.jl's graph types.
- **Python/NetworkX interop**: No direct bridge exists. The `PyPSA2PowerSystems.jl` package suggests some cross-ecosystem work but is focused on data import, not runtime interop.
- **Version gap**: The installed version is 0.30.2 but the latest release is 0.33.1 (Feb 2026). Some extension APIs may have changed between these versions; the compat range in Project.toml allows 0.27-0.33.
- **`ext` dictionary usage**: The `ext::Dict{String, Any}` field on `DecisionModel` is not documented. It may be intended for user metadata but no examples of its use were found.
