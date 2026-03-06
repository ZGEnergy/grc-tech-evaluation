# B-6: Code Architecture — Qualitative Assessment

- **Test ID:** B-6
- **Slug:** code_architecture
- **Tool:** PyPSA 1.1.2 + linopy 0.6.4
- **Status:** PASS (qualitative)

## Architecture Overview

PyPSA has a well-structured, layered architecture with clear separation of concerns. Five distinct layers are identifiable in the DCPF/OPF solve path:

### Abstraction Layers

| Layer | Module(s) | Lines | Responsibility |
|-------|-----------|-------|---------------|
| Data Model | `pypsa.Network` / `pypsa.network.*` | (subpackage) | Network components as pandas DataFrames. Static data in `n.buses`, `n.lines`, etc. Time-varying data in `n.buses_t`, `n.lines_t`, etc. |
| Power Flow Solver | `pypsa.network.power_flow` | 1862 | Direct DCPF (`lpf`) and ACPF (`pf`) solvers. DCPF uses sparse numpy linear algebra. ACPF uses Newton-Raphson iteration. |
| Optimization Formulation | `pypsa.optimization.variables` (323), `pypsa.optimization.constraints` (2159), `pypsa.optimization.global_constraints` (867) | ~3350 total | Builds linopy.Model from Network. Variables, constraints, and objective defined in separate modules. |
| Optimization Entry | `pypsa.optimization.optimize` | 1183 | Orchestrates `create_model()` / `solve_model()` / `assign_solution()`. User extension point between create and solve. |
| Solver Interface | `linopy` | (package) | Abstracted solver interface. HiGHS, GLPK, SCIP, Gurobi, CPLEX all supported via unified `model.solve(solver_name=...)`. |

### Separation of Concerns

**Network model vs. problem formulation:** Clean separation. The Network class is a data container with pandas DataFrames; it knows nothing about optimization. The `pypsa.optimization` module reads from the Network to build a linopy model, and `assign_solution()` writes back.

**Problem formulation vs. solver:** Clean separation via linopy. The optimization modules build a linopy model with variables, constraints, and objective using an algebraic modeling API. The solver choice is a runtime parameter, not a formulation concern.

**Results vs. solve:** Results are assigned back to Network DataFrames (`n.generators_t.p`, `n.buses_t.marginal_price`, etc.), making them immediately accessible as pandas objects.

### Extension Points

1. **Custom constraints:** `create_model()` exposes the linopy model for user modification before `solve_model()`. Variables are accessible by name (e.g., `n.model.variables["Line-s"]`), and constraints can be added using linopy's algebraic API.

2. **Graph access:** `n.graph()` returns a NetworkX graph for topology queries.

3. **PTDF/BODF:** `sub_network.calculate_PTDF()` and `calculate_BODF()` expose network sensitivity matrices as numpy arrays.

4. **Timeseries:** `n.loads_t.p_set`, `n.generators_t.p_max_pu`, etc. accept DataFrame assignment for multi-period studies.

### Internal Documentation

| Feature | Documented? |
|---------|------------|
| create_model / solve_model workflow | Yes |
| linopy model manipulation | Yes (linopy docs) |
| Network graph export | Yes |
| Sub-network PTDF/BODF | Partially (API reference, limited examples) |
| extra_functionality callback | Documented but deprecated |

### Version Info

- PyPSA 1.1.2
- linopy 0.6.4

## Assessment

PyPSA's architecture is well-designed for extensibility. The linopy intermediate layer provides a clean algebraic modeling interface that insulates users from solver-specific details while still allowing full access to the optimization model. The pandas-based data model is intuitive for Python-literate analysts. The main architectural weakness is that the `pypsa.optimization.constraints` module (2159 lines) is large and handles many constraint types in a single file, which could be better decomposed.

## Test Script

`evaluations/pypsa/tests/extensibility/test_b6_code_architecture.py`
