# PowerSimulations.jl — Research: API & Formulations

## Key Findings

- **PowerSimulations.jl (v0.30.2) is an optimization-based operations simulation tool**, not a power-flow solver. It builds JuMP optimization models for unit commitment (SCUC), economic dispatch (SCED), and multi-stage production cost simulations. Power flow is handled by the companion package PowerFlows.jl (v0.9.0).
- **The data model lives in PowerSystems.jl (v4.6.2)**, which provides typed Julia structs for buses (`ACBus`), generators (`ThermalStandard`, `RenewableDispatch`, etc.), branches (`Line`, `Transformer2W`, etc.), loads, storage, and services. It parses MATPOWER `.m`, PSS/E `.raw`/`.dyr`, and tabular CSV files via `System(file_path)`.
- **15 network formulations are available**, including 4 native PSI types (`CopperPlatePowerModel`, `AreaBalancePowerModel`, `PTDFPowerModel`, `AreaPTDFPowerModel`) and 11 re-exported from PowerModels.jl (ranging from `DCPPowerModel` to `ACPPowerModel`).
- **9 thermal generation formulations** span dispatch-only (`ThermalBasicDispatch`, `ThermalStandardDispatch`) through full unit commitment with multi-start profiles (`ThermalMultiStartUnitCommitment`), with intermediate options for compact representations and relaxed minimums.
- **Solver-agnostic via JuMP/MathOptInterface**: any MOI-compatible solver works. The installed environment includes HiGHS (LP/MILP), Ipopt (NLP), GLPK (LP/MILP), and SCIP (MINLP). Solver attributes are passed via `optimizer_with_attributes()`.
- **Two-level problem architecture**: `DecisionModel` for single-step optimization (20 keyword arguments controlling horizon, resolution, warm start, etc.), and `Simulation` (wrapping `SimulationModels` + `SimulationSequence`) for multi-stage sequential problems with feedforward constraints and chronology management.
- **Results returned as DataFrames** via `read_variable()`, `read_dual()`, `read_expression()`, `read_parameter()`, `read_aux_variable()`. For multi-stage simulations, `read_realized_variable()` concatenates intervals across steps. Long simulations use HDF5 storage with caching.
- **Network matrices** (PTDF, LODF, Ybus, incidence) are computed by PowerNetworkMatrices.jl (v0.12.1), supporting dense, KLU sparse, and virtual (lazy) evaluation modes with HDF5 serialization.
- **PowerFlows.jl provides standalone power flow** with AC solvers (Newton-Raphson, trust region, Levenberg-Marquardt, robust homotopy) and DC variants (standard DC, PTDF-based, virtual PTDF). Results can be exported to PSS/E format.
- **No storage or hydro formulations in core PSI v0.30.2.** These are in extension packages (StorageSystemsSimulations.jl, HydroPowerSimulations.jl) which are not installed in this evaluation environment.
- **Parallel simulation support** via `run_parallel_simulation()` with Julia's `Distributed` module, partitioning simulation steps across worker processes.

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

**Storage:** `EnergyReservoirStorage` (data type exists in PowerSystems.jl, but formulations require the StorageSystemsSimulations.jl extension package, not installed)

**Services:**
- `Reserve` > `ConstantReserve`, `VariableReserve`, `ReserveDemandCurve`
- `ReserveNonSpinning` > `ConstantReserveNonSpinning`, `VariableReserveNonSpinning`
- `AGC`, `ConstantReserveGroup`, `TransmissionInterface`

**Time series** handled by InfrastructureSystems.jl (v2.6.0): `Forecast` (multi-value per timestamp: `Deterministic`, `Probabilistic`) and `StaticTimeSeries` (`SingleTimeSeries`).

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

