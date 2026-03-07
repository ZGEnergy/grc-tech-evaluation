---
test_id: F-8
tool: pypsa
dimension: supply_chain
slug: solver_dependency_assessment
network: N/A
protocol_version: v4
status: pass
workaround_class: null
timestamp: 2026-03-06T18:00:00Z
---

# F-8: Solver Dependency Assessment

## Summary

| Metric | Value |
|--------|-------|
| Optimization backend | Linopy 0.6.4 |
| Solvers supported (total) | 13 |
| Open-source solvers supported | HiGHS, GLPK, CBC, SCIP, Ipopt |
| Commercial solvers supported | Gurobi, CPLEX, Xpress, Knitro, Mosek, COPT, MindOpt |
| Other solvers | PIPS, cuPDLPx |
| Default solver installed | HiGHS 1.13.1 (via highspy) |
| Solver required for core functionality | Yes (optimization requires at least one) |

## Open-Source Solver Availability

### HiGHS (installed and tested)

- **Package:** highspy 1.13.1
- **License:** MIT
- **Status:** Installed by default as a PyPSA dependency. Fully functional.
- **Capabilities:** LP, MILP, QP. Covers all PyPSA optimization modes (DCOPF, unit commitment, SCOPF, multi-period investment).
- **Performance:** Production-quality solver. Competitive with commercial solvers for LP/MILP problems up to moderate scale.

### GLPK (not installed, installable)

- **System library:** libglpk40 is present in the devcontainer (installed via apt).
- **Python binding:** Not installed. Linopy reports GLPK as unavailable (`linopy.available_solvers` returns only `['highs']`).
- **Installability:** The `glpk-utils` package is not available in the container's apt sources, but the runtime library `libglpk40` is present. The Python `glpk` package fails to build from source. The `pyglpk` or `swiglpk` packages could provide the binding.
- **Capabilities:** LP, MILP. No QP support.
- **Note:** GLPK is significantly slower than HiGHS for large problems. Not recommended for production use.

### SCIP (not installed, installable)

- **Python binding:** `pyscipopt` 6.1.0 installs successfully via pip in the devcontainer.
- **Installability:** The Python package bundles the SCIP solver binaries. No separate system installation required.
- **Capabilities:** LP, MILP, MINLP. More capable than HiGHS for nonlinear problems.
- **License:** Apache-2.0 (since SCIP 8.0).

### Ipopt (not installed)

- **System package:** Not available in the devcontainer's apt sources (`coinor-libipopt` not found).
- **Installability:** Would require manual compilation or Conda installation. The `cyipopt` Python package provides bindings but requires the Ipopt C library.
- **Capabilities:** Nonlinear optimization (NLP). Not used by PyPSA's standard optimization modes (which are LP/MILP/QP only).
- **Relevance:** Low for PyPSA. PyPSA's optimization is exclusively LP/MILP/QP via Linopy. Ipopt would only be relevant if custom nonlinear constraints were added outside the standard framework.

### CBC (not tested)

- **Installability:** Available via `coinor-cbc` apt package or `cylp` Python package.
- **Capabilities:** LP, MILP. Open-source alternative to HiGHS.
- **Note:** Supported by Linopy but not tested in this evaluation.

## Commercial Solver Dependency Analysis

PyPSA does NOT require any commercial solver. All standard optimization modes work with HiGHS:

| PyPSA Operation | Problem Type | HiGHS Support |
|----------------|-------------|---------------|
| DCOPF / LOPF | LP | Yes |
| Unit Commitment | MILP | Yes |
| SCOPF | LP | Yes |
| Multi-period Investment | LP/MILP | Yes |
| Quadratic Costs | QP | Yes |
| MGA (Modeling to Generate Alternatives) | LP | Yes |
| Rolling Horizon | LP/MILP | Yes |

Commercial solvers (Gurobi, CPLEX) may provide better performance for very large problems (10,000+ buses with unit commitment), but are not required for correctness.

## Solver Selection Mechanism

Solver selection is straightforward:

```python
n.optimize(solver_name="highs")       # default
n.optimize(solver_name="glpk")        # if installed
n.optimize(solver_name="gurobi")      # if licensed
n.optimize(solver_name="scip")        # if pyscipopt installed
```

Solver-specific options are passed via `solver_options` dict.

## Assessment

**PASS** -- PyPSA operates fully on open-source solvers alone. HiGHS (MIT licensed) is installed by default and covers all optimization modes (LP, MILP, QP). No commercial solver is required for any standard use case. Additional open-source solvers (SCIP, GLPK, CBC) are supported and installable. Commercial solvers are optional performance upgrades, not functional requirements.
