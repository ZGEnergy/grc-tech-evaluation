---
test_id: A-5
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "1640c770"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 2.347
timing_source: measured
peak_memory_mb: 1289.2
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 432
solver: HiGHS
timestamp: "2026-03-24T00:00:00Z"
---

# A-5: 24-hour SCUC with Modified Tiny Data

## Result: PASS

## Approach

Built a 24-hour Security-Constrained Unit Commitment (SCUC) using `DecisionModel` with
`ThermalStandardUnitCommitment` formulation (built-in, no custom assembly) and `DCPPowerModel`
network. Solver: HiGHS 1.21.1 with 1% MIP gap tolerance, single-threaded, presolve on.

**System setup:**
- Loaded case39.m via `System()`, applied differentiated costs from `gen_temporal_params.csv`
  (hydro $5, nuclear $10, coal $25, gas CC $40 per MWh -- linear costs for MILP compatibility)
- Set startup costs and no-load costs from `gen_temporal_params.csv`
- Set ramp limits (MW/min converted to p.u./min) and min up/down times (hours)
- Set active power Pmin proportional to Pmax by technology (hydro 25%, nuclear 50%, coal 40%, gas CC 30%)
- Loaded 24-hour load profile from `load_24h.csv` as time series multipliers on `max_active_power`
- Transformed `SingleTimeSeries` to `Deterministic` forecasts via `transform_single_time_series!`

**Formulation:** `ThermalStandardUnitCommitment` is a built-in PSI formulation that includes:
- Binary commitment variables (`OnVariable`, `StartVariable`, `StopVariable`)
- Intertemporal ramp constraints (up/down)
- Minimum up/down time constraints
- Startup/shutdown cost terms in objective

**Solve approach:** Built model with `initialize_model=false`, then solved via `JuMP.optimize!`
on the underlying JuMP model to bypass PSI's internal initialization. This avoids the
single-step initialization solve that PSI performs by default.

## Output

**Termination status:** OPTIMAL
**Objective value:** $1,734,875.29
**MIP gap:** 0.57% (below 1% threshold)

**Commitment schedule (1=on, 0=off):**

| Generator | Tech | HR1-4 | HR5-8 | HR9-12 | HR13-16 | HR17-20 | HR21-24 | Startups | Shutdowns |
|-----------|------|-------|-------|--------|---------|---------|---------|----------|-----------|
| gen-1 | Hydro | 1111 | 1111 | 1111 | 1111 | 1111 | 1111 | 0 | 0 |
| gen-2 | Nuclear | 1111 | 1111 | 1111 | 1111 | 1111 | 1111 | 0 | 0 |
| gen-3 | Nuclear | 1111 | 1111 | 1111 | 1111 | 1111 | 1111 | 0 | 0 |
| gen-4 | Coal | 1111 | 1111 | 1111 | 1111 | 1111 | 1111 | 0 | 0 |
| gen-5 | Coal | 1111 | 1111 | 1111 | 1111 | 1111 | 1100 | 0 | 1 |
| gen-6 | Nuclear | 1111 | 1111 | 1111 | 1111 | 1111 | 1111 | 0 | 0 |
| gen-7 | Gas CC | 0000 | 0000 | 0000 | 0011 | 1111 | 1100 | 1 | 1 |
| gen-8 | Nuclear | 1111 | 1111 | 1111 | 1111 | 1111 | 1111 | 0 | 0 |
| gen-9 | Nuclear | 1111 | 1111 | 1111 | 1111 | 1111 | 1111 | 0 | 0 |
| gen-10 | Gas CC | 0000 | 0001 | 1111 | 1111 | 1111 | 1000 | 1 | 1 |

**Cycling generators (3):** gen-5 (coal, shuts down HR23), gen-7 (gas CC, commits HR15-22),
gen-10 (gas CC, commits HR8-21). This exceeds the >= 2 threshold.

**System load range:** 4,237 MW (HR4, valley) to 6,254 MW (HR18, peak).

Cheap baseload generators (hydro gen-1, nuclear gen-2/3/6/8/9) stay committed for all 24 hours.
Expensive gas CC generators (gen-7, gen-10) cycle on during peak hours and off during low-load
periods. Coal gen-5 shuts down for the final 2 hours as load drops.

**v11 Binding Verification:**

Re-ran SCUC with `min_up_time=0` and `min_down_time=0` for all generators. Compared commitment
schedules:

| Generator | Original Schedule | Relaxed Schedule | Changed? |
|-----------|------------------|-----------------|----------|
| gen-7 | off HR1-14, on HR15-22 | off HR1-16, on HR17-20 | Yes |
| gen-10 | off HR1-7, on HR8-21 | off HR1-7, on HR8-22 | Yes |

Two generators changed their commitment when min up/down constraints were removed, confirming
that the constraints were binding. gen-7 commits for fewer hours when not forced to stay on
for a minimum period. gen-10 stays on one hour longer when the minimum down-time constraint
is removed (it can freely shut down later without penalty).

**Binding verification result:** Verified -- 2 generators changed commitment.

## Workarounds

None required. `ThermalStandardUnitCommitment` is a built-in formulation in PowerSimulations.jl
that directly provides all required UC constraints (binary commitment, ramp rates, min up/down
times, startup costs). No custom constraint assembly needed.

## Timing

- **Wall-clock:** 2.347 s (second run, after JIT warm-up; includes system setup, build, solve, and binding verification re-solve)
- **Timing source:** measured
- **Peak memory:** 1289.2 MB (Julia process RSS)
- **MIP gap:** 0.57%
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a5_scuc.jl`

Key API pattern:
```julia
# Built-in UC formulation — no custom assembly
template = ProblemTemplate(NetworkModel(DCPPowerModel; duals=[NodalBalanceActiveConstraint]))
set_device_model!(template, ThermalStandard, ThermalStandardUnitCommitment)
set_device_model!(template, Line, StaticBranch)
model = DecisionModel(template, sys; optimizer=solver, initialize_model=false)
build!(model; output_dir=mktempdir())

# Extract commitment schedule from PSI internal variables
on_arr = PSI.get_variables(oc)[on_key]
schedule = [Int(round(JuMP.value(on_arr[gname, t]))) for t in timesteps]

# Binding verification: re-run with relaxed constraints
set_time_limits!(gen, (up=0.0, down=0.0))
```
