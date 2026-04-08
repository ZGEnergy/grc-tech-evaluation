---
tag: solver-issues
source_dimension: scalability
source_test: C-5
tool: powermodels
severity: high
timestamp: 2026-03-24T16:45:00Z
---

# Observation: Progressive Relaxation Ineffective for solve_ac_pf (0 Inequality Constraints)

## Finding

PowerModels' `solve_ac_pf` formulation contains 0 inequality constraints, making progressive thermal limit relaxation entirely ineffective. Relaxing branch rate_a limits by 10% or 20% does not change the NLP formulation because `solve_ac_pf` does not include thermal limits as constraints. The divergence on the 10k-bus network is driven by the power balance equality constraints (23,392 equalities), not thermal limits. Ipopt diverges with inf_du reaching 6.94e+22 by iteration 18, while MUMPS exhausts memory (icntl[13] increased from 1000 to 32000). [solver-specific: Ipopt/MUMPS divergence at 10k-bus scale]

## Context

C-5 tests progressive AC feasibility relaxation (0%, 10%, 20% thermal limit relaxation). The protocol assumes that thermal limits may cause ACPF convergence difficulties and that relaxing them could enable convergence. However, PowerModels' `solve_ac_pf` is a pure power balance feasibility problem with no thermal limit constraints. Ipopt reports 23,392 equality constraints and 0 inequality constraints. The same finding was observed in G-FNM-4 on the ~28,000-bus FNM case.

## Implications

The progressive relaxation protocol is structurally inapplicable to PowerModels' `solve_ac_pf`. The formulation would need to be changed (e.g., using `solve_ac_opf` with fixed generator dispatch and relaxed limits) to make thermal relaxation effective. This is a formulation architecture observation relevant to the Extensibility assessment: PowerModels' separation of power flow (feasibility) from optimal power flow (optimization) means that thermal limits only appear in the OPF formulation, not the PF formulation.
