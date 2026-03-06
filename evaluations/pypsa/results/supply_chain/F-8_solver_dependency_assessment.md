---
test_id: F-8
tool: pypsa
dimension: supply_chain
status: pass
timestamp: 2026-03-05
---

# F-8: Solver Dependency Assessment (Open-Source Solver Sufficiency)

## Finding

PyPSA works out-of-the-box with HiGHS, an open-source LP/MIP/QP solver bundled via the highspy package. No commercial solver is required for full functionality.

## Evidence

Default solver: **HiGHS**

- License: MIT
- Capabilities: LP, MIP, QP
- Distribution: Bundled in `highspy` wheel (no separate install)
- Performance: Competitive with commercial solvers for LP; adequate for MIP
- Source: <https://github.com/ERGO-Code/HiGHS>
- Maintained by: ERGO-Code group at University of Edinburgh

**Solver selection in PyPSA:**
- `n.optimize(solver_name="highs")` -- default when highspy is installed
- linopy routes to the appropriate solver backend
- No solver configuration file or external setup needed

**Alternative open-source solvers supported by linopy:**
- **GLPK:** LP/MIP (GPL-3.0) -- available via `swiglpk` or system package
- **SCIP:** LP/MIP/MINLP (Apache-2.0) -- available via `pyscipopt`
- **Ipopt:** NLP (EPL-2.0) -- for nonlinear problems
- **CBC:** LP/MIP (EPL-2.0) -- via `cylp`

**Commercial solvers also supported (not required):**
- Gurobi, CPLEX, MOSEK, XPRESS -- via their respective Python APIs

**HiGHS sufficiency for typical PyPSA workloads:**
- Linear OPF: HiGHS handles LP problems efficiently
- Unit commitment (MILP): HiGHS MIP solver is functional; may be slower than Gurobi for very large instances but adequate for most planning studies
- Network expansion (MILP): Same as above
- Quadratic costs: HiGHS supports QP

**Note:** The evaluation lock file previously included `pyscipopt` and `swiglpk` but they were uninstalled during `uv sync` (they were likely optional extras that were removed from the resolved set).

## Implications

HiGHS provides a fully open-source, MIT-licensed solver that is sufficient for all standard PyPSA optimization formulations. No commercial solver license is needed. This is a significant advantage for government/air-gapped deployments. The MIT license of HiGHS avoids any copyleft concerns (unlike GLPK which is GPL-3.0).
