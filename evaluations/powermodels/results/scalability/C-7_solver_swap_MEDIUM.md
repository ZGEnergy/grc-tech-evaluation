---
test_id: C-7
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: qualified_pass
workaround_class: stable
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: "HiGHS, GLPK, SCIP, Ipopt"
timestamp: "2026-03-07T00:00:00Z"
---

# C-7: Solver Swap (MEDIUM, ACTIVSg 10k-bus DC OPF)

## Result: QUALIFIED PASS

PowerModels supports solver swapping via JuMP's `optimizer_with_attributes()`. All four
solvers (HiGHS, GLPK, SCIP, Ipopt) can be used with `solve_dc_opf`, but the ACTIVSg
10k-bus QP is challenging for some solvers.

## Solver Results

| Solver | Termination | Time (s) | Objective | Notes |
|--------|-------------|----------|-----------|-------|
| **Ipopt** | LOCALLY_SOLVED | 2.75 | 2,436,631.22 | QP-capable, reliable |
| **HiGHS** | TIME_LIMIT | 302.28 | 2,436,631.23 | QP feasible but not proven optimal in 300s |
| **GLPK** | OPTIMAL | 46.81 | 2,401,337.08 | LP only; linearized costs (ncost=2) |
| **SCIP** | OPTIMAL | 40.45 | 2,401,337.08 | LP only; linearized costs (ncost=2), no dual support |

HiGHS found a near-optimal feasible solution (matching Ipopt's objective to 0.01) but
could not prove optimality via QP ASM within the 300s time limit. The P-D objective
error was 8.77e-10.

GLPK and SCIP produce a different objective (2,401,337.08 vs 2,436,631.22) because
linearizing costs (removing the quadratic term) changes the dispatch order.

## Solver Swap Mechanism

Swapping solvers requires only changing the optimizer constructor:

```julia

# Each solver is a one-line change
result = PowerModels.solve_dc_opf(data, HiGHS.Optimizer)
result = PowerModels.solve_dc_opf(data, Ipopt.Optimizer)
result = PowerModels.solve_dc_opf(data, GLPK.Optimizer)  # needs linearized costs
result = PowerModels.solve_dc_opf(data, SCIP.Optimizer)  # needs linearized costs

```

No model reconstruction or reformulation is needed (except cost linearization for
LP-only solvers).

## Observations

1. **Ipopt is the most reliable** for 10k-bus DC OPF with quadratic costs. It solves
   as a QP using interior-point methods in 2.75s.

2. **HiGHS QP struggles at scale.** On 10k-bus, the QP solver hits the 300s time limit.
   HiGHS LP (with linearized costs) works well on both scales.

3. **LP-only solvers (GLPK, SCIP)** require a cost linearization workaround: removing
   the quadratic term and reducing `ncost` from 3 to 2. Setting `cost[1] = 0.0` while
   keeping `ncost = 3` is insufficient -- PowerModels still constructs a quadratic
   objective function that LP solvers reject.

4. **SCIP does not support dual extraction** via MOI `ConstraintDual`. Requesting duals
   in the PowerModels settings causes a `GetAttributeNotAllowed` error.

5. **Solver swapping is trivial** from the API perspective. The qualification is due to
   solver-specific limitations, not PowerModels API friction.

## Workarounds

1. **Cost linearization for LP solvers (stable):** Set `gen["cost"] = [gen["cost"][2], gen["cost"][3]]`
   and `gen["ncost"] = 2` to convert from quadratic to linear cost model. This changes
   the dispatch order but enables GLPK and SCIP.

## Test Script

Path: `evaluations/powermodels/tests/test_medium_c7_c10.jl`
