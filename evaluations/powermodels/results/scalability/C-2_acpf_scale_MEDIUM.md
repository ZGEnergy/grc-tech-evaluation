---
test_id: C-2
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: v10
skill_version: v1
test_hash: 46f6d3db
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: null
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: 14
loc: 205
solver: Ipopt 3.14.19
timestamp: 2026-03-13T23:00:00Z
---

# C-2: ACPF Scale MEDIUM

## Result: FAIL

## Approach

Per v10 protocol, this test uses Ipopt (rather than the v9 NLsolve approach which also failed). Two initialization strategies were attempted:

1. **Flat start with Ipopt (vm=1.0 pu, va=0.0 rad):** Ipopt diverged rapidly. After 14 iterations, MUMPS linear solver exhausted memory (icntl[13] increased from 1000 to 32000). Primal infeasibility grew from 701 to 1.86e+04; dual infeasibility exploded from 0 to 7.58e+23. The solver became unresponsive during the 14th restoration phase (MUMPS trying to allocate ~32GB workspace). Process was killed after several minutes of no progress.

2. **DC warm-start with Ipopt:** Not reached because flat start consumed the process before completing. Based on the C-5 MEDIUM test (which used DC warm-start angles + mu_init=1e-2), the same divergence pattern occurs: Ipopt reaches 12-14 iterations before MUMPS memory exhaustion, with dual infeasibility exceeding 1e+22.

### Why Both Solvers Fail

The `solve_ac_pf` formulation in PowerModels constructs a pure feasibility NLP with 23,874 variables, 23,392 equality constraints, and 0 inequality constraints. This is a challenging problem structure for interior-point methods:

- **No inequality constraints** means no barrier terms guide the solver toward a feasible interior point
- **Large initial mismatch** (inf_pr = 701 at iteration 0) from the flat start
- **MUMPS memory growth** indicates the Jacobian/Hessian factorization requires progressively larger workspace as the solver explores increasingly distant points during divergence
- **23,874 variables** (2x bus count: vm + va per bus, plus generator q per gen) produce a dense enough Hessian to trigger MUMPS workspace exhaustion

### Comparison with v9 (NLsolve)

| Solver | Flat Start Time | DC Warm-Start Time | Converged? |
|--------|----------------|-------------------|------------|
| NLsolve (v9) | 581.85s | 621.57s | No |
| Ipopt (v10) | killed at iter 14 (~5 min) | not reached | No |

Ipopt fails faster (memory exhaustion at ~5 min vs NLsolve's 10+ min per attempt) but with the same outcome: no convergence.

## Output

### Ipopt Flat Start (aborted)

| Metric | Value |
|--------|-------|
| Buses | 10,000 |
| Branches | 12,706 |
| Generators | 2,485 |
| NLP variables | 23,874 |
| NLP equality constraints | 23,392 |
| NLP inequality constraints | 0 |
| Jacobian nonzeros | 145,002 |
| Hessian nonzeros | 402,076 |
| Iterations completed | 14 |
| Final inf_pr | 1.86e+04 |
| Final inf_du | 7.58e+23 |
| MUMPS icntl[13] final | 32,000 |
| Outcome | Diverged / killed (memory exhaustion) |

## Workarounds

No workaround available. Both `compute_ac_pf` (NLsolve) and `solve_ac_pf` (Ipopt) fail to converge ACPF on the 10,000-bus ACTIVSg network. The `solve_ac_opf` path uses Ipopt but optimizes generation dispatch (AC OPF) rather than solving a fixed-dispatch AC power flow.

- **What:** Neither ACPF solver path converges at MEDIUM scale.
- **Why:** NLsolve lacks convergence features for large-scale AC power flow. Ipopt's interior-point method diverges on the unconstrained feasibility formulation (0 inequality constraints) with MUMPS memory exhaustion.
- **Durability:** blocking -- no API path exists to solve ACPF on 10k-bus networks in PowerModels.
- **Grade impact:** ACPF scalability is capped at fail. PowerModels can solve ACPF on SMALL (2,000 buses, per C-5 SMALL) but not MEDIUM (10,000 buses).

## Timing

- **Wall-clock:** Not available (flat start killed after ~5 min of no solver progress; DC warm start not reached)
- **Timing source:** measured (Ipopt iteration log observed in real-time)
- **Peak memory:** Not available (process killed during MUMPS allocation)
- **Solver iterations:** 14 (flat start, before MUMPS memory exhaustion)
- **Convergence residual:** Diverging -- inf_pr = 1.86e+04, inf_du = 7.58e+23 at iteration 14
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/scalability/test_c2_acpf_scale_medium.jl`

Key API calls:

```julia
# Ipopt optimizer with convergence-protocol settings
ipopt_opt = JuMP.optimizer_with_attributes(
    Ipopt.Optimizer,
    "max_iter" => 10000,
    "tol" => 1e-6,
    "acceptable_tol" => 1e-4,
    "print_level" => 5,
    "linear_solver" => "mumps",
)

# Flat start
for (_, bus) in data_flat["bus"]
    bus["vm"] = 1.0
    bus["va"] = 0.0
end
result_flat = PowerModels.solve_ac_pf(data_flat, ipopt_opt)
# Diverges: inf_du grows to 7.58e+23 by iteration 14, MUMPS memory exhaustion
```

## Observations

- [solver-issues observation](../observations/solver-issues-scalability-C2_acpf_medium_ipopt_divergence.md)
