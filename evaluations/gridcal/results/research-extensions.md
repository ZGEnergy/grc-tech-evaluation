# gridcal -- Research: Extensions & Architecture

## Key Findings

- **No formal plugin/extension API exists.** GridCal (now "VeraGrid" / `VeraGridEngine` v5.6.28) has no documented plugin system, hook registry, or callback framework for third-party extensions. The single exception is a `plugin_fcn_ptr` callback in the investment evaluation solver, which accepts a plain callable.
- **Architecture follows a clear three-layer separation:** Object-oriented device model (`MultiCircuit` / `Assets`) -> array-oriented numerical compilation (`NumericalCircuit`) -> simulation drivers (`DriverTemplate` subclasses) -> results (`ResultsTemplate`). This is well-structured but tightly coupled.
- **NetworkX is a direct dependency** and `MultiCircuit.build_graph()` returns a `nx.MultiDiGraph`. NetworkX is also used internally for topology reduction, node grouping, and synthetic network generation.
- **Pandas DataFrame export is built-in:** `PowerFlowResults.get_bus_df()` and `get_branch_df()` return DataFrames; `ResultsTable.to_df()` converts any result type to a DataFrame. The `export_all()` method returns bus and branch DataFrames.
- **Scipy sparse matrices are the primary internal representation** for admittance matrices, connectivity, and adjacency. The `NumericalCircuit` exposes `get_connectivity_matrices()`, `get_admittance_matrices()`, and `compute_adjacency_matrix()`.
- **Multi-engine compilation** via `Compilers/` translates `MultiCircuit` to external formats (Bentayga, Newton Power Analytics, Power Grid Model, GSLV, Gurobi Optimods). The `EngineType` enum selects the backend at runtime.
- **No constraint injection API.** OPF formulations are monolithic functions (e.g., `add_linear_branches_formulation`, `add_linear_node_balance`) that build the LP problem procedurally. Users cannot add custom constraints without modifying the source.
- **IO parsers support import/export from pandapower, PyPSA, MATPOWER, PSS/e, CGMES, DGS, UCTE, and IIDM formats.** Conversion is format-level, not live interop.
- **Signal system is a stub.** `DummySignal` replaces Qt signals in the engine, providing `emit()`/`connect()` methods. When used headless, signals are no-ops. The GUI package presumably replaces these with real Qt signals.
- **The `~/.VeraGrid/plugins/` directory exists** in the filesystem API, suggesting planned plugin support in the GUI layer, but no plugin loading mechanism was found in the engine code.

## Detailed Notes

### Architecture: Three-Layer Design

The codebase has a clear separation between three representations of a power system:

1. **Object-Oriented Layer (`Devices/`):** `MultiCircuit` extends `Assets`, which holds typed lists of device objects (buses, lines, generators, loads, etc.). Each device inherits from `EditableDevice`, which provides a property introspection system via `GCProp` descriptors. Devices are organized under `Devices/Branches/`, `Devices/Injections/`, `Devices/Substation/`, `Devices/Aggregation/`, `Devices/Fluid/`, `Devices/Dynamic/`.
   - Source: `VeraGridEngine/Devices/assets.py`, `VeraGridEngine/Devices/multi_circuit.py`

2. **Numerical Layer (`DataStructures/`):** `NumericalCircuit` stores array-oriented data (NumPy arrays, SciPy sparse matrices) compiled from the object model. Contains `BusData`, `PassiveBranchData`, `GeneratorData`, `LoadData`, etc. Compilation is performed by `compile_numerical_circuit_at()` in `Compilers/circuit_to_data.py`.
   - Source: `VeraGridEngine/DataStructures/numerical_circuit.py`, `VeraGridEngine/Compilers/circuit_to_data.py`

3. **Simulation Layer (`Simulations/`):** `DriverTemplate` is the base class for all simulation drivers. Each driver takes a `MultiCircuit`, compiles it, runs the algorithm, and populates a `ResultsTemplate` subclass. Drivers include: PowerFlow, OPF, LinearAnalysis, ContingencyAnalysis, ShortCircuit, ContinuationPowerFlow, StateEstimation, Stochastic, Clustering, InvestmentsEvaluation, NodalCapacity, NTC/ATC, Reliability, Rms (dynamics), and more.
   - Source: `VeraGridEngine/Simulations/driver_template.py`, `VeraGridEngine/Simulations/driver_handler.py`

