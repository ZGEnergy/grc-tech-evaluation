---
tag: solver-issues
source_dimension: expressiveness
source_test: A-3
tool: pandapower
severity: medium
timestamp: 2026-03-06T00:00:00Z
---

# Observation: pandapower OPF locked to PYPOWER interior point solver

## Finding

pandapower's native DC OPF (`rundcopp()`) and AC OPF (`runopp()`) use PYPOWER's built-in interior point solver exclusively. There is no API to swap in HiGHS, GLPK, or other external solvers without using the PowerModels.jl bridge (which requires Julia installation and additional setup).

## Context

During A-3 (DC OPF on TINY), the eval-config specified HiGHS/GLPK as target solvers. pandapower cannot use these solvers for its native OPF functions. The PYPOWER interior point solver converged on the TINY case but is known to have convergence problems on larger/more constrained networks.

## Implications

This is relevant to scalability (C-3, C-7) where solver swap and solver comparison are tested. pandapower will not be able to demonstrate solver flexibility unless the PowerModels.jl bridge is used, which introduces significant architectural complexity (Julia dependency, cross-language bridge). The PYPOWER interior point solver's known convergence weaknesses may also impact scalability results on MEDIUM networks.
