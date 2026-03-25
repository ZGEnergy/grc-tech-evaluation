---
test_id: F-8
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v11
skill_version: v2
test_hash: be95fcde
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-24T14:00:00Z
---

# F-8: Solver Dependency Assessment

## Result: PASS

## Finding

PyPSA operates fully with open-source solvers. HiGHS (MIT) is a direct dependency and default solver, covering LP/MILP/QP. GLPK (GPL) is available as secondary. Ipopt (EPL) is available via pyomo for NLP. No commercial-only test cases were encountered across Suites A, B, and C. SCIP is not installed in the devcontainer (confirmed C-4 finding) but this is an environment issue, not a PyPSA limitation.

## Evidence

### Solver Availability (devcontainer, 2026-03-24)

Tested via `linopy.available_solvers` and direct import checks:

| Solver | Available | LP | MILP | QP | NLP | License | Detection Method |
|--------|-----------|:--:|:----:|:--:|:---:|---------|-----------------|
| HiGHS | Yes (v1.13.1) | Y | Y | Y | N | MIT | `linopy.available_solvers` + `import highspy` |
| GLPK | Yes (v5.0) | Y | Y | N | N | GPL-3.0 | `linopy.available_solvers` + `glpsol --version` |
| SCIP | No | Y | Y | Y | N | Apache 2.0 | `pyscipopt` not installed |
| Ipopt | Yes (via pyomo) | Y | N | Y | Y | EPL-2.0 | `pyo.SolverFactory('ipopt').available() == True` |

### Open-Source Solver Coverage

| Use Case | Solver Used | Status |
|----------|------------|--------|
| DCPF (`n.lpf()`) | scipy spsolve (direct) | Fully functional |
| ACPF (`n.pf()`) | scipy NR (direct) | Fully functional |
| DC OPF (LP) | HiGHS | Fully functional |
| DC OPF (LP) | GLPK | Fully functional |
| SCUC (MILP) | HiGHS | Fully functional |
| SCUC (MILP) | GLPK | Functional (slower) |
| Multi-period OPF | HiGHS | Fully functional |
| SCOPF | HiGHS | Fully functional |
| Quadratic costs (QP) | HiGHS | Fully functional |
| AC feasibility | Ipopt (via pyomo) | Functional |

### Commercial-Only Tests

**None.** All evaluation test cases across Suites A, B, and C were completed using open-source solvers only. No test required Gurobi, CPLEX, or any other commercial solver.

### SCIP Status

SCIP (PySCIPOpt) is not installed in the devcontainer. This was identified in C-4 findings. PyPSA/linopy supports SCIP when PySCIPOpt is installed, but it is not required. HiGHS covers all problem classes that SCIP would handle (LP, MILP, QP) and is the recommended default.

### HiGHS as Default Solver

HiGHS is declared as a direct dependency in PyPSA's `pyproject.toml` (`highspy`), meaning it is always available when PyPSA is installed. This eliminates the common pain point of needing to separately install and configure a solver. HiGHS performed well across all test scales (39-bus through 10k-bus).

## Implications

PyPSA's solver story is a supply chain strength. The bundled HiGHS solver covers LP/MILP/QP with a permissive MIT license. No commercial solver dependency exists for any tested capability. GLPK provides a secondary option for LP/MILP. The only gap is SCIP (not installed), which is an environment configuration issue, not a tool limitation.
