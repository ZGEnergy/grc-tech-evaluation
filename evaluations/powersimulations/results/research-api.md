# powersimulations — Research: API & Formulations

## Key Findings

- PowerSimulations.jl (v0.30.2 installed, latest v0.33.1) is a modular optimization-based simulation framework for power system operations, built on JuMP.jl. It does **not** solve power flow directly — it builds and solves optimization problems (UC, ED, OPF) using a template-based API where device formulations are composed independently.
- The data model is fully delegated to **PowerSystems.jl** (`System` objects with typed components: `ThermalStandard`, `RenewableDispatch`, `Line`, `Bus`, etc.). PowerSimulations.jl never defines its own bus/branch/gen types — it dispatches formulations against PowerSystems.jl abstract types.
- Network representation is pluggable via `NetworkModel(T)` where `T` can be a native formulation (`CopperPlatePowerModel`, `PTDFPowerModel`, `AreaBalancePowerModel`, `AreaPTDFPowerModel`) or any PowerModels.jl formulation (`ACPPowerModel`, `DCPPowerModel`, `SOCWRPowerModel`, etc.).
- Thermal generation has 9 formulation tiers from `ThermalBasicDispatch` (no ramps, no commitment) to `ThermalMultiStartUnitCommitment` (hot/warm/cold starts, min up/down, ramps) — the most granular UC formulation library of any tool evaluated.
- Solver interface is via JuMP.jl's `optimizer_with_attributes()` — any MathOptInterface-compatible solver works. The project includes HiGHS, GLPK, Ipopt, and SCIP.
- Input formats are handled by PowerSystems.jl: MATPOWER `.m`, PSS/e `.raw`/`.dyr`, and tabular CSV. Output uses HDF5 for simulation results, with programmatic access via `read_variable()`, `read_realized_variables()`, etc., returning DataFrames.
- Multi-stage simulations (e.g., DA UC + RT ED) are first-class via `SimulationSequence` with feedforward mechanisms (`SemiContinuousFeedforward`, `FixValueFeedforward`, `UpperBoundFeedforward`, `LowerBoundFeedforward`).
- Hydro and storage formulations are in separate extension packages (`HydroPowerSimulations.jl`, `StorageSystemsSimulations.jl`), not in the core package. This modular design adds installation complexity but keeps the core focused.
- The package exports 297 symbols — a large API surface covering variables, constraints, parameters, formulations, and result accessors.

## Detailed Notes

### Architecture and Package Relationships

PowerSimulations.jl sits in the NREL Sienna ecosystem with a clear separation of concerns:

| Package | Role | Version Installed |
|---------|------|-------------------|
| **PowerSystems.jl** | Data model (`System`, components, time series) | 4.6.2 |
| **InfrastructureSystems.jl** | Base infrastructure (time series storage, validation) | 2.6.0 |
| **PowerSimulations.jl** | Optimization model building and simulation orchestration | 0.30.2 |
| **PowerFlows.jl** | Standalone power flow solvers (DCPF, ACPF) | 0.9.0 |
| **PowerNetworkMatrices.jl** | PTDF, LODF, Ybus matrix computation | 0.12.1 |
| **PowerModels.jl** | Network formulations (AC/DC OPF relaxations) | Used indirectly |
| **JuMP.jl** | Algebraic modeling language for optimization | 1.29.4 |

The key insight is that PowerSimulations.jl does **not** do power flow — `PowerFlows.jl` handles that separately. PowerSimulations.jl builds JuMP optimization models for scheduling/dispatch problems.