The `api.py` module exposes high-level convenience functions (`power_flow()`, `linear_opf()`, `open_file()`, etc.) that wrap driver creation and execution.
   - Source: `VeraGridEngine/api.py`

### Plugin / Extension Mechanisms

**Investment Evaluation Plugin Callback:**
The `InvestmentsEvaluationOptions` class accepts a `plugin_fcn_ptr: Callable` parameter. When `solver=InvestmentEvaluationMethod.FromPlugin`, the driver calls `self.options.plugin_fcn_ptr(self)`, passing the entire driver as context. This is the only formal extension point found in the engine.
   - Source: `VeraGridEngine/Simulations/InvestmentsEvaluation/investments_evaluation_options.py` (line 24), `investments_evaluation_driver.py` (lines 318-319)
   - Enum: `InvestmentEvaluationMethod.FromPlugin` in `enumerations.py` (line 166)

**Plugins Directory:**
`file_system.py` defines `plugins_path()` returning `~/.VeraGrid/plugins/`. No loader code was found in the engine; this is likely used by the GUI layer.
   - Source: `VeraGridEngine/IO/file_system.py` (line 36)

**No General Hook/Event System:**
There is no observer pattern, event bus, or hook registry. The `DummySignal` class provides `emit()`/`connect()` stubs that are no-ops in headless mode. These are designed for Qt signal replacement, not for user-extensible callbacks.
   - Source: `VeraGridEngine/Simulations/driver_template.py` (lines 20-35)

### Network Graph Access

**NetworkX Integration:**
`MultiCircuit.build_graph()` returns a `nx.MultiDiGraph` with bus indices as nodes and weighted edges (weight = branch reactance X). A second method `build_graph_real_power_flow(current_flow)` builds a `nx.DiGraph` with edge direction based on actual power flow.
   - Source: `VeraGridEngine/Devices/multi_circuit.py` (lines 368-428)

NetworkX is also used in:
- `Simulations/Topology/node_groups_driver.py` -- Dijkstra shortest paths for node grouping
- `Simulations/Topology/topology_reduction_driver.py` -- Simple paths for topology reduction
- `Topology/GridReduction/` -- Di Shi and PTDF-based grid reduction
- `Utils/ThirdParty/SyntheticNetworks/rpgm_algo.py` -- Random power grid model generation
- `Devices/Diagrams/base_diagram.py` -- Diagram layout

**Adjacency and Connectivity Matrices:**
`MultiCircuit.get_adjacent_matrix()` returns a `scipy.sparse.csc_matrix`. `get_bus_branch_connectivity_matrix()` returns `(Cf, Ct, C)` sparse matrices. `NumericalCircuit.compute_adjacency_matrix()` provides the same from the numerical layer.
   - Source: `VeraGridEngine/Devices/multi_circuit.py` (lines 878-920), `DataStructures/numerical_circuit.py` (line 858)

**Island Detection:**
`Topology/topology.py` contains `find_islands()` using a Numba-JIT'd DFS on sparse CSC adjacency matrices. This is the core topology processing routine.
   - Source: `VeraGridEngine/Topology/topology.py`

### DataFrame Interoperability

**Results to DataFrame:**
- `PowerFlowResults.get_bus_df()` -> `pd.DataFrame` with columns `Vm, Va, P, Q`
- `PowerFlowResults.get_branch_df()` -> `pd.DataFrame` with columns `Pf, Qf, Pt, Qt, loading, Ploss, Qloss`
- `PowerFlowResults.export_all()` -> tuple of `(df_bus, df_branch)` DataFrames
- `ResultsTable.to_df()` converts any results model to a DataFrame
- `ResultsTable.save_to_excel(file_name)` and `save_to_csv(file_name)` for disk export
   - Source: `VeraGridEngine/Simulations/PowerFlow/power_flow_results.py` (lines 447-475, 951-991), `VeraGridEngine/Simulations/results_table.py` (to_df at ~line 356)

