# Observation: A-4 MEDIUM Blocked by A-2 MEDIUM ACPF Failure

**Tag:** cascaded-failure
**Dimension:** expressiveness
**Test:** A-4 (ac_feasibility_check), MEDIUM network
**Severity:** high

## Summary

A-4 MEDIUM (AC feasibility check) fails because no PowerModels.jl ACPF solver can converge on the 10,000-bus ACTIVSg10k network. This is a direct cascade from A-2 MEDIUM's failure. The DC OPF dispatch step (reproduced from A-3 MEDIUM) succeeds, but the subsequent ACPF step fails regardless of which solver is used.

## Failure Chain

| Test | Network | Status | Root Cause |
|------|---------|--------|------------|
| A-2 | MEDIUM | FAIL | `compute_ac_pf` (NLsolve) cannot converge on 10k-bus (1261.51s, both flat-start and DC warm-start) |
| A-4 | MEDIUM | FAIL | Both `compute_ac_pf` (NLsolve) and `solve_model(ACPPowerModel, build_pf)` (Ipopt) fail at 10k-bus |

**A-4 MEDIUM additional context:** A-4 attempted the alternative Ipopt path (not available at the time A-2 was run) and documented Ipopt's specific failure mode: catastrophic dual infeasibility growth (inf_du → 9.90e+20) with MUMPS memory exhaustion, taking 2035s CPU time before the timer fires. This provides more diagnostic detail than A-2 (which only recorded NLsolve Bool=false).

## What Would Be Needed

A PowerModels.jl-based AC feasibility check at MEDIUM scale would require:
1. A numerically robust ACPF initialization strategy (not flat start) — e.g., DC warm-start with voltage angle initialization
2. An iterative refinement approach — e.g., solve AC OPF first (letting dispatch float), then tighten bounds toward fixed dispatch
3. Solver settings tuned for the fixed-dispatch formulation — e.g., reduced mu_init, warm_start_init_point

None of these are first-class operations in the PowerModels.jl API. They require JuMP-level manipulation of the model before calling `optimize_model!`.

## Grade Implications

The A-4 MEDIUM failure directly impacts the Expressiveness grade. For a tool to demonstrate AC feasibility check capability at MEDIUM scale, it must:
1. Run ACPF within the same model context as the DC OPF (workflow criterion — met)
2. Produce a converged ACPF solution (convergence criterion — not met)
3. Report voltage and thermal violations (output criterion — cannot be checked without convergence)

The workflow criterion is satisfied (no file I/O between steps). The convergence criterion fails due to solver limitations, not API design limitations. This is a solver scaling issue, not an expressiveness limitation per se, but it makes the test unpassable at MEDIUM scale.
