---
test_id: C-3
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v11"
skill_version: "v2"
test_hash: "bac66bc2"
status: partial_pass
workaround_class: fragile
blocked_by: null
wall_clock_seconds: 23.836
wall_clock_per_solver:
  highs_seconds: 23.836
  glpk_seconds: 79.905
timing_source: measured
peak_memory_mb: 1716.0
loc: 409
solver: HiGHS, GLPK
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: "2026-03-24T00:00:00Z"
---

# C-3: DC OPF on MEDIUM with HiGHS and GLPK

## Result: PARTIAL PASS

## Approach

Built a single-period DC OPF on the ACTIVSg 10000-bus network using `DecisionModel` with
`DCPPowerModel` and `ThermalDispatchNoMin` formulation. Solved with HiGHS (single-threaded)
and GLPK sequentially. Five workarounds were required to achieve feasibility at 10K scale
(same pattern as prior evaluation, all using documented public API in non-obvious ways
or addressing tool limitations at this scale).

1. **initialize_model=false + JuMP.optimize!():** PSI initialization bypass.
2. **Linear cost override:** Replaced MATPOWER quadratic cost curves with linear costs by
   quartile ($10-55/MWh). Required because GLPK does not support QP objectives.
3. **Generator availability override:** Set all thermal (1136) and renewable (634) generators
   to `available=true`. ACTIVSg10k marks 210 thermal + 153 renewable as unavailable, creating
   an 11 GW deficit since HydroDispatch (715 units, 45.5 GW) cannot be modeled.
4. **StaticBranchUnbounded:** Replaced `StaticBranch` with `StaticBranchUnbounded` for all
   branch types. Branch flow limit constraints cause numerical infeasibility at 10K scale
   (basis matrix condition number > 10^15) [tool-specific].
5. **HydroDispatch omitted:** PSI v0.30.2 has no exported formulation for `HydroDispatch`
   in OPF templates [tool-specific].

## Output

### HiGHS Results

| Metric | Value |
|--------|-------|
| Termination status | OPTIMAL |
| Wall-clock (build+solve) | 23.8 s |
| Objective value | $3,659,662.46 |
| Peak memory (RSS) | 1,360 MB |
| Variables | 24,476 |
| Constraints | 41,370 |

### GLPK Results

| Metric | Value |
|--------|-------|
| Termination status | OPTIMAL |
| Wall-clock (build+solve) | 79.9 s |
| Objective value | $3,659,662.46 |
| Peak memory (RSS) | 1,716 MB |
| Variables | 24,476 |
| Constraints | 41,370 |

### Objective Consistency

| Solver | Objective ($) | Difference |
|--------|---------------|------------|
| HiGHS | 3,659,662.46 | baseline |
| GLPK | 3,659,662.46 | 0.0000% |

Objectives are consistent to machine precision across both solvers, confirming the LP
formulation is identical and solver-agnostic.

### LMP Note

LMP extraction from duals is not attempted with `StaticBranchUnbounded` -- the unbounded
branch formulation produces no congestion since branch flow limits are not enforced. Per
the cross-tool watchpoint, LMPs would be uniform on ACTIVSg10k regardless (no binding
branch constraints at ~84% max loading).

## Workarounds

- **What:** (1) `initialize_model=false` + `JuMP.optimize!()`. (2) Linear cost override by
  quartile. (3) All generators set available. (4) `StaticBranchUnbounded` instead of
  `StaticBranch`. (5) HydroDispatch omitted.
- **Why:** (1) PSI initialization routine fails at scale [tool-specific]. (2) GLPK cannot
  handle QP [solver-specific: GLPK LP-only]. (3) MATPOWER unavailability flags create 11 GW
  deficit without hydro [tool-specific: no hydro formulation]. (4) Branch flow limit
  constraints cause numerical infeasibility at 10K (basis matrix cond > 10^15) [tool-specific].
  (5) No hydro dispatch formulation in PSI v0.30.2 [tool-specific].
- **Durability:** fragile -- Five stacked workarounds. Items (1), (4), and (5) depend on
  internal PSI behavior and architectural limitations rather than documented usage patterns.
  Loss of branch flow limits means the OPF does not enforce thermal ratings, yielding a
  relaxed (unbounded flow) solution. The cascaded workaround pattern indicates scaling
  limitations in the PSI/MATPOWER interface at 10K bus scale.
- **Grade impact:** Both solvers produce optimal solutions with identical objectives. The
  DCOPF formulation works at 10K scale but requires significant scaffolding. Without branch
  flow limits, the solution is a network-constrained economic dispatch (DC power balance
  enforced, no congestion enforcement).

## Timing

- **Wall-clock (HiGHS, build+solve):** 23.8 s (after JIT warm-up)
- **Wall-clock (GLPK, build+solve):** 79.9 s (after JIT warm-up)
- **Timing source:** measured
- **Peak memory:** 1,716 MB (process RSS after both solves)
- **CPU threads used:** 1 (HiGHS configured single-threaded)
- **CPU threads available:** 32

## Test Script

**Path:** `evaluations/powersimulations/tests/scalability/test_c3_dcopf_scale.jl`

Key patterns:
```julia
# All generators must be available (10K has 11 GW deficit without hydro)
for gen in get_components(ThermalStandard, sys)
    set_available!(gen, true)
end

# StaticBranchUnbounded required at 10K scale
set_device_model!(template, Line, StaticBranchUnbounded)

# PSI initialization bypass
model = DecisionModel(template, sys; optimizer=solver, initialize_model=false)
build!(model; output_dir=mktempdir())
oc = PSI.get_optimization_container(model)
jm = PSI.get_jump_model(oc)
JuMP.optimize!(jm)
```

## Observations

- **solver-issues:** Branch flow limit constraints (`StaticBranch`) cause numerical
  infeasibility on ACTIVSg10k across tested solvers (HiGHS, GLPK). The per-unit branch
  constraint formulation produces badly conditioned constraints at 10K bus scale
  [tool-specific: PSI/PowerModels constraint formulation].
- **cascaded-failure:** The 10K DCOPF requires 5 stacked workarounds to achieve feasibility.
  Each addresses a different limitation: PSI initialization, cost curve format, generator
  availability, branch constraint numerics, and hydro formulation gap [tool-specific].
- **api-friction:** HydroDispatch (715 generators, 45.5 GW in ACTIVSg10k) cannot be modeled
  in any OPF formulation in PSI v0.30.2 [tool-specific]. This forces generator availability
  overrides and fundamentally changes the optimization problem.
