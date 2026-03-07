---
tag: solver-issues
dimension: expressiveness
tool: powermodels
tests: [A-5]
timestamp: "2026-03-06T00:00:00Z"
---

# Solver Issue: HiGHS Cannot Solve MIQP -- Forces Cost Linearization for SCUC

When attempting to use PowerModels' `build_mn_opf` (multi-network OPF) as a base for SCUC and adding binary commitment variables, the resulting problem becomes a Mixed-Integer Quadratic Program (MIQP) because case39.m generators have quadratic cost functions (model=2, polynomial costs).

HiGHS v1.13.1 explicitly rejects MIQP: `ERROR: Cannot solve MIQP problems with HiGHS`.

**Workaround:** Linearized the generator cost functions (kept only the linear coefficient, dropped the quadratic term). This changes the optimal solution but allows the problem to be solved as a MILP.

**Production alternative:** Use a MIQP-capable solver (Gurobi, CPLEX, SCIP) or implement piecewise-linear cost approximation. SCIP is included in the project dependencies and could handle MIQP, but the test specification requires HiGHS.

**Impact:** This is a solver limitation, not a PowerModels limitation. However, it interacts with PowerModels' design: since PowerModels stores costs as polynomials and its OPF formulations use them directly as quadratic objectives, users combining PowerModels OPF with integer variables must handle the MIQP incompatibility themselves.
