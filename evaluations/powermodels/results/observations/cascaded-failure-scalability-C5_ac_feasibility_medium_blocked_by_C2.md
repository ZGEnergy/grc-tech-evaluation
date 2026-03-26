---
tag: cascaded-failure
source_dimension: scalability
source_test: C-5
tool: powermodels
severity: high
timestamp: 2026-03-24T16:45:00Z
---

# Observation: C-5 MEDIUM ACPF Diverges at 10k-Bus Scale (Same Root Cause as C-2)

## Finding

C-5 (AC Feasibility Progressive Relaxation on MEDIUM) records divergence because the underlying ACPF solver cannot converge on the 10,000-bus network. This is the same root cause as C-2 (ACPF Scale MEDIUM): both `compute_ac_pf` (NLsolve) and `solve_ac_pf` (Ipopt) diverge on the ACTIVSg 10k network. Progressive thermal relaxation cannot help because `solve_ac_pf` has 0 inequality constraints. Ipopt dual infeasibility explodes to 6.94e+22 by iteration 18, with MUMPS memory exhaustion (icntl[13] maxed at 32000). [solver-specific: Ipopt/MUMPS divergence]

## Context

C-5 MEDIUM depends on the ability to solve ACPF at MEDIUM scale. C-2 established that this capability does not exist in PowerModels. The DCPF warm-start step succeeds (0.4s, 9999 nonzero angles), confirming DC power flow is functional at MEDIUM scale. The failure is specific to the AC power flow NLP formulation at this network size.

## Implications

The ACPF convergence boundary for PowerModels lies between SMALL (2,000 buses, converges in 0.279s with NLsolve) and MEDIUM (10,000 buses, diverges with both Ipopt and NLsolve). Any test requiring ACPF at MEDIUM scale will produce a divergence finding. Under v11 protocol, C-5 is informational (diagnostic), so this is a recorded finding rather than a scored failure.
