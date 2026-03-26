---
tag: solver-issues
source_dimension: scalability
source_test: C-2
tool: powermodels
severity: high
timestamp: 2026-03-24T20:50:00Z
---

# Observation: Ipopt Also Fails on 10k-Bus ACPF (Confirmed Across v10 and v11)

## Finding

PowerModels' `solve_ac_pf(data, Ipopt.Optimizer)` -- the optimizer-backed ACPF path -- fails to converge on the ACTIVSg 10,000-bus network. Ipopt diverges within 14 iterations with MUMPS memory exhaustion (icntl[13] growing from 1000 to 32000) and dual infeasibility reaching 7.58e+23. This was confirmed in v11 re-run (2026-03-24), producing the exact same numerical trajectory as the v10 run. `compute_ac_pf` (NLsolve) also fails (~580-620s per attempt, documented in v10). No PowerModels ACPF path works at MEDIUM scale.

## Context

The v9 evaluation used `compute_ac_pf` (NLsolve Newton-Raphson) which failed after ~21 minutes across flat-start and DC warm-start attempts. The v10 protocol directed testing with Ipopt as an alternative. The v11 protocol confirmed both paths. The `solve_ac_pf` function formulates ACPF as a pure feasibility NLP with 23,874 variables, 23,392 equality constraints, and 0 inequality constraints. This problem structure -- large equality-only NLP without barrier terms from inequality constraints -- is numerically challenging for interior-point methods. [solver-specific: Ipopt/MUMPS memory management on equality-only NLP]

## Implications

Both solver backends (NLsolve and Ipopt) fail on 10k-bus ACPF. PowerModels' ACPF capability is bounded at approximately 2,000 buses (SMALL tier converges in 0.231s). This affects any test that depends on ACPF at MEDIUM scale (C-2, C-5 MEDIUM). The root cause is architectural: PowerModels' `solve_ac_pf` formulation as a pure feasibility NLP without inequality constraints creates a challenging problem structure that both solvers fail on at scale.
