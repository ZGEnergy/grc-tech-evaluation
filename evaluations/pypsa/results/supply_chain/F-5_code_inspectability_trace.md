---
test_id: F-5
tool: pypsa
dimension: supply_chain
status: pass
timestamp: 2026-03-05
---

# F-5: Code Inspectability Trace

## Finding

The complete call path from `n.optimize()` to the HiGHS solver is traceable through pure Python code until the final solver invocation. Every layer is open-source and inspectable.

## Evidence

**Call chain traced via `inspect.getfile()` and `inspect.getsource()` in the devcontainer:**

### Layer 1: PyPSA Network.optimize()
- **Type:** `OptimizationAccessor` (xarray-style accessor pattern)
- **File:** `.venv/lib/python3.12/site-packages/pypsa/optimization/optimize.py`
- **Entry point:** `OptimizationAccessor.__call__()` which accepts parameters for solver selection, transmission losses, unit commitment, etc.
- **Language:** Pure Python
- **License:** MIT

### Layer 2: PyPSA optimization internals
- **Module:** `pypsa.optimization.optimize`
- Constructs a `linopy.Model` by defining variables, constraints, and objective function
- Calls `model.solve(solver_name=..., **solver_options)`
- **Language:** Pure Python
- **License:** MIT

### Layer 3: linopy Model.solve()
- **File:** `.venv/lib/python3.12/site-packages/linopy/model.py`
- Accepts solver_name, io_api, and solver options
- Routes to solver-specific backends (HiGHS, GLPK, Gurobi, CPLEX, etc.)
- For HiGHS: uses the `highspy` direct API (no file I/O needed)
- **Language:** Pure Python
- **License:** MIT

### Layer 4: highspy (HiGHS Python bindings)
- **File:** `.venv/lib/python3.12/site-packages/highspy/__init__.py`
- **Compiled extension:** `highspy/_core.cpython-312-x86_64-linux-gnu.so`
- Python bindings to the HiGHS C++ solver library
- **Language:** Python wrapper + C++ compiled extension
- **License:** MIT
- **Source:** <https://github.com/ERGO-Code/HiGHS>

### Layer 5: HiGHS solver (compiled C++)
- LP/MIP/QP solver
- Bundled inside the highspy wheel (no external system library needed)
- Full C++ source available at <https://github.com/ERGO-Code/HiGHS>
- **License:** MIT

**Inspectability assessment:**
- Layers 1-3: Fully inspectable pure Python. Can set breakpoints, read source, trace execution.
- Layer 4: Python wrapper is inspectable; C++ extension requires building from source to inspect at that level.
- Layer 5: Full C++ source available; standard CMake build system; can be compiled from source.

**No proprietary or obfuscated code in the chain.** Every component from the user API to the solver core has publicly available source code under permissive licenses.

## Implications

Excellent code inspectability. The optimization pipeline is a clean stack of MIT-licensed open-source layers. The only compiled code is in the solver itself (HiGHS), which has full source availability. An auditor can trace any optimization result from the PyPSA API through linopy to the solver formulation.
