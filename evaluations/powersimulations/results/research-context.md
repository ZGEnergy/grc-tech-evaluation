# PowerSimulations.jl — Research Context

Merged research from three parallel agents. Generated 2026-03-06.

---

## Section 1: API & Formulations

## Key Findings

- PowerSimulations.jl (v0.30.2 installed, latest v0.33.1) is a modular optimization-based simulation framework for power system operations, built on JuMP.jl. It does **not** solve power flow directly — it builds and solves optimization problems (UC, ED, OPF) using a template-based API where device formulations are composed independently.
- The data model is fully delegated to **PowerSystems.jl** (`System` objects with typed components: `ThermalStandard`, `RenewableDispatch`, `Line`, `Bus`, etc.). PowerSimulations.jl never defines its own bus/branch/gen types — it dispatches formulations against PowerSystems.jl abstract types.
- Network representation is pluggable via `NetworkModel(T)` where `T` can be a native formulation (`CopperPlatePowerModel`, `PTDFPowerModel`, `AreaBalancePowerModel`, `AreaPTDFPowerModel`) or any PowerModels.jl formulation (`ACPPowerModel`, `DCPPowerModel`, `SOCWRPowerModel`, etc.).
- Thermal generation has 9 formulation tiers from `ThermalBasicDispatch` (no ramps, no commitment) to `ThermalMultiStartUnitCommitment` (hot/warm/cold starts, min up/down, ramps) — the most granular UC formulation library of any tool evaluated.
- Solver interface is via JuMP.jl's `optimizer_with_attributes()` — any MathOptInterface-compatible solver works. The project includes HiGHS, GLPK, Ipopt, and SCIP.
- Input formats are handled by PowerSystems.jl: MATPOWER `.m`, PSS/e `.raw`/`.dyr`, and tabular CSV. Output uses HDF5 for simulation results, with programmatic access via `read_variable()`, `read_realized_variables()`, etc., returning DataFrames.
- Multi-stage simulations (e.g., DA UC + RT ED) are first-class via `SimulationSequence` with feedforward mechanisms (`SemiContinuousFeedforward`, `FixValueFeedforward`, `UpperBoundFeedforward`, `LowerBoundFeedforward`).
- The package exports 297 symbols — a large API surface covering variables, constraints, parameters, formulations, and result accessors.

## Detailed Notes

### Architecture and Package Relationships

| Package | Role | Version Installed |
|---------|------|-------------------|
| **PowerSystems.jl** | Data model (`System`, components, time series) | 4.6.2 |
| **InfrastructureSystems.jl** | Base infrastructure (time series storage, validation) | 2.6.0 |
| **PowerSimulations.jl** | Optimization model building and simulation orchestration | 0.30.2 |
| **PowerFlows.jl** | Standalone power flow solvers (DCPF, ACPF) | 0.9.0 |
| **PowerNetworkMatrices.jl** | PTDF, LODF, Ybus matrix computation | 0.12.1 |
| **PowerModels.jl** | Network formulations (AC/DC OPF relaxations) | Used indirectly |
| **JuMP.jl** | Algebraic modeling language for optimization | 1.29.4 |

PowerSimulations.jl does **not** do power flow — `PowerFlows.jl` handles that separately.

### Core API Workflow

```julia
# Single-step problem (DecisionModel)
sys = System("case.m")
template = ProblemTemplate()
set_device_model!(template, ThermalStandard, ThermalStandardUnitCommitment)
set_device_model!(template, RenewableDispatch, RenewableFullDispatch)
set_device_model!(template, PowerLoad, StaticPowerLoad)
set_network_model!(template, NetworkModel(CopperPlatePowerModel))
solver = optimizer_with_attributes(HiGHS.Optimizer, "mip_rel_gap" => 0.5)
model = DecisionModel(template, sys; optimizer = solver, horizon = Hour(24))
build!(model; output_dir = mktempdir())
solve!(model)
res = OptimizationProblemResults(model)
```

Convenience templates: `template_unit_commitment()`, `template_economic_dispatch()`.

### Network Formulations

**Native:** CopperPlatePowerModel, PTDFPowerModel, AreaBalancePowerModel, AreaPTDFPowerModel
**Via PowerModels.jl:** ACPPowerModel, ACRPowerModel, DCPPowerModel, SOCWRPowerModel, LPACCPowerModel, etc.

### Thermal Generation Formulations (9 tiers)

ThermalBasicDispatch → ThermalDispatchNoMin → ThermalStandardDispatch → ThermalCompactDispatch → ThermalBasicUnitCommitment → ThermalBasicCompactUnitCommitment → ThermalCompactUnitCommitment → ThermalStandardUnitCommitment → ThermalMultiStartUnitCommitment

### Cost Functions

LinearFunctionData, QuadraticFunctionData, PolynomialFunctionData, PiecewiseLinearData, PiecewiseLinearSlopeData, StorageCost

### Time Series

SingleTimeSeries, Deterministic (forecast), Probabilistic (scenarios). Multi-resolution supported in simulations.

### Solvers Installed

HiGHS v1.21.1, GLPK v1.2.1, Ipopt v1.14.1, SCIP v0.12.8

---

## Section 2: Extensions & Architecture

## Key Findings

