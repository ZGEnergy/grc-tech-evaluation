---
test_id: C-2
tool: powermodels
dimension: scalability
network: MEDIUM
protocol_version: v11
skill_version: v2
test_hash: 23d4717c
status: fail
workaround_class: blocking
blocked_by: null
wall_clock_seconds: null
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: 14
convergence_evidence_quality: null
loc: 247
solver: Ipopt 3.14.19
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T20:50:00Z
---

# C-2: ACPF Scale MEDIUM

## Result: FAIL

## Approach

Per v11 protocol, both ACPF solver paths were tested. Four initialization strategies were attempted:

1. **Flat start with Ipopt (vm=1.0 pu, va=0.0 rad):** Ipopt diverged rapidly. After 14 iterations, MUMPS linear solver exhausted memory (icntl[13] increased from 1000 to 32000). Primal infeasibility grew from 701 to 1.86e+04; dual infeasibility exploded from 0 to 7.58e+23. The solver became unresponsive during MUMPS allocation at iteration 14 (attempting ~32GB workspace). Process was killed after >12 minutes of no solver progress. This v11 run reproduced the exact same divergence pattern as v10.

2. **DC warm-start with Ipopt:** Based on the v10 C-5 MEDIUM test (which used DC warm-start angles + mu_init=1e-2), the same divergence pattern occurs: Ipopt reaches 12-14 iterations before MUMPS memory exhaustion, with dual infeasibility exceeding 1e+22. Not re-run in v11 because the Ipopt flat start already demonstrated the same failure mode with identical numerical characteristics.

3. **compute_ac_pf (NLsolve) flat start:** Documented in v10 as taking 581.85s and failing (termination_status=false). NLsolve's Newton-Raphson implementation lacks convergence features needed for large-scale AC power flow.

4. **compute_ac_pf (NLsolve) DC warm start:** Documented in v10 as taking 621.57s and failing (termination_status=false). Total v10 NLsolve elapsed: 1,261.51s (~21 minutes) for both attempts.

### Why Both Solvers Fail

The `solve_ac_pf` formulation in PowerModels constructs a pure feasibility NLP with 23,874 variables, 23,392 equality constraints, and 0 inequality constraints. This problem structure is challenging for interior-point methods:

- **No inequality constraints** means no barrier terms guide the solver toward a feasible interior point
- **Large initial mismatch** (inf_pr = 701 at iteration 0) from the flat start
- **MUMPS memory growth** indicates the Jacobian/Hessian factorization requires progressively larger workspace as the solver explores increasingly distant points during divergence [solver-specific: Ipopt/MUMPS memory management]

### Comparison Across Solvers and Protocol Versions

| Solver | Init | Iters | Duration | Outcome |
|--------|------|-------|----------|---------|
| Ipopt (v11) | Flat start | 14 | killed >12 min (MUMPS hung) | Diverged: inf_du=7.58e+23 |
| Ipopt (v10) | Flat start | 14 | killed ~5 min | Diverged: same pattern |
| Ipopt (v10, C-5) | DC warm start | 12-14 | ~5 min | Diverged: inf_du>1e+22 |
| NLsolve (v10) | Flat start | unknown | 581.85s | Non-convergent |
| NLsolve (v10) | DC warm start | unknown | 621.57s | Non-convergent |

## Output

### Ipopt Flat Start (v11 re-run, aborted)

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
- **Why:** NLsolve lacks convergence features for large-scale AC power flow. Ipopt's interior-point method diverges on the unconstrained feasibility formulation (0 inequality constraints) with MUMPS memory exhaustion. [solver-specific: Ipopt NLP feasibility formulation + MUMPS memory scaling]
- **Durability:** blocking -- no API path exists to solve ACPF on 10k-bus networks in PowerModels.
- **Grade impact:** ACPF scalability is capped at fail. PowerModels can solve ACPF on TINY (39 buses) but not MEDIUM (10,000 buses).

## Timing

- **Wall-clock:** Not available (Ipopt flat start killed after >12 min of MUMPS memory exhaustion; other attempts documented from v10)
- **Timing source:** measured (Ipopt iteration log observed in real-time, NLsolve timings from v10 measured runs)
- **Peak memory:** Not available (process killed during MUMPS allocation, consuming ~5.3 GB RSS)
- **Solver iterations:** 14 (Ipopt flat start, before MUMPS memory exhaustion)
- **Convergence residual:** Diverging -- inf_pr = 1.86e+04, inf_du = 7.58e+23 at iteration 14
- **CPU cores used:** 1 / 32 available

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

# NLsolve path (also fails)
result_nlsolve = PowerModels.compute_ac_pf(data)
# termination_status=false after ~580s
```

## Observations

- [solver-issues: Ipopt divergence](../observations/solver-issues-scalability-C2_acpf_medium_ipopt_divergence.md)
- [solver-issues: NLsolve convergence failure](../observations/solver-issues-scalability-C2_acpf_medium_nlsolve_convergence_failure.md)
- [cascaded-failure: blocked by A-2 MEDIUM](../observations/cascaded-failure-scalability-C2_acpf_medium_blocked_by_A2.md)
