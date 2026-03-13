# Observation: Ipopt ACPF Diverges at MEDIUM Scale (10k-bus)

**Tag:** solver-issues
**Dimension:** expressiveness
**Test:** A-4 (ac_feasibility_check), MEDIUM network
**Severity:** high

## Summary

Ipopt's interior-point solver cannot converge on the AC power flow problem for the 10,000-bus ACTIVSg10k network. Dual infeasibility grows catastrophically from flat start, reaching 9.90e+20 before the 300s CPU time limit fires (actual CPU: 2035s due to MUMPS reallocation loops). Both available PowerModels.jl ACPF solvers (NLsolve via `compute_ac_pf`, Ipopt via `solve_model(ACPPowerModel, build_pf)`) fail at MEDIUM scale.

## Evidence

### Ipopt divergence trajectory (A-4 MEDIUM):

| Iter | inf_pr | inf_du | Notes |
|------|--------|--------|-------|
| 0 | 7.01e+02 | 0.00e+00 | Initial point (flat start) |
| 5 | 2.60e+01 | 1.95e+04 | Early divergence in dual space |
| 10 | 1.93e+01 | 3.60e+10 | Exponential dual growth |
| 12 | 1.39e+02 | 6.88e+14 | Watchdog mode entered |
| 13 | 1.97e+02 | 6.97e+14 | Second watchdog iteration |
| 14 | 2.03e+04 | 9.90e+20 | MUMPS reallocated 4× (OOM), still diverging |

**Ipopt termination:** `EXIT: Maximum CPU time exceeded` at iter 14 after 2035.07s CPU / 2093.72s wall clock.

#### MUMPS memory escalation:

```

MUMPS returned INFO(1) = -9 and requires more memory, reallocating. Attempt 1 → icntl[13] 1000→2000
MUMPS returned INFO(1) = -9 and requires more memory, reallocating. Attempt 2 → icntl[13] 2000→4000
MUMPS returned INFO(1) = -9 and requires more memory, reallocating. Attempt 3 → icntl[13] 4000→8000
MUMPS returned INFO(1) = -9 and requires more memory, reallocating. Attempt 4 → icntl[13] 8000→16000

```

#### Context:
- Problem size: 23,874 variables, 23,392 equality constraints (AC power balance at each bus/branch)
- Jacobian nonzeros: 145,002
- Hessian nonzeros: 402,076
- The fixed-dispatch AC PF formulation (pmin=pmax=pg_dispatch) makes the NLP highly constrained — no reactive slack means Ipopt cannot find a feasible interior point

**A-2 MEDIUM result for comparison:** NLsolve also failed (both flat-start and DC warm-start attempts failed after 1261.51s total).

## Implications

PowerModels.jl has no ACPF solver capable of handling 10,000-bus networks within practical time budgets. This is a fundamental scalability limit of the tool's ACPF API:
- `compute_ac_pf`: NLsolve Newton-Raphson, fails within 21 minutes on 10k-bus (A-2 MEDIUM)
- `solve_model(ACPPowerModel, build_pf)`: Ipopt interior-point, fails within 36.6 minutes on 10k-bus (A-4 MEDIUM)

At SMALL scale (2k-bus), Ipopt AC OPF converges (used as proxy in A-4 SMALL). The MEDIUM-scale failure is likely attributable to the combination of (a) flat-start initialization very far from the solution manifold, (b) MUMPS linear solver memory limitations causing numerical breakdown, and (c) the fixed-dispatch constraint making the problem ill-conditioned.

**Possible mitigations not tested:** (1) DC warm-start for Ipopt ACPF (initialize angles from DCPF, keep vm=1.0); (2) solve unconstrained AC OPF first as a proxy for feasibility; (3) reduce the fixed-dispatch constraint (allow small tolerance in pmin/pmax). None of these are part of the standard PowerModels.jl API.
