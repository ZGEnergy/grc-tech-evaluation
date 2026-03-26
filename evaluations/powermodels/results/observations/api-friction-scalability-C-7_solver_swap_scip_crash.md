---
tag: api-friction
source_dimension: scalability
source_test: C-7
tool: powermodels
severity: low
timestamp: 2026-03-24T22:00:00Z
---

# Observation: SCIP solver swap crashes on solution retrieval despite successful solve

## Finding

The JuMP/MOI solver abstraction makes solver swap a parameter-only change (no reformulation needed), but SCIP encounters a practical exception: InfrastructureModels v0.7.8 unconditionally attempts dual extraction during solution building, which crashes because SCIP.jl v0.11.6 does not support `ConstraintDual`. Users must implement a two-level API fallback (instantiate_model + optimize_model! with manual JuMP solution extraction) to use SCIP as a drop-in solver.

## API Friction Detail

The solver swap itself is clean -- one line change to `optimizer_with_attributes(SCIP.Optimizer, ...)`. However, the crash occurs in solution retrieval, not in problem formulation. This is a compatibility gap between SCIP.jl and InfrastructureModels, transparent to the user only after the solve has completed. The error message (`MathOptInterface.GetAttributeNotAllowed`) does not suggest the workaround path.

## Cross-Tool Context

All four tested solvers (HiGHS, GLPK, SCIP, Ipopt) produce identical objectives ($2,401,337.08/h) on the MEDIUM DCOPF problem. Three (HiGHS, GLPK, Ipopt) work transparently; SCIP requires the two-level API workaround. [solver-specific]
