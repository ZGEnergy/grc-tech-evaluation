---
test_id: A-5
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "2fe64f1c"
status: qualified_pass
workaround_class: fragile
blocked_by: null
wall_clock_seconds: 0.797
timing_source: measured
peak_memory_mb: 1253.6
convergence_residual: null
convergence_iterations: null
loc: 374
solver: HiGHS
timestamp: "2026-03-14T00:00:00Z"
---

# A-5: 24-hour SCUC with Modified Tiny Data

## Result: QUALIFIED PASS

## Approach

Built a 24-hour Security-Constrained Unit Commitment (SCUC) using `DecisionModel` with
`ThermalStandardUnitCommitment` formulation (built-in, no custom assembly) and `DCPPowerModel`
network. Solver: HiGHS with 1% MIP gap tolerance.

**Cost differentiation:** Applied linear costs from Modified Tiny data (hydro $5, nuclear $10,
coal $25, gas CC $40 per MWh) plus no-load costs and cold startup costs from
`gen_temporal_params.csv`. Used `LinearCurve` (not `QuadraticCurve`) because HiGHS cannot
solve QP-MIP problems.

**UC parameters:** Set per-technology Pmin (hydro 25%, nuclear 50%, coal 40%, gas CC 30% of
Pmax), ramp rates from `gen_temporal_params.csv`, min up/down times, and startup costs.
All generators initialized as committed with sufficient time-at-status to allow decommit.

**Time series:** Loaded 24-hour load profile from `load_24h.csv` as hourly scaling factors
on each bus's `max_active_power`. Used `SingleTimeSeries` + `transform_single_time_series!`
with Hour(24) horizon and Hour(1) resolution.

**Initialization bypass:** Used `initialize_model=false` to skip PSI's automatic initialization
solve (which fails with HiGHS on this system configuration). Called `JuMP.optimize!(jm)`
directly instead of PSI's `solve!()`. Results extracted from PSI's internal variable containers
via `PSI.get_variables()`.

## Output

**Solver status:** OPTIMAL (MIP gap: 0.57%)

**Commitment schedule (1 = committed, 0 = off):**

| Generator | Bus | Tech | Cost | HR1-6 | HR7-12 | HR13-18 | HR19-24 |
|-----------|-----|------|------|-------|--------|---------|---------|
| gen-1 | 30 | Hydro | $5 | 111111 | 111111 | 111111 | 111111 |
| gen-2 | 31 | Nuclear | $10 | 111111 | 111111 | 111111 | 111111 |
| gen-3 | 32 | Nuclear | $10 | 111111 | 111111 | 111111 | 111111 |
| gen-4 | 33 | Coal | $25 | 111111 | 111111 | 111111 | 111111 |
| gen-5 | 34 | Coal | $25 | 111111 | 111111 | 111111 | 110000 |
| gen-6 | 35 | Nuclear | $10 | 111111 | 111111 | 111111 | 111111 |
| gen-7 | 36 | Gas CC | $40 | 000000 | 000000 | 01111111 | 10000 |
| gen-8 | 37 | Nuclear | $10 | 111111 | 111111 | 111111 | 111111 |
| gen-9 | 38 | Nuclear | $10 | 111111 | 111111 | 111111 | 111111 |
| gen-10 | 39 | Gas CC | $40 | 000000 | 001111 | 111111 | 111000 |

**Cycling generators (3):** gen-5 (Coal), gen-7 (Gas CC), gen-10 (Gas CC)

| Generator | Startups | Shutdowns | Tech | Marginal Cost |
|-----------|----------|-----------|------|---------------|
| gen-5 | 0 | 1 | Coal | $25/MWh |
| gen-7 | 1 | 1 | Gas CC | $40/MWh |
| gen-10 | 1 | 1 | Gas CC | $40/MWh |

The two gas CC units (most expensive) cycle on for peak hours and off during low-load
hours, consistent with economic dispatch logic. Coal gen-5 shuts down near the end when
load decreases. Nuclear and hydro units remain committed for all 24 hours due to their
low marginal costs and high min-up times (24h for nuclear).

