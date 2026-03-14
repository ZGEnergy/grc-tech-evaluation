# PowerSimulations.jl — Research: API & Formulations

## Key Findings

- **PowerSimulations.jl (v0.30.2) is an optimization-based operations simulation tool**, not a power-flow solver. It builds JuMP optimization models for unit commitment (SCUC), economic dispatch (SCED), and multi-stage production cost simulations. Power flow is handled by the companion package PowerFlows.jl (v0.9.0).
- **The data model lives in PowerSystems.jl (v4.6.2)**, which provides typed Julia structs for buses (`ACBus`), generators (`ThermalStandard`, `RenewableDispatch`, etc.), branches (`Line`, `Transformer2W`, etc.), loads, storage, and services. It parses MATPOWER `.m`, PSS/E `.raw`/`.dyr`, and tabular CSV files via `System(file_path)`.
- **15 network formulations are re-exported** from PowerModels.jl, ranging from `CopperPlatePowerModel` (single-node) to `ACPPowerModel` (full nonlinear AC) and including PTDF-based linear approximations (`PTDFPowerModel`, `AreaPTDFPowerModel`).
- **9 thermal generation formulations** span dispatch-only (`ThermalBasicDispatch`, `ThermalStandardDispatch`) through full unit commitment with multi-start profiles (`ThermalMultiStartUnitCommitment`), with intermediate options for compact representations and relaxed minimums.
- **Solver-agnostic via JuMP/MathOptInterface**: any MOI-compatible solver works. The installed environment includes HiGHS (LP/MILP), Ipopt (NLP), GLPK (LP/MILP), and SCIP (MINLP). Solver attributes are passed via `optimizer_with_attributes()`.
- **Two-level problem architecture**: `DecisionModel` for single-step optimization, and `Simulation` (wrapping `SimulationModels` + `SimulationSequence`) for multi-stage sequential problems with feedforward constraints and chronology management.
- **Results returned as DataFrames** via `read_variable()`, `read_dual()`, `read_expression()`, etc. For multi-stage simulations, `read_realized_variable()` concatenates intervals across steps. Long simulations use HDF5 storage with caching.
- **Network matrices** (PTDF, LODF, Ybus, incidence) are computed by PowerNetworkMatrices.jl (v0.12.1), supporting dense, KLU sparse, and virtual (lazy) evaluation modes with HDF5 serialization.
- **PowerFlows.jl provides standalone power flow** with AC solvers (Newton-Raphson, trust region, Levenberg-Marquardt, robust homotopy) and DC variants (standard DC, PTDF-based, virtual PTDF). Results can be exported to PSS/E format.
- **Parallel simulation support** via `run_parallel_simulation()` with configurable partitioning and overlap periods.

## Detailed Notes

### Data Model (PowerSystems.jl v4.6.2)

The `System` struct is the top-level container. Components are organized in a type hierarchy rooted at `InfrastructureSystemsType > Component`.

**Topology types:**
- `ACBus` — fields: `number`, `name`, `bustype`, `angle`, `magnitude`, `voltage_limits`, `base_voltage`, `area`, `load_zone`
- `DCBus`, `Arc`, `Area`, `LoadZone`

**Generator hierarchy** (`Generator` abstract type):
- `ThermalGen` > `ThermalStandard`, `ThermalMultiStart`
- `RenewableGen` > `RenewableDispatch`, `RenewableNonDispatch`
- `HydroGen` > `HydroDispatch`, `HydroEnergyReservoir`, `HydroPumpedStorage`

**Branch hierarchy** (`Branch` abstract type):
- `ACBranch` > `Line`, `MonitoredLine`, `Transformer2W`, `TapTransformer`, `PhaseShiftingTransformer`, `DynamicBranch`, `TwoTerminalHVDCLine`, `TwoTerminalVSCDCLine`
- `DCBranch` > `TModelHVDCLine`
- `AreaInterchange`

`Line` fields: `name`, `available`, `active_power_flow`, `reactive_power_flow`, `arc`, `r`, `x`, `b` (from/to), `rating`, `angle_limits`, `g` (from/to)

