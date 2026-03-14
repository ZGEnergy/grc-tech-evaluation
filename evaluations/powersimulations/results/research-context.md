# PowerSimulations.jl — Consolidated Research Context

## Section 1: API & Formulations

*(from research-api.md)*

### Key Findings

- **PowerSimulations.jl (v0.30.2) is an optimization-based operations simulation tool**, not a power-flow solver. It builds JuMP optimization models for unit commitment (SCUC), economic dispatch (SCED), and multi-stage production cost simulations. Power flow is handled by the companion package PowerFlows.jl (v0.9.0).
- **The data model lives in PowerSystems.jl (v4.6.2)**, which provides typed Julia structs for buses (`ACBus`), generators (`ThermalStandard`, `RenewableDispatch`, etc.), branches (`Line`, `Transformer2W`, etc.), loads, storage, and services. It parses MATPOWER `.m`, PSS/E `.raw`/`.dyr`, and tabular CSV files via `System(file_path)`.
- **15 network formulations are re-exported** from PowerModels.jl, ranging from `CopperPlatePowerModel` (single-node) to `ACPPowerModel` (full nonlinear AC) and including PTDF-based linear approximations (`PTDFPowerModel`, `AreaPTDFPowerModel`).
- **9 thermal generation formulations** span dispatch-only through full unit commitment with multi-start profiles.
- **Solver-agnostic via JuMP/MathOptInterface**: HiGHS (LP/MILP), Ipopt (NLP), GLPK (LP/MILP), and SCIP (MINLP) installed.
- **Two-level problem architecture**: `DecisionModel` for single-step optimization, and `Simulation` for multi-stage sequential problems with feedforward constraints.
- **Results returned as DataFrames** via `read_variable()`, `read_dual()`, `read_expression()`, etc.
- **Network matrices** (PTDF, LODF, Ybus, incidence) computed by PowerNetworkMatrices.jl (v0.12.1).
- **PowerFlows.jl provides standalone power flow** with AC solvers (Newton-Raphson, trust region, Levenberg-Marquardt, robust homotopy) and DC variants.
- **Parallel simulation support** via `run_parallel_simulation()`.

### Critical API Patterns

**DecisionModel workflow:**
```julia
sys = System("case.m")
template = template_unit_commitment(network=NetworkModel(PTDFPowerModel, use_slacks=true))
solver = optimizer_with_attributes(HiGHS.Optimizer, "mip_rel_gap" => 0.01)
model = DecisionModel(template, sys; optimizer=solver, horizon=Hour(24))
build!(model; output_dir=mktempdir())
solve!(model)
results = OptimizationProblemResults(model)
thermal_power = read_variable(results, "ActivePowerVariable__ThermalStandard")
duals = read_dual(results, "CopperPlateBalanceConstraint__System")
```

**Power flow (separate package):**
```julia
solve_power_flow(ACPowerFlow(), sys)  # Returns Dict of DataFrames
solve_power_flow(DCPowerFlow(), sys)
```

**Result naming convention:** `"VariableType__DeviceType"` (double underscore separator).

---

## Section 2: Extensions & Architecture

*(from research-extensions.md)*

### Key Findings

- **Julia's multiple dispatch is the extension mechanism.** No plugin registry or callback API. Users subtype abstract formulation types, then define `construct_device!` methods.
- **Three official extension packages** demonstrate the pattern: StorageSystemsSimulations.jl, HydroPowerSimulations.jl, HybridSystemsSimulations.jl.
- **Custom `DecisionProblem` types** allow completely overriding `build_model!`.
- **Clean separation of concerns**: PowerSystems.jl (data), PowerSimulations.jl (optimization), PowerNetworkMatrices.jl (matrices), InfrastructureSystems.jl (time series), PowerModels.jl (formulations).
- **No Graphs.jl dependency.** Topology via sparse adjacency/incidence matrices with custom DFS.
- **Results are returned as DataFrames.** CSV export built-in.
- **JuMP model fully accessible** via `get_jump_model(model)`.
- **Two-stage construction pattern**: ArgumentConstructStage (variables) and ModelConstructStage (constraints).

### Custom Constraint Addition
```julia
jump_model = PSI.get_jump_model(model)  # Direct JuMP access after build!
# Add arbitrary JuMP constraints before solve!
```

### No Graphs.jl Integration
Network topology accessed through PowerNetworkMatrices.jl (`AdjacencyMatrix`, `IncidenceMatrix`, `find_subnetworks`). Manual construction of Graphs.jl graph required for BFS/DFS.

---

## Section 3: Limitations & Ecosystem

*(from research-limitations.md)*

### Key Findings

- **No built-in SCOPF**: Open feature request since 2023 (#944). Test A-9 requires manual constraint assembly.
- **No built-in loss approximation for PTDF models**: Open issue #1537. Test A-10 may be difficult.
- **No documented distributed slack formulation**: Test A-11 likely requires workaround.
- **Active bugs**: Ramp-down inequality flipped (#1530), DC PF init bug with renewables (#1545), renewable profile scaling bug (#1557).
- **Very active development**: 1021 commits/12mo, 21 releases/24mo, but bus factor of 1 (jd-lara: 72% all-time commits).
- **Large dependency footprint**: 80+ resolved packages.
- **BSD-3-Clause across all Sienna packages**.
- **NREL institutional backing**: DOE/NREL funded, but no utility/ISO production deployment evidence.

### GitHub Metrics
- 311 stars / 78 forks (PowerSimulations.jl)
- 359 stars / 101 forks (PowerSystems.jl)
- 66 open issues, 10 documentation issues

---

## Section 4: Version & Capabilities

*(from research-version.md)*

### Version Summary
- **Installed**: v0.30.2 (June 9, 2024)
- **Latest**: v0.33.1 (February 24, 2025)
- **Gap**: 3 minor versions, ~8 months
- Companion packages also behind: PowerSystems.jl v4.6.2 (latest v5.5.0), PowerNetworkMatrices.jl v0.12.1 (latest v0.18.2)

### Capability Table

| Feature | Supported | Notes |
|---------|-----------|-------|
| DC Power Flow (DCPF) | yes | Via DCPPowerModel or PTDFPowerModel |
| AC Power Flow (ACPF) | yes | Via ACPPowerModel (requires Ipopt) |
| DC OPF | yes | DecisionModel + DCPPowerModel/PTDFPowerModel |
| AC OPF | yes | DecisionModel + ACPPowerModel (nonlinear) |
| SCUC | partial | UC fully supported; N-1 security constraints NOT built-in |
| SCED | partial | ED fully supported; same contingency limitation |
| PTDF Extraction | yes | PowerNetworkMatrices.jl: PTDF, VirtualPTDF, LODF |
| Contingency Analysis (N-1) | partial | LODF for post-contingency estimation; no built-in SCOPF |
| Custom Constraint Injection | yes | Full JuMP model access via get_jump_model() |
| Network Graph Access | yes | IncidenceMatrix, AdjacencyMatrix, find_subnetworks |
| CSV Data Import | yes | PowerSystems.jl tabular CSV import |
| MATPOWER Case Import | yes | System("case.m") via built-in parser |
| Multi-Period / Time Series | yes | Core design feature (Simulation sequences) |
| Warm Start / Solution Reuse | yes | _apply_warm_start! with MIP start hints |
| Parallel Computation | yes | run_parallel_simulation() |

### Breaking Changes (v0.30.2 → v0.33.1)
- v0.33.0: Removed legacy N-1/G-1 contingency code, renamed PowerFlowLine → PowerFlowBranch
- PowerSystems v5.0: Major API changes (not in installed version)