Source: [PowerSimulations.jl Welcome Page](https://nrel-sienna.github.io/PowerSimulations.jl/latest/), [arxiv paper](https://arxiv.org/html/2404.03074v1)

### Core API Workflow

#### Single-Step Problem (DecisionModel)

```julia
using PowerSystems, PowerSimulations, HiGHS

# 1. Load system data
sys = System("case.m")  # or from PSS/e, CSV, PowerSystemCaseBuilder

# 2. Create problem template
template = ProblemTemplate()
set_device_model!(template, ThermalStandard, ThermalStandardUnitCommitment)
set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
set_device_model!(template, PowerLoad, StaticPowerLoad)
set_device_model!(template, Line, StaticBranch)
set_service_model!(template, VariableReserve{ReserveUp}, RangeReserve)
set_network_model!(template, NetworkModel(CopperPlatePowerModel))

# 3. Build and solve
solver = optimizer_with_attributes(HiGHS.Optimizer, "mip_rel_gap" => 0.5)
model = DecisionModel(template, sys; optimizer = solver, horizon = Hour(24))
build!(model; output_dir = mktempdir())
solve!(model)

# 4. Access results
res = OptimizationProblemResults(model)
get_objective_value(res)
read_variables(res)  # Dict of DataFrames
read_variable(res, "ActivePowerVariable__ThermalStandard")
```

Convenience templates exist: `template_unit_commitment()` and `template_economic_dispatch()`.

Source: [Decision Problem Tutorial](https://nrel-sienna.github.io/PowerSimulations.jl/latest/tutorials/generated_decision_problem/)

#### Multi-Stage Simulation

```julia
# DA + RT simulation with feedforward
models = SimulationModels(;
    decision_models = [
        DecisionModel(template_uc, sys_DA; optimizer=solver, name="UC"),
        DecisionModel(template_ed, sys_RT; optimizer=solver, name="ED"),
    ],
)

feedforward = Dict(
    "ED" => [
        SemiContinuousFeedforward(;
            component_type = ThermalStandard,
            source = OnVariable,
            affected_values = [ActivePowerVariable],
        ),
    ],
)

sequence = SimulationSequence(;
    models = models,
    ini_cond_chronology = InterProblemChronology(),
    feedforwards = feedforward,
)

sim = Simulation(; name="da-rt", steps=365, models=models, sequence=sequence,
                   simulation_folder="./results")
build!(sim)
execute!(sim)

# Read results
results = SimulationResults(sim)
uc_results = get_decision_problem_results(results, "UC")
read_realized_variables(uc_results, ["ActivePowerVariable__ThermalStandard"])
```

Source: [PCM Simulation Tutorial](https://nrel-sienna.github.io/PowerSimulations.jl/latest/tutorials/generated_pcm_simulation/)

### Network Formulations

#### Native Formulations (PowerSimulations.jl)

| Formulation | Description | Transmission Constraints |
|---|---|---|
| `CopperPlatePowerModel` | Single-node, no transmission | System-wide balance only |
| `AreaBalancePowerModel` | One node per area | Area-level balance |
| `PTDFPowerModel` | PTDF-based linear DC approximation | Branch flow limits via PTDF |
| `AreaPTDFPowerModel` | PTDF with area balancing | Area balance + PTDF flows |

All native models support optional slack variables (`SystemBalanceSlackUp/Down`) with configurable penalty costs (default 1e6).

Source: [Network Formulations](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/Network/)

#### PowerModels.jl Formulations (available via re-export)

These are usable as the network model type parameter:

| Category | Formulations |
|---|---|
| **Exact nonlinear** | `ACPPowerModel`, `ACRPowerModel`, `ACTPowerModel` |
| **Linear approximation** | `DCPPowerModel`, `DCPLLPowerModel`, `NFAPowerModel` |
| **Quadratic relaxation** | `QCRMPowerModel`, `QCLSPowerModel` |
| **SOC relaxation** | `SOCWRPowerModel`, `SOCWRConicPowerModel` |
| **SDP relaxation** | `LPACCPowerModel` |

All of these are confirmed exported by PowerSimulations.jl (verified in devcontainer via `names(PowerSimulations)`).

Source: [PowerModels.jl Formulations](https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/), confirmed in installed exports

### Thermal Generation Formulations

Nine formulations from simple dispatch to detailed multi-start commitment:

| Formulation | Binary Vars | Ramps | Min Up/Down | Multi-Start |
|---|---|---|---|---|
| `ThermalBasicDispatch` | No | No | No | No |
| `ThermalDispatchNoMin` | No | No | No | No |
| `ThermalStandardDispatch` | No | Yes (with optional slack) | No | No |
| `ThermalCompactDispatch` | No | Yes | No | No |
| `ThermalBasicUnitCommitment` | Yes (on/start/stop) | No | No | No |
| `ThermalBasicCompactUnitCommitment` | Yes | No | No | No |
| `ThermalCompactUnitCommitment` | Yes | Yes | Yes | No |
| `ThermalStandardUnitCommitment` | Yes | Yes (with optional slack) | Yes | No |
| `ThermalMultiStartUnitCommitment` | Yes (on/start/stop + hot/warm/cold) | Yes | Yes | Yes |

The "Compact" variants use `PowerAboveMinimumVariable` (delta above Pmin) instead of absolute power, which produces tighter LP relaxations. `ThermalMultiStartUnitCommitment` implements the pg-lib formulation with three startup temperature categories.

Source: [Thermal Gen Formulations](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/ThermalGen/)

### Renewable Generation Formulations

| Formulation | Description |
|---|---|
| `RenewableFullDispatch` | Dispatch between 0 and time-series max; negative cost incentivizes generation |
| `RenewableConstantPowerFactor` | Same as above + reactive power proportional to active via power factor |
| `FixedOutput` | No variables; time series injected directly into balance (non-dispatchable) |

Source: [Renewable Gen Formulations](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/RenewableGen/)

### Load Formulations

| Formulation | Description |
|---|---|
| `StaticPowerLoad` | Fixed demand from time series; no variables or constraints |
| `PowerLoadDispatch` | Continuous curtailable load (demand response) |
| `PowerLoadInterruption` | Binary load interruption (on/off switching) |

Source: [Load Formulations](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/Load/)

### Branch Formulations

| Formulation | Network Model | Description |
|---|---|---|
| `StaticBranch` | PTDF | Bounded flow with optional slack for violations |
| `StaticBranchBounds` | PTDF | Bounded flow variable [-Rmax, Rmax], no slack |
| `StaticBranchUnbounded` | PTDF | Unbounded flow, no rating enforcement |
| `HVDCTwoTerminalUnbounded` | PTDF | Lossless unbounded HVDC |
| `HVDCTwoTerminalLossless` | PTDF | Lossless HVDC with directional limits |
| `HVDCTwoTerminalDispatch` | PTDF | Lossy HVDC with binary direction variable |
| `PhaseAngleControl` | PTDF | Phase-shifting transformer with angle control |
| `TwoTerminalLCCLine` | ACP | Full LCC HVDC with converter physics (14+ variables) |

Source: [Branch Formulations](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/Branch/)

### Service/Reserve Formulations

| Formulation | Description |
|---|---|
| `RangeReserve` | Reserve >= requirement; per-device participation limits |
| `StepwiseCostReserve` | ORDC (Operating Reserve Demand Curve) with piecewise linear costs |
| `GroupReserve` | Aggregated reserve across multiple services |
| `RampReserve` | Reserve with ramp-rate constraints |
| `NonSpinningReserve` | Non-spinning reserve dependent on startup times |
| `ConstantMaxInterfaceFlow` | Fixed transmission interface/corridor limits |
| `VariableMaxInterfaceFlow` | Time-varying transmission interface limits |

Source: [Service Formulations](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/Service/)

### Feedforward Mechanisms

Feedforwards connect models in multi-stage simulations:

| Feedforward | Effect |
|---|---|
| `SemiContinuousFeedforward` | Passes commitment decisions to modify dispatch bounds (most common) |
| `FixValueFeedforward` | Fixes variable/parameter values from upstream model |
| `UpperBoundFeedforward` | Imposes upper bound from upstream with optional slack |
| `LowerBoundFeedforward` | Imposes lower bound from upstream with optional slack |

Source: [Feedforward Formulations](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/Feedforward/)

### Cost Functions

PowerSimulations.jl supports multiple cost representations:

- **LinearFunctionData** — fixed marginal cost
- **QuadraticFunctionData** / **PolynomialFunctionData** — polynomial cost curves
- **PiecewiseLinearData** / **PiecewiseLinearSlopeData** — piecewise linear (SOS2 or incremental)
- **StorageCost** — penalty/incentive framework for energy targets (surplus/shortage costs)

Source: [General Formulations](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/General/)

### Data Model (PowerSystems.jl)

PowerSimulations.jl relies entirely on PowerSystems.jl for its data model. Key component types:

**Topology:** `Bus`, `Arc`, `Area`, `LoadZone`

**Generators:**
- `ThermalStandard`, `ThermalMultiStart` (thermal with multi-start profiles)
- `RenewableDispatch`, `RenewableNonDispatch` (curtailable vs fixed renewables)
- `HydroDispatch`, `HydroEnergyReservoir` (hydro with/without storage)

**Loads:** `PowerLoad`, `InterruptibleLoad` (PSS/e v35: `InterruptibleStandardLoad`)

**Storage:** `GenericBattery`, `EnergyReservoirStorage`, `HybridSystem`

**Branches:** `Line`, `MonitoredLine`, `Transformer2W`, `TapTransformer`, `PhaseShiftingTransformer`, `HVDCLine`, `VSCDCLine`

**Services:** `VariableReserve{ReserveUp}`, `VariableReserve{ReserveDown}`, `StaticReserveNonSpinning`, `AGC`, `Transfer`

**Cost types:** `TwoPartCost`, `ThreePartCost`, `MarketBidCost`, `MultiStartCost`

The type hierarchy is abstract-type-based: `ThermalStandard <: ThermalGen <: Generator <: StaticInjection <: Device <: Component`. Formulations dispatch on these abstract types, so new concrete types automatically inherit compatible formulations.

Source: [PowerSystems.jl Type Structure](https://nrel-sienna.github.io/PowerSystems.jl/v1.11/modeler_guide/type_structure/)

### Input/Output Formats

**Input (via PowerSystems.jl):**
- MATPOWER `.m` files (parsing originally from PowerModels.jl, now diverged)
- PSS/e `.raw` and `.dyr` files (v30, v33, v35)
- Tabular CSV data with configurable column mappings
- Programmatic construction via `System()` + `add_component!()`
- PowerSystemCaseBuilder.jl for standard test cases (RTS-GMLC, IEEE cases)

Parsing handles industrial-scale cases (WECC, MMWG). Notable conventions: isolated bus correction, synchronous condenser detection, multi-section line handling.

**Output:**
- HDF5 files for simulation results (with compression, caching layer for 1 MiB minimum writes)
- In-memory store alternative for small problems
- Programmatic access returns DataFrames:
  - `read_variable(res, name)` / `read_variables(res)`
  - `read_realized_variables(res, [names])` — final realized values per timestep
  - `read_parameter(res, name)` / `read_dual(res, name)`
  - `read_aux_variable(res, name)` / `read_expression(res, name)`
  - `get_optimizer_stats(res)` — solver statistics
  - `export_results(res)` / `export_realized_results(res)` — bulk export

Source: [PSS/e Parsing](https://nrel-sienna.github.io/PowerSystems.jl/stable/how_to/parse_matpower_psse/), [arxiv paper](https://arxiv.org/html/2404.03074v1)

### Solver Interface

Solvers are configured via JuMP's `optimizer_with_attributes()`:

```julia
solver = optimizer_with_attributes(HiGHS.Optimizer, "mip_rel_gap" => 0.05)
model = DecisionModel(template, sys; optimizer = solver)
```

Any MathOptInterface-compatible solver works. Solvers installed in the evaluation project:
- **HiGHS** v1.21.1 — open-source LP/MIP (primary)
- **GLPK** v1.2.1 — open-source LP/MIP
- **Ipopt** v1.14.1 — nonlinear interior-point (needed for AC OPF formulations)
- **SCIP** v0.12.8 — open-source MINLP

Commercial solvers (Gurobi, CPLEX, Mosek) work via their JuMP interfaces. Solver warm-starting is supported — JuMP keeps the model in memory and can update parameters without rebuilding the matrix factorization.

Source: [JuMP Solver Page](https://jump.dev/JuMP.jl/stable/installation/#Supported-solvers), Project.toml

### Time Series Handling

PowerSystems.jl supports three time series types:
- **SingleTimeSeries** — a single scenario (deterministic)
- **Deterministic** — forecast with configurable horizon, interval, resolution
- **Probabilistic** — multiple scenarios with percentiles/quantiles

PowerSimulations.jl uses `ActivePowerTimeSeriesParameter`, `ReactivePowerTimeSeriesParameter`, and `RequirementTimeSeriesParameter` to inject time series into the optimization model. Parameters are updated before each solve step in a simulation.

The simulation framework manages time series alignment across multiple models with different resolutions (e.g., hourly DA vs. 5-minute RT) through the `SimulationSequence` interval/horizon/resolution validation.

Source: [arxiv paper](https://arxiv.org/html/2404.03074v1)

### Extension Packages

Hydro and storage formulations are in separate packages:

- **HydroPowerSimulations.jl** — hydro generation formulations (HydroDispatchRunOfRiver, HydroEnergyReservoir, etc.). Part of the FLASH/R2D2 projects at NREL. [GitHub](https://github.com/NREL-Sienna/HydroPowerSimulations.jl)
- **StorageSystemsSimulations.jl** — battery/storage operation formulations (EnergyReservoirStorage dispatch, merchant storage models). [GitHub](https://github.com/NREL-Sienna/StorageSystemsSimulations.jl)

These are Julia package extensions that register new `DeviceModel` formulations against PowerSystems.jl device types, seamlessly integrating into the template-based API.

## Sources

1. [PowerSimulations.jl Documentation (latest)](https://nrel-sienna.github.io/PowerSimulations.jl/latest/)
2. [PowerSimulations.jl GitHub](https://github.com/NREL-Sienna/PowerSimulations.jl)
3. [PowerSimulations.jl arxiv paper (2404.03074)](https://arxiv.org/html/2404.03074v1)
4. [Formulation Library — Introduction](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/Introduction/)
5. [Formulation Library — Network](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/Network/)
6. [Formulation Library — Thermal Gen](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/ThermalGen/)
7. [Formulation Library — Renewable Gen](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/RenewableGen/)
8. [Formulation Library — Load](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/Load/)
9. [Formulation Library — Branch](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/Branch/)
10. [Formulation Library — Service](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/Service/)
11. [Formulation Library — Feedforward](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/Feedforward/)
12. [Formulation Library — General (costs)](https://nrel-sienna.github.io/PowerSimulations.jl/latest/formulation_library/General/)
13. [Public API Reference](https://nrel-sienna.github.io/PowerSimulations.jl/latest/api/PowerSimulations/)
14. [Modeling Structure Explanation](https://nrel-sienna.github.io/PowerSimulations.jl/latest/explanation/psi_structure/)
15. [PowerSystems.jl Type Structure](https://nrel-sienna.github.io/PowerSystems.jl/v1.11/modeler_guide/type_structure/)
16. [PowerSystems.jl — MATPOWER/PSS/e Parsing](https://nrel-sienna.github.io/PowerSystems.jl/stable/how_to/parse_matpower_psse/)
17. [PowerModels.jl Network Formulations](https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/)
18. [HydroPowerSimulations.jl GitHub](https://github.com/NREL-Sienna/HydroPowerSimulations.jl)
19. [StorageSystemsSimulations.jl GitHub](https://github.com/NREL-Sienna/StorageSystemsSimulations.jl)
20. Installed package versions verified via `Pkg.dependencies()` in devcontainer (PowerSimulations v0.30.2)
21. Exported symbols verified via `names(PowerSimulations)` in devcontainer (297 exports)
22. `/home/joe/code/zge-workspace/grc-tech-evaluation/.claude/worktrees/eval/powersimulations-v4/evaluations/powersimulations/Project.toml`
23. `/home/joe/code/zge-workspace/grc-tech-evaluation/.claude/worktrees/eval/powersimulations-v4/evaluations/powersimulations/notes/install-findings.md`

## Gaps and Uncertainties

- **Storage formulation details**: `StorageSystemsSimulations.jl` documentation is sparse. The specific formulation types (e.g., `BookKeeping`, merchant dispatch models) and their constraint sets could not be fully enumerated from available docs. Needs hands-on testing.
- **Hydro formulation details**: `HydroPowerSimulations.jl` formulation names are referenced in tutorials (`HydroDispatchRunOfRiver`) but the full formulation library is not documented on the main PowerSimulations.jl docs site. Needs source code inspection.
- **AC OPF via PowerModels.jl integration**: While PowerModels.jl formulations are exported (e.g., `ACPPowerModel`), it is unclear how seamlessly they work as `NetworkModel` types in practice — whether all device formulations are compatible with nonlinear network models, or if only specific combinations work. Needs testing.
- **EmulationModel**: The `EmulationModel` type for real-time emulation (myopic, no-horizon problems like AGC) is documented conceptually but no tutorial or worked example was found. Its API surface is less clear than `DecisionModel`.
- **Parallel simulation**: `run_parallel_simulation()` and `SimulationPartitions` are exported but documentation on partitioning strategies and distributed execution is limited.
- **Version gap**: The evaluation uses v0.30.2 while the latest release is v0.33.1 (Feb 2026). Some API differences may exist; the compat bounds in Project.toml allow up to v0.33.
- **SCUC/SCED as named problems**: PowerSimulations.jl does not use the terms "SCUC" or "SCED" directly. Instead, security-constrained problems are built by composing `MonitoredLine` branch formulations with UC/ED templates. The exact approach for N-1 contingency analysis is not documented in the formulation library.
- **Stochastic optimization**: The arxiv paper mentions "stochastic and robust optimization variants" but no concrete formulation or API for scenario-based stochastic UC was found in the current documentation.
