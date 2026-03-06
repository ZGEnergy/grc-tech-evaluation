---
test_id: F-8
tool: powermodels
dimension: supply_chain
status: pass
timestamp: 2026-03-05
---

# F-8: Solver Dependency Assessment

## Finding

PowerModels.jl does not require any commercial solver. All four solvers in the evaluation environment (HiGHS, Ipopt, SCIP, GLPK) are open-source. PowerModels itself is solver-agnostic via JuMP/MathOptInterface. The only license concern is GLPK (GPL-3.0), which is optional and replaceable.

## Evidence

**Solvers in evaluation environment**:

| Solver | License | Type | Required? |

|--------|---------|------|-----------|

| HiGHS | MIT | LP/MIP | No (optional) |

| Ipopt | EPL-2.0 | NLP | No (optional, needed for AC-OPF) |

| SCIP | Apache-2.0 | MILP/MINLP | No (optional) |

| GLPK | GPL-3.0 | LP/MIP | No (optional) |

**Solver-agnostic architecture**: PowerModels uses JuMP.jl's solver abstraction (MathOptInterface). Any MOI-compatible solver can be used. The solver is passed as a parameter:

```julia
solve_dc_opf("case.m", HiGHS.Optimizer)  # or any MOI-compatible solver

```

**Minimum viable solver set**:
- DC-OPF: Any LP solver (HiGHS MIT is sufficient)
- AC-OPF: Ipopt (EPL-2.0) or any NLP solver
- OTS/TNEP: Any MILP solver (HiGHS MIT is sufficient)

**GLPK GPL-3.0 concern**: GLPK is GPL-3.0 licensed, meaning linking to it may trigger copyleft obligations. However, GLPK is entirely optional -- HiGHS (MIT) provides equivalent LP/MIP capability. Removing GLPK from the environment eliminates the GPL concern entirely.

**Commercial solver support**: PowerModels can also use commercial solvers (Gurobi, CPLEX, Mosek) via their JuMP wrappers, but none are required.

Source: Project.toml, JuMP.jl documentation, solver license files

## Implications

No commercial solver dependency exists. The solver-agnostic architecture is a significant supply chain strength -- if any solver becomes problematic, it can be swapped without changing PowerModels code. The GLPK GPL-3.0 issue is easily mitigated by removing it from the dependency set and using HiGHS (MIT) instead. For the recommended deployment configuration, GLPK should be excluded.
