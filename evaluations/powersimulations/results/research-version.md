---
tool: powersimulations
installed_version: 0.30.2
release_date: 2024-06-09
latest_version: 0.33.5
latest_release_date: 2025-03-21
research_date: 2026-03-24
---

# powersimulations — Version & Capability Report

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
