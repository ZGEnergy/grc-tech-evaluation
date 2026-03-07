---
test_id: B-6
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.0
peak_memory_mb: null
loc: 0
solver: null
timestamp: 2026-03-06T02:00:00Z
---

# B-6: Code Architecture (Qualitative Audit)

## Result: PASS

## Architecture Overview

GridCal (VeraGridEngine 5.6.28) has a three-tier architecture with clear separation of concerns.

### Tier 1: Domain Model (`MultiCircuit`)

The user-facing data model. `MultiCircuit` holds device collections (buses, generators, loads, lines, transformers, etc.) as Python lists of typed device objects. Each device has typed attributes (e.g., `Generator.Pmin`, `Generator.Cost`, `Line.rate`).

Key files:
- `VeraGridEngine/Devices/multi_circuit.py` -- master grid container
- `VeraGridEngine/Devices/Substation/bus.py` -- bus device
- `VeraGridEngine/Devices/Injections/generator.py` -- generator device
- `VeraGridEngine/Devices/Branches/line.py` -- line device

### Tier 2: Numerical Representation (`NumericalCircuit`)

Compiled from `MultiCircuit` via `compile_numerical_circuit_at()`. Converts the object-oriented device model into sparse matrices and numpy arrays suitable for numerical solvers. This compilation step handles:

- Topology analysis (island splitting)
- Admittance matrix construction
- Bus type classification (PQ/PV/Slack)
- Per-unit conversion

Key files:
- `VeraGridEngine/Compilers/circuit_to_data.py` -- `compile_numerical_circuit_at()`
- `VeraGridEngine/DataStructures/numerical_circuit.py` -- `NumericalCircuit`

### Tier 3: Solvers and Drivers

Each simulation type has a Driver (orchestrator) and solver functions:

**DCPF call path:**

```
vge.power_flow(grid, options)           # api.py -- convenience wrapper
  -> PowerFlowDriver(grid, options)     # power_flow_driver.py
       .run()
  -> multi_island_pf(grid, options)     # power_flow_worker.py
  -> compile_numerical_circuit_at()     # circuit_to_data.py -- Tier 1 -> Tier 2
  -> multi_island_pf_nc(nc, options)    # power_flow_worker.py
  -> __multi_island_pf_nc_limited_support()  # handles Linear solver type
  -> PfBasicFormulation(nc, options)    # pf_basic_formulation.py
  -> Direct linear solve (Bdc @ theta = P)
```

**Key design patterns:**
- **Driver pattern**: Each simulation type has a `*Driver` class (e.g., `PowerFlowDriver`, `OptimalPowerFlowDriver`, `LinearAnalysisDriver`) that wraps setup, execution, and result packaging.
- **Engine abstraction**: `EngineType` enum allows switching between solver backends (VeraGrid, NewtonPA, GSLV, Bentayga, PGM) with automatic fallback.
- **Formulation classes**: Power flow uses `PfBasicFormulation`, `PfGeneralizedFormulation`, `PfAcDcWithNegativePoles` -- each wraps a Jacobian + residual function for Newton-type solvers.
- **Retry logic**: If the primary solver fails, `multi_island_pf_nc` can retry with alternative solvers (NR -> Powell -> LM).

### Separation of Concerns Assessment

| Layer | Responsibility | Coupling |
|-------|---------------|----------|
| API (`api.py`) | Thin wrappers, ~5-10 lines each | Depends on Drivers |
| Drivers | Orchestration, threading support | Depends on Workers |
| Workers | Numerical compilation + solver dispatch | Depends on NumericalCircuit |
| Formulations | Jacobian/residual math | Depends on sparse matrices |
| NumericalCircuit | Data compilation | Depends on MultiCircuit |
| MultiCircuit | Domain objects | Independent |

### Internal Interfaces

1. **MultiCircuit -> NumericalCircuit**: `compile_numerical_circuit_at()` is the single bridge. Clean interface but the function has many parameters (temperature, tolerances, OPF results, etc.).

2. **NumericalCircuit -> Solver**: Formulation classes (`PfBasicFormulation`) consume `NumericalCircuit` and expose a standard `fx(x)` interface for Newton-type solvers.

3. **Solver -> Results**: `NumericPowerFlowResults` (internal) is translated to `PowerFlowResults` (external) by the Driver.

4. **OPF path**: Uses `run_linear_opf_ts()` which builds an LP/MIP model directly from `NumericalCircuit` arrays. Solver interface is through HiGHS/CBC/SCIP via `MIPSolvers` enum.

### Extensibility Assessment

**Strengths:**
- Clean three-tier separation makes it possible to add new device types or solvers without modifying other layers
- NetworkX graph export (`build_graph()`) enables external analysis
- Numerical arrays are accessible for custom computations
- Driver pattern makes it easy to add new simulation types

**Weaknesses:**
- OPF formulation is monolithic -- custom constraints require modifying source code
- No plugin or callback mechanism for user-defined constraints
- Transformer handling bugs (TapPhaseControl) affect multiple simulation types
- UC constraint enforcement incomplete (issue #397)

## Source Files Examined

- `VeraGridEngine/api.py` -- public API surface
- `VeraGridEngine/Simulations/PowerFlow/power_flow_driver.py` -- PF driver
- `VeraGridEngine/Simulations/PowerFlow/power_flow_worker.py` -- PF worker with solver dispatch
- `VeraGridEngine/Compilers/circuit_to_data.py` -- compilation bridge
- `VeraGridEngine/DataStructures/numerical_circuit.py` -- numerical representation
- `VeraGridEngine/Simulations/PowerFlow/Formulations/pf_basic_formulation.py` -- solver formulation
- `VeraGridEngine/Simulations/LinearFactors/linear_analysis_driver.py` -- PTDF/LODF driver
- `VeraGridEngine/enumerations.py` -- SolverType, EngineType, SimulationTypes enums
