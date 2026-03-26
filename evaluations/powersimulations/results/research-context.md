# PowerSimulations.jl — Research Context

Merged from 4 research agents on 2026-03-24.

---

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

---

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

---

# PowerSimulations.jl — Research: Limitations & Ecosystem

## Key Findings

- **No built-in SCOPF**: Security-constrained OPF is an open feature request since March 2023 ([#944](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/944)), with zero comments. Test A-9 will require manual contingency constraint assembly or a workaround via B-1's custom constraint API.
- **No built-in loss approximation for PTDF models**: Open issue [#1537](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1537) explicitly states "Add losses approximations to PTDF models" is planned but requires LHS parameter implementation. Test A-10 (lossy DCOPF with LMP decomposition) may be difficult or impossible.
- **No documented distributed slack formulation**: The network formulation library documents CopperPlate, AreaBalance, PTDF, and AreaPTDF models but makes no mention of distributed slack. Test A-11 will likely require a workaround.
- **Active bugs affect evaluation tests**: Ramp-down inequality may be flipped ([#1530](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1530)), DC power flow initialization bug with renewables ([#1545](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1545)), renewable natural-unit profiles treated as scaling factors ([#1557](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1557)).
- **Very active development**: 1021 commits in last 12 months, 21 releases in last 24 months, but dominated by a single lead developer (jd-lara: ~70% of all-time commits).
- **Large dependency footprint**: 80+ resolved packages in Manifest.toml (1186 lines), including MKL, HDF5, SQLite — far heavier than PowerModels.jl for equivalent tasks.
- **Fragile cross-package compat bounds**: The Sienna ecosystem (5+ tightly coupled packages) requires careful version archaeology to get a satisfiable dependency resolution. Multiple packages pinned below latest.
- **BSD-3-Clause across all Sienna packages**: Permissive licensing with no copyleft concerns.
- **NREL institutional backing**: Federally funded via DOE/NREL with named PI (Clayton Barrows) and development lead (José Daniel Lara). Durable funding but bus-factor risk is high.
- **Post-contingency evaluation is an open issue** ([#1522](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1522)) — no body/description, just a title.

## Detailed Notes

### Known Limitations Relevant to Evaluation Tests

#### SCOPF (Test A-9)
SCOPF has been an open feature request since 2023-03-14 ([#944](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/944)). The issue requests "N-1 (N-k) security constrained optimal power flow (unit commitment, economic dispatch) with PTDF formulation against branch and generator contingencies." It has zero comments and remains unimplemented. The evaluation test A-9 requires DC OPF with N-1 contingency constraints embedded in the optimization. This will need to be accomplished via manual constraint addition using JuMP's API (B-1 custom constraint approach), which is a significant workaround.

#### Lossy DCOPF / LMP Decomposition (Test A-10)
Issue [#1537](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1537) ("Add losses approximations to PTDF models") is open and explicitly states the feature "will require the implementation of LHS parameters" — a prerequisite that is itself an open feature request ([#1150](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1150)). Loss-inclusive LMPs and decomposition may not be achievable without substantial custom formulation work.

#### Distributed Slack (Test A-11)
The documented network formulations (CopperPlatePowerModel, AreaBalancePowerModel, PTDFPowerModel, AreaPTDFPowerModel, plus PowerModels.jl formulations) do not include a distributed slack option. The AreaBalancePowerModel could potentially approximate this behavior but is not equivalent. This test may require a custom formulation.

#### Ramp-Down Constraint Bug (Tests A-5, A-6)
Issue [#1530](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1530) reports that ramp-down constraints may have a flipped inequality sign in `rateofchange_constraints.jl`. The reporter notes "I'm not seeing any tests at all for ramp limits." This could affect SCUC (A-5) and SCED (A-6) results where ramp enforcement is a pass condition.

#### DC Power Flow Initialization Bug (Tests A-1, A-3)
Issue [#1545](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1545) describes a bug where bus active power injections/withdrawals are non-zero (should be zero) when renewables use FixedOutput formulation in the power-flow-in-the-loop simulation context. This affects combined optimization + power flow workflows.

#### Renewable Profile Scaling Bug
Issue [#1557](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1557) reports that renewable profiles defined in natural units (MW) are treated as scaling factors, multiplying by rated capacity and producing values 10x too high. This could affect any test involving renewable dispatch (A-12 multi-period with renewables).

### Open Issues Summary (as of 2026-03-13)

**66 open issues total**. Breakdown by label:
- **Code bugs (open):** 8 — including DC PF init (#1545), renewable scaling (#1557), startup time data (#1558), emulation results (#1474, #1554), MarketBidCost loads (#1299), NonSpinningReserve (#1173), docstring build (#1246)
- **Feature requests (open):** 9 — SCOPF (#944), ShiftablePowerLoad (#1491), storage outages in SCUC (#1461), matrix/reduction interface (#1452), ComponentSelector filter (#1152), RHS parameter (#1150), MOF deserialization (#722), hurdle rates (#1339), device simulation docs (#1353)
- **Documentation (open):** 10 — HVDCTwoTerminalLCC (#1533), invalid RenewableNonDispatch configs (#1357), device simulation extensions (#1353), slack explanation (#1338), 2T HVDC docs (#1277), forced outages docs (#1266), FunctionData corrections (#1262), performance guide (#1252), large simulation guide (#1213), doc reorganization (#1165)

### Ecosystem Packages

The NREL-Sienna GitHub organization contains 50+ repositories. Core packages and their metrics:

| Package | Stars | Forks | Open Issues | License | Last Push |
|---------|-------|-------|-------------|---------|-----------|
| PowerSystems.jl | 359 | 101 | 63 | BSD-3 | 2026-03-11 |
| PowerSimulations.jl | 311 | 78 | 66 | BSD-3 | 2026-03-07 |
| PowerSimulationsDynamics.jl | 215 | — | — | BSD-3 | 2026-02-25 |
| InfrastructureSystems.jl | 41 | 40 | 29 | BSD-3 | 2026-03-11 |
| PowerGraphics.jl | 33 | — | — | BSD-3 | 2026-03-06 |
| PowerFlows.jl | 29 | 23 | 42 | BSD-3 | 2026-03-13 |
| PowerNetworkMatrices.jl | 28 | 20 | 44 | BSD-3 | 2026-03-13 |
| PowerSystemsInvestments.jl | 21 | — | — | BSD-3 | 2026-01-13 |

**Extension packages** (domain-specific formulations):
- StorageSystemsSimulations.jl (7 stars) — battery/storage models
- HydroPowerSimulations.jl (12 stars) — hydro dispatch/commitment
- HybridSystemsSimulations.jl (6 stars) — hybrid resource models
- SiennaPRASInterface.jl (5 stars) — probabilistic reliability
- PowerSystemsInvestmentsPortfolios.jl (14 stars) — capacity expansion

**Sienna branding**: Three application layers:
1. **Sienna\Data** — PowerSystems.jl + InfrastructureSystems.jl (data model, time series)
2. **Sienna\Ops** — PowerSimulations.jl (scheduling, dispatch, production cost modeling)
3. **Sienna\Dyn** — PowerSimulationsDynamics.jl (transient/small-signal stability)

### Community Size

- **311 stars / 78 forks** on PowerSimulations.jl (moderate for a Julia power systems package)
- **359 stars / 101 forks** on PowerSystems.jl (the data model layer)
- Compare to PowerModels.jl: ~400 stars, broader community adoption
- Slack channel exists for community support (mentioned on Sienna landing page)
- No Discourse or dedicated forum

### Contributor Concentration

**All-time top contributors:**

| Contributor | Commits | % of Total (~10,463) |
|-------------|---------|---------------------|
| jd-lara | 7,537 | 72% |
| sourabhdalvi | 680 | 6.5% |
| claytonpbarrows | 577 | 5.5% |
| rodrigomha | 513 | 4.9% |
| daniel-thom | 401 | 3.8% |

**Last 12 months (pages 1-2 sample, 200 commits):**

| Contributor | Commits (sample) |
|-------------|-----------------|
| jd-lara | ~91 |
| luke-kiernan | ~41 |
| rodrigomha | ~20 |
| m-bossart | ~18 |
| kdayday | ~9 |
| GabrielKS | ~9 |
| Copilot (AI) | ~9 |

**Bus factor: 1.** jd-lara accounts for 72% of all-time commits and remains the dominant contributor. The project is heavily dependent on a single developer at NREL.

### Documentation Quality

**Structure**: Follows Diataxis framework (Tutorials, How-To, Explanation, Reference). Well-organized.

**Coverage gaps (from open issues):**
- 10 open documentation issues
- No documentation for HVDC LCC models (#1533)
- Invalid configuration examples listed as valid (#1357)
- FunctionData section has known errors (#1262)
- No performance best practices guide (#1252)
- No guide for large-scale simulation setup (#1213)
- Forced outage capability undocumented (#1266)
- Overall doc reorganization needed (#1165)

**Formulation library**: Documents General, Network, Thermal, Renewable, Load, Branch, Source, Services, Feedforwards, and Piecewise Linear Cost formulations. Good tabular format with constraints and variables listed.

**What's NOT documented**: SCOPF, loss approximations, distributed slack, contingency analysis, dynamic line ratings (DLR — under active development per #1559 but not yet documented).

**Multi-package cognitive overhead**: Users must know which package provides which type (e.g., `DCPowerFlow()` from PowerNetworkMatrices, `System()` from PowerSystems, `solve_powerflow!()` from PowerFlows).

### Release History

**21 releases in last 24 months** (since 2024-03-13):

| Version | Date | Notes |
|---------|------|-------|
| v0.33.1 | 2026-02-24 | Latest |
| v0.33.0 | 2026-02-18 | |
| v0.32.4 | 2025-12-18 | |
| v0.32.3 | 2025-12-13 | |
| v0.32.2 | 2025-12-10 | |
| v0.32.1 | 2025-12-09 | |
| v0.32.0 | 2025-12-08 | |
| v0.31.0 | 2025-11-11 | |
| v0.30.2 | 2025-06-09 | (Version in our Manifest) |
| v0.30.1 | 2025-02-27 | |
| v0.30.0 | 2025-02-06 | |
| v0.29.2 | 2025-01-13 | |
| v0.29.1 | 2024-12-26 | |
| v0.29.0 | 2024-12-12 | |
| v0.28.3 | 2024-07-24 | |

**Cadence**: Approximately monthly releases. Frequent patch releases (4 patches for v0.32 in 10 days) suggest instability at minor version boundaries. Semver used but still pre-1.0 (no stability guarantees).

**Note**: Our evaluation environment has v0.30.2 pinned, which is 5 minor versions behind v0.33.1. The compat bounds (`PowerSimulations = "0.27 - 0.33"`) should allow upgrading.

### CI and Testing

**CI workflows (GitHub Actions):**
- Main - CI (active)
- Test-CI (active)
- CrossPackageTest (active) — tests compatibility with other Sienna packages
- Format Check (active)
- Documentation (active)
- Performance Comparison (active)
- Copilot code review + coding agent (active)

CI infrastructure is comprehensive. CrossPackageTest is notable — it tests the full Sienna stack integration.

### Institutional Backing

- **Primary institution**: National Renewable Energy Laboratory (NREL), U.S. Department of Energy
- **PI**: Clayton Barrows, Ph.D. — Group Manager at NREL
- **Development lead**: José Daniel Lara — Senior Researcher at NREL
- **Funding model**: Federal (DOE) research funding. Durable as long as NREL's grid modeling program continues, but subject to federal budget cycles and administration priorities.
- **First Principles Advisory** mentioned as an industry adopter on the Sienna landing page, but no specific utility/ISO deployment evidence found.

### Dependency and Supply Chain

**Direct dependencies in our Project.toml**: 10 packages (PowerSimulations, PowerSystems, PowerFlows, PowerNetworkMatrices, InfrastructureSystems, JuMP, HiGHS, GLPK, Ipopt, SCIP)

**Resolved dependency count**: ~80+ packages in Manifest.toml (1186 lines), including:
- Heavy numerical libraries: MKL, HDF5, BLAS
- Data infrastructure: SQLite, CSV, DataFrames
- Serialization: JSON3, YAML
- Solver interfaces: MathOptInterface, JuMP

**License audit**: All Sienna packages are BSD-3-Clause. JuMP ecosystem is MIT/BSD. Solvers (HiGHS, GLPK, Ipopt, SCIP) are open-source (MIT, GPL for GLPK, EPL for Ipopt). GLPK is GPL-3.0 — potential copyleft concern if linking applies.

**Compat pin issues**: Multiple packages restricted by compat constraints (marked with ⌅ by Pkg resolver). The ecosystem does not keep pace with its own dependency upgrades.

## Sources

1. GitHub: [NREL-Sienna/PowerSimulations.jl](https://github.com/NREL-Sienna/PowerSimulations.jl) — repo metadata, issues, releases, contributors
2. GitHub: [NREL-Sienna/PowerSystems.jl](https://github.com/NREL-Sienna/PowerSystems.jl)
3. GitHub: [NREL-Sienna/PowerNetworkMatrices.jl](https://github.com/NREL-Sienna/PowerNetworkMatrices.jl)
4. GitHub: [NREL-Sienna/InfrastructureSystems.jl](https://github.com/NREL-Sienna/InfrastructureSystems.jl)
5. GitHub: [NREL-Sienna/PowerFlows.jl](https://github.com/NREL-Sienna/PowerFlows.jl)
6. PowerSimulations.jl documentation: https://nrel-sienna.github.io/PowerSimulations.jl/stable/
7. Sienna landing page: https://nrel-sienna.github.io/Sienna/
8. Issue [#944](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/944) — SCOPF feature request (open since 2023-03)
9. Issue [#1537](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1537) — Losses in PTDF models
10. Issue [#1530](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1530) — Ramp-down inequality flipped
11. Issue [#1545](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1545) — DC PF initialization bug
12. Issue [#1557](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1557) — Renewable scaling bug
13. Issue [#1522](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1522) — Post contingency evaluation
14. Issue [#1559](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1559) — Dynamic Line Ratings PR
15. Local file: `evaluations/powersimulations/notes/install-findings.md`
16. Local file: `evaluations/powersimulations/Project.toml`
17. Local file: `evaluations/powersimulations/Manifest.toml`

## Gaps and Uncertainties

- **SCOPF workaround feasibility**: Unclear how difficult it is to manually add N-1 contingency constraints via JuMP. Need to test during A-9 / B-1.
- **Lossy DCOPF**: May be achievable via PowerModels.jl's DCPLLPowerModel formulation (documented as available through the PowerModels integration) — needs testing.
- **Distributed slack**: AreaBalancePowerModel might approximate distributed slack with single-bus areas, but this is speculation — needs testing.
- **Ramp-down bug severity**: Reporter says "I don't have code that triggers the bug right now." May not affect our test configurations if they use ThermalGen with AbstractThermalDispatch (which is excluded from the bug scope).
- **v0.30.2 vs v0.33.1**: Our pinned version is 5 minor versions behind. Some bugs may be fixed in newer versions, but upgrading risks breaking the dependency resolution that was already difficult.
- **Operational deployment evidence**: Only one industry reference (First Principles Advisory) found. No utility or ISO deployment evidence. No published case studies with real-world production use. NREL internal use for research is the primary use case.
- **PSS/E RAW parsing**: PowerFlowFileParser.jl exists in the NREL-Sienna org (pushed 2026-03-10) but its capabilities and maturity are unknown — needs investigation for P2-1.
- **Academic citation count**: Google Scholar search did not return results (page rendering issue). Citation impact is unknown.
- **GLPK GPL-3.0 license**: Whether Julia's JLL wrapper for GLPK triggers copyleft obligations needs legal review for F-3.
- **Air-gap installability**: Julia's package manager supports offline registries, but the 80+ dependency footprint makes air-gap bundling non-trivial. Needs testing for F-7.

---

<!-- version capability report metadata -->

# powersimulations — Version & Capability Report

- **Installed version:** 0.30.2 (released 2024-06-09)
- **Latest version:** 0.33.5 (released 2025-03-21)
- **Research date:** 2026-03-24

## Version Summary

The installed version of PowerSimulations.jl is **v0.30.2** (released June 9, 2024), which is **three minor versions behind** the latest release **v0.33.5** (released March 21, 2025). The gap spans approximately 9 months and includes three breaking-change minor releases (v0.31.0, v0.32.0, v0.33.0) plus five patch releases. The installed environment also pins older versions of companion Sienna ecosystem packages:

| Package | Installed | Latest | Gap |
|---------|-----------|--------|-----|
| PowerSimulations.jl | 0.30.2 | 0.33.5 | 3 minor versions |
| PowerSystems.jl | 4.6.2 | 5.6.1 | 1 major version |
| InfrastructureSystems.jl | 2.6.0 | 3.3.1 | 1 major version |
| PowerNetworkMatrices.jl | 0.12.1 | 0.19.0 | 7 minor versions |
| PowerFlows.jl | 0.9.0 | 0.16.1 | 7 minor versions |
| TimeSeries.jl | 0.24.2 | 0.24.2 | current |

These are constrained by compatibility bounds in the Project.toml `[compat]` section, which permits PowerSimulations 0.27-0.33 and PowerSystems 4-5. Upgrading to v0.33.5 would require upgrading the entire Sienna dependency chain, including crossing the PowerSystems v4 to v5 major version boundary and InfrastructureSystems v2 to v3.

Despite being behind, the installed v0.30.2 retains all core evaluation-relevant capabilities (UC, ED, PTDF network models, MATPOWER import, time series, warm start, parallel simulation). The newer versions primarily add HVDC multi-terminal models, 3-winding transformers, outage event simulation, synchronous condensers, dynamic line ratings (DLRs), and performance improvements — features that are not central to the evaluation protocol.

## Capability Table

| Feature | Supported | Since Version | Notes |
|---------|-----------|---------------|-------|
| DC Power Flow (DCPF) | yes | 0.1.0 | Via `DCPPowerModel` network formulation (from PowerModels.jl); also `PTDFPowerModel` for PTDF-based DC approximation. Source: [Network formulation docs](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Network/) |
| AC Power Flow (ACPF) | yes | 0.1.0 | Via `ACPPowerModel`, `ACRPowerModel`, `ACTPowerModel` network formulations (from PowerModels.jl). Requires nonlinear solver (e.g., Ipopt). Source: [Network formulation docs](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Network/) |
| DC Optimal Power Flow (DC OPF) | yes | 0.1.0 | `DecisionModel` with `DCPPowerModel` or `PTDFPowerModel` network formulation solves DC OPF. Source: [Formulation library intro](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Introduction/) |
| AC Optimal Power Flow (AC OPF) | yes | 0.1.0 | `DecisionModel` with `ACPPowerModel` or other AC formulations; non-convex NLP, requires nonlinear solver (e.g., Ipopt). SOC and SDP relaxations also available. Source: [Network formulation docs](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Network/) |
| Security-Constrained Unit Commitment (SCUC) | partial | — | Unit commitment is fully supported via `ThermalStandardUnitCommitment`, `ThermalMultiStartUnitCommitment`, etc. ([ThermalGen docs](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/ThermalGen/)). Security constraints (N-1 contingency enforcement within the UC) are **not built-in**; legacy N-1/G-1 code was removed in v0.33.0. Users can manually add contingency constraints via JuMP API. |
| Security-Constrained Economic Dispatch (SCED) | partial | — | Economic dispatch is fully supported via `ThermalStandardDispatch`, `ThermalCompactDispatch`, etc. Same contingency limitation as SCUC above. |
| PTDF / Shift Factor Extraction | yes | 0.1.0 | `PTDFPowerModel` and `AreaPTDFPowerModel` in PowerSimulations; standalone `PTDF`, `VirtualPTDF`, `LODF`, `VirtualLODF` available via PowerNetworkMatrices.jl. Supports sparse storage via `tol` threshold, distributed slack bus via weight vectors. Source: [PTDF tutorial](https://nrel-sienna.github.io/PowerNetworkMatrices.jl/stable/tutorials/tutorial_PTDF_matrix/) |
| Contingency Analysis (N-1) | partial | — | PowerNetworkMatrices.jl provides `LODF`/`VirtualLODF` for post-contingency flow estimation. PowerSimulations had N-1/G-1 contingency formulations that were **removed in v0.33.0** ([v0.33.0 release](https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.33.0)). In v0.30.2, some contingency code may still exist but is undocumented. Manual implementation via LODF matrices is feasible. |
| Custom Constraint Injection | yes | 0.1.0 | Full access to underlying JuMP model via `get_jump_model()`. Users can add arbitrary constraints, variables, and objectives using JuMP's API. Feedforward mechanisms also allow inter-model constraint coupling in simulations. Source: [Formulation library intro](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Introduction/) |
| Network Graph Access | yes | 0.1.0 | PowerNetworkMatrices.jl provides `IncidenceMatrix`, `AdjacencyMatrix`, `ABA_Matrix`, `BA_Matrix`, `Ybus`, plus `find_subnetworks` and `validate_connectivity` for topology analysis. `RadialNetworkReduction` available for network reduction. Source: [PowerNetworkMatrices.jl](https://github.com/NREL-Sienna/PowerNetworkMatrices.jl) |
| CSV Data Import | yes | 0.1.0 | PowerSystems.jl supports tabular CSV import for system construction and time series data via descriptor files and `bulk_add_time_series!`. Results can be exported to CSV via `export_realized_results` and `export_results`. Source: [PowerSystems.jl parsing docs](https://nrel-sienna.github.io/PowerSystems.jl/stable/how_to/parsing/) |
| MATPOWER Case Import | yes | 0.1.0 | `System("path/to/case.m")` parses MATPOWER case files via PowerSystems.jl's built-in parser (originally derived from PowerModels.jl). Also supports PSS/e `.raw` and `.dyr` formats. Source: [MATPOWER/PSS/e parsing](https://nrel-sienna.github.io/PowerSystems.jl/stable/how_to/parse_matpower_psse/) |
| Multi-Period / Time Series | yes | 0.1.0 | Core design feature. `Simulation` sequences multiple `DecisionModel` steps (e.g., day-ahead UC followed by real-time ED). Time series attach to components via `SingleTimeSeries`, `Deterministic`, and `Probabilistic` types in InfrastructureSystems.jl. Source: [PSI documentation](https://nrel-sienna.github.io/PowerSimulations.jl/latest/); [arxiv:2404.03074](https://arxiv.org/html/2404.03074v1) |
| Warm Start / Solution Reuse | yes | 0.1.0 | `_apply_warm_start!` passes previous solution as MIP start hints. Initial conditions (on/off status, energy levels, duration counters) propagate between simulation steps automatically. Configurable via `get_warm_start`/`set_warm_start!`. Effectiveness depends on solver (HiGHS, GLPK, Ipopt, SCIP). Source: JuMP warm start API; PSI initial conditions framework |
| Parallel Computation | yes | ~0.27 | `run_parallel_simulation` partitions a simulation across multiple Julia processes. Parameters include `num_parallel_processes`, `num_overlap_steps`, and custom `exeflags`. Uses Julia's `Distributed` module. PSI docs include a dedicated "How to run a parallel simulation" guide. Source: [PSI docs](https://nrel-sienna.github.io/PowerSimulations.jl/latest/) |

## Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|----------------------|
| v0.31.0 (Nov 2024) | Updated all dependencies; new outage events API; multi-terminal HVDC and 3WT models; time-variable MarketBidCost; voltage stability in-the-loop; PowerSystems v5 interface. Source: [v0.31.0 release](https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.31.0) | Low — new features not required by protocol; dependency updates may require compat adjustments if upgrading |
| v0.32.0 (Dec 2024) | New dependencies introduced; branch model implementation corrected; MarketBidCost refactored for time-variable service bidding; decomposition strategy changes. Source: [v0.32.0 release](https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.32.0) | Low — branch model corrections could affect flow results on specific topologies; MarketBidCost changes affect cost modeling |
| v0.33.0 (Feb 2025) | Renamed power flow variables (`PowerFlowLine` to `PowerFlowBranch`); removed legacy N-1 and G-1 contingency code; eliminated unmonitored line creation for performance; synchronous condenser model added. Source: [v0.33.0 release](https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.33.0) | Medium — variable renaming breaks scripts referencing old names; N-1/G-1 removal means contingency analysis must use LODF-based approach if upgrading |
| PowerSystems v5.0 | Major version bump with breaking API changes; migration from v4.x required. Latest is v5.6.1. Source: [PSY releases](https://github.com/NREL-Sienna/PowerSystems.jl/releases) | High if upgrading — would affect all system construction and component access code |
| InfrastructureSystems v3.0 | Major version bump with breaking changes (iterator behavior, cost function APIs). Latest is v3.3.1. Source: [IS releases](https://github.com/NREL-Sienna/InfrastructureSystems.jl/releases) | High if upgrading — foundational dependency; affects time series and component internals |

## Changelog Analysis

### v0.30.2 to v0.31.0 (June 2024 to November 2024)

**New capabilities:** Outage event simulation framework; multi-terminal HVDC (lossless and lossy NLP LCC model); three-winding transformer support; time-variable MarketBidCost for thermals and renewables; time-varying ImportExportCost with ReservationVariable; 3D results handling; voltage stability integration; load modeling without time series requirement; source device formulations with time-series support.

**Infrastructure:** Network reduction compatibility restored (radial and degree-two reductions); area interchange enhancements; PowerFlowData output corrections for HVDC flow direction; documentation restructured following Diataxis framework; improved PSY5 interface.

### v0.31.0 to v0.32.0 (November to December 2024)

**Fixes:** Cost tracking and ramp constraint corrections for thermal generators; MarketBidCost SingleTimeSeries compatibility; inter-area mapping refactoring. Decomposition algorithm refinements introduced. Parallel branches with unequal impedances now supported (v0.32.3). DC power flow testing improvements.

**New:** Time-variable service bidding in MarketBidCost (issue #961); automatic DegreeTwo reduction restrictions for interfaces/interchanges.

### v0.32.0 to v0.33.0 (December 2024 to February 2025)

**Performance:** Eliminated creation of variables for unmonitored branches, improving solve time on large networks. Type inference and annotation improvements. Import syntax modernized (`import Package as ALIAS`).

**New:** Synchronous condenser model; FuelCurve with `PiecewiseAverageCurve` in `ThermalStandardUnitCommitment`; quadratic cost curves for `RenewableDispatch`; feedforward frequency arguments for renewables.

**Removed:** Legacy N-1 and G-1 contingency formulation code.

**Renamed:** `PowerFlowLine` to `PowerFlowBranch` nomenclature in auxiliary variables (PR #1543).

### v0.33.0 to v0.33.5 (February to March 2025)

- **v0.33.1** (Feb 24, 2025): Auxiliary variable for AC line losses; time series handling fix for renewables. Source: [v0.33.1 release](https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.33.1)
- **v0.33.2** (Mar 19, 2025): Default time series names for sources; testing improvements for breakpoints and slopes; documentation updates. Source: [v0.33.2 release](https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.33.2)
- **v0.33.3** (Mar 19, 2025): Increased maximum resolution size for problems; refactored production cost expression. Source: [v0.33.3 release](https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.33.3)
- **v0.33.4** (Mar 20, 2025): Bug fix for missing term in system expression for PTDF models with Interconnecting Converters. Source: [v0.33.4 release](https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.33.4)
- **v0.33.5** (Mar 21, 2025): Dynamic Line Ratings (DLRs) implementation. Source: [v0.33.5 release](https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.33.5)

## Sources

1. GitHub releases — PowerSimulations.jl: https://github.com/NREL-Sienna/PowerSimulations.jl/releases
2. PowerSimulations.jl v0.30.2 release: https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.30.2
3. PowerSimulations.jl v0.31.0 release: https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.31.0
4. PowerSimulations.jl v0.32.0 release: https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.32.0
5. PowerSimulations.jl v0.33.0 release: https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.33.0
6. PowerSimulations.jl v0.33.5 release: https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.33.5
7. PowerSimulations.jl main branch Project.toml: https://github.com/NREL-Sienna/PowerSimulations.jl/blob/main/Project.toml
8. PowerSimulations.jl documentation — Network formulations: https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Network/
9. PowerSimulations.jl documentation — Thermal generation formulations: https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/ThermalGen/
10. PowerSimulations.jl documentation — Formulation library introduction: https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Introduction/
11. PowerSystems.jl MATPOWER parsing: https://nrel-sienna.github.io/PowerSystems.jl/stable/how_to/parse_matpower_psse/
12. PowerSystems.jl CSV/tabular parsing: https://nrel-sienna.github.io/PowerSystems.jl/stable/how_to/parsing/
13. PowerSystems.jl releases: https://github.com/NREL-Sienna/PowerSystems.jl/releases
14. InfrastructureSystems.jl releases: https://github.com/NREL-Sienna/InfrastructureSystems.jl/releases
15. PowerNetworkMatrices.jl repository: https://github.com/NREL-Sienna/PowerNetworkMatrices.jl
16. PowerNetworkMatrices.jl PTDF tutorial: https://nrel-sienna.github.io/PowerNetworkMatrices.jl/stable/tutorials/tutorial_PTDF_matrix/
17. PowerFlows.jl releases: https://github.com/NREL-Sienna/PowerFlows.jl/releases
18. arXiv paper — PowerSimulations.jl: https://arxiv.org/html/2404.03074v1
19. Installed package versions via `Pkg.status()` in devcontainer
20. `evaluations/powersimulations/Project.toml` — compat bounds
21. `evaluations/powersimulations/Manifest.toml` — pinned versions

## Gaps and Uncertainties

- **Contingency analysis depth in v0.30.2:** The legacy N-1/G-1 code was removed in v0.33.0, but its actual functionality and API in v0.30.2 is undocumented. It is unclear whether this code was ever production-ready or was experimental.
- **Exact "Since Version" for parallel simulation:** `run_parallel_simulation` exists in v0.30.2 but the exact version it was introduced is not documented in release notes; estimated as ~v0.27 based on compat bounds.
- **CSV import specifics:** PowerSystems.jl supports CSV-based system construction via a descriptor file format, but the exact schema and limitations for tabular data parsing were not fully documented in accessible pages for v4.x docs.
- **Warm start effectiveness:** The warm start mechanism exists and is callable, but whether it materially improves solve times depends on the solver (HiGHS, GLPK, Ipopt, SCIP) and problem structure. No benchmarks were found.
- **PowerFlows.jl v0.9.0 capabilities:** The installed PowerFlows.jl is significantly behind (latest v0.16.1). Its role in "power flow in the loop" simulation features may be limited at this version. The v0.15.0 and v0.16.0 releases introduced breaking changes including removal of old `solve_powerflow` API and a PSY 5.5 minimum requirement.
- **PowerNetworkMatrices.jl v0.12.1 vs v0.19.0:** The installed version lacks features added in v0.18.0+ (emergency ratings, dynamic line ratings support, ward reduction bug fixes). Core PTDF/LODF/Ybus functionality is present in both.
- **Result export format:** `export_realized_results` writes to a directory structure; confirmed to produce CSV output by method signature but not verified by direct file inspection.
- **PowerSystems v5 migration scope:** Upgrading from PSY v4.6.2 to v5.x is a major version crossing. No migration guide was found in public docs. The scope of API breakage (component constructors, accessors, time series API) is uncertain.
