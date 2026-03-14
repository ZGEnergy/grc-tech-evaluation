---
test_id: F-8
tool: pypsa
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: 10863706
---

# F-8: Solver Dependency

## Findings

### Solvers Tested

| Solver | Available | LP | MILP | QP | NLP | Open Source |
|--------|-----------|:--:|:----:|:--:|:---:|:----------:|
| HiGHS | Yes | Y | Y | Y | N | Yes (MIT) |
| GLPK | Yes | Y | Y | N | N | Yes (GPL) |
| SCIP | No* | Y | Y | Y | N | Yes (Apache 2.0) |
| Ipopt | N/A** | Y | N | Y | Y | Yes (EPL) |

*SCIP was listed in devcontainer configuration but not available via
linopy's solver detection (`AssertionError: Solver scip not installed`).
See observation doc-gaps-scalability-C-4. This is an environment
configuration issue, not a PyPSA limitation.

**Ipopt is used for AC power flow via PyPSA's internal Newton-Raphson
solver, not via linopy. PyPSA's NR solver uses scipy's sparse linear
algebra directly, so Ipopt is not in the OPF path. For AC OPF, PyPSA
uses an iterative LOPF+PF approach, not a direct NLP formulation.

### Available Solvers in Evaluation Environment

From `linopy.solvers.available_solvers`: `['highs', 'glpk']`

### Use Case Coverage with Open-Source Solvers

| Use Case | Solver | Status |
|----------|--------|--------|
| DCPF | scipy (direct) | Fully functional |
| ACPF | scipy NR (direct) | Fully functional |
| DC OPF (LP) | HiGHS | Fully functional |
| DC OPF (LP) | GLPK | Fully functional |
| SCUC (MILP) | HiGHS | Fully functional |
| SCUC (MILP) | GLPK | Functional (slower) |
| Multi-period OPF | HiGHS | Fully functional |
| SCOPF | HiGHS | Fully functional |
| Quadratic costs (QP) | HiGHS | Fully functional |

### Failures Without Commercial Solver

**None.** All evaluation test cases (Suites A, B, C) were completed
using open-source solvers only (HiGHS for LP/MILP/QP, GLPK as
secondary LP/MILP, scipy for direct linear solves).

HiGHS is PyPSA's default solver and is declared as a direct dependency
in `pyproject.toml`, ensuring it is always available when PyPSA is
installed. This eliminates the common pain point of needing to separately
install and configure a solver.

### Performance Notes

- HiGHS is the recommended solver for all PyPSA use cases and performed
  well across all test scales (39-bus to 10k-bus)
- GLPK is functional but slower on larger problems (observed in
  scalability tests C-3 and C-7)
- SCIP support exists in linopy but requires separate installation of
  PySCIPOpt bindings

## Recorded Metrics

- solvers_tested: HiGHS (available, MIT), GLPK (available, GPL)
- failures_without_commercial: 0
