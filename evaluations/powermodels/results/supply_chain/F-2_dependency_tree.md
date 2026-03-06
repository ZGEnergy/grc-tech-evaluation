---
test_id: F-2
tool: powermodels
dimension: supply_chain
status: qualified_pass
timestamp: 2026-03-05
---

# F-2: Dependency Tree

## Finding

The evaluation environment has 6 direct dependencies and 114 total packages (108 transitive). Of these, 35 are JLL (binary wrapper) packages providing pre-compiled C/C++/Fortran libraries. The dependency count is moderate for a Julia optimization package but includes significant native code.

## Evidence

**Direct dependencies** (from `Project.toml`):

| Package | Version | Purpose |

|---------|---------|---------|

| PowerModels | 0.21.5 | Core power systems modeling |

| JuMP | 1.29.4 | Mathematical optimization modeling |

| HiGHS | 1.21.1 | LP/MIP solver (MIT) |

| Ipopt | 1.14.1 | Nonlinear solver (EPL-2.0) |

| GLPK | 1.2.1 | LP/MIP solver (GPL-3.0) |

| SCIP | 0.11.6 | Constraint integer programming solver (Apache-2.0) |

**Dependency breakdown** (from `julia --project=. -e 'Pkg.dependencies()'`):
- Direct: 6
- Transitive: 108
- Total: 114
- JLL (binary) packages: 35

**PowerModels.jl's own direct dependencies** (from its registered Project.toml, not the eval env):
- InfrastructureModels.jl (LANL, BSD)
- JuMP.jl (MPL-2.0)
- Memento.jl (logging)
- JSON (MIT)
- SparseArrays (stdlib)
- LinearAlgebra (stdlib)

The 4 solver packages (HiGHS, Ipopt, GLPK, SCIP) are our evaluation additions, not PowerModels requirements.

Source: `Pkg.status()` and `Pkg.dependencies()` in devcontainer

## Implications

114 total packages is a moderate dependency footprint. The 35 JLL packages mean a significant fraction of the runtime is pre-compiled native code (see F-4 for audit). PowerModels itself has a lean dependency set (6 direct deps); the bulk of the transitive tree comes from JuMP and the solver wrappers. The dependency count is typical for Julia optimization packages and not a red flag per se, but the JLL binary fraction warrants scrutiny.
