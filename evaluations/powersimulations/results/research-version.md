---
tool: powersimulations
installed_version: 0.30.2
release_date: 2024-06-09
latest_version: 0.33.1
latest_release_date: 2025-02-24
research_date: 2026-03-13
---

# powersimulations — Version & Capability Report

## Version Summary

The installed version of PowerSimulations.jl is **v0.30.2** (released June 9, 2024), which is **three minor versions behind** the latest release **v0.33.1** (released February 24, 2025). The gap spans approximately 8 months and includes two breaking-change releases (v0.31.0 and v0.32.0, v0.33.0). The installed environment also pins older versions of companion packages: PowerSystems.jl v4.6.2 (latest is v5.5.0), PowerNetworkMatrices.jl v0.12.1 (latest is v0.18.2), InfrastructureSystems.jl v2.6.0 (latest is v3.3.1), and PowerFlows.jl v0.9.0 (latest is v0.16.0). These are constrained by compatibility bounds in the Project.toml `[compat]` section, which permits PowerSimulations 0.27–0.33 and PowerSystems 4–5. Upgrading to v0.33.1 would require upgrading the entire Sienna dependency chain.

Despite being behind, the installed v0.30.2 retains all core evaluation-relevant capabilities (UC, ED, PTDF network models, MATPOWER import, time series, warm start, parallel simulation). The newer versions primarily add HVDC multi-terminal models, 3-winding transformers, outage event simulation, synchronous condensers, and performance improvements — features that are not central to the evaluation protocol.

## Capability Table

| Feature | Supported | Since Version | Notes |
|---------|-----------|---------------|-------|
| DC Power Flow (DCPF) | yes | 0.1.0 | Via `DCPPowerModel` network formulation (from PowerModels.jl); also `PTDFPowerModel` for PTDF-based DC approximation |
| AC Power Flow (ACPF) | yes | 0.1.0 | Via `ACPPowerModel`, `ACRPowerModel`, `ACTPowerModel` network formulations (from PowerModels.jl) |
| DC Optimal Power Flow (DC OPF) | yes | 0.1.0 | `DecisionModel` with `DCPPowerModel` or `PTDFPowerModel` network formulation solves DC OPF |
| AC Optimal Power Flow (AC OPF) | yes | 0.1.0 | `DecisionModel` with `ACPPowerModel` or other AC formulations; non-convex, requires nonlinear solver (e.g., Ipopt) |
| Security-Constrained Unit Commitment (SCUC) | partial | — | Unit commitment is fully supported via `ThermalStandardUnitCommitment`, `ThermalMultiStartUnitCommitment`, etc. Security constraints (N-1 contingency enforcement within the UC) are **not built-in**; legacy N-1/G-1 code was removed in v0.33.0. Users can manually add contingency constraints via JuMP API. |
| Security-Constrained Economic Dispatch (SCED) | partial | — | Economic dispatch is fully supported via `ThermalStandardDispatch`, `ThermalCompactDispatch`, etc. Same contingency limitation as SCUC above. |
| PTDF / Shift Factor Extraction | yes | 0.1.0 | `PTDFPowerModel` and `AreaPTDFPowerModel` in PowerSimulations; `PTDF`, `VirtualPTDF`, `LODF`, `VirtualLODF` available via PowerNetworkMatrices.jl v0.12.1 |
| Contingency Analysis (N-1) | partial | — | PowerNetworkMatrices.jl provides `LODF`/`VirtualLODF` for post-contingency flow estimation. PowerSimulations had N-1/G-1 contingency formulations that were **removed in v0.33.0**. In v0.30.2, some contingency code may still exist but is undocumented. Manual implementation via LODF matrices is feasible. |
| Custom Constraint Injection | yes | 0.1.0 | Full access to underlying JuMP model via `get_jump_model()`. Users can add arbitrary constraints, variables, and objectives using JuMP's API. Feedforward mechanisms also allow inter-model constraint coupling. |
| Network Graph Access | yes | 0.1.0 | PowerNetworkMatrices.jl provides `IncidenceMatrix`, `AdjacencyMatrix`, `ABA_Matrix`, `BA_Matrix`, `Ybus`, plus `find_subnetworks` and `validate_connectivity` for topology analysis. `RadialNetworkReduction` available for network reduction. |
| CSV Data Import | yes | 0.1.0 | PowerSystems.jl supports tabular CSV import for system construction and time series data. Results can be exported to CSV via `export_realized_results` and `export_results`. |
| MATPOWER Case Import | yes | 0.1.0 | `System("path/to/case.m")` parses MATPOWER case files via PowerSystems.jl's built-in parser (originally derived from PowerModels.jl). Also supports PSS/e `.raw` and `.dyr` formats. |
| Multi-Period / Time Series | yes | 0.1.0 | Core design feature. `Simulation` sequences multiple `DecisionModel` steps (e.g., day-ahead UC followed by real-time ED). Time series attach to components via `SingleTimeSeries`, `Deterministic`, and `Probabilistic` types in InfrastructureSystems.jl. |
| Warm Start / Solution Reuse | yes | 0.1.0 | `_apply_warm_start!` passes previous solution as MIP start hints. Initial conditions (on/off status, energy levels, duration counters) propagate between simulation steps automatically. Configurable via `get_warm_start`/`set_warm_start!`. |
| Parallel Computation | yes | ~0.27 | `run_parallel_simulation` partitions a simulation across multiple Julia processes. Parameters include `num_parallel_processes`, `num_overlap_steps`, and custom `exeflags`. Uses Julia's Distributed module. |

## Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|----------------------|
| v0.31.0 | Updated all dependencies; new outage events API; multi-terminal HVDC and 3WT models added | Low — new features not required by protocol; dependency updates may require compat adjustments if upgrading |
| v0.32.0 | New dependencies introduced; branch model implementation corrected; MarketBidCost refactored for time-variable service bidding | Low — branch model corrections could affect flow results on specific topologies; MarketBidCost changes affect cost modeling |
| v0.33.0 | Renamed power flow variables (`PowerFlowLine` → `PowerFlowBranch`); removed legacy N-1 and G-1 contingency code; eliminated unmonitored line creation for performance | Medium — variable renaming breaks scripts referencing old names; N-1/G-1 removal means contingency analysis must use LODF-based approach if upgrading |
| PowerSystems v5.0 | Major version bump with breaking API changes; migration guide required from v4.x | High if upgrading — would affect all system construction and component access code |

## Changelog Analysis

### v0.30.2 → v0.31.0 (June 2024 → November 2024)

**New capabilities:** Outage event simulation framework; multi-terminal HVDC (lossless and lossy); three-winding transformer support; time-variable MarketBidCost for thermals and renewables; time-varying ImportExportCost; 3D results handling; voltage stability integration; load modeling without time series requirement.

**Infrastructure:** Network reduction compatibility; area interchange enhancements; PowerFlowData output corrections for HVDC flow direction.

### v0.31.0 → v0.32.0 (November → December 2024)

**Fixes:** Cost tracking and ramp constraint corrections; MarketBidCost SingleTimeSeries compatibility; inter-area mapping refactoring. Decomposition algorithm refinements introduced. Parallel branches with unequal impedances now supported (v0.32.3).

### v0.32.0 → v0.33.0 (December 2024 → February 2025)

**Performance:** Eliminated creation of variables for unmonitored branches, improving solve time on large networks. Type inference and annotation improvements.

**New:** Synchronous condenser model; FuelCurve with PiecewiseAverageCurve in ThermalStandardUnitCommitment; quadratic cost curves for RenewableDispatch; feedforward arguments for renewables.

**Removed:** Legacy N-1 and G-1 contingency formulation code.

**Renamed:** PowerFlowLine → PowerFlowBranch nomenclature.

### v0.33.0 → v0.33.1 (February 2025)

**Patch:** Auxiliary variable for AC line losses; time series handling fix for renewables.

## Sources

1. GitHub releases — PowerSimulations.jl: https://github.com/NREL-Sienna/PowerSimulations.jl/releases
2. PowerSimulations.jl v0.30.2 release: https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.30.2
3. PowerSimulations.jl v0.31.0 release: https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.31.0
4. PowerSimulations.jl v0.32.0 release: https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.32.0
5. PowerSimulations.jl v0.33.0 release: https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.33.0
6. PowerSimulations.jl v0.33.1 release: https://github.com/NREL-Sienna/PowerSimulations.jl/releases/tag/v0.33.1
7. PowerSimulations.jl documentation — Network formulations: https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Network/
8. PowerSimulations.jl documentation — Thermal generation: https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/ThermalGen/
9. PowerSimulations.jl documentation — Branch formulations: https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Branch/
10. PowerSimulations.jl documentation — Service formulations: https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Service/
11. PowerSystems.jl documentation: https://nrel-sienna.github.io/PowerSystems.jl/stable/
12. PowerNetworkMatrices.jl repository: https://github.com/NREL-Sienna/PowerNetworkMatrices.jl
13. Installed package status via `Pkg.status()` and `Pkg.status(; outdated=true)` — run in devcontainer
14. Runtime symbol inspection via `names(PowerSimulations; all=true)` and `names(PowerNetworkMatrices)` — run in devcontainer
15. `evaluations/powersimulations/Project.toml` — compat bounds

## Gaps and Uncertainties

- **Contingency analysis depth in v0.30.2:** The legacy N-1/G-1 code was removed in v0.33.0, but its actual functionality and API in v0.30.2 is undocumented. It is unclear whether this code was ever production-ready or was experimental.
- **Exact "Since Version" for parallel simulation:** `run_parallel_simulation` exists in v0.30.2 but the exact version it was introduced is not documented in release notes; estimated as ~v0.27 based on compat bounds.
- **CSV import specifics:** PowerSystems.jl supports CSV-based system construction via a descriptor file format, but the exact schema and limitations for tabular data parsing were not fully documented in accessible pages (404 errors on tutorial URLs for v4.x docs).
- **Warm start effectiveness:** The warm start mechanism exists and is callable, but whether it materially improves solve times depends on the solver (HiGHS, GLPK, Ipopt, SCIP) and problem structure. No benchmarks were found.
- **PowerFlows.jl v0.9.0 capabilities:** The installed PowerFlows.jl is significantly behind (latest v0.16.0). Its role in "power flow in the loop" simulation features may be limited at this version.
- **Result export format:** `export_realized_results` writes to a directory structure; whether the output format is CSV or another tabular format was confirmed by method signature but not by direct file inspection.
