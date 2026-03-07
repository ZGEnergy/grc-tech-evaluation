---
test_id: D-3
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

# D-3: Example Verification

## Result: INFORMATIONAL

## Finding

The Sienna ecosystem provides a small number of official tutorials (5 across three
packages). The tutorials that exist are structurally complete and appear to use the current
API, but they are narrowly scoped to pre-packaged datasets and do not cover the breadth of
use cases encountered in this evaluation. Legacy tutorial repositories are referenced in
GitHub issues but not integrated into the main documentation.

## Example Inventory

### PowerSimulations.jl

| # | Tutorial | Data Source | Scope | Current API? |
|---|----------|------------|-------|-------------|
| 1 | Single-step Problem | RTS-GMLC via `PowerSystemCaseBuilder.jl` | Build a `DecisionModel`, configure device/network formulations, solve, extract results | Yes |
| 2 | Multi-stage PCM Simulation | RTS-GMLC (two systems: DA hourly, RT 5-min) | Two-stage DA/RT simulation with `SimulationModels`, `SimulationSequence`, feedforward | Yes |

**Assessment:** Both tutorials run through the complete workflow and produce output inline
(Documenter.jl `@example` blocks). They reference current API constructs
(`DecisionModel`, `ProblemTemplate`, `OptimizationProblemResults`, `read_variables`). The
single-step tutorial covers the core DecisionModel pattern that was used in tests A-3
through A-11.

**Gaps:**
- Neither tutorial uses MATPOWER `.m` files. Both rely on `PowerSystemCaseBuilder.jl`
  which provides pre-configured systems with time series already attached. A user starting
  from a MATPOWER case file has no tutorial coverage for the time series setup boilerplate.
- No UC-specific tutorial exists. GitHub issue #1108 ("Examples for Unit Commitment
  Problem," May 2024, closed) confirms users have requested this. A contributor directed
  users to the PCM tutorial as the closest available example.
- No tutorial covers economic dispatch as a standalone problem.
- No tutorial covers `ThermalRampLimited` or ramp constraint verification.

### PowerSystems.jl

| # | Tutorial | Scope | Current API? |
|---|----------|-------|-------------|
| 3 | Create and Explore a Power System | System construction, component access | Yes |
| 4 | Manipulating Data Sets | Editing components, bulk operations | Yes |
| 5 | Working with Time Series | SingleTimeSeries, Deterministic, Scenarios types | Yes |
| 6 | Adding Data for Dynamic Simulations | Dynamic simulation data | Yes |

**Assessment:** Tutorial #5 (time series) is the most relevant to this evaluation. It
documents the time series types and `transform_single_time_series!()` that were needed
for every PSI test. However, it does not show the specific pattern of adding synthetic
time series to MATPOWER-loaded systems for single-period OPF.

**Breaking change note:** PowerSystems.jl v5.0 (November 2025) included breaking changes.
The documentation includes a migration guide. The evaluated PSI v0.30.2 uses PSY v4.x, so
the current stable docs may not fully match the version under test.

### PowerFlows.jl

| # | Tutorial | Scope | Current API? |
|---|----------|-------|-------------|
| 7 | Solving a Power Flow | DC, AC, and PTDF power flow on 5-bus system | Mostly |

**Assessment:** This is the only PowerFlows tutorial. It demonstrates the three solver
types (`DCPowerFlow`, `ACPowerFlow`, `PTDFDCPowerFlow`) and shows the result structure
(DataFrames with `bus_results` and `flow_results`). Uses `PowerSystemCaseBuilder.jl`
rather than direct MATPOWER loading.

**Issues noted:**
- Documentation self-reports as "still in progress."
- How-to guides and explanation sections are stubs.
- A variable naming inconsistency was observed (PTDF section references `dc_results`
  instead of `ptdf_results`).

## Legacy Tutorials

GitHub issue #1165 references two external tutorial repositories:
- `NREL-Sienna/SIIP-Tutorial` -- historical tutorials from the SIIP (Scalable Integrated
  Infrastructure Planning) project era.
- `NREL-Sienna/OldExamples.jl` -- legacy examples.

These are not linked from the current documentation sidebar and their API currency is
unknown. Issue #1165 includes a task to "Move tutorials to documentation" which remains
unchecked as of the evaluation date.

## Known Issues Affecting Examples

1. **Issue #1165** (open, Oct 2024): "Initial clean-up and reorganization of
   PowerSimulations documentation." Acknowledges simulation recorder examples use
   copy-pasted `julia` blocks instead of working `@example` blocks, causing the
   documentation formatter to fail.

2. **Issue #1246** (open, Feb 2025): "`get_decision_problem_results` docstring not
   building." Indicates at least one API function's documentation is broken in the
   generated docs.

3. **Issue #1357** (open, Aug 2025): "Valid Configurations lists invalid configuration for
   `RenewableNonDispatch`." The Formulation Library's valid configuration table contains
   at least one incorrect entry.

4. **Issue #1338** (open, Jul 2025): "`SystemBalanceSlackDown` explanation is ambiguous."
   A formulation library entry has unclear documentation.

## Overall Assessment

- **Quantity:** 7 tutorials across 3 packages (2 PSI, 4 PSY, 1 PowerFlows).
- **Quality:** The PSI tutorials are well-structured and produce working output. They
  demonstrate the full build-solve-extract lifecycle. However, they are narrowly scoped
  to pre-packaged RTS-GMLC data.
- **Currency:** Tutorials appear to use the current API. No deprecated function calls were
  observed. The PowerSystems v5.0 migration may affect future compatibility.
- **Coverage:** Tutorials cover approximately 20% of the use cases encountered in this
  evaluation. Single-period OPF from MATPOWER data, unit commitment, economic dispatch,
  contingency analysis, and cross-package workflows all lack tutorial coverage.
- **Maintenance:** Multiple open issues acknowledge documentation gaps. The documentation
  reorganization effort (issue #1165) has been in progress since October 2024 with
  incomplete checklist items.