- **Multiple dispatch is the extension mechanism.** Custom device formulations via subtyping `AbstractDeviceFormulation` and implementing `construct_device!` methods.
- **Two-stage build process.** `ArgumentConstructStage` (variables, parameters) then `ModelConstructStage` (constraints, objective).
- **External extension packages prove the pattern.** StorageSystemsSimulations.jl and HydroPowerSimulations.jl.
- **Full JuMP model access** via `get_jump_model(model)`. Users can pass pre-built JuMP models.
- **Custom `DecisionProblem` subtypes** bypass the template system entirely with own `build_model!`.
- **All results are DataFrames.** CSV export built in.
- **No Graphs.jl integration** anywhere in the Sienna stack. Topology via component iteration and matrix representations.
- **No explicit callback/hook/event API.** Extension through dispatch only.

## Detailed Notes

### Extension Mechanism 1: Custom Device Formulations

```julia
struct MyCustomFormulation <: PSI.AbstractDeviceFormulation end

function PSI.construct_device!(container, sys, ::PSI.ArgumentConstructStage,
    model::PSI.DeviceModel{PSY.ThermalStandard, MyCustomFormulation},
    network_model::PSI.NetworkModel{<:PM.AbstractPowerModel})
    # add variables, parameters
end

function PSI.construct_device!(container, sys, ::PSI.ModelConstructStage,
    model::PSI.DeviceModel{PSY.ThermalStandard, MyCustomFormulation},
    network_model::PSI.NetworkModel{<:PM.AbstractPowerModel})
    # add constraints
end
```

### Extension Mechanism 2: Custom DecisionProblem

```julia
struct MyCustomProblem <: PSI.DecisionProblem end
function PSI.build_model!(model::PSI.DecisionModel{MyCustomProblem})
    # full control over model building
end
```

### JuMP Model Access

```julia
jump_model = PSI.get_jump_model(model)
container = PSI.get_optimization_container(model)
```

### Constraint and Variable Registration API

- `add_variable_container!`, `add_constraints_container!`, `add_variables!`, `add_constraints!`, `add_to_expression!`, `add_parameters!`

### Graph / Network Topology Access

No Graphs.jl dependency. Topology via:
1. Component collections: `PSY.get_components(PSY.ACBus, sys)`
2. Incidence/PTDF/LODF matrices via PowerNetworkMatrices.jl
3. Subnetwork detection: `PNM.find_subnetworks(sys)`
4. Radial branch reduction: `PNM.RadialNetworkReduction(sys)`

### DataFrame Interoperability

All result accessors return DataFrames. Export via `export_realized_results(results, path)`.

---

## Section 3: Limitations & Ecosystem

## Key Findings

- **SCOPF is not natively implemented.** Issue #944 open since Mar 2023. Legacy SecurityConstrainedPTDFPowerModel removed in v0.33.0, replaced with branch-level N-1 formulation.
- **No stochastic optimization support.** No built-in scenario-based or two-stage stochastic formulations.
- **PTDF well-supported** but loss approximations still in development (#1537).
- **No LMP decomposition utilities.** Must manually extract JuMP dual variables.
- **183 dependencies** in Manifest.toml (vs ~30 for PowerModels.jl).
- **Very active development** — 15 releases in 14 months (v0.28.3 to v0.33.1).
- **High bus-factor risk** — one developer (jd-lara) has 7,537 commits out of 39 total contributors.
- **311 stars, 78 forks, BSD-3-Clause.** Government-backed (DOE/NREL) but no documented production deployments.
- **Documentation:** Diataxis framework, 2 tutorials, 7+ open doc issues. No performance guides or case studies.

## Detailed Notes

### Evaluation-Relevant Limitations

| Capability | Status | Evidence |
|---|---|---|
| SCOPF (N-1/N-k) | Not implemented | Issue #944 (open), #1462 (refactored) |
| Stochastic optimization | Not implemented | No issues, docs, or code |
| LMP decomposition | Not built-in | Must use JuMP duals manually |
| PTDF loss approximation | In development | Issue #1537 |
| Distributed slack | Available in PowerNetworkMatrices.jl | Unclear if PSI passes through |
| AC OPF | Via PowerModels.jl integration | Maturity uncertain (#1478) |
| N-1 SCUC | Recently refactored | v0.33.0, Jan 2026 |

### Community Metrics

| Metric | Value |
|---|---|
| GitHub stars | 311 |
| GitHub forks | 78 |
| Open issues | 66 |
| Total contributors | 39 |
| Top contributor | jd-lara (7,537 commits) |
| License | BSD-3-Clause |
| Created | 2017-11-03 |

### Release History (recent)

v0.33.1 (2026-02-24), v0.33.0 (2026-02-18, breaking), v0.32.4 (2025-12-18), v0.32.3 (2025-12-13), v0.30.2 (2025-06-09, installed version)

### Dependency Footprint

183 packages in Manifest.toml including MKL, HDF5, SQLite, MPI. All Sienna packages BSD-3-Clause. JuMP MPL-2.0. GLPK GPL-3.0.

### Operational Deployment

- DOE contract DE-AC36-08GO28308 at NREL
- PSI-Cambodia study (7 stars)
- No utility/ISO production deployments documented

## Key Gaps for Testing

- Stochastic optimization must be built manually on JuMP
- SCOPF requires custom constraint injection via B-1 pathway
- LMP decomposition requires manual dual extraction
- Distributed slack passthrough in PSI needs code verification
- AC OPF via PowerModels integration needs hands-on testing
- N-1 SCUC just refactored — stability unknown
- Version gap: installed v0.30.2 vs latest v0.33.1