`ThermalStandard` fields: `name`, `available`, `status`, `bus`, `active_power`, `reactive_power`, `rating`, `active_power_limits` (min/max), `reactive_power_limits`, `ramp_limits` (up/down), `operation_cost`, `base_power`, `time_limits` (up/down), `must_run`, `prime_mover_type`, `fuel`, `services`, `time_at_status`

**Load types** (`ElectricLoad`):
- `PowerLoad`, `StandardLoad`, `ExponentialLoad`, `InterruptiblePowerLoad` (controllable), `FixedAdmittance`, `SwitchedAdmittance`

**Storage:** `EnergyReservoirStorage`

**Services:**
- `Reserve` > `ConstantReserve`, `VariableReserve`, `ReserveDemandCurve`
- `ReserveNonSpinning` > `ConstantReserveNonSpinning`, `VariableReserveNonSpinning`
- `AGC`, `ConstantReserveGroup`, `TransmissionInterface`

**Time series** handled by InfrastructureSystems.jl (v2.6.0): `Forecast` (multi-value per timestamp) and `StaticTimeSeries` (single value per timestamp).

Sources:
- [PowerSystems.jl type structure docs](https://nrel-sienna.github.io/PowerSystems.jl/stable/explanation/type_structure/)
- [PowerSystems.jl GitHub](https://github.com/NREL-Sienna/PowerSystems.jl)
- Verified via `subtypes()` and `fieldnames()` in Julia REPL (PowerSystems v4.6.2)

### Input Formats

`System(file_path)` auto-detects format:

1. **MATPOWER `.m` files** — parsed via PowerModels.jl integration. Example: `sys = System("case39.m")`
2. **PSS/E `.raw` files** — v30 (partial), v33, v35 supported
3. **PSS/E `.raw` + `.dyr` files** — `System(raw_file, dyr_file)` for dynamic data
4. **Tabular CSV** — custom format with `bus.csv`, `gen.csv`, `branch.csv`, `load.csv`, `storage.csv`, `reserves.csv`, `dc_branch.csv`

All values are stored in per-unit (system base power). The `System` constructor normalizes data automatically.

Sources:
- [Parse MATPOWER/PSS/E docs](https://nrel-sienna.github.io/PowerSystems.jl/stable/how_to/parse_matpower_psse/)
- [Parsing guide](https://nrel-sienna.github.io/PowerSystems.jl/stable/how_to/parsing/)
- Verified: `System` constructor methods from Julia REPL

### Problem Formulations and Templates

#### Entry Points

Two convenience templates create pre-configured `ProblemTemplate` objects:

**`template_unit_commitment(; network, devices, services)`**
Default devices: `ThermalStandard`/`ThermalBasicUnitCommitment`, `RenewableDispatch`/`RenewableFullDispatch`, `RenewableNonDispatch`/`FixedOutput`, `PowerLoad`/`StaticPowerLoad`, `InterruptiblePowerLoad`/`PowerLoadInterruption`, `Line`/`StaticBranch`, `Transformer2W`/`StaticBranch`, `TapTransformer`/`StaticBranch`, `TwoTerminalHVDCLine`/`HVDCTwoTerminalDispatch`. Default network: `CopperPlatePowerModel`. Default services: `VariableReserve{ReserveUp}`/`RangeReserve`, `VariableReserve{ReserveDown}`/`RangeReserve`.

**`template_economic_dispatch(; network, devices, services)`**
Same as UC template but thermal uses `ThermalBasicDispatch` instead of `ThermalBasicUnitCommitment`.

Source: PowerSimulations source at `src/operation/operation_problem_templates.jl` (verified in devcontainer)

#### Custom Templates

```julia
template = ProblemTemplate(NetworkModel(PTDFPowerModel, use_slacks=true))
set_device_model!(template, ThermalStandard, ThermalStandardUnitCommitment)
set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
set_device_model!(template, PowerLoad, StaticPowerLoad)
set_device_model!(template, Line, StaticBranch)
set_service_model!(template, ServiceModel(VariableReserve{ReserveUp}, RangeReserve))
```

Source: [PowerSimulations.jl API reference](https://nrel-sienna.github.io/PowerSimulations.jl/latest/api/PowerSimulations/)

### Network Formulations

All 15 re-exported network formulation types, categorized:

**Native PSI formulations (no PowerModels dependency):**

| Type | Description |
|------|-------------|
| `CopperPlatePowerModel` | Single-node, no branch flow constraints |
| `AreaBalancePowerModel` | One node per area, area-level balance |
| `PTDFPowerModel` | Linear PTDF-based with system-wide balance |
| `AreaPTDFPowerModel` | PTDF with per-area balance |

**PowerModels.jl formulations (via re-export):**

| Type | Description |
|------|-------------|
| `DCPPowerModel` | Linear DC approximation (voltage angles) |
| `DCPLLPowerModel` | DC with linear losses |
| `NFAPowerModel` | Network flow approximation |
| `ACPPowerModel` | Full nonlinear AC (polar coordinates) |
| `ACRPowerModel` | Full nonlinear AC (rectangular coordinates) |
| `ACTPowerModel` | Full nonlinear AC (trigonometric) |
| `SOCWRPowerModel` | SOC relaxation of AC |
| `SOCWRConicPowerModel` | Conic SOC relaxation |
| `QCRMPowerModel` | QC relaxation |
| `QCLSPowerModel` | QC relaxation with linear strengthening |
| `LPACCPowerModel` | Linear approximation of AC |

The `NetworkModel` constructor accepts: `use_slacks`, `PTDF_matrix`, `reduce_radial_branches`, `subnetworks`, `duals`, `power_flow_evaluation`.

Sources:
- [Network formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Network/)
- Verified: all 15 types confirmed present via `isdefined()` in PowerSimulations v0.30.2

### Device Formulations

#### Thermal Generation (9 formulations)

**Dispatch (continuous, no commitment variables):**
- `ThermalBasicDispatch` — range constraints, no ramp limits
- `ThermalDispatchNoMin` — like BasicDispatch but lower bound set to 0
- `ThermalCompactDispatch` — uses `PowerAboveMinimumVariable`, includes ramp constraints
- `ThermalStandardDispatch` — range constraints + intertemporal ramp constraints, optional slack

**Unit Commitment (binary on/off/start/stop variables):**
- `ThermalBasicUnitCommitment` — commitment constraints, no intertemporal constraints
- `ThermalBasicCompactUnitCommitment` — compact (above-minimum) formulation without intertemporal constraints
- `ThermalCompactUnitCommitment` — compact with minimum up/down time constraints
- `ThermalStandardUnitCommitment` — full UC with ramp rates + min up/down time + simplified startup
- `ThermalMultiStartUnitCommitment` — hot/warm/cold startup modeling (`ThermalMultiStart` devices only)

All add costs via `ProductionCostExpression`. Apply to `ThermalStandard` and `ThermalMultiStart` (except `ThermalMultiStartUnitCommitment` which requires `ThermalMultiStart`).

Source: [Thermal generation formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/ThermalGen/)

#### Renewable Generation (3 formulations)
- `FixedOutput` — inject at forecast level, no optimization variables
- `RenewableFullDispatch` — dispatch between 0 and forecast maximum
- `RenewableConstantPowerFactor` — dispatch with reactive power linked via constant power factor

Apply to `RenewableDispatch` and `RenewableNonDispatch`.

Source: [Renewable generation formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/RenewableGen/)

#### Load (3 formulations)
- `StaticPowerLoad` — non-dispatchable, time series parameter only
- `PowerLoadDispatch` — continuously curtailable
- `PowerLoadInterruption` — binary on/off interruption

Apply to `PowerLoad`, `StandardLoad`, `InterruptiblePowerLoad`, `ExponentialLoad`, etc.

Source: [Load formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Load/)

#### Branch (7+ formulations)
- `StaticBranch` — PTDF-based flow with rate bounds and optional slack
- `StaticBranchBounds` — bounds applied directly to flow variable
- `StaticBranchUnbounded` — PTDF flow equation without rate limits
- `PhaseAngleControl` — for `PhaseShiftingTransformer`, includes phase shift variable
- `HVDCTwoTerminalUnbounded` — no constraints, contributes to nodal balance
- `HVDCTwoTerminalLossless` — directional power limits
- `HVDCTwoTerminalDispatch` — directional limits + loss modeling + binary flow direction

Apply to `Line`, `MonitoredLine`, `Transformer2W`, `PhaseShiftingTransformer`, `TwoTerminalHVDCLine`, etc.

Source: [Branch formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Branch/)

#### Services/Reserves (7 formulations)
- `RangeReserve` — standard reserve requirement constraint
- `StepwiseCostReserve` — demand curve (e.g., ISO ORDC)
- `GroupReserve` — aggregates multiple services
- `RampReserve` — ramp-rate-limited reserves
- `NonSpinningReserve` — offline generator startup-based reserves
- `ConstantMaxInterfaceFlow` — fixed transmission interface limits
- `VariableMaxInterfaceFlow` — time-varying interface limits

Source: [Service formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Service/)

### Solver Interface

PowerSimulations.jl delegates to JuMP.jl / MathOptInterface.jl. Any MOI-compatible solver works.

**Installed solvers in this evaluation environment:**

| Solver | Version | Capabilities |
|--------|---------|-------------|
| HiGHS | 1.21.1 | LP, MILP, QP |
| GLPK | 1.2.1 | LP, MILP |
| Ipopt | 1.14.1 | NLP (interior point) |
| SCIP | 0.12.8 | MILP, MINLP |

**Solver configuration pattern:**
```julia
solver = optimizer_with_attributes(HiGHS.Optimizer, "mip_rel_gap" => 0.01)
model = DecisionModel(template, sys; optimizer=solver, horizon=Hour(24))
```

The `optimizer_with_attributes` function is re-exported from JuMP for convenience. Solver warm-starting and matrix factorization reuse are handled automatically for sequential solves within simulations.

Sources:
- [PowerSimulations.jl API](https://nrel-sienna.github.io/PowerSimulations.jl/latest/api/PowerSimulations/)
- [arXiv paper](https://arxiv.org/html/2404.03074v1)
- Verified: `Project.toml` and `Pkg.dependencies()` in devcontainer

### Single-Step Problem Workflow (DecisionModel)

```julia
using PowerSimulations, PowerSystems, HiGHS

# 1. Load system
sys = System("case.m")

# 2. Create template
template = template_unit_commitment(
    network=NetworkModel(PTDFPowerModel, use_slacks=true)
)

# 3. Configure solver
solver = optimizer_with_attributes(HiGHS.Optimizer, "mip_rel_gap" => 0.5)

# 4. Build model
model = DecisionModel(template, sys; optimizer=solver, horizon=Hour(24))
build!(model; output_dir=mktempdir())

# 5. Solve
solve!(model)

# 6. Read results
results = OptimizationProblemResults(model)
thermal_power = read_variable(results, "ActivePowerVariable__ThermalStandard")
duals = read_dual(results, "CopperPlateBalanceConstraint__System")
cost = read_expression(results, "ProductionCostExpression__ThermalStandard")
```

Sources:
- [PowerSimulations.jl tutorials](https://nrel-sienna.github.io/PowerSimulations.jl/latest/)
- [How to read results](https://nrel-sienna.github.io/PowerSimulations.jl/latest/how_to/read_results/)

### Multi-Stage Simulation Workflow

```julia
# 1. Define templates for each stage
template_uc = template_unit_commitment()
template_ed = template_economic_dispatch(
    network=NetworkModel(PTDFPowerModel, use_slacks=true)
)

# 2. Create simulation models
models = SimulationModels(decision_models=[
    DecisionModel(template_uc, sys_DA; optimizer=solver, name="UC"),
    DecisionModel(template_ed, sys_RT; optimizer=solver, name="ED"),
])

# 3. Define sequence with feedforwards
sequence = SimulationSequence(
    models=models,
    feedforwards=Dict(
        "ED" => [SemiContinuousFeedforward(
            component_type=ThermalStandard,
            source=OnVariable,
            affected_values=[ActivePowerVariable],
        )]
    ),
    ini_cond_chronology=InterProblemChronology(),
)

# 4. Build and execute
sim = Simulation(; name="test", steps=5, models=models,
                   sequence=sequence, simulation_folder=mktempdir())
build!(sim)
execute!(sim)

# 5. Read results
results = SimulationResults(sim)
results_uc = get_decision_problem_results(results, "UC")
realized = read_realized_variable(results_uc, "ActivePowerVariable__ThermalStandard")
```

Two chronology modes:
- `InterProblemChronology` — initial conditions from realized system state
- `IntraProblemChronology` — initial conditions from previous decision problem

Sources:
- [arXiv paper](https://arxiv.org/html/2404.03074v1)
- [PowerSimulations.jl API](https://nrel-sienna.github.io/PowerSimulations.jl/latest/api/PowerSimulations/)

### Output / Results Access

All result-reading functions return **DataFrames**:

| Function | Returns | Context |
|----------|---------|---------|
| `read_variable(results, name)` | DataFrame (single-step) or SortedDict{DateTime,DataFrame} (simulation) | Decision variables |
| `read_dual(results, name)` | Same | Constraint dual values (shadow prices / LMPs) |
| `read_expression(results, name)` | Same | Computed expressions (e.g., production cost) |
| `read_parameter(results, name)` | Same | Input parameters |
| `read_aux_variable(results, name)` | Same | Auxiliary variables |
| `read_realized_variable(results, name)` | Single concatenated DataFrame | Realized values across all simulation steps |

Naming convention: `"VariableType__DeviceType"` (double underscore separator).

**Storage backends:**
- In-memory store for small problems
- HDF5 store for large simulations (with caching layer, min 1 MiB writes, compression)

**Export functions:** `export_results()`, `export_realized_results()`, `export_optimizer_stats()`

Sources:
- [How to read results](https://nrel-sienna.github.io/PowerSimulations.jl/latest/how_to/read_results/)
- [arXiv paper](https://arxiv.org/html/2404.03074v1)

### Power Flow (PowerFlows.jl v0.9.0)

Standalone power flow (not optimization), separate from PowerSimulations.jl.

**AC Power Flow** via `solve_power_flow(ACPowerFlow(), sys)`:
- Newton-Raphson (default), Trust Region, Levenberg-Marquardt, Robust Homotopy
- Options: reactive power limit checking, loss factors, voltage stability factors
- Returns Dict of DataFrames with bus voltages and branch flows

**DC Power Flow** via `solve_power_flow(DCPowerFlow(), sys)`:
- Standard DC, `PTDFDCPowerFlow`, `vPTDFDCPowerFlow` (virtual/lazy for large grids)

**In-place variant**: `solve_and_store_power_flow!(pf, sys)` updates the `System` object directly.

**PSS/E export**: results can be written to PSS/E v33/v35 format via `PSSEExportPowerFlow`.

Source: [PowerFlows.jl public API](https://nrel-sienna.github.io/PowerFlows.jl/stable/reference/api/public/)

### Network Matrices (PowerNetworkMatrices.jl v0.12.1)

Provides standard network analysis matrices:

| Matrix | Description |
|--------|-------------|
| `Ybus(sys)` | Nodal admittance matrix |
| `IncidenceMatrix(sys)` | Bus-branch connectivity {-1, 0, +1} |
| `BA_Matrix(sys)` | Branch-bus weighted by susceptances |
| `ABA_Matrix(sys)` | Bus susceptance matrix (supports KLU factorization) |
| `PTDF(sys)` | Power Transfer Distribution Factors |
| `LODF(sys)` | Line Outage Distribution Factors |
| `VirtualPTDF(sys)` | Lazy row-by-row PTDF (memory-efficient for large systems) |
| `VirtualLODF(sys)` | Lazy LODF |

Features: KLU/Dense/MKLPardiso linear solver options, sparsification tolerance, distributed slack, network reductions (radial, degree-two, Ward equivalent), HDF5 serialization via `to_hdf5()`/`from_hdf5()`.

Source: [PowerNetworkMatrices.jl public API](https://nrel-sienna.github.io/PowerNetworkMatrices.jl/stable/api/public/)

## Sources

1. [PowerSimulations.jl documentation (latest)](https://nrel-sienna.github.io/PowerSimulations.jl/latest/)
2. [PowerSimulations.jl GitHub repository](https://github.com/NREL-Sienna/PowerSimulations.jl) — 311 stars, BSD-3-Clause, last updated 2026-03-03
3. [PowerSystems.jl GitHub repository](https://github.com/NREL-Sienna/PowerSystems.jl) — 359 stars, BSD-3-Clause
4. [PowerSystems.jl type structure](https://nrel-sienna.github.io/PowerSystems.jl/stable/explanation/type_structure/)
5. [Network formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Network/)
6. [Thermal generation formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/ThermalGen/)
7. [Branch formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Branch/)
8. [Renewable generation formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/RenewableGen/)
9. [Load formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Load/)
10. [Service formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Service/)
11. [PowerFlows.jl public API](https://nrel-sienna.github.io/PowerFlows.jl/stable/reference/api/public/)
12. [PowerNetworkMatrices.jl public API](https://nrel-sienna.github.io/PowerNetworkMatrices.jl/stable/api/public/)
13. [arXiv paper: PowerSimulations.jl — A Power Systems Operations Simulation Library](https://arxiv.org/html/2404.03074v1)
14. [Parse MATPOWER/PSS/E files](https://nrel-sienna.github.io/PowerSystems.jl/stable/how_to/parse_matpower_psse/)
15. PowerSimulations.jl source code in devcontainer: `/opt/julia-depot/packages/PowerSimulations/89s3Q/`
16. PowerSystems.jl source code in devcontainer: `/opt/julia-depot/packages/PowerSystems/AHyDB/`

## Gaps and Uncertainties

- **No SCUC/SCED as named problem types.** PowerSimulations.jl does not provide explicit `SCUC` or `SCED` named formulations. Instead, these are composed from templates: UC template + `PTDFPowerModel` network + security constraints approximates SCUC; ED template similarly approximates SCED. Whether N-1 security constraints can be modeled natively (vs. requiring custom constraints) needs testing.
- **Hydro formulations not fully explored.** `HydroDispatch`, `HydroEnergyReservoir`, and `HydroPumpedStorage` exist as device types but their available formulations were not enumerated in this research pass.
- **Storage formulations not fully explored.** `EnergyReservoirStorage` exists but its formulation options were not cataloged.
- **AGC template is commented out** in the source code (v0.30.2). The `AGCReserveDeployment` problem type exists but the `template_agc_reserve_deployment()` convenience function is disabled.
- **EmulationModel** is documented as a separate problem type for real-time simulation, but its detailed API and formulation options were not explored.
- **PowerModels.jl integration depth unclear.** The 11 re-exported PowerModels formulations (ACP, ACR, ACT, DCP, etc.) are available for `NetworkModel`, but whether all formulations work correctly with all device model combinations needs verification during testing.
- **Custom formulation extensibility.** The documentation emphasizes extensibility via Julia's multiple dispatch, but the exact extension points (which abstract types to subtype, which methods to implement) need hands-on verification.
- **DecisionModel keyword arguments** (e.g., `horizon`, `resolution`, `warm_start_enabled`, `initial_time`) were not fully enumerated. The constructor signature shows `kwargs...` patterns.
- **MATPOWER parsing correctness.** The evaluation's shared MATPOWER loader applies patches for pypsa correctness; whether PowerSystems.jl's parser has similar issues with cost curves, transformer parameters, or per-unit normalization needs testing.
- **Piecewise linear cost handling.** A "Piecewise Linear Cost" formulation library section exists but was not explored. Whether cost curves from MATPOWER files are correctly interpreted needs verification.
