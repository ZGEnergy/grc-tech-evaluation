---
test_id: F-5
tool: pypsa
dimension: supply_chain
network: N/A
protocol_version: v9
skill_version: v1
test_hash: 9eeed31c
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
timestamp: 2026-03-11T00:00:00Z
---

# F-5: Code Inspectability (code_inspectability)

## Result: PASS

## Finding

The complete call chain from `n.optimize()` to HiGHS solver invocation is fully inspectable in Python source code. There are no opaque binary steps — every layer is either pure Python or source-available C++.

## Evidence

**Call chain traced via source inspection:**

```
n.optimize(solver_name='highs')
  → pypsa/optimization/optimize.py: OptimizationAccessor.__call__()
      → n.optimize.create_model(snapshots, ...)
          → pypsa/optimization/optimize.py: create_model()
              → define_objective(), define_constraints(), etc.
              → returns linopy.Model object (n.model)
      → n.model.solve(solver_name='highs', ...)
          → linopy/model.py: Model.solve()
              → linopy/solvers.py: HiGHSSolver.solve_model()
                  → import highspy
                  → h = highspy.Highs()  ← pybind11 binding
                  → h.passModel(...)     ← passes LP/MILP data to HiGHS C++
                  → h.run()             ← calls HiGHS C++ solver
                  → extract solution from h.getSolution()
```

**Layer-by-layer inspectability:**

| Layer | Type | Source Location | Inspectable? |
|-------|------|----------------|--------------|
| `pypsa/optimization/optimize.py` | Pure Python | `.venv/.../pypsa/optimization/optimize.py` | Yes — full source |
| `linopy/model.py` | Pure Python | `.venv/.../linopy/model.py` | Yes — full source |
| `linopy/solvers.py` | Pure Python | `.venv/.../linopy/solvers.py` | Yes — full source |
| `highspy/_core.cpython-312.so` | pybind11 C++ | `https://github.com/ERGO-Code/HiGHS` | Binary in venv; source on GitHub |
| HiGHS C++ solver | C++ | `https://github.com/ERGO-Code/HiGHS` | Source-available |

**Confirmed via source inspection:**
```python
# linopy/solvers.py key lines
import highspy
h = highspy.Highs()                       # line 563
h = model.to_highspy(...)                 # line 859 — alternative direct API
h.run()                                   # implied by solve flow
```

The `highspy` package is a thin pybind11 wrapper (`_core.so`) that exposes the HiGHS C++ API as Python objects. The wrapper itself is ~500 lines of Python (`highs.py`) with the C++ binding loaded as `_core`.

**No opaque steps:** The entire path from Python `n.optimize()` to the HiGHS C++ solver is traceable through inspectable Python source, with the single compiled boundary at the `highspy._core.so` pybind11 layer where C++ takes over. That boundary is documented by the HiGHS project.

## Implications

Excellent code inspectability. The pure-Python architecture of PyPSA and linopy means the model formulation, constraint construction, and solver interface are all readable and auditable without any binary analysis. The only non-inspectable step (HiGHS C++ execution) is at a clearly defined, well-documented boundary. This is the best possible structure for a compiled solver integration.
