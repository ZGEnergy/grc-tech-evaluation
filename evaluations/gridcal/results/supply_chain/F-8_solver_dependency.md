---
test_id: F-8
tool: gridcal
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
protocol_version: "v10"
skill_version: v1
test_hash: "6025d2ba"
timestamp: "2026-03-13T23:00:00Z"
---

# F-8: Solver Dependency

## Finding

VeraGridEngine uses open-source solvers exclusively for its optimization capabilities. HiGHS is bundled as a direct dependency. PuLP provides the solver abstraction layer with access to CBC (bundled with PuLP) and GLPK (available in the devcontainer). No proprietary solver is required. SCIP and Ipopt are not installed.

## Evidence

**Solver availability (devcontainer, veragridengine 5.6.28):**

| Solver | Available | How Provided | Used For |
|--------|-----------|-------------|----------|
| HiGHS | Yes | Direct dependency (`highspy>=1.8.0`) | LP, MILP, QP via PuLP |
| CBC | Yes | Bundled with PuLP (`PULP_CBC_CMD`) | LP, MILP fallback |
| GLPK | Yes | System package (`GLPK_CMD`) | LP, MILP alternative |
| SCIP | No | Not installed (available via `pyscipopt`) | MILP alternative |
| Ipopt | No | Not installed (available via `cyipopt`) | NLP (AC OPF) |
| Gurobi | No | Commercial license required | LP, MILP, QP |
| CPLEX | No | Commercial license required | LP, MILP, QP |

**PuLP solver framework:**
- PuLP is used as the solver abstraction layer for all linear/mixed-integer optimization
- Available solver backends reported by PuLP: `['GLPK_CMD', 'PULP_CBC_CMD', 'HiGHS']`
- All available solvers supported by PuLP: 27 backends including commercial (Gurobi, CPLEX, XPRESS, MOSEK, COPT)

**Solver selection in VeraGridEngine:**
- Default solver: HiGHS (configured via `MIPSolvers` enumeration)
- Selectable alternatives: SCIP, CPLEX, Gurobi, Xpress, CBC, GLPK, PDLP (via OR-Tools)
- Solver selection: `OptimalPowerFlowOptions(mip_solver=MIPSolvers.HiGHS)`

**AC OPF solver:**
- VeraGridEngine uses a custom interior-point solver (IPS) for nonlinear OPF
- Does NOT use Ipopt or any external NLP solver
- The IPS is implemented in pure Python with numba JIT acceleration
- Source: `Utils/NumericalMethods/ips.py`

**Power flow solvers (non-optimization):**
- Newton-Raphson, Gauss-Seidel, HELM, Fast Decoupled, etc. are all implemented internally
- Use scipy.sparse.linalg.spsolve for linear system solving
- No external solver dependency for power flow

## Implications

The solver dependency profile is favorable for open-source deployment. HiGHS (MIT licensed) is the primary solver and is bundled as a direct dependency — no additional installation or license is needed. The custom AC OPF solver avoids the Ipopt dependency entirely, though this means AC OPF quality depends on VeraGridEngine's own implementation rather than a well-established NLP solver. CBC and GLPK provide fallback options. Commercial solver support (Gurobi, CPLEX) is available via PuLP but not required.