**Device Data:**
Device properties use a `GCProp` descriptor system for introspection. The `EditableDevice` base class supports `get_dict()` for serialization. However, there is no built-in `to_dataframe()` on the device model itself -- users must iterate device lists manually.

### Constraint Addition (OPF)

The linear OPF formulation is implemented as a series of procedural functions in `Simulations/OPF/Formulations/linear_opf_ts.py`:
- `add_linear_simple_generation_formulation()`
- `add_linear_battery_formulation()`
- `add_linear_branches_formulation()`
- `add_linear_branches_contingencies_formulation()`
- `add_linear_hvdc_formulation()`
- `add_linear_node_balance()`
- `add_linear_load_formulation()`
- `add_hydro_formulation()`
- etc.

These functions operate on an `LpModel` object and add variables/constraints procedurally. The AC OPF uses `NonLinearOptimalPfProblem` class with `update()` and `get_jacobians_and_hessians()` methods.

**There is no API to inject custom constraints.** Users would need to either:
1. Fork the formulation functions and add constraints directly
2. Extract the `NumericalCircuit` data and build their own optimization problem

   - Source: `VeraGridEngine/Simulations/OPF/Formulations/linear_opf_ts.py`, `ac_opf_problem.py`

### Multi-Engine Compilation (Compilers/)

The `Compilers/` module provides translation from `MultiCircuit` to external solver formats:
- `circuit_to_bentayga.py` -- Bentayga (commercial, license-gated)
- `circuit_to_newton_pa.py` -- Newton Power Analytics
- `circuit_to_pgm.py` -- Power Grid Model (open-source)
- `circuit_to_gslv.py` -- GSLV solver
- `circuit_to_optimods.py` -- Gurobi Optimods (for AC OPF via Gurobi)

The `EngineType` enum (`VeraGrid`, `Bentayga`, `NewtonPA`, `PGM`, `GSLV`) selects the backend at driver construction. The internal `circuit_to_data.py` compiles to the native `NumericalCircuit`.
   - Source: `VeraGridEngine/Compilers/__init__.py`, `VeraGridEngine/enumerations.py` (line 294)

### Format Interoperability (IO/)

Import parsers:
- MATPOWER `.m` files (`IO/matpower/`)
- PSS/e `.raw`/`.rawx` files (`IO/raw/`)
- CGMES/CIM XML (`IO/cim/`)
- DigiSilent DGS (`IO/dgs/`)
- PSLF `.epc` (`IO/epc/`)
- UCTE (`IO/ucte/`)
- IIDM (`IO/iidm/`)
- pandapower pickle/JSON/SQLite/Excel (`IO/others/pandapower_parser.py`)
- PyPSA Network (`IO/others/pypsa_parser.py`)
- ANAREDE, IPA, PLX, DPX, RTE formats (`IO/others/`)

Export:
- `to_matpower()` function for MATPOWER dict format
- CGMES export via `save_cgmes_file()`
- PSS/e `.raw` export (`IO/raw/veragrid_to_raw.py`)
- Native formats: `.veragrid` (zip/HDF5/SQLite), `.ejson`, Excel
   - Source: `VeraGridEngine/IO/` directory, `VeraGridEngine/IO/matpower/__init__.py`

### Code Organization Metrics

- `multi_circuit.py`: 3,199 lines (the central god-class, inherits from `Assets`)
- `assets.py`: 7,000+ lines (device list management)
- `linear_opf_ts.py`: 2,600+ lines (linear OPF formulation)
- `ac_opf_problem.py`: 1,700+ lines (nonlinear OPF)
- `circuit_to_data.py`: 2,200+ lines (numerical compilation)
- `topology.py`: 700+ lines (island detection, connectivity)

The `MultiCircuit`/`Assets` class is a large monolith with 100+ methods. While the subpackage organization is clean (Devices, DataStructures, Simulations, Compilers, IO, Topology, Utils), the central classes are not decomposed.

## Sources

