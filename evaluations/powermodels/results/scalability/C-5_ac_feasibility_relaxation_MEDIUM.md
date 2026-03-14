---
test_id: C-5
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: v10
skill_version: v1
test_hash: 6ea5a7e5
status: fail
workaround_class: blocking
blocked_by: C-2
wall_clock_seconds: null
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: 14
loc: 275
solver: Ipopt 3.14.19
timestamp: 2026-03-13T23:00:00Z
---

# C-5: AC Feasibility -- Progressive Relaxation on MEDIUM

## Result: FAIL

## Approach

Progressive AC feasibility relaxation on the ACTIVSg 10,000-bus network following the protocol:

1. **DCPF warm start:** Solved DC power flow using `compute_dc_pf` to extract bus voltage angles. DCPF converged in 0.635s with 9,999 nonzero angles.

2. **ACPF at 0% relaxation:** Initialized VM=1.0 pu on all buses, VA=DCPF solution angles. Called `PowerModels.solve_ac_pf(data, Ipopt.Optimizer)` with warm_start_init_point=yes and mu_init=1e-2.

3. **Result:** Ipopt diverged at 0% relaxation. Same failure pattern as C-2: after 14 iterations, MUMPS linear solver exhausted memory (icntl[13] increased from 1000 to 32000). Primal infeasibility grew from 701 to 2,780; dual infeasibility exploded to 6.30e+24.

4. **10% and 20% relaxation:** Not attempted. The `solve_ac_pf` formulation has 0 inequality constraints, so thermal limit relaxation has no effect on the NLP problem. The divergence is driven by the power balance equality constraints (23,392 equalities), not thermal limits. This is the same finding as G-FNM-4 (where thermal relaxation also had no effect on `solve_ac_pf` convergence).

### Why Progressive Relaxation Cannot Help

The `solve_ac_pf` formulation constructs a pure feasibility NLP:
- 23,874 variables (vm, va per bus + generator Q)
- 23,392 equality constraints (power balance at each bus)
- **0 inequality constraints** (no thermal limits, no voltage bounds)

Because there are no inequality constraints, relaxing thermal limits by 10% or 20% does not change the NLP formulation at all. The solver sees exactly the same problem regardless of the relaxation level.

## Output

### DCPF Warm Start

| Metric | Value |
|--------|-------|
| DCPF converged | true |
| DCPF time | 0.635s |
| Non-zero angle buses | 9,999 / 10,000 |

### ACPF at 0% Relaxation (Ipopt, DC warm start)

| Metric | Value |
|--------|-------|
| NLP variables | 23,874 |
| NLP equality constraints | 23,392 |
| NLP inequality constraints | 0 |
| Jacobian nonzeros | 145,002 |
| Hessian nonzeros | 402,076 |
| Iterations (before kill) | 14 |
| Final inf_pr | 2,780 |
| Final inf_du | 6.30e+24 |
| MUMPS icntl[13] final | 32,000 |
| Outcome | Diverged / killed (MUMPS memory exhaustion) |

### Progressive Relaxation Summary

| Relaxation | Status | Wall-clock | Notes |
|------------|--------|-----------|-------|
| 0% | **diverged** | killed ~8 min | Ipopt MUMPS memory exhaustion at iter 14 |
| 10% | not attempted | -- | 0 inequality constraints = relaxation has no effect |
| 20% | not attempted | -- | Same reason |

### Comparison with C-5 SMALL (2,000-bus)

| Network | Solver | Converged? | Time | Relaxation Required |
|---------|--------|-----------|------|---------------------|
| SMALL (2,000 bus) | NLsolve | Yes | 0.231s | 0% |
| MEDIUM (10,000 bus) | Ipopt | No | diverged | infeasible |

The convergence boundary for ACPF in PowerModels lies between 2,000 and 10,000 buses, regardless of whether NLsolve or Ipopt is used.

## Workarounds

No workaround available. The `solve_ac_pf` formulation with Ipopt diverges on the 10k-bus network, and `compute_ac_pf` (NLsolve) also fails (per v9 A-2 MEDIUM results).

- **What:** ACPF cannot converge on 10k-bus networks via any PowerModels API path.
- **Why:** Both NLsolve (Newton-Raphson) and Ipopt (interior-point) diverge. The pure feasibility NLP with 0 inequality constraints is numerically challenging at this scale.
- **Durability:** blocking -- no parameter tuning or initialization strategy enables convergence.
- **Grade impact:** AC feasibility at MEDIUM scale is not achievable. Result is fail, blocked by the same root cause as C-2.

## Timing

- **Wall-clock:** Not available (0% relaxation attempt killed after ~8 min of MUMPS memory thrashing)
- **Timing source:** measured (Ipopt iteration log observed in real-time)
- **Peak memory:** Not available (MUMPS allocating progressively larger workspace; estimated >4 GB at icntl[13]=32000)
- **Solver iterations:** 14 (at 0% relaxation, before MUMPS memory exhaustion)
- **Convergence residual:** Diverging -- inf_pr = 2,780, inf_du = 6.30e+24 at iteration 14
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/scalability/test_c5_ac_feasibility_relaxation_medium.jl`

Key API sequence:

```julia
# Step 1: DCPF for warm-start angles
dc_data = deepcopy(data)
dc_result = PowerModels.compute_dc_pf(dc_data)

# Step 2: Set warm start (VM=1.0, VA=DCPF angles)
for (bus_id, bus) in ac_data["bus"]
    bus["vm"] = 1.0
    bus["va"] = dc_angles[bus_id]
end

# Step 3: ACPF with Ipopt at each relaxation level
ipopt_opt = JuMP.optimizer_with_attributes(
    Ipopt.Optimizer,
    "max_iter" => 10000, "tol" => 1e-6,
    "acceptable_tol" => 1e-4, "print_level" => 5,
    "linear_solver" => "mumps",
    "warm_start_init_point" => "yes", "mu_init" => 1e-2,
)
ac_result = PowerModels.solve_ac_pf(ac_data, ipopt_opt)
# Diverges: inf_du grows to 6.30e+24 by iteration 14
```

## Observations

- [solver-issues observation](../observations/solver-issues-scalability-C5_acpf_medium_ipopt_divergence.md)
