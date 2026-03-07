---
test_id: D-2
tool: powersimulations
dimension: accessibility
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# D-2: Documentation Audit

## Result: INFORMATIONAL

## Finding

Official documentation across the Sienna ecosystem (PowerSimulations.jl, PowerSystems.jl,
PowerFlows.jl) covers the core multi-period simulation workflow well but has significant
gaps for single-period/MATPOWER-based workflows and advanced formulations. Of 11 Suite A
tests, only 4 were achievable from documentation alone. The remaining tests required source
code reading, GitHub issue searching, or outright guessing.

## Per-Test Documentation Assessment

| Test | Topic | Achievability | Notes |
|------|-------|---------------|-------|
| A-1  | DCPF | docs alone | PowerFlows.jl tutorial shows `solve_powerflow(DCPowerFlow(), sys)` directly. |
| A-2  | ACPF | docs alone | Same PowerFlows.jl tutorial covers `ACPowerFlow()`. Flat-start and warm-start patterns not documented but intuitive. |
| A-3  | DCOPF | docs + source reading | PSI tutorial shows `DecisionModel` + `ProblemTemplate` workflow but uses RTS-GMLC data with pre-built time series. Time series boilerplate for MATPOWER snapshot data is undocumented. Branch type registration requirement (Line, Transformer2W, TapTransformer all need explicit `set_device_model!`) is not called out. |
| A-4  | AC Feasibility | docs + source reading | Cross-package workflow (PSI DecisionModel -> PowerFlows ACPF) is not documented as a recipe. Dispatch unit mismatch between PSI result values and PowerSystems component limits is undocumented. |
| A-5  | SCUC | docs + issue searching | PSI tutorial demonstrates `ThermalStandardUnitCommitment` formulation. However, HiGHS failure during SCUC initial condition initialization required GitHub issue searching to identify solver compatibility. UC parameter setup (ramp rates, min up/down time) for MATPOWER data is undocumented. |
| A-6  | SCED | docs alone | `ThermalBasicDispatch` and `ThermalRampLimited` formulations are documented in the Formulation Library. UC/ED separation via formulation selection is documented. |
| A-7  | Contingency sweep | guessing required | No documentation for contingency analysis. Manual graph construction from PowerSystems bus/branch data, BFS neighborhood scoping, and branch toggling via `set_available!()` all required guessing. No Graphs.jl integration documented. |
| A-8  | Stochastic | docs + source reading | Documentation confirms `Scenarios` time series type exists in PowerSystems.jl. However, source reading was needed to confirm PSI `DecisionModel` is deterministic-only and does not consume `Scenarios` for stochastic programs. No documentation explicitly states this limitation. |
| A-9  | SCOPF | guessing required | No SCOPF documentation exists. The approach of accessing the JuMP model via `get_jump_model()` and injecting LODF-based constraints required reading PSI source to discover the function. LODF computation via PowerNetworkMatrices.jl is documented at API level but not as a SCOPF recipe. |
| A-10 | Lossy DCOPF | docs + source reading | Formulation Library documents `PTDFPowerModel` and `DCPPowerModel` but does not mention loss support. Source reading confirmed all DC formulations are lossless. No lossy DC formulation (e.g., DCPLLPowerModel from PowerModels.jl) is exposed. |
| A-11 | Distributed slack | docs + source reading | `PTDFPowerModel` vs `DCPPowerModel` formulations are documented, but the distributed-vs-single-slack distinction is not explained. Source reading was needed to understand that PTDF eliminates the reference bus angle variable. Slack weight configurability is not documented (and does not exist). |

## Summary Statistics

- **Docs alone:** 4 of 11 tests (A-1, A-2, A-6, and A-1/A-2 via PowerFlows tutorial)
- **Docs + source reading:** 4 of 11 tests (A-3, A-4, A-8, A-10, A-11)
- **Docs + issue searching:** 1 of 11 tests (A-5)
- **Guessing required:** 2 of 11 tests (A-7, A-9)

## Documentation Sources Assessed

### PowerSimulations.jl (stable docs)

- **Tutorials:** 2 pages -- "Single-step Problem" (DecisionModel with RTS-GMLC data) and
  "Multi-stage Production Cost Simulation" (two-stage DA/RT market simulation). Both are
  complete, working examples but use pre-packaged RTS-GMLC datasets via
  `PowerSystemCaseBuilder.jl`, not MATPOWER files.
- **How-to guides:** 7 pages covering variable registration, problem templates, results
  reading, debugging infeasible models, logging, simulation recorder, and parallel
  simulations.
- **Formulation Library:** 10 categories documenting device formulations
  (`ThermalStandardUnitCommitment`, `ThermalBasicDispatch`, etc.) and network models.
- **API Reference:** Comprehensive but auto-generated; limited narrative context.

### PowerSystems.jl (stable docs)

- **Tutorials:** 4 pages -- creating a System, manipulating data, working with time series,
  dynamic simulation data. The time series tutorial covers `SingleTimeSeries`,
  `Deterministic`, and `Scenarios` types.
- **Breaking change warning:** PowerSystems.jl v5.0 (November 2025) introduced breaking
  changes. Migration guide exists. The evaluated version (used with PSI v0.30.2) is v4.x.

### PowerFlows.jl (stable docs)

- **Tutorials:** 1 page -- "Solving a Power Flow" demonstrating DC, AC, and PTDF power
  flow on a 5-bus system via `PowerSystemCaseBuilder.jl`.
- **Note:** Documentation states it is "still in progress." How-to guides and explanation
  sections contain stubs only.
- **Minor issue:** The tutorial appears to have a variable naming inconsistency where PTDF
  results reference `dc_results` instead of `ptdf_results`.

## Key Documentation Gaps

1. **MATPOWER single-period workflow:** No recipe for converting a MATPOWER `.m` file
   snapshot into PSI's required time-series-annotated format. This is the most common
   newcomer use case and requires approximately 20 lines of boilerplate per test.

2. **Branch type registration:** No documentation warns that MATPOWER case39.m contains
   Lines, Transformer2W, and TapTransformers, all of which need explicit
   `set_device_model!()` calls. Omitting any one causes a silent or cryptic error.

3. **Dispatch unit basis:** `read_variables()` returns values in an undocumented unit basis
   that differs from PowerSystems component limits by approximately 100x. No documentation
   explains the unit conversion.

4. **Solver compatibility matrix:** No documentation lists which solvers work with which
   formulations. GLPK fails on quadratic costs (case39 uses `QuadraticCurve`); HiGHS fails
   on SCUC initial condition initialization. Users must discover these by trial and error.

5. **Advanced analysis patterns:** Contingency analysis, SCOPF, lossy OPF, and stochastic
   optimization have no documentation, how-to guides, or even brief mentions of whether
   they are supported.

6. **Open issue #1165:** "Initial clean-up and reorganization of PowerSimulations
   documentation" (opened October 2024, still open as of evaluation date). The issue
   acknowledges documentation gaps including moving tutorials from external repos
   (SIIP-Tutorial, OldExamples.jl) into the main docs, fixing broken code examples in the
   simulation recorder page, and proof-reading for formatting errors.
