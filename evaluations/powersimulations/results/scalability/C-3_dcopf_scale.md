---
test_id: C-3
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v10"
skill_version: "v1"
test_hash: "a3df9080"
status: qualified_pass
workaround_class: fragile
blocked_by: null
wall_clock_seconds: 11.303
wall_clock_per_solver:
  highs_seconds: 11.303
  glpk_seconds: 50.650
timing_source: measured
peak_memory_mb: 1526.1
loc: 398
solver: HiGHS, GLPK
timestamp: "2026-03-14T00:00:00Z"
---

# C-3: DC OPF on MEDIUM with HiGHS and GLPK

## Result: QUALIFIED PASS

## Approach

Built a single-period DC OPF on the ACTIVSg 10000-bus network using `DecisionModel` with
`DCPPowerModel` and `ThermalDispatchNoMin` formulation. Solved with HiGHS and GLPK.

Five workarounds were required to achieve feasibility at 10K scale:

1. **initialize_model=false + JuMP.optimize!():** Same initialization bypass as at SMALL scale.
2. **Linear cost override:** Replaced MATPOWER quadratic cost curves with linear costs by quartile
   ($10-55/MWh). Required because GLPK does not support quadratic objectives.
3. **Generator availability override:** Set all thermal (1136) and renewable (634) generators to
   `available=true`. ACTIVSg10k marks 210 thermal + 153 renewable generators as unavailable,
   creating an 11 GW generation deficit since HydroDispatch (715 units, 45.5 GW) cannot be
   modeled in PSI v0.30.2.
4. **StaticBranchUnbounded:** Replaced `StaticBranch` with `StaticBranchUnbounded` for all branch
   types. Branch flow limit constraints cause numerical infeasibility at 10K scale (basis matrix
   condition number > 10^15). This removes branch flow limits but preserves DC network topology.
5. **HydroDispatch omitted:** PSI v0.30.2 has no exported formulation for `HydroDispatch`
   (FixedOutput only supports ThermalGen/RenewableGen/ElectricLoad).

## Output

### HiGHS Results

| Metric | Value |
|--------|-------|
| Termination status | OPTIMAL |
| Wall-clock (build+solve) | 11.3 s |
| Objective value | $3,659,662 |
| Peak memory (RSS) | 1,404 MB |
| Variables | 24,476 |
| Constraints | 41,370 |

### GLPK Results

| Metric | Value |
|--------|-------|
| Termination status | OPTIMAL |
| Wall-clock (build+solve) | 50.7 s |
| Objective value | $3,659,662 |
| Peak memory (RSS) | 1,526 MB |
| Variables | 24,476 |
| Constraints | 41,370 |

### Objective Consistency

| Solver | Objective ($) | Difference |
|--------|---------------|------------|
| HiGHS | 3,659,662.46 | baseline |
| GLPK | 3,659,662.46 | 0.0000% |

Objectives are consistent to machine precision across both solvers, confirming the LP formulation
is identical and solver-agnostic.

### LMP Note

LMP extraction from duals was not successful with `StaticBranchUnbounded` — the dual structure
differs from `StaticBranch`. Per the cross-tool watchpoint, LMPs should be uniform on ACTIVSg10k
(no binding branch constraints at ~84% max loading), so this is not a material gap.

## Workarounds

- **What:** (1) `initialize_model=false` + `JuMP.optimize!()`. (2) Linear cost override.
  (3) All generators set available. (4) `StaticBranchUnbounded` instead of `StaticBranch`.
  (5) HydroDispatch omitted.
- **Why:** (1) PSI initialization fails at scale. (2) GLPK cannot handle QP. (3) MATPOWER
  unavailability flags create 11 GW deficit without hydro. (4) Branch flow limits cause
  numerical infeasibility (cond > 10^15). (5) No hydro formulation in PSI v0.30.2.
- **Durability:** fragile — Five workarounds stacked. Loss of branch flow limits means the
  OPF does not enforce thermal ratings, yielding a relaxed (unbounded flow) solution. The
  workaround-of-workarounds pattern suggests the PSI/MATPOWER interface has scaling limitations.
- **Grade impact:** Both solvers solve to optimality with consistent objectives. The DCOPF
  formulation works at 10K scale, but requires significant scaffolding. Without branch flow
  limits, the solution is equivalent to a network-constrained economic dispatch (DC power
  balance enforced, but no congestion).

## Timing

- **Wall-clock (HiGHS):** 11.3 s (build + solve, after JIT warm-up)
- **Wall-clock (GLPK):** 50.7 s (build + solve, after JIT warm-up)
- **Timing source:** measured
- **Peak memory:** 1,526 MB (process RSS after both solves)
- **CPU cores used:** 1 (32 available)

## Test Script

**Path:** `evaluations/powersimulations/tests/scalability/test_c3_dcopf_scale.jl`

Key differences from A-3 (TINY DCOPF):
```julia
# All generators must be available (10K has 11 GW deficit without hydro)
for gen in get_components(ThermalStandard, sys)
    set_available!(gen, true)
end

# StaticBranchUnbounded required at 10K scale
set_device_model!(template, Line, StaticBranchUnbounded)
set_device_model!(template, Transformer2W, StaticBranchUnbounded)
```

## Observations

- **solver-issues:** Branch flow limit constraints (`StaticBranch`) cause numerical infeasibility
  on ACTIVSg10k across all 4 tested solvers (HiGHS, GLPK, SCIP, Ipopt). The basis matrix
  condition number exceeds 10^15. This is a PSI/PowerModels scaling limitation — the per-unit
  branch constraint formulation produces badly conditioned constraints at 10K bus scale.
- **cascaded-failure:** The 10K DCOPF requires 5 stacked workarounds to achieve feasibility.
  Each addresses a different limitation: PSI initialization, cost curve format, generator
  availability, branch constraint numerics, and hydro formulation gap. This cascaded workaround
  pattern is a significant scalability concern.
- **api-friction:** HydroDispatch (715 generators, 45.5 GW in ACTIVSg10k) cannot be modeled
  in any OPF formulation in PSI v0.30.2. This forces generator availability overrides and
  fundamentally changes the optimization problem.