1. `VeraGridEngine/__version__.py` -- Version 5.6.28, MPL-2.0 license
2. `VeraGridEngine/api.py` -- Public API convenience functions
3. `VeraGridEngine/__init__.py` -- Package initialization and contributor list
4. `VeraGridEngine/Devices/multi_circuit.py` -- Core MultiCircuit class with `build_graph()`, `get_adjacent_matrix()`
5. `VeraGridEngine/Devices/assets.py` -- Assets base class with device list management
6. `VeraGridEngine/Simulations/driver_template.py` -- DriverTemplate, DummySignal, TimeSeriesDriverTemplate
7. `VeraGridEngine/Simulations/results_template.py` -- ResultsTemplate with data serialization
8. `VeraGridEngine/Simulations/results_table.py` -- ResultsTable with `to_df()`, `save_to_excel()`, `save_to_csv()`
9. `VeraGridEngine/Simulations/PowerFlow/power_flow_results.py` -- `get_bus_df()`, `get_branch_df()`, `export_all()`
10. `VeraGridEngine/Simulations/InvestmentsEvaluation/investments_evaluation_options.py` -- `plugin_fcn_ptr` callback
11. `VeraGridEngine/Simulations/InvestmentsEvaluation/investments_evaluation_driver.py` -- `FromPlugin` dispatch
12. `VeraGridEngine/Simulations/OPF/Formulations/linear_opf_ts.py` -- Linear OPF constraint functions
13. `VeraGridEngine/Simulations/OPF/Formulations/ac_opf_problem.py` -- Nonlinear OPF problem class
14. `VeraGridEngine/DataStructures/numerical_circuit.py` -- NumericalCircuit with sparse matrices
15. `VeraGridEngine/Topology/topology.py` -- Island detection, adjacency, connectivity
16. `VeraGridEngine/Compilers/__init__.py` -- Compiler module exports
17. `VeraGridEngine/Compilers/circuit_to_pgm.py` -- Power Grid Model translation
18. `VeraGridEngine/Compilers/circuit_to_bentayga.py` -- Bentayga translation
19. `VeraGridEngine/Compilers/circuit_to_optimods.py` -- Gurobi Optimods translation
20. `VeraGridEngine/IO/file_system.py` -- `plugins_path()`, `scripts_path()`
21. `VeraGridEngine/IO/others/pypsa_parser.py` -- PyPSA import parser
22. `VeraGridEngine/IO/others/pandapower_parser.py` -- pandapower import parser
23. `VeraGridEngine/IO/matpower/__init__.py` -- MATPOWER import/export
24. `VeraGridEngine/Devices/Parents/editable_device.py` -- GCProp, EditableDevice
25. `VeraGridEngine/enumerations.py` -- EngineType, InvestmentEvaluationMethod, SimulationTypes
26. GitHub repository metadata: https://github.com/SanPen/VeraGrid (516 stars, 29 open issues, MPL-2.0)

## Gaps and Uncertainties

- **No developer documentation for extensions.** The GitHub wiki pages mostly fail to load; readthedocs returns 404. Extension patterns must be inferred entirely from source code.
- **Plugin loading mechanism unclear.** The `plugins_path()` exists but no loader was found in the engine. This likely lives in the GUI package (`VeraGrid` as opposed to `VeraGridEngine`), which is not installed here.
- **Custom constraint injection untested.** While the LP/NLP problem objects are accessible in theory, there is no documented or supported way to add custom constraints. Needs verification whether one can subclass `NonLinearOptimalPfProblem` or inject into the `LpModel`.
- **Graphs.jl interop does not exist.** GridCal is Python-only; no Julia interop is available.
- **The rename from GridCal to VeraGrid is recent** (the PyPI package is `veragridengine`, GitHub repo is `SanPen/VeraGrid` but still referenced as GridCal in many places). Documentation may lag behind.
- **Signal/callback system untested with real Qt.** The `DummySignal.connect()` method exists but its behavior when connected to real callbacks in headless mode needs verification.
- **No event hooks for pre/post simulation.** There is no documented way to register callbacks that fire before or after a simulation run.
- **Device-level DataFrame export not built-in.** While results have `to_df()`, the device model (buses, generators, etc.) does not provide a direct DataFrame export method -- users must iterate and construct manually.
