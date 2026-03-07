---
test_id: F-5
tool: pypsa
dimension: supply_chain
slug: code_inspectability_trace
network: N/A
protocol_version: v4
status: pass
workaround_class: null
timestamp: 2026-03-06T12:00:00Z
---

# F-5: Code Inspectability Trace

## Execution Trace: `n.optimize()` to Solver Invocation

The full call chain from user-facing API to solver execution:

### Layer 1: PyPSA Network API (Pure Python)

```
n.optimize(solver_name="highs", ...)
  -> OptimizationAccessor.__call__()
```

- Module: `pypsa/optimization/optimize.py`
- Class: `OptimizationAccessor` (registered via `@Accessor`)
- Pure Python, fully inspectable

### Layer 2: PyPSA Optimization Subsystem (Pure Python)

```
OptimizationAccessor.__call__()
  -> create_model(n, snapshots)     # Build Linopy model
  -> solve_model(n, ...)            # Dispatch to solver
```

- Modules in `pypsa/optimization/`:
  - `optimize.py` -- entry point, model creation/solve orchestration
  - `variables.py` -- decision variable definitions
  - `constraints.py` -- power balance, flow limits, ramp constraints
  - `expressions.py` -- objective function terms
  - `global_constraints.py` -- emission limits, transmission caps
  - `abstract.py` -- abstract optimization interface
  - `mga.py` -- Modeling to Generate Alternatives
  - `common.py` -- shared utilities
- All pure Python, fully inspectable

### Layer 3: Linopy Model (Pure Python)

```
n.model = linopy.Model()
n.model.add_variables(...)
n.model.add_constraints(...)
n.model.objective = ...
n.model.solve(solver_name="highs")
```

- Module: `linopy/model.py`
- Pure Python, fully inspectable
- Translates abstract LP/MILP into solver-specific calls

### Layer 4: Linopy Solver Interface (Pure Python)

```
Model.solve()
  -> linopy.solvers.run_highs(...)
```

- Module: `linopy/solvers.py`
- Constructs the HiGHS problem via the highspy Python API
- Pure Python, fully inspectable

### Layer 5: HiGHS Python Bindings (Thin C++ Wrapper)

```
highspy.Highs()
h.addVars(...)
h.addRows(...)
h.run()
```

- Module: `highspy/__init__.py` (Python) + `highspy/_core.cpython-312-x86_64-linux-gnu.so` (compiled)
- The `.so` file wraps the HiGHS C++ solver library
- **This is the only opaque binary step in the chain**
- Source: <https://github.com/ERGO-Code/HiGHS> (MIT, fully buildable)

### Layer 6: HiGHS Solver (C++)

```
HiGHS::run() -> Simplex/IPM solve
```

- Compiled C++ code (simplex, interior point, branch-and-bound)
- Full source available at ERGO-Code/HiGHS

## Module Summary

| Layer | Module | Language | Inspectable |
|-------|--------|----------|-------------|
| 1 | pypsa.optimization.optimize | Python | Yes |
| 2 | pypsa.optimization.{variables,constraints,expressions,...} | Python | Yes |
| 3 | linopy.model | Python | Yes |
| 4 | linopy.solvers | Python | Yes |
| 5 | highspy (Python API) | Python | Yes |
| 5 | highspy._core.so | C++ | Source available |
| 6 | HiGHS solver engine | C++ | Source available |

## Assessment

**PASS** -- The execution path from `n.optimize()` to solver invocation traverses 4 pure-Python layers (PyPSA optimization, Linopy model, Linopy solver interface, highspy Python API) before reaching a single compiled C++ binary (HiGHS solver). All Python code is fully inspectable. The compiled HiGHS solver has complete source code available under MIT license. No opaque or proprietary binary steps exist in the chain.
