---
tag: cascaded-failure
source_dimension: scalability
source_test: C-5
tool: powermodels
severity: high
timestamp: 2026-03-13T23:00:00Z
---

# Observation: C-5 MEDIUM Blocked by C-2 ACPF Failure at 10k-Bus Scale

## Finding

C-5 (AC Feasibility Progressive Relaxation on MEDIUM) fails because the underlying ACPF solver cannot converge on the 10,000-bus network. This is the same root cause as C-2 (ACPF Scale MEDIUM): both `compute_ac_pf` (NLsolve) and `solve_ac_pf` (Ipopt) diverge on the ACTIVSg 10k network. Progressive thermal relaxation cannot help because `solve_ac_pf` has 0 inequality constraints.

## Context

C-5 MEDIUM depends on the ability to solve ACPF at MEDIUM scale. C-2 established that this capability does not exist in PowerModels. The DCPF warm-start step succeeds (0.635s, 9999 nonzero angles), confirming the DC power flow is functional at MEDIUM scale. The failure is specific to the AC power flow formulation.

## Implications

C-5 MEDIUM is a cascaded failure from C-2. The ACPF convergence boundary for PowerModels lies between SMALL (2,000 buses, converges in 0.231s) and MEDIUM (10,000 buses, diverges). Any test requiring ACPF at MEDIUM scale will fail.
