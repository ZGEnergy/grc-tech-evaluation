---
test_id: F-8
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# F-8: Solver Dependency Assessment

## Method

Assessed whether all target use cases are functional on open-source solvers alone, based on evaluation results from other test dimensions.

## Solvers Tested

| Solver | Type | License | Use Cases |
|--------|------|---------|-----------|
| HiGHS | LP, QP, MIP | MIT | DC-OPF (LP), economic dispatch, unit commitment (MIP), quadratic costs (QP) |
| SCIP | MIP, MINLP | Apache-2.0 | Unit commitment (MIP), integer programming |
| Ipopt | NLP | EPL-2.0 | AC-OPF (nonlinear), nonlinear power flow |
| GLPK | LP, MIP | GPL-3.0 | LP problems only (fails on quadratic objectives) |

## Results by Use Case

| Use Case | Solver(s) That Work | Commercial Solver Required? |
|----------|--------------------|-----------------------------|
| DC-OPF (linear) | HiGHS, GLPK, SCIP | No |
| DC-OPF (quadratic costs) | HiGHS | No |
| Unit Commitment (MIP) | HiGHS, SCIP | No |
| Economic Dispatch | HiGHS | No |
| AC-OPF (nonlinear) | Ipopt | No |
| Multi-period simulation | HiGHS, SCIP | No |

## Findings

- **All target use cases work on open-source solvers.** No commercial solver (Gurobi, CPLEX, Mosek) is required.
- **HiGHS is the most versatile open-source solver**, handling LP, QP, and MIP problems. It is the recommended default.
- **GLPK has a limitation:** it cannot handle quadratic objective functions. This is a solver limitation, not a PowerSimulations limitation. GLPK also carries a GPL-3.0 license.
- **Ipopt is required for nonlinear (AC-OPF) formulations.** No other open-source NLP solver was tested, but Ipopt is well-established and widely used.
- **SCIP provides an alternative MIP solver** for unit commitment problems.

## Commercial Solver Compatibility

PowerSimulations.jl also supports commercial solvers (Gurobi, CPLEX, Mosek) via JuMP's solver abstraction layer. These may offer better performance on large-scale MIP problems but are not required for functionality.

## Assessment

All evaluated use cases are fully functional with open-source solvers. No commercial solver dependency exists. **Pass.**
