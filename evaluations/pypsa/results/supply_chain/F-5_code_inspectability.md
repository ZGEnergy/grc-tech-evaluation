---
test_id: F-5
tool: pypsa
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: 2026-03-13T12:00:00Z
protocol_version: v10
skill_version: v1
test_hash: 6108ab51
---

# F-5: Code Inspectability

## Findings

### Execution Path: `n.lpf()` (DCPF)

| Step | Module | Function | Inspectable |
|------|--------|----------|-------------|
| 1 | `pypsa/network/abstract.py` | `Network.lpf()` | Yes (Python) |
| 2 | `pypsa/network/power_flow.py` | `SubNetworkPowerFlowMixin.lpf()` | Yes (Python) |
| 3 | `pypsa/network/power_flow.py` | `calculate_B_H()` | Yes (Python) |
| 4 | `scipy.sparse` | `csc_matrix`, `lil_matrix` | Yes (Python/C) |
| 5 | `scipy.sparse.linalg` | `spsolve()` | Yes (Python wrapper -> UMFPACK C) |
| 6 | `pypsa/network/power_flow.py` | Result assignment to DataFrames | Yes (Python) |

### Execution Path: `n.optimize()` (OPF)

| Step | Module | Function | Inspectable |
|------|--------|----------|-------------|
| 1 | `pypsa/optimization/optimize.py` | `OptimizationAccessor.__call__()` | Yes (Python) |
| 2 | `pypsa/optimization/optimize.py` | `create_model()` | Yes (Python) |
| 3 | `pypsa/optimization/variables.py` | Variable definitions | Yes (Python) |
| 4 | `pypsa/optimization/constraints.py` | Constraint definitions | Yes (Python) |
| 5 | `pypsa/optimization/optimize.py` | `solve_model()` | Yes (Python) |
| 6 | `linopy/model.py` | `Model.solve()` | Yes (Python) |
| 7 | `linopy/solvers.py` | Solver dispatch | Yes (Python) |
| 8 | `highspy` | HiGHS solver binary | Source available (C++) |
| 9 | `pypsa/optimization/optimize.py` | `assign_solution()` | Yes (Python) |

### Module Inventory

PyPSA v1.1.2 source modules in the execution path:

```
pypsa/
  network/
    abstract.py          - Network class, top-level API
    components.py        - Component add/remove methods
    graph.py             - Graph topology methods
    io.py                - Import/export
    power_flow.py        - PF and LPF solvers
  optimization/
    optimize.py          - OPF entry point, model build/solve
    variables.py         - Decision variable definitions
    constraints.py       - Constraint definitions
    global_constraints.py - System-wide constraints
    mga.py               - Modelling-to-Generate-Alternatives
  components/
    store.py             - Component data storage
  data/
    components.csv       - Component type definitions
    component_attrs/     - Per-component attribute definitions
    variables.csv        - Variable naming conventions
```

### Opaque Steps

**None.** The entire execution path from API call to solver invocation
is inspectable:

1. **PyPSA source**: Pure Python, fully readable
2. **Linopy source**: Pure Python, fully readable
3. **Solver interface**: HiGHS is called via highspy Python bindings
   with an inspectable C++ source. The solver itself is a black box
   in the sense that verifying LP/MILP solver correctness requires
   understanding the simplex/interior point algorithms, but the solver
   source is available and auditable.

The only non-trivial opacity is in scipy's sparse linear algebra
(`spsolve`), which delegates to UMFPACK (C library). However, UMFPACK
is a well-known, audited library with published source code and
extensive academic validation.

### Consumed Observations

Architecture quality observation from B-6 confirmed:
- 4-layer architecture: User API -> Mixin Dispatch -> SubNetwork
  Computation -> Linear Algebra Backend
- Clean separation between data model (pandas DataFrames), formulation
  (power_flow.py / constraints.py), and solver (linopy/scipy)
- 5 documented injection points for extending behavior

## Recorded Metrics

- module_list: pypsa.network.{abstract,power_flow,graph,components,io},
  pypsa.optimization.{optimize,variables,constraints,global_constraints},
  linopy.{model,solvers}, scipy.sparse.linalg, highspy
- opaque_steps: 0 (all Python source inspectable; solver C++ source available)
