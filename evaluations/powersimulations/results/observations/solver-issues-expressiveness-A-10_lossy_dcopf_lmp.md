---
tag: solver-issues
source_dimension: expressiveness
source_test: A-10
tool: powersimulations
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: DCPLLPowerModel requires quadratic constraint-capable solver

## Finding

PowerModels.jl's `DCPLLPowerModel` (DC OPF with linearized losses) uses quadratic constraints
that are incompatible with HiGHS (LP/MILP/QP only). The formulation exists but is unusable
with the open-source evaluation solver stack.

## Context

A-10 tests lossy DCOPF with LMP decomposition. The `DCPLLPowerModel` formulation was discovered
in PowerModels.jl but fails at build time when used with HiGHS because the linearized Ohm's
law constraint uses `ScalarQuadraticFunction-in-GreaterThan`, which HiGHS does not support.
A solver with SOCP or QCP support (e.g., Gurobi, CPLEX, Mosek) would be required.

## Implications

This is a mixed solver-tool limitation relevant to the Scalability audit (C-7 solver swap).
The formulation's solver requirements are undocumented, and there is no API to check solver
compatibility before building the model. A solver swap to a QCP-capable solver would likely
resolve this -- but no open-source QCP solver is in the evaluation stack.
