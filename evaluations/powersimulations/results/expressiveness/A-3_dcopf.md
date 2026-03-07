---
test_id: A-3
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: 70.44
peak_memory_mb: null
loc: 297
solver: "HiGHS (pass), GLPK (fail)"
timestamp: "2026-03-07T01:30:00Z"
---

# A-3: Solve DC OPF with generation costs and line flow limits

## Result: QUALIFIED PASS

## Approach

DC OPF was solved using PowerSimulations.jl (v0.30.2) `DecisionModel` with `PTDFPowerModel`
network formulation. The test required several preparatory steps beyond what a typical
single-period OPF tool would need:

1. **System loading:** `System("/workspace/data/networks/case39.m")` -- same as A-1/A-2.
2. **Generator limit fix:** case39.m has gen-2 with `active_power=6.78` exceeding
   `Pmax=6.46`. Clamped to Pmax before time series creation.
3. **Time series injection:** PSI requires forecast/time series data for its DecisionModel.
   MATPOWER files have only snapshot data. Added `SingleTimeSeries("max_active_power", ...)`
   with multiplier value `1.0` for all generators and loads, then transformed to
   `Deterministic` forecasts via `transform_single_time_series!()`.
4. **Device model registration:** Every component type in the system must have an explicit
   device model. case39 has 34 Lines, 1 Transformer2W, and 11 TapTransformers -- all
   registered as `StaticBranch`.
5. **Dual extraction:** Requested duals on `CopperPlateBalanceConstraint` to obtain
   system-wide energy price.

**HiGHS** solved successfully (QP with quadratic cost curves). **GLPK** failed at
build stage because the cost curves are quadratic (`QuadraticCurve`) and GLPK does not
support QP -- this is a solver limitation, not a tool limitation.

**Cost curve type:** `ThermalGenerationCost` with `CostCurve{QuadraticCurve}(0.01x^2 + 0.3x + 0.0)` in DEVICE_BASE units.

## Output

**HiGHS results:**

| Metric | Value |
|--------|-------|
| Objective value | 22.70 |
| Solve status | SUCCESSFULLY_FINALIZED |
| Build status | BUILT |

**Generator dispatch (MW):**

| Generator | Dispatch (MW) | Pmax (MW) | At limit? |
|-----------|--------------|-----------|-----------|
| gen-1 | 660.85 | 1040.0 | No |
| gen-2 | 646.00 | 646.0 | Yes |
| gen-3 | 660.84 | 725.0 | No |
| gen-4 | 652.00 | 652.0 | Yes |
| gen-5 | 508.00 | 508.0 | Yes |
| gen-6 | 660.84 | 687.0 | No |
| gen-7 | 580.00 | 580.0 | Yes |
| gen-8 | 564.00 | 564.0 | Yes |
| gen-9 | 660.85 | 865.0 | No |
| gen-10 | 660.85 | 1100.0 | No |

**LMP extraction:**

| Metric | Value |
|--------|-------|
| Dual variable | CopperPlateBalanceConstraint__System |
| System price | 0.432 $/MWh |
| LMP count | 1 (system-wide, not nodal) |

Note: The `PTDFPowerModel` with `CopperPlateBalanceConstraint` produces a single
system-wide energy price, not bus-specific nodal LMPs. Nodal LMPs would require
`DCPPowerModel` with `NodalBalanceActiveConstraint` duals, which is a different
formulation path. The system-wide dual reflects the marginal cost of the system
energy balance constraint.

**GLPK results:** Build FAILED -- GLPK cannot solve QP problems. The case39 generators
use quadratic cost curves (`QuadraticCurve(0.01, 0.3, 0.0)`) which produce a quadratic
objective. GLPK only supports LP/MILP.

**Solver comparison:** Only HiGHS produced results. GLPK incompatibility is expected
for quadratic cost curves.

**Variables available:** `ActivePowerVariable__ThermalStandard`,
`FlowActivePowerVariable__Line`, `FlowActivePowerVariable__Transformer2W`,
`FlowActivePowerVariable__TapTransformer`.

## Workarounds

- **What:** Added synthetic single-period time series (multiplier=1.0) to all generators
  and loads before building the DecisionModel.
- **Why:** PSI `DecisionModel` requires forecast/time series data. MATPOWER .m files
  contain only snapshot data. PSI is designed as a multi-period simulation framework,
  not a single-period OPF solver.
- **Durability:** stable -- uses documented public API (`SingleTimeSeries`,
  `transform_single_time_series!`). This pattern is shown in PSI tutorials.
- **Grade impact:** Adds significant boilerplate (~30 LOC) for what is conceptually
  a single-period OPF. However, the API is well-documented and the pattern is stable.

- **What:** Registered explicit device models for `Transformer2W` and `TapTransformer`
  as `StaticBranch`.
- **Why:** PSI requires every component type present in the system to have a registered
  device model in the `ProblemTemplate`. The system parser creates these types from the
  MATPOWER data.
- **Durability:** stable -- documented API requirement. Every PSI example shows this
  pattern.
- **Grade impact:** Minor -- adds 2 lines. Part of PSI's explicit-is-better-than-implicit
  design philosophy.

## Timing

- **Wall-clock (total):** 70.44s (includes JIT compilation for PowerSimulations)
- **HiGHS solve time:** 48.14s (includes JIT for model construction)
- **Peak memory:** not measured
- **CPU cores used:** 1

Note: First invocation of PSI `DecisionModel` / `build!` / `solve!` triggers extensive
JIT compilation. Subsequent solves in the same session would be significantly faster
(estimated <5s for this problem size).

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a3_dcopf.jl`