All 15 network formulation types, categorized:

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
- Source code: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/formulations.jl`

### Device Formulations

#### Thermal Generation (9 formulations)

**Dispatch (continuous, no commitment variables):**
- `ThermalBasicDispatch` — range constraints, no ramp limits
- `ThermalDispatchNoMin` — like BasicDispatch but lower bound set to 0. *May not work with non-convex PWL cost definitions* (per source code docstring)
- `ThermalCompactDispatch` — uses `PowerAboveMinimumVariable`, includes ramp constraints
- `ThermalStandardDispatch` — range constraints + intertemporal ramp constraints, optional slack

**Unit Commitment (binary on/off/start/stop variables):**
- `ThermalBasicUnitCommitment` — commitment constraints, no intertemporal constraints
- `ThermalBasicCompactUnitCommitment` — compact (above-minimum) formulation without intertemporal constraints
- `ThermalCompactUnitCommitment` — compact with minimum up/down time constraints
- `ThermalStandardUnitCommitment` — full UC with ramp rates + min up/down time + simplified startup
- `ThermalMultiStartUnitCommitment` — hot/warm/cold startup modeling (`ThermalMultiStart` devices only). Uses `HotStartVariable`, `WarmStartVariable`, `ColdStartVariable`.

All add costs via `ProductionCostExpression`. Apply to `ThermalStandard` and `ThermalMultiStart` (except `ThermalMultiStartUnitCommitment` which requires `ThermalMultiStart`).

**Type hierarchy** (from source code):
```
AbstractDeviceFormulation
  AbstractThermalFormulation
    AbstractThermalDispatchFormulation
      ThermalBasicDispatch
      ThermalStandardDispatch
      ThermalDispatchNoMin
      ThermalCompactDispatch
    AbstractThermalUnitCommitment
      AbstractStandardUnitCommitment
        ThermalBasicUnitCommitment
        ThermalStandardUnitCommitment
      AbstractCompactUnitCommitment
        ThermalMultiStartUnitCommitment
        ThermalCompactUnitCommitment
        ThermalBasicCompactUnitCommitment
```

Source: [Thermal generation formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/ThermalGen/); `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/formulations.jl`

#### Renewable Generation (3 formulations)
- `FixedOutput` — inject at forecast level, no optimization variables. Defined in `device_model.jl`, not `formulations.jl`.
- `RenewableFullDispatch` — dispatch between 0 and forecast maximum
- `RenewableConstantPowerFactor` — dispatch with reactive power linked via constant power factor

Apply to `RenewableDispatch` and `RenewableNonDispatch`.

Source: [Renewable generation formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/RenewableGen/); `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/formulations.jl`

#### Load (3 formulations)
- `StaticPowerLoad` — non-dispatchable, time series parameter only
- `PowerLoadDispatch` — continuously curtailable
- `PowerLoadInterruption` — binary on/off interruption

Apply to `PowerLoad`, `StandardLoad`, `InterruptiblePowerLoad`, `ExponentialLoad`, etc.

Source: [Load formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Load/)

#### Branch (8 formulations)
- `StaticBranch` — PTDF-based flow with rate bounds and optional slack
- `StaticBranchBounds` — bounds applied directly to flow variable
- `StaticBranchUnbounded` — PTDF flow equation without rate limits
- `PhaseAngleControl` — for `PhaseShiftingTransformer`, includes phase shift variable
- `HVDCTwoTerminalUnbounded` — no constraints, contributes to nodal balance
- `HVDCTwoTerminalLossless` — directional power limits
- `HVDCTwoTerminalDispatch` — directional limits + loss modeling + binary flow direction
- `HVDCTwoTerminalPiecewiseLoss` — piecewise lossy power flow on two-terminal DC lines

Additional: `LossLessConverter` (for AC/DC converters), `LossLessLine`

Apply to `Line`, `MonitoredLine`, `Transformer2W`, `PhaseShiftingTransformer`, `TwoTerminalHVDCLine`, etc.

Source: [Branch formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Branch/); `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/formulations.jl`

#### Regulation Device (2 formulations)
- `ReserveLimitedRegulation` — regulation limited by reserve requirement
- `DeviceLimitedRegulation` — regulation limited by device capacity

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/formulations.jl`

#### Services/Reserves (7 formulations)
- `RangeReserve` — standard reserve requirement constraint
- `StepwiseCostReserve` — demand curve (e.g., ISO ORDC)
- `GroupReserve` — aggregates multiple services
- `RampReserve` — ramp-rate-limited reserves
- `NonSpinningReserve` — offline generator startup-based reserves
- `ConstantMaxInterfaceFlow` — fixed transmission interface limits
- `VariableMaxInterfaceFlow` — time-varying interface limits
- `PIDSmoothACE` — AGC-specific formulation for ACE smoothing

Source: [Service formulation library](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Service/); `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/formulations.jl`

#### Storage and Hydro (NOT in core v0.30.2)

