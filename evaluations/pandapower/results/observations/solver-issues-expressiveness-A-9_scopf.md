---
tag: solver-issues
source_dimension: expressiveness
source_test: A-9
tool: pandapower
severity: medium
timestamp: 2026-03-06T00:00:00Z
---

# Observation: PYPOWER interior point is the only native OPF solver; no MILP/LP solver swap

## Finding

pandapower's native OPF (`rundcopp`, `runopp`) uses only the PYPOWER interior point solver. There is no mechanism to swap in HiGHS, SCIP, GLPK, or any external solver for the native OPF. This prevents SCOPF (which needs custom constraint injection), SCUC (which needs MILP), and limits solver benchmarking.

## Context

Tests A-5, A-9, A-10, and A-11 all encountered the single-solver constraint. The PYPOWER interior point solver is a continuous NLP solver -- it cannot handle binary variables (SCUC) or easily accept custom linear constraints (SCOPF). The PowerModels.jl bridge would support external solvers but requires Julia integration and is a separate system.

## Implications

For scalability evaluation (C-7 solver swap), pandapower cannot swap solvers for its native OPF. For extensibility, the hard-coded solver limits what formulations can be expressed. This is a recurring architectural limitation across multiple expressiveness tests.
