---
test_id: D-5
tool: powersimulations
dimension: accessibility
network: TINY
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# D-5: Code Volume Comparison

## Result: INFORMATIONAL

## Finding

Test scripts for PowerSimulations.jl range from 87 to 380 LOC (non-blank, non-comment).
Simple power flow tests (A-1, A-2) are compact, but optimization tests (A-3 onward) are
significantly inflated by mandatory time series boilerplate (~20 LOC per test) and
explicit device model registration (~6 LOC per test). Advanced tests (A-9 SCOPF, A-11
distributed slack) exceed 350 LOC due to multi-formulation comparison and JuMP model
access patterns.

## LOC Table

Lines counted: non-blank, non-comment (excluding both `#` line comments and `#= ... =#`
block comments). Source directory:
`evaluations/powersimulations/tests/expressiveness/`

| Test | File | LOC | Category |
|------|------|-----|----------|
| A-1  | test_a1_dcpf.jl | 87 | Power flow (PowerFlows.jl) |
| A-2  | test_a2_acpf.jl | 129 | Power flow (PowerFlows.jl) |
| A-3  | test_a3_dcopf.jl | 218 | Optimization (PSI DecisionModel) |
| A-4  | test_a4_ac_feasibility.jl | 235 | Cross-package (PSI + PowerFlows) |
| A-5  | test_a5_scuc.jl | 349 | Optimization (PSI DecisionModel, MIP) |
| A-6  | test_a6_sced.jl | 369 | Optimization (PSI, two formulations) |
| A-7  | test_a7_contingency.jl | 255 | Manual sweep (PowerFlows + graph logic) |
| A-8  | test_a8_stochastic.jl | 270 | Capability probe + workaround loop |
| A-9  | test_a9_scopf.jl | 367 | JuMP model injection (PSI + LODF) |
| A-10 | test_a10_lossy_dcopf.jl | 210 | Capability probe (expected fail) |
| A-11 | test_a11_distributed_slack.jl | 360 | Two-formulation comparison |
| | **Total** | **2,849** | |
| | **Median** | **255** | |
| | **Mean** | **259** | |

## LOC Breakdown by Concern

A typical PSI optimization test (e.g., A-3 DCOPF) contains these recurring code sections:

| Concern | Approx. LOC | Notes |
|---------|-------------|-------|
| Imports | 8-10 | 6-9 packages (PowerSystems, PowerSimulations, solver, JuMP, JSON, etc.) |
| Solver config constants | 4-8 | Solver-specific parameter pairs |
| Time series boilerplate | 18-25 | Loop over ThermalStandard, RenewableDispatch, PowerLoad; create TimeArray, SingleTimeSeries, add_time_series!, transform_single_time_series! |
| Generator limit fix | 5-7 | Fix active_power > Pmax data issue in MATPOWER case39 |
| Device model registration | 6 | One `set_device_model!()` call per component type (6 types in case39) |
| DecisionModel build/solve | 8-12 | Template, model construction, build!, solve!, status checks |
| Result extraction | 15-30 | OptimizationProblemResults, read_variables, read_duals, DataFrame iteration |
| JSON output scaffolding | 15-25 | Dict construction, error handling, timing, JSON serialization |

The time series boilerplate and device model registration together account for
approximately 25-30 LOC per optimization test. This overhead is constant regardless of
problem complexity and represents framework ceremony rather than problem-specific logic.

## Observations

1. **Power flow tests (A-1, A-2) are lean.** PowerFlows.jl's `solve_powerflow()` API
   requires no time series setup, no device model registration, and no solver
   configuration. The LOC is dominated by result extraction and validation logic.

2. **Optimization tests jump in complexity at A-3.** The transition from PowerFlows to
   PSI DecisionModel adds a fixed overhead of ~30 LOC for time series and device model
   setup. This overhead recurs identically in A-3, A-4, A-5, A-6, A-8, A-9, A-10, and
   A-11.

3. **Multi-formulation tests are the longest.** A-6 (SCED) tests both
   `ThermalBasicDispatch` and `ThermalRampLimited`; A-11 tests both `PTDFPowerModel` and
   `DCPPowerModel`. Each formulation requires a separate system load, time series setup,
   and solve cycle, roughly doubling the code.

4. **A-9 (SCOPF) requires low-level JuMP access.** The SCOPF test is 367 LOC because PSI
   has no native SCOPF support. The script must access the underlying JuMP model via
   `get_jump_model()`, compute the LODF matrix, parse PSI's internal variable naming
   convention, map flow variables to branch names, and inject contingency constraints.
   This pattern is not documented and required significant source code reading.

5. **A-7 (contingency sweep) builds its own graph.** 255 LOC includes a manual adjacency
   list construction, BFS implementation, and combinatorial enumeration -- none of which
   use PSI's optimization framework. The test operates entirely through PowerFlows.jl's
   linear solver.

6. **JSON output scaffolding inflates all tests.** Each test script includes 15-25 LOC
   of Dict construction, try/catch error handling, wall-clock timing, and JSON
   serialization. This is evaluation harness code, not tool-specific logic, but it is
   included in the count since it is part of the test script.

## Cross-Tool Context

This is a single-tool measurement. Cross-tool LOC comparison will be performed during
the synthesis phase. The LOC values above include evaluation harness overhead (JSON output,
error handling, timing) that is roughly constant across tools, so relative comparisons
should focus on the tool-specific logic portions.
