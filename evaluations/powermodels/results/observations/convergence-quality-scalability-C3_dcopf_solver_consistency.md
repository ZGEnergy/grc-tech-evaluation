---
tag: convergence-quality
source_dimension: scalability
source_test: C-3
tool: powermodels
severity: low
timestamp: 2026-03-13T23:00:00Z
---

# Observation: HiGHS and GLPK Produce Identical DCOPF Results on 10k-Bus Network

## Finding

Both HiGHS and GLPK converge to the same optimal objective ($2,401,337.08/h) on the ACTIVSg 10k-bus DCOPF, with objective difference of 3.19e-6 $/h (1.33e-10%). HiGHS completes in 3.91s (6,032 iterations) while GLPK takes 61.86s (50,193 iterations), a 16x performance difference. Both solvers converge in the v10 run, improving on v9 where GLPK hit the 300s time limit.

## Context

C-3 requires testing DC OPF with both HiGHS and GLPK and verifying objective consistency. The ACTIVSg10k network has no binding branch constraints, producing uniform LMPs ($20.064/MWh). The cost linearization workaround (dropping c2 for 1,130 generators) converts the QP to LP, enabling both solvers to converge.

## Implications

The solver swap interface in PowerModels (via JuMP/MathOptInterface) works cleanly at MEDIUM scale. Solver swap requires only a one-line optimizer change. This is relevant for the Extensibility assessment (C-7 solver swap test).
