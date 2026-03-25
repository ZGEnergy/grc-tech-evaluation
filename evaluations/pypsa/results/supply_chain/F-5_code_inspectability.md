---
test_id: F-5
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 6108ab51
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

# F-5: Code Inspectability Trace

## Result: PASS

## Finding

The entire execution path from `n.optimize()` to solver invocation is fully inspectable. PyPSA is pure Python; linopy is pure Python; the only binary step is the HiGHS solver itself, whose C++ source is publicly available on GitHub under MIT license. Zero opaque binary steps in the critical path.

## Evidence

### Execution Path: `n.optimize()` (OPF)

| Step | Module | Function | Inspectable |
|------|--------|----------|-------------|
| 1 | `pypsa/optimization/optimize.py` | `OptimizationAccessor.__call__()` | Yes (Python) |
| 2 | `pypsa/optimization/optimize.py` | `create_model()` | Yes (Python) |
| 3 | `pypsa/optimization/variables.py` | Variable definitions | Yes (Python) |
| 4 | `pypsa/optimization/constraints.py` | Constraint definitions | Yes (Python) |
| 5 | `pypsa/optimization/optimize.py` | `solve_model()` | Yes (Python) |
| 6 | `linopy/model.py` | `Model.solve()` | Yes (Python) |
| 7 | `linopy/solvers.py` | Solver dispatch (HiGHS path) | Yes (Python) |
| 8 | `highspy` | HiGHS solver binary | Source available (C++, MIT, GitHub) |
| 9 | `pypsa/optimization/optimize.py` | `assign_solution()` | Yes (Python) |

### Execution Path: `n.lpf()` (DCPF)

| Step | Module | Function | Inspectable |
|------|--------|----------|-------------|
| 1 | `pypsa/network/abstract.py` | `Network.lpf()` | Yes (Python) |
| 2 | `pypsa/network/power_flow.py` | `SubNetworkPowerFlowMixin.lpf()` | Yes (Python) |
| 3 | `pypsa/network/power_flow.py` | `calculate_B_H()` | Yes (Python) |
| 4 | `scipy.sparse` | `csc_matrix`, `lil_matrix` | Yes (Python/C) |
| 5 | `scipy.sparse.linalg` | `spsolve()` | Yes (Python wrapper -> UMFPACK C) |
| 6 | `pypsa/network/power_flow.py` | Result assignment to DataFrames | Yes (Python) |

### Module Inventory

Key PyPSA v1.1.2 source modules in the execution path:

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
```

### Opaque Steps

**None.** The complete path from user API call to solver invocation is inspectable Python source code. The HiGHS solver binary is the only compiled component in the critical path, and its C++ source is available at https://github.com/ERGO-Code/HiGHS under MIT license.

scipy's `spsolve` delegates to UMFPACK (C library) for the DCPF sparse solve, but UMFPACK is a well-known, peer-reviewed library with published source code.

## Implications

Full code inspectability from API surface to solver invocation. No proprietary or undiscoverable binary steps. The 4-layer architecture (User API -> Mixin Dispatch -> SubNetwork Computation -> Linear Algebra Backend) provides clean separation of concerns, making it straightforward to audit any specific computation step.