**System load profile:** 4,237 MW (valley, HR 4) to 6,254 MW (peak, HR 18).

**Objective value:** $1,734,875.29 (total 24h production + startup costs)

**Formulation:** `ThermalStandardUnitCommitment` (built-in). Includes binary on/off/start/stop
variables, ramp constraints, and minimum up/down time constraints. No custom assembly required.
Start and stop variables present: yes.

## Workarounds

- **What:** (1) Used `LinearCurve` instead of `QuadraticCurve` for generator costs.
  (2) Set `initialize_model=false` and called `JuMP.optimize!()` directly.
  (3) Extracted results from PSI internal containers via `PSI.get_variables()` instead
  of `OptimizationProblemResults`.
- **Why:** (1) HiGHS cannot solve mixed-integer QP (MIQP) problems. The initialization
  model (an internal dispatch solve) also fails with quadratic costs on HiGHS. (2) PSI's
  built-in initialization solve fails even with linear costs on this system configuration
  (the initialization OPF itself returns NO_SOLUTION from HiGHS). (3) Bypassing PSI's
  `solve!()` means its internal state tracking doesn't register the solve as successful,
  so `OptimizationProblemResults(model)` refuses to extract data.
- **Durability:** fragile — The workaround accesses PSI's internal `get_variables()` and
  `get_optimization_container()` methods, which are not part of the public API. The
  `initialize_model=false` flag is documented but the need to bypass `solve!()` and call
  `JuMP.optimize!()` directly is not. This approach could break on PSI version upgrades.
- **Grade impact:** The UC formulation itself (`ThermalStandardUnitCommitment`) is fully
  built-in and works correctly once the initialization issue is bypassed. The workaround
  is in the solve/extract workflow, not in the formulation. The fragile classification
  reflects the internal API access needed for result extraction.

## Timing

- **Wall-clock:** 0.797 s (second run, after JIT warm-up; includes build + solve)
- **Timing source:** measured
- **Peak memory:** 1253.6 MB (Julia process RSS)
- **MIP gap:** 0.57%
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a5_scuc.jl`

Key API pattern:
```julia
# Cost setup (linear only — HiGHS can't do MIQP)
set_operation_cost!(gen, ThermalGenerationCost(
    CostCurve(LinearCurve(c1)), no_load_cost, startup_cost, 0.0))

# UC template
template = ProblemTemplate(NetworkModel(DCPPowerModel; duals=[...]))
set_device_model!(template, ThermalStandard, ThermalStandardUnitCommitment)

# Build without initialization, solve via JuMP directly
model = DecisionModel(template, sys; optimizer=solver, initialize_model=false)
build!(model; output_dir=mktempdir())
oc = PSI.get_optimization_container(model)
jm = PSI.get_jump_model(oc)
JuMP.optimize!(jm)

# Extract commitment from PSI internal containers
psi_vars = PSI.get_variables(oc)
on_arr = psi_vars[on_key]  # DenseAxisArray{VariableRef, 2}
schedule = [Int(round(JuMP.value(on_arr[gname, t]))) for t in timesteps]
```

## Observations

- **solver-issues:** HiGHS cannot solve MIQP problems. The PSI initialization model uses the
  same solver as the main model, so quadratic costs cause initialization failure even though
  the UC itself is a MIP (binary commitment) + LP (dispatch). Linear costs work correctly.
- **api-friction:** PSI's initialization model is opaque — it constructs and solves an internal
  OPF to determine initial conditions, with no way to configure the initialization solver
  separately from the main solver. When initialization fails, the error message ("Model failed
  to initialize") gives no diagnostic detail about why.
- **api-friction:** Bypassing `solve!()` to use `JuMP.optimize!()` directly breaks PSI's
  result tracking. The `OptimizationProblemResults` constructor checks an internal run status
  flag that is only set by PSI's `solve!()`. This forces users to extract results through
  internal APIs.
- **workaround-needed:** The initialization + result extraction workaround is fragile. An
  alternative would be to use GLPK (which handles the initialization correctly) but GLPK
  is slower on large MIPs.
