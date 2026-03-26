---
test_id: F-8
tool: gridcal
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
protocol_version: "v11"
skill_version: v2
test_hash: "29bce75b"
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T18:00:00Z"
---

# F-8: Solver Dependency

## Result: PASS

## Finding

VeraGridEngine uses open-source solvers exclusively for all target use cases. HiGHS (MIT license) is bundled as a direct dependency via `highspy`. PuLP provides the solver abstraction layer with access to CBC (bundled with PuLP) and GLPK (system package). The AC OPF uses a custom interior-point solver implemented in pure Python, avoiding any external NLP solver dependency. No proprietary solver is required for any functionality.

**JLL binary artifact audit:** Not applicable. VeraGridEngine is a Python package; no Julia JLL solver packages are in the dependency tree.

## Evidence

**Solver availability (devcontainer, veragridengine 5.6.28):**

| Solver | Available | License | How Provided | Used For |
|--------|-----------|---------|-------------|----------|
| HiGHS | Yes | MIT | Direct dependency (`highspy>=1.8.0`) | LP, MILP, QP (default) |
| CBC | Yes | EPL-1.0 | Bundled with PuLP (`PULP_CBC_CMD`) | LP, MILP fallback |
| GLPK | Yes | GPL-3.0 | System package (`GLPK_CMD`) | LP, MILP alternative |
| SCIP | No | Apache-2.0 (v8.0.3+) | Not installed; available via `pyscipopt` | MILP alternative |
| Ipopt | No | EPL-2.0 | Not installed; not used by VeraGridEngine | NLP (not needed) |
| Gurobi | No | Commercial | Optional via PuLP | LP, MILP, QP |
| CPLEX | No | Commercial | Optional via PuLP | LP, MILP, QP |

**PuLP solver framework:**
- PuLP 3.3.0 (MIT license) is the solver abstraction layer for all linear/mixed-integer optimization
- Available solver backends: `['GLPK_CMD', 'PULP_CBC_CMD', 'HiGHS']`
- Solver selection: `OptimalPowerFlowOptions(mip_solver=MIPSolvers.HIGHS)`
- 27 total backends registered in PuLP (including commercial)

**AC OPF solver:**
- VeraGridEngine uses a **custom interior-point solver** (IPS) for nonlinear OPF
- Implemented in pure Python with numba JIT: `Utils/NumericalMethods/ips.py`
- Does NOT depend on Ipopt or any external NLP solver
- Problem formulation with analytical Jacobians and Hessians in `Simulations/OPF/Formulations/ac_opf_problem.py`

**Power flow solvers (non-optimization):**
- Newton-Raphson, Gauss-Seidel, HELM, Fast Decoupled, Levenberg-Marquardt, etc. -- all implemented internally in pure Python with numba JIT
- Use `scipy.sparse.linalg.spsolve` (BSD) for sparse linear system solving
- No external solver dependency for any power flow algorithm

**Commercial solver support (optional, not required):**
- VeraGridEngine's `MIPSolvers` enum includes CPLEX, Gurobi, Xpress entries
- These are optional and only work if the commercial solver is independently installed
- All evaluation use cases (DCPF, DCOPF, SCUC, AC OPF) work with open-source solvers only

## Implications

The solver dependency profile is strongly favorable for open-source deployment. HiGHS (MIT) is the primary solver and is bundled -- no additional installation or license is needed. The custom AC OPF solver avoids the Ipopt dependency entirely, which is unusual among power systems tools and means AC OPF quality depends on VeraGridEngine's own IPS implementation rather than an established NLP solver. This is a trade-off: full inspectability and no external dependency, but less battle-tested than Ipopt for large-scale NLP. All target use cases (DCPF, DCOPF, SCUC, AC PF, AC OPF) are covered by open-source solvers with no commercial dependency.