PowerSimulations.jl v0.30.2 does **not** include device model files for storage or hydro generation. The `src/devices_models/devices/` directory contains: `thermal_generation.jl`, `renewable_generation.jl`, `electric_loads.jl`, `AC_branches.jl`, `TwoTerminalDC_branches.jl`, `HVDCsystems.jl`, `area_interchange.jl`, `regulation_device.jl`. No `storage*.jl` or `hydro*.jl` files exist.

Storage and hydro formulations require separate extension packages:
- **StorageSystemsSimulations.jl** — provides `StorageDispatchWithReserves`, `BookKeeping`, and other storage formulations
- **HydroPowerSimulations.jl** — provides hydro-specific dispatch and energy budget formulations
- **HybridSystemsSimulations.jl** — provides hybrid (solar+storage, wind+storage) formulations

None of these extension packages are installed in the evaluation environment. The PowerSystems.jl data types (`EnergyReservoirStorage`, `HydroDispatch`, `HydroEnergyReservoir`, `HydroPumpedStorage`) exist for data modeling, but no optimization formulations can be applied to them without the extension packages.

Sources:
- Directory listing: `find /opt/julia-depot/packages/PowerSimulations/89s3Q/src/devices_models -name "*.jl"` (no storage/hydro files)
- `ls /opt/julia-depot/packages/ | grep -i storage` (no StorageSystemsSimulations package)
- [HydroPowerSimulations.jl GitHub](https://github.com/NREL-Sienna/HydroPowerSimulations.jl)
- [StorageSystemsSimulations.jl](https://github.com/NREL-Sienna/StorageSystemsSimulations.jl) (referenced in PowerSimulations.jl docs)

### Optimization Variables (Complete List from Source)

All variable types defined in `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/variables.jl`:

**Generation/Load:**
- `ActivePowerVariable` (p) — active power output
- `PowerAboveMinimumVariable` (delta p) — for compact thermal formulations
- `ActivePowerInVariable` (p_in) — for 2-directional devices (storage, pump-hydro)
- `ActivePowerOutVariable` (p_out) — for 2-directional devices
- `ReactivePowerVariable` (q) — reactive power output
- `EnergyVariable` (e) — energy storage level / state of charge

**Commitment:**
- `OnVariable` (u) — binary commitment status
- `StartVariable` (v) — binary start
- `StopVariable` (w) — binary stop
- `HotStartVariable`, `WarmStartVariable`, `ColdStartVariable` — multi-start thermal

**Flow:**
- `FlowActivePowerVariable` (f) — bidirectional
- `FlowActivePowerFromToVariable`, `FlowActivePowerToFromVariable` — unidirectional
- `FlowReactivePowerFromToVariable`, `FlowReactivePowerToFromVariable` — unidirectional reactive
- `VoltageAngle` (theta) — bus voltage angle
- `VoltageMagnitude` (v) — bus voltage magnitude
- `PhaseShifterAngle` — phase shifting transformer control

**HVDC:**
- `HVDCLosses`, `HVDCFlowDirectionVariable`
- `HVDCActivePowerReceivedFromVariable`, `HVDCActivePowerReceivedToVariable`
- `HVDCPiecewiseLossVariable`, `HVDCPiecewiseBinaryLossVariable`

**Reserves:**
- `ActivePowerReserveVariable` (r) — reserve contribution
- `ServiceRequirementVariable` — service requirement level
- `ReservationVariable` — binary storage charge reservation

**Slacks:**
- `SystemBalanceSlackUp`, `SystemBalanceSlackDown` — system-wide balance
- `FlowActivePowerSlackUpperBound`, `FlowActivePowerSlackLowerBound` — branch flow
- `ReserveRequirementSlack` — reserve requirement
- `InterfaceFlowSlackUp`, `InterfaceFlowSlackDown` — interface flow
- `UpperBoundFeedForwardSlack`, `LowerBoundFeedForwardSlack` — feedforward bounds
- `RateofChangeConstraintSlackUp`, `RateofChangeConstraintSlackDown` — ramp rate

**AGC:**
- `SteadyStateFrequencyDeviation`, `AreaMismatchVariable`, `SmoothACE`
- `DeltaActivePowerUpVariable`, `DeltaActivePowerDownVariable`
- `AdditionalDeltaActivePowerUpVariable`, `AdditionalDeltaActivePowerDownVariable`

**Cost:**
- `PieceWiseLinearCostVariable` — PWL lambda-model variables
- `PieceWiseLinearBlockOffer` — block offer variables

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/variables.jl`

### Expression Types

Expressions represent computed quantities that aggregate variable contributions:

- `ActivePowerBalance` — system-wide active power balance (used in network constraints)
- `ReactivePowerBalance` — system-wide reactive power balance
- `ProductionCostExpression` — total production cost per device
- `FuelConsumptionExpression` — fuel consumption tracking
- `ActivePowerRangeExpressionLB`, `ActivePowerRangeExpressionUB` — range constraint bounds
- `ComponentReserveUpBalanceExpression`, `ComponentReserveDownBalanceExpression` — reserve allocation tracking
- `InterfaceTotalFlow` — total flow on transmission interfaces
- `PTDFBranchFlow` — PTDF-computed branch flow
- `EmergencyUp`, `EmergencyDown` — emergency reserve expressions
- `RawACE` — raw area control error for AGC

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/expressions.jl`

### Auxiliary Variables

Auxiliary variables are computed post-solve or from power flow evaluations:

- `TimeDurationOn`, `TimeDurationOff` — thermal commitment duration tracking
- `PowerOutput` — actual power output (for compact formulations where the optimization variable is power-above-minimum)
- `PowerFlowVoltageAngle`, `PowerFlowVoltageMagnitude` — from embedded power flow evaluation
- `PowerFlowLineActivePowerFromTo`, `PowerFlowLineActivePowerToFrom` — line active flows from PF
- `PowerFlowLineReactivePowerFromTo`, `PowerFlowLineReactivePowerToFrom` — line reactive flows from PF
- `PowerFlowLossFactors` — loss factors from AC power flow Jacobian

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/core/auxiliary_variables.jl`

### Cost Function Handling

PowerSimulations.jl supports multiple cost curve representations via PowerSystems.jl's cost types:

**Cost curve types** (from `operation_cost` field on generators):
- **Linear curves** — proportional cost per MW (`linear_curve.jl`)
- **Quadratic curves** — polynomial cost function (`quadratic_curve.jl`)
- **Piecewise linear (PWL)** — defined by points $(P_k, C_k)$ representing power-cost pairs (`piecewise_linear.jl`)
- **Market bid curves** — time-varying bid-based costs (`market_bid.jl`)

**PWL implementation** uses the lambda-model formulation (equivalent to the formulation in "The Impacts of Convex Piecewise Linear Cost Formulations on AC OPF"). SOS2 constraints are only added if the PWL data is non-convex. PWL variables (`PieceWiseLinearCostVariable`) are bounded [0,1] and represent the interpolation weights.

**Cost components:**
- Variable cost — from `operation_cost` via `_add_variable_cost_to_objective!`
- VOM (variable O&M) cost — added separately via `_add_vom_cost_to_objective!`
- Startup cost — proportional to start variable (including hot/warm/cold differentiation for `ThermalMultiStart`)
- Shutdown cost — proportional to stop variable

Sources:
- [Piecewise Linear Cost formulation](https://docs.juliahub.com/PowerSimulations/ixScC/0.28.1/formulation_library/Piecewise.html)
- `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/devices_models/devices/common/objective_function/`

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

### DecisionModel Constructor (Complete kwargs from Source)

The `DecisionModel` constructor accepts 20 keyword arguments (verified from source at `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/operation/decision_model.jl`):

| Keyword | Type | Default | Description |
|---------|------|---------|-------------|
| `name` | `String`/`Symbol`/`Nothing` | `nothing` | Model name; defaults to type name |
| `optimizer` | `MOI.OptimizerWithAttributes`/`Nothing` | `nothing` | Solver configuration |
| `horizon` | `Dates.Period` | `UNSET_HORIZON` | Forecast horizon length |
| `resolution` | `Dates.Period` | `UNSET_RESOLUTION` | Time step resolution |
| `initial_time` | `Dates.DateTime` | `UNSET_INI_TIME` | Initial solve time |
| `warm_start` | `Bool` | `true` | Use current operating point to initialize variables |
| `system_to_file` | `Bool` | `true` | Serialize system copy |
| `initialize_model` | `Bool` | `true` | Run initialization routine |
| `initialization_file` | `String` | `""` | Pre-existing initialization values |
| `deserialize_initial_conditions` | `Bool` | `false` | Deserialize initial conditions |
| `export_pwl_vars` | `Bool` | `false` | Export PWL intermediate variables (slow) |
| `allow_fails` | `Bool` | `false` | Continue simulation on solve failure |
| `optimizer_solve_log_print` | `Bool` | `false` | Print solver log (unsets MOI.Silent) |
| `detailed_optimizer_stats` | `Bool` | `false` | Save detailed solver stats |
| `calculate_conflict` | `Bool` | `false` | Use solver conflict analysis for infeasible problems |
| `direct_mode_optimizer` | `Bool` | `false` | Use JuMP direct model |
| `store_variable_names` | `Bool` | `false` | Store variable names (slower build) |
| `rebuild_model` | `Bool` | `false` | Force JuMP model rebuild each update |
| `check_numerical_bounds` | `Bool` | `true` | Check numerical bounds on build |
| `time_series_cache_size` | `Int` | `1 MiB` | Time series cache size in bytes |

The constructor also accepts a custom `JuMP.Model` as the third positional argument for advanced use cases.

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/operation/decision_model.jl`

### EmulationModel

`EmulationModel` is a separate problem type for real-time simulation emulation. It uses `SingleTimeSeries` (not forecast-type time series) and is designed for problems that operate at a single time step without a multi-period horizon.

Key differences from `DecisionModel`:
- Uses `SingleTimeSeries` instead of `Deterministic` forecast type
- Does not require `horizon` parameter (operates step-by-step)
- Has `resolution` parameter for time step size
- Designed to be embedded in `Simulation` alongside `DecisionModel` instances
- Similar kwargs to `DecisionModel` minus `horizon`, `export_optimization_model`

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/operation/emulation_model.jl`

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

`SimulationSequence` automatically determines execution order from interval ratios. For example, if UC has 24h intervals and ED has 1h intervals, ED executes 24 times per UC execution. Horizons and resolutions are validated for consistency.

Sources:
- [arXiv paper](https://arxiv.org/html/2404.03074v1)
- [PowerSimulations.jl API](https://nrel-sienna.github.io/PowerSimulations.jl/latest/api/PowerSimulations/)
- `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/simulation/simulation_sequence.jl`

### Feedforward Types (Complete List from Source)

Feedforwards pass information between models in multi-stage simulations. Four concrete types exist in v0.30.2:

| Type | Purpose | Affected Values |
|------|---------|-----------------|
| `SemiContinuousFeedforward` | Enable/disable variable bounds to 0 based on commitment status. Typical use: UC `OnVariable` constrains ED `ActivePowerVariable` | `VariableType` only |
| `UpperBoundFeedforward` | Parameterized upper bound from another model. Optional slack variables via `add_slacks=true` | `VariableType` only |
| `LowerBoundFeedforward` | Parameterized lower bound from another model. Optional slack variables via `add_slacks=true` | `VariableType` only |
| `FixValueFeedforward` | Fix a variable or parameter to values from another model | `VariableType` or `ParameterType` |

**Note:** No `EnergyTargetFeedforward` or `EnergyLimitFeedforward` exists in v0.30.2 core. The constraint type `FeedforwardEnergyTargetConstraint` exists in the constraint definitions, suggesting this was planned or is in an extension package.

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/feedforward/feedforwards.jl`

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
| `read_realized_dual(results, name)` | Single concatenated DataFrame | Realized duals across steps |
| `read_realized_expression(results, name)` | Single concatenated DataFrame | Realized expressions across steps |

Naming convention: `"VariableType__DeviceType"` (double underscore separator).

**Available result names** can be listed via:
- `list_variable_names(results)`
- `list_dual_names(results)`
- `list_expression_names(results)`
- `list_parameter_names(results)`
- `list_aux_variable_names(results)`

**Storage backends:**
- In-memory store for small problems (`InMemorySimulationStore`)
- HDF5 store for large simulations (`HdfSimulationStore`) with caching layer, min 1 MiB writes, compression

**Export functions:** `export_results()`, `export_realized_results()`, `export_optimizer_stats()`

Sources:
- [How to read results](https://nrel-sienna.github.io/PowerSimulations.jl/latest/how_to/read_results/)
- [arXiv paper](https://arxiv.org/html/2404.03074v1)
- `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/simulation/`

### Parallel Simulation

`run_parallel_simulation()` partitions a simulation into chunks and distributes them across Julia worker processes using `Distributed.pmap()`.

```julia
run_parallel_simulation(
    build_function,          # Function to build simulation
    execute_function;        # Function to execute simulation
    script::AbstractString,  # Script file to include on workers
    output_dir::AbstractString,
    name::AbstractString,
    num_steps::Integer,      # Total simulation steps
    period::Integer,         # Steps per partition
    num_overlap_steps = 1,   # Overlap for initial conditions
    num_parallel_processes = Sys.CPU_THREADS,
    exeflags = nothing,      # Julia startup flags for workers
    force = false,           # Overwrite output directory
)
```

Workers are created via `Distributed.addprocs()`, the script is included on each worker via `@everywhere include()`, and partitions are dispatched via `pmap()`. Results from partitions can be joined via `SimulationPartitionResults`.

Source: `/opt/julia-depot/packages/PowerSimulations/89s3Q/src/simulation/simulation_partitions.jl`

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

### JuMP Model Access

The underlying JuMP optimization model is fully accessible for custom modifications:

```julia
# After build!, before solve!
jump_model = PSI.get_jump_model(model)

# Add custom constraints using JuMP API
@constraint(jump_model, my_constraint, ...)

# Access optimization container for PSI-managed objects
container = PSI.get_optimization_container(model)
```

The two-stage construction pattern (`ArgumentConstructStage` then `ModelConstructStage`) means all variables exist before constraints are added, enabling custom constraint injection between stages or after `build!`.

Source: [arXiv paper](https://arxiv.org/html/2404.03074v1); devcontainer REPL verification

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
15. [Piecewise Linear Cost formulation (v0.28.1 docs)](https://docs.juliahub.com/PowerSimulations/ixScC/0.28.1/formulation_library/Piecewise.html)
16. [HydroPowerSimulations.jl GitHub](https://github.com/NREL-Sienna/HydroPowerSimulations.jl)
17. PowerSimulations.jl source code in devcontainer: `/opt/julia-depot/packages/PowerSimulations/89s3Q/`
18. PowerSystems.jl source code in devcontainer: `/opt/julia-depot/packages/PowerSystems/AHyDB/`

## Gaps and Uncertainties

- **No SCUC/SCED as named problem types.** PowerSimulations.jl does not provide explicit `SCUC` or `SCED` named formulations. Instead, these are composed from templates: UC template + `PTDFPowerModel` network + security constraints approximates SCUC; ED template similarly approximates SCED. Whether N-1 security constraints can be modeled natively (vs. requiring custom constraints) needs testing.
- **Storage and hydro formulations not available.** The extension packages (StorageSystemsSimulations.jl, HydroPowerSimulations.jl) are not installed. `EnergyReservoirStorage` data types exist but cannot be optimized without extension formulations. If storage evaluation is needed, these packages must be added to `Project.toml`.
- **AGC template is commented out** in the source code (v0.30.2). The `AGCReserveDeployment` problem type exists but the `template_agc_reserve_deployment()` convenience function is disabled.
- **EmulationModel** usage pattern is clear from source but there is limited documentation and no tutorials demonstrating it as part of a `Simulation` sequence.
- **PowerModels.jl integration depth unclear.** The 11 re-exported PowerModels formulations (ACP, ACR, ACT, DCP, etc.) are available for `NetworkModel`, but whether all formulations work correctly with all device model combinations needs verification during testing. The source code comment lists additional PowerModels types (SOCBFPowerModel, SDPWRMPowerModel, SparseSDPWRMPowerModel) that are NOT re-exported.
- **Custom formulation extensibility.** The documentation emphasizes extensibility via Julia's multiple dispatch. The extension points are: (1) subtype `AbstractDeviceFormulation`, (2) define `construct_device!` methods for `ArgumentConstructStage` and `ModelConstructStage`. Hands-on verification of this pattern is needed.
- **MATPOWER parsing correctness.** The evaluation's shared MATPOWER loader applies patches for pypsa correctness; whether PowerSystems.jl's parser has similar issues with cost curves, transformer parameters, or per-unit normalization needs testing.
- **Piecewise linear cost handling.** PWL uses the lambda-model with SOS2 constraints for non-convex data. Whether cost curves from MATPOWER files are correctly interpreted (especially the mapping from MATPOWER's polynomial/piecewise format to PowerSystems.jl cost types) needs verification.
- **`FeedforwardEnergyTargetConstraint` exists as a constraint type** but no corresponding `EnergyTargetFeedforward` struct exists in v0.30.2 core. This may be in an extension package or was removed/refactored.
- **Result export format details.** `export_realized_results` writes to a directory structure of CSV files, but the exact column format and whether units are in per-unit or natural units needs verification. Source code indicates `convert_result_to_natural_units` flags exist per variable type.
