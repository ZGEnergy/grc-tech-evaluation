---
test_id: B-6
tool: gridcal
dimension: extensibility
network: N/A
protocol_version: "v11"
skill_version: v2
test_hash: "0f337d8d"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.13
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 332
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# B-6: Qualitative assessment of DCPF solve path source code architecture

## Result: INFORMATIONAL

## Finding

GridCal/VeraGridEngine has a **5-layer architecture** with clear separation of concerns between network model, simulation drivers, solver implementations, and results. However, several files are excessively large (7671 LOC for assets.py, 3199 for multi_circuit.py, 3146 for linear_opf_ts.py), and the OPF formulation is monolithic and procedural rather than modular.

## Evidence

### DCPF Solve Path Trace

```
vge.power_flow(grid, options)           [api.py:101-118]
  -> PowerFlowDriver(grid, options)     [power_flow_driver.py, 252 LOC]
    -> driver.run()
      -> multi_island_pf()              [power_flow_worker.py:994-1031]
        -> compile_numerical_circuit_at()  [compilation step]
        -> multi_island_pf_nc()         [power_flow_worker.py:913-991]
          -> __multi_island_pf_nc_limited_support()  [power_flow_worker.py:815-912]
            -> __solve_island_limited_support()      [power_flow_worker.py:316-732]
              -> For SolverType.Linear: Bdc construction + scipy.sparse solve
```

### Layer Summary

| Layer | File | LOC | Role |
|-------|------|-----|------|
| L1: API | api.py | 503 | Convenience functions wrapping Driver pattern |
| L2: Driver | power_flow_driver.py | 252 | Engine selection, QThread support, logging |
| L3: Worker | power_flow_worker.py | 1031 | Island decomposition, solver dispatch (14 algorithms) |
| L4: Results | power_flow_results.py | 1016 | Typed results with DataFrame export, JSON serialization |
| L5: Data Model | multi_circuit.py + assets.py + numerical_circuit.py | 12,058 | Device-oriented model -> matrix-oriented model |

### Separation of Concerns

| Concern | Separated? | Notes |
|---------|-----------|-------|
| Network model | Yes | MultiCircuit (Devices/) clearly separated from Simulations/. NumericalCircuit bridges via compilation. |
| Problem formulation | Yes | PF: solver algorithms in power_flow_worker.py. OPF: linear_opf_ts.py (3146 LOC, monolithic). |
| Solver interface | Yes | MIP solvers abstracted via Utils/MIP/ with PuLP/OR-Tools backends behind LpModel interface. PF solvers use NumPy/SciPy directly. |
| Results | Yes | Dedicated result classes with DataFrame export, JSON serialization, area aggregation. |

### Documentation Quality

| File | Functions/Classes | With Docstring | Coverage |
|------|------------------|----------------|----------|
| api.py | 17 | 2 | 12% |
| power_flow_driver.py | 5 | 3 | 60% |
| power_flow_worker.py | 7 | 1 | 14% |
| multi_circuit.py | 112 | 90 | 80% |
| assets.py | 576 | 473 | 82% |
| numerical_circuit.py | 34 | 25 | 74% |

The data model layer has good documentation coverage (74-82%). The simulation layer has poor docstring coverage (12-14%), though the code uses descriptive parameter names and inline comments with mathematical notation (e.g., Bdc, Sbus, Sf).

### Numerical Method Implementations

| File | LOC | Algorithm |
|------|-----|-----------|
| newton_raphson_fx.py | 133 | Newton-Raphson |
| fast_decoupled.py | 226 | Fast Decoupled |
| gauss_power_flow.py | 215 | Gauss-Seidel |
| helm_power_flow.py | 847 | HELM |
| iwamoto_newton_raphson.py | 301 | Iwamoto-NR |
| levenberg_marquadt_fx.py | 183 | Levenberg-Marquardt |
| linearized_power_flow.py | 491 | DC (Linear) PF |
| powell_fx.py | 196 | Powell Dog-Leg |

### PF Formulations

| File | LOC |
|------|-----|
| pf_basic_formulation.py | 316 |
| pf_advanced_formulation.py | 874 |
| pf_generalized_formulation.py | 2001 |
| pf_full_acdc_with_negative_poles.py | 2597 |
| pf_basic_formulation_3ph.py | 1220 |
| pf_formulation_template.py | 228 |

### Architecture Concerns

1. **Monolithic OPF formulation:** `linear_opf_ts.py` (3146 LOC) contains the entire LP formulation as a single procedural function. All dispatch modes (Normal, UC, Redispatch, GEP, NodalCapacity) are handled via if/else branches within the same function. No hook points for user-defined constraints.

2. **Very large data model files:** `assets.py` (7671 LOC) with 576 functions/classes is the largest file in the codebase. `multi_circuit.py` (3199 LOC) is also very large.

3. **Compilation bottleneck:** Every solve recompiles MultiCircuit -> NumericalCircuit via `compile_numerical_circuit_at()`. No caching mechanism. This adds overhead for repeated solves.

4. **Engine extensibility:** PowerFlowDriver supports 5 compute engines via EngineType enum, but adding a new engine requires modifying the driver's `run()` method (no plugin pattern).

5. **Internal interface documentation:** Worker functions use double-underscore prefix (`__solve_island_limited_support`) indicating they are private. The public API surface is narrow (api.py), which is good for stability but limits extensibility.

### Total LOC in DCPF Path

| Component | LOC |
|-----------|-----|
| DCPF solve path (api + driver + worker + results + numerical_circuit) | 3,990 |
| Data model (multi_circuit + assets + numerical_circuit) | 12,058 |
| OPF formulation (linear_opf_ts.py) | 3,146 |

## Implications

The architecture shows good separation at the macro level (model/simulation/results) but poor modularity within the OPF formulation layer. The lack of hook points or plugin architecture for custom constraints (B-1) is an architectural limitation, not just a missing feature. The monolithic OPF formulation file would need significant refactoring to support user-defined constraint injection through a clean API.

The data model layer is well-documented and object-oriented. The simulation layer is less documented but uses consistent patterns (Driver -> Worker -> Results). The MIP solver abstraction (PuLP/OR-Tools behind LpModel) is clean and extensible.

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b6_code_architecture.py`
