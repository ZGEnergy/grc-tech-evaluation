# Observation: A-4 MEDIUM ACPF Cascaded Failure (Ipopt + MUMPS)

**Tag:** cascaded-failure
**Dimension:** expressiveness
**Test:** A-4 (ac_feasibility_check), MEDIUM network
**Severity:** high
**Related:** cascaded-failure-expressiveness-A4_blocked_by_A2_medium.md

## Summary

A-4 MEDIUM confirms the cascaded failure from A-2 MEDIUM with additional diagnostic detail from Ipopt. Both available ACPF backends in PowerModels.jl fail on the 10,000-bus ACTIVSg10k network. The Ipopt path (attempted as fallback after NLsolve failed in A-2) diverges catastrophically within 14 iterations and hits a CPU time limit of 2059.82s — over 6x the configured 300s `max_cpu_time`.

## Confirmed Run (2026-03-12)

The test script ran to completion with the following outcome:

| Stage | Status | Wall Clock |
|-------|--------|------------|
| DC OPF (HiGHS LP) | OPTIMAL, $2,401,337/h | 10.03s |
| Ipopt ACPF (`build_pf`, ACPPowerModel) | TIME_LIMIT (14 iters) | 2071.38s |
| Total | fail | 2084.33s |

## Ipopt Divergence Pattern

Ipopt entered numerical divergence from the very first iteration due to the
highly infeasible starting point (flat start, fixed-dispatch formulation, 10k-bus):

| Iter | inf_pr (primal) | inf_du (dual) | Notes |
|------|----------------|---------------|-------|
| 0 | 7.01e+02 | 0.00e+00 | Flat start |
| 5 | 2.60e+01 | 1.95e+04 | Decreasing primal, exploding dual |
| 10 | 1.93e+01 | 3.60e+10 | |
| 12 | 1.39e+02 | 6.88e+14 | Watchdog mode (w) |
| 13 | 1.97e+02 | 6.97e+14 | Watchdog mode (w) |
| 14 | 2.03e+04 | 9.90e+20 | MUMPS OOM × 4; icntl[13]: 1000→16000 |

**EXIT: Maximum CPU time exceeded** after 2059.82s (300s limit not respected during MUMPS reallocation loops).

## MUMPS Memory Pressure

During iteration 14, MUMPS returned INFO(1) = -9 (insufficient memory) four
consecutive times, doubling its work array allocation each attempt:

```

icntl[13]: 1000 → 2000 → 4000 → 8000 → 16000

```

This indicates the 402,076-nonzero Hessian factorization exceeded MUMPS's
initial memory estimates, suggesting the problem conditioning degrades severely
when dual infeasibility reaches 10^20 scale.

## Root Cause

The fixed-dispatch formulation (pmin = pmax = pg_dispatch) creates a highly
constrained NLP where generators have no reactive power flexibility for voltage
regulation. Starting from a flat voltage profile (all vm=1.0, va=0.0) on a
10,000-bus network, the initial constraint residual of 702 pu is too far from
the feasible manifold for Ipopt's interior-point method with MUMPS to handle
within practical time budgets.

## Cascaded Failure Chain

```

A-2 MEDIUM: compute_ac_pf (NLsolve) → FAIL (diverged, ~21 min)
    ↓
A-4 MEDIUM: solve_model(ACPPowerModel, build_pf) with Ipopt → FAIL (TIME_LIMIT, ~34 min)
    ↓
AC feasibility check at MEDIUM scale: BLOCKED (no viable ACPF backend)

```

## Impact

- A-4 MEDIUM expressiveness test: fail
- Voltage violations at MEDIUM scale: not determinable
- Thermal violations at MEDIUM scale: not determinable
- The workflow criterion (same model context, no file I/O) is satisfied by design;
  only the solver convergence criterion fails
