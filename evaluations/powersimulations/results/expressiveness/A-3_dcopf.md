---
test_id: A-3
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "0ab69b36"
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 0.077
timing_source: measured
peak_memory_mb: 1386.2
convergence_residual: null
convergence_iterations: null
loc: 271
solver: HiGHS
timestamp: "2026-03-14T00:00:00Z"
---

# A-3: DCOPF with Differentiated Costs and 70% Branch Derating

## Result: PASS

## Approach

Built a `DecisionModel` with `DCPPowerModel` network formulation (angle-based DC OPF),
`ThermalDispatchNoMin` device model, and `NodalBalanceActiveConstraint` duals to extract
bus-level LMPs. Solver: HiGHS 1.21.1 (single-threaded, presolve on).

**Cost differentiation:** Read `gen_temporal_params.csv` to map each generator's
`tech_class_key` to a marginal cost (hydro $5, nuclear $10, coal $25, gas CC $40 per
MWh). Applied quadratic cost curves `c2*P^2 + c1*P` with `c2 = c1 * 0.001` per the
Modified Tiny README recipe. Used `CostCurve(QuadraticCurve(c2, c1, 0.0))` in
NATURAL_UNITS.

**Branch derating:** Multiplied all Line, Transformer2W, and TapTransformer ratings by
0.70 (46 branches total).

**Time series requirement:** PowerSimulations.jl requires deterministic time series
data even for single-snapshot optimization. Added a 1-step forecast with multiplier 1.0
for all loads to satisfy this constraint.

**LMP extraction:** Nodal balance duals from `read_dual(res, "NodalBalanceActiveConstraint__ACBus")`.
The raw dual values are in internal units (per-unit basis); conversion to $/MWh requires
dividing by `base_power` (100 MVA) and negating per shadow price sign convention.

## Output

**Dispatch:**

| Generator | Bus | Tech | Dispatch (MW) | Pmax (MW) | Utilization |
|-----------|-----|------|--------------|----------|-------------|
| gen-1 | 30 | Hydro | 275.6 | 1040.0 | 26.5% |
| gen-2 | 31 | Nuclear | 646.0 | 646.0 | 100.0% |
| gen-3 | 32 | Nuclear | 630.0 | 725.0 | 86.9% |
| gen-4 | 33 | Coal | 592.0 | 652.0 | 90.8% |
| gen-5 | 34 | Coal | 508.0 | 508.0 | 100.0% |
| gen-6 | 35 | Nuclear | 630.0 | 687.0 | 91.7% |
| gen-7 | 36 | Gas CC | 580.0 | 580.0 | 100.0% |
| gen-8 | 37 | Nuclear | 564.0 | 564.0 | 100.0% |
| gen-9 | 38 | Nuclear | 840.0 | 865.0 | 97.1% |
| gen-10 | 39 | Gas CC | 988.6 | 1100.0 | 89.9% |

Total dispatch: 6254.2 MW = system load. Hydro (cheapest) dispatches well below
capacity due to network congestion limiting power transfer from bus 30.

**LMP summary:**

| Metric | Value |
|--------|-------|
| Min LMP | $7.76/MWh (bus 30 - hydro) |
| Max LMP | $290.11/MWh (bus 3) |
| Mean LMP | $163.50/MWh |
| **LMP spread** | **$282.36/MWh** |
| Buses with LMP > min | 37/39 |

The LMP at bus 30 (hydro) equals its marginal cost: 5 + 2 x 0.005 x 275.6 = $7.76/MWh.
Bus 3 has the highest LMP due to congestion on branch 2-3.

**Binding branches:**

| Branch | Flow (MW) | Rating (MW) | Loading |
|--------|----------|-----------|---------|
| bus-2-bus-3-i_3 | 350.0 | 350.0 | 100% |
| bus-16-bus-19-i_27 | 420.0 | 420.0 | 100% |

Two branches bind at their derated ratings, meeting the >= 2 threshold.

**Objective:** $215,211.33/h total production cost.

## Workarounds

- **What:** Added deterministic time series data for a single-snapshot solve
- **Why:** PowerSimulations.jl's `DecisionModel` constructor requires the `System` to
  contain forecast data (throws `"The System does not contain any forecast data"` error
  without it). This is by design -- PSI is a simulation framework, not a standalone OPF
  solver.
- **Durability:** stable -- the time series requirement is a fundamental architecture
  decision. Adding a 1-step forecast with multiplier 1.0 is straightforward and
  produces correct results.
- **Grade impact:** Minor friction. The workaround adds ~5 lines of boilerplate per
  test. It does not affect the mathematical correctness of the result.

## Timing

- **Wall-clock:** 0.077 s (second run, after JIT warm-up; includes build + solve)
- **Timing source:** measured
- **Peak memory:** 1386.2 MB (Julia process RSS, includes JIT compilation cache)
- **Solver iterations:** not separately reported (HiGHS simplex)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a3_dcopf.jl`

Key API pattern:
```julia
# Cost differentiation
set_operation_cost!(gen, ThermalGenerationCost(
    CostCurve(QuadraticCurve(c2, c1, 0.0)), 0.0, 0.0, 0.0))

# Branch derating
set_rating!(line, get_rating(line) * 0.7)

# Time series (required boilerplate)
add_time_series!(sys, load, SingleTimeSeries("max_active_power", ...))
transform_single_time_series!(sys, Hour(1), Hour(1))

# Model
template = ProblemTemplate(NetworkModel(DCPPowerModel;
    duals=[NodalBalanceActiveConstraint]))
set_device_model!(template, ThermalStandard, ThermalDispatchNoMin)
model = DecisionModel(template, sys; optimizer=solver)
build!(model; output_dir=mktempdir()); solve!(model)

# LMPs
nodal_dual = read_dual(res, "NodalBalanceActiveConstraint__ACBus")
lmp_mwh = -raw_dual / base_power
```

## Observations

- **api-friction:** PowerSimulations requires time series data even for single-snapshot
  OPF. The `DecisionModel` constructor refuses to build without deterministic forecasts.
- **unit-mismatch:** `read_variable` returns dispatch in MW (natural units), but
  `read_dual` returns shadow prices in internal per-unit-based units. Converting LMP
  duals to $/MWh requires dividing by `base_power` and negating. This is not documented.
- **api-friction:** PTDFPowerModel with `use_slacks=true` produced an infeasible/nonsensical
  model (dispatch exceeded generator Pmax by 100x). Switched to DCPPowerModel which
  works correctly. The root cause of the PTDFPowerModel failure was not diagnosed but may
  relate to unit conversion in the slack variable formulation.
- **workaround-needed:** Time series boilerplate is required for every single-snapshot
  test using PowerSimulations. Time series value is a multiplier on `max_active_power`
  (not the absolute MW value), which is undocumented and discovered empirically.
