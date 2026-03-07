# GridCal (VeraGridEngine 5.6.28) — Research: Extensions & Architecture

## Key Findings

- **Three-tier architecture** with clear separation: object-oriented data model (`MultiCircuit`/`Assets`), compiled numerical arrays (`NumericalCircuit`), and structured results (`ResultsTemplate`). This is a deliberate design choice to separate human-friendly modeling from computation-friendly arrays.
- **Plugin system exists** but lives in the GUI package (`VeraGrid`), not the engine (`VeraGridEngine`). Plugins are JSON-declared Python files placed in `~/.VeraGrid/plugins/`, with two hook points: a `main_fcn` (general-purpose, receives the `MainGUI` instance) and an `investments_fcn` (receives `InvestmentsEvaluationDriver`).
- **No formal callback/hook API** in the engine itself. The `DriverTemplate` base class uses Qt-compatible signal placeholders (`DummySignal`) for progress/done reporting, but these are not extensible event hooks. There is no pre/post-simulation callback mechanism.
- **NetworkX is a first-class dependency.** `MultiCircuit.build_graph()` returns a `nx.MultiDiGraph` with buses as nodes and branches as weighted edges (weight = reactance). A directed power-flow graph variant (`build_graph_real_power_flow()`) is also provided.
- **DataFrame interoperability is strong.** Results can be exported to `pd.DataFrame` via `ResultsTable.to_df()`, power flow results via `PowerFlowResults.export_all()`, and profiles via `MultiCircuit.export_profiles()`. Pandas is used throughout for time series handling.
- **No user-facing API to add custom OPF constraints.** The LP/MIP formulations are hard-coded in `Simulations/OPF/Formulations/`. Users cannot inject constraints without modifying source code. The MIP interface abstracts solver choice (PuLP, OR-Tools, HiGHS) but not the formulation.
- **Multi-engine architecture** supports five computation backends via `EngineType` enum: VeraGrid (native), Bentayga, NewtonPA, PGM (Power Grid Model), and GSLV. Backend selection is per-driver, and each has a dedicated compiler (`circuit_to_*.py`).
- **Rich import/export format support:** MATPOWER (.m), PSS/e RAW/RAWX, CIM/CGMES, DGS, EPC, IIDM, UCTE, pandapower (pickle/JSON/SQLite), PyPSA, and native VeraGrid (.veragrid/.ejson). Parsers for pandapower and PyPSA perform bidirectional conversion.
- **Sparse matrix access** is available through `MultiCircuit.get_bus_branch_connectivity_matrix()` (returns Cf, Ct, C) and `get_adjacent_matrix()`. The admittance matrix (Ybus) is built inside `NumericalCircuit` via the `Topology/admittance_matrices.py` module.
- **866 Python source files** in the engine package; monolithic but well-organized into Devices, Simulations, DataStructures, Compilers, IO, Topology, Utils, and Templates.

## Detailed Notes

### Internal Architecture and Separation of Concerns

The architecture follows a three-layer design documented in the official structure page:

1. **`MultiCircuit` (Data Model Layer):** An object-oriented "database" inheriting from `Assets`. Contains lists of device objects (buses, lines, generators, loads, etc.) with full property metadata, UUIDs, and profile support. Objects reference each other directly (e.g., a branch references its `bus_from` and `bus_to` objects). This layer is human-readable and GUI-friendly. Source: `VeraGridEngine/Devices/multi_circuit.py` (3199 lines), `VeraGridEngine/Devices/assets.py`.

2. **`NumericalCircuit` (Computation Layer):** A compiled snapshot of the data model at a specific time step. Contains typed numpy arrays and sparse matrices organized into data structures (`BusData`, `PassiveBranchData`, `GeneratorData`, etc.). Created by the compiler (`Compilers/circuit_to_data.py`). Multiple NumericalCircuits can exist independently for safe parallelism. Source: `VeraGridEngine/DataStructures/numerical_circuit.py`.

3. **`ResultsTemplate` (Results Layer):** Structured output container. Each simulation type has its own results class (e.g., `PowerFlowResults`, `OptimalPowerFlowResults`) inheriting from `ResultsTemplate`. Results never overwrite input data. Each result variable is registered with type information for serialization. Source: `VeraGridEngine/Simulations/results_template.py`.

The compilation step (`compile_numerical_circuit_at()`) converts the object-oriented model to array-oriented numerical data, which is documented as a deliberate design to separate "management convenience from computational speed."

Sources:
- [VeraGrid Structure Documentation](https://veragrid.readthedocs.io/en/latest/md_source/structure.html)
- `VeraGridEngine/Compilers/circuit_to_data.py`
- `VeraGridEngine/DataStructures/numerical_circuit.py`

### Driver Pattern (Simulation Execution)

All simulations follow a uniform Driver pattern:

```
Driver = SomeDriver(grid=MultiCircuit, options=SomeOptions, ...)
Driver.run()
results = Driver.results  # SomeResults instance
```

The `DriverTemplate` base class (`Simulations/driver_template.py`) provides:
- Progress reporting via `DummySignal` placeholders (compatible with Qt signals when used in GUI)
- Timing (`tic()`/`toc()`)
- Cancellation support (`cancel()`, `is_cancel()`)
- Serialization via `get_save_data() -> DriverToSave`
- Logger for warnings/errors

`TimeSeriesDriverTemplate` extends this with time indexing and clustering support.

The `driver_handler.py` module provides a factory function `create_driver()` that instantiates drivers by `SimulationTypes` enum, useful for deserialization.

Source: `VeraGridEngine/Simulations/driver_template.py`, `VeraGridEngine/Simulations/driver_handler.py`

### Plugin System

The plugin system is documented at [VeraGrid Plugins Documentation](https://veragrid.readthedocs.io/en/latest/md_source/plugins.html).

**Plugin structure** requires three files in `~/.VeraGrid/plugins/`:
- `plugins.plugin.json` — declares name, path, icon, and function entry points
- `plugin.py` — the Python implementation
- `icon.svg` — optional custom icon

**Two hook points:**
1. `main_fcn`: Receives the `MainGUI` instance, giving full access to the circuit object and all GUI controls. This is a general-purpose extension point.
2. `investments_fcn`: Receives an `InvestmentsEvaluationDriver` instance. This is used when `InvestmentEvaluationMethod.FromPlugin` is selected, enabling custom investment optimization algorithms.

**Installation:** Drag-and-drop `.vgplugin` files into the GUI.

**Limitation:** The plugin system is entirely GUI-side. The engine (`VeraGridEngine`) has no plugin infrastructure. The `plugins_path()` function in `IO/file_system.py` merely returns the filesystem path `~/.VeraGrid/plugins/` — there is no plugin loader, registry, or lifecycle management in the engine.

The `InvestmentsEvaluationOptions.plugin_fcn_ptr` is the only engine-level callback, accepting a `Callable` that receives the `InvestmentsEvaluationDriver`:

```python
# In investments_evaluation_driver.py, line 319:
elif self.options.solver == InvestmentEvaluationMethod.FromPlugin:
    self.options.plugin_fcn_ptr(self)
```

Source: `VeraGridEngine/IO/file_system.py` (line 36), `VeraGridEngine/Simulations/InvestmentsEvaluation/investments_evaluation_options.py`, `VeraGridEngine/Simulations/InvestmentsEvaluation/investments_evaluation_driver.py` (line 319)

### NetworkX Graph Access

`MultiCircuit` imports and uses `networkx` directly:

**`build_graph() -> nx.MultiDiGraph`** (line 368 of `multi_circuit.py`):
- Nodes = bus indices (integers)
- Edges = branches (lines, transformers, DC lines, HVDC, switches) with weight = reactance (X)
- Returns a `MultiDiGraph` allowing parallel edges

**`build_graph_real_power_flow(current_flow) -> nx.DiGraph`** (line 407):
- Directed graph based on actual power flow direction
- Requires solved power flow results (`current_flow` array)

**`plot_graph()`** (line 741): Uses `nx.draw_spring()` for quick visualization.

NetworkX is also used internally in topology detection algorithms. The package imports `import networkx as nx` at the top of `multi_circuit.py`.

Source: `VeraGridEngine/Devices/multi_circuit.py` lines 14, 368-430

### DataFrame and Data Export

**Results to DataFrame:**
- `ResultsTable.to_df() -> pd.DataFrame` — converts any results table to a DataFrame
- `ResultsTable.get_data_frame() -> pd.DataFrame` — alias for the above
- `ResultsTable.save_to_excel(filename)` and `save_to_csv(filename)` — direct file export
- `PowerFlowResults.export_all() -> (df_bus, df_branch)` — returns bus and branch result DataFrames

**Model data to DataFrame:**
- `MultiCircuit.export_pf(filename, results)` — exports power flow results to Excel with bus and branch sheets
- `MultiCircuit.export_profiles(filename)` — exports load/generator profiles to Excel as DataFrames
- `TapChanger.to_df() -> pd.DataFrame` — individual device DataFrame export
- `LineLocations.to_df() -> pd.DataFrame` — geographic line coordinate export

**Results serialization:**
- `ResultsTemplate.get_dict()` and `parse_data()` — JSON-compatible dict conversion for all registered result variables
- `ResultsTemplate.to_json(filename)` — direct JSON export

Pandas is a core dependency used throughout for time indexing (`pd.DatetimeIndex`) and tabular data.

Source: `VeraGridEngine/Simulations/results_table.py`, `VeraGridEngine/Simulations/results_template.py`, `VeraGridEngine/Devices/multi_circuit.py` (lines 743-800)

### Sparse Matrix and Admittance Matrix Access

**Connectivity matrices:**
- `MultiCircuit.get_bus_branch_connectivity_matrix() -> (Cf, Ct, C)` — returns from-bus, to-bus, and combined incidence matrices as `csc_matrix`
- `MultiCircuit.get_adjacent_matrix() -> csc_matrix` — bus adjacency matrix (C^T @ C)

**Admittance matrix:**
- Built inside `NumericalCircuit` via `Topology/admittance_matrices.py`
- Uses numba-JIT compiled functions for performance
- Accessible after compilation: `nc = compile_numerical_circuit_at(grid, t_idx=None)` then access `nc` data structures

The topology module (`Topology/topology.py`) implements island detection using numba-optimized DFS on CSC sparse matrices, independent of NetworkX.

Source: `VeraGridEngine/Devices/multi_circuit.py` (lines 878-920), `VeraGridEngine/Topology/admittance_matrices.py`, `VeraGridEngine/Topology/topology.py`

### OPF Constraint Architecture

The OPF is implemented in `Simulations/OPF/Formulations/`:
- `linear_opf_ts.py` — DC-OPF for time series using MIP solver
- `ac_opf_problem.py` — AC-OPF formulation
- `linear_opf_ts_b.py` — alternative linear OPF variant

The MIP interface (`Utils/MIP/selected_interface.py`) abstracts across:
- PuLP (always available)
- OR-Tools (optional)
- HiGHS (via SimpleMip)

Constraints are built programmatically inside the formulation functions (e.g., Kirchhoff balance, generator limits, branch flow limits). There is **no user-facing API to add custom constraints**. Modifying the OPF requires editing the formulation source files directly.

Solver selection is via `MIPSolvers` and `MIPFramework` enums in the options.

Source: `VeraGridEngine/Simulations/OPF/Formulations/linear_opf_ts.py`, `VeraGridEngine/Utils/MIP/selected_interface.py`

### Multi-Engine Support

The `EngineType` enum defines five computation backends:

| Engine | Compiler | Description |
|--------|----------|-------------|
| `VeraGrid` | `circuit_to_data.py` | Native Python/NumPy/Numba engine |
| `Bentayga` | `circuit_to_bentayga.py` | External C++ engine |
| `NewtonPA` | `circuit_to_newton_pa.py` | Newton Power Analytics |
| `PGM` | `circuit_to_pgm.py` | Power Grid Model (C library) |
| `GSLV` | `circuit_to_gslv.py` | GSLV engine |

Each compiler translates the `MultiCircuit` into the target engine's native data format. Engine selection is per-driver call. This is a form of extensibility — new engines can be added by creating a new compiler module and adding an `EngineType` enum value, though it requires modifying the engine source code.

Source: `VeraGridEngine/enumerations.py` (line 294), `VeraGridEngine/Compilers/`

### Import/Export Format Interoperability

**Import parsers (IO module):**
- MATPOWER `.m` files (`IO/matpower/`)
- PSS/e RAW and RAWX (`IO/raw/`)
- CIM/CGMES XML (`IO/cim/`)
- DGS (DIgSILENT) (`IO/dgs/`)
- EPC (`IO/epc/`)
- IIDM (`IO/iidm/`)
- UCTE-DEF (`IO/ucte/`)
- pandapower pickle/JSON/SQLite (`IO/others/pandapower_parser.py`)
- PyPSA Network objects (`IO/others/pypsa_parser.py`)
- ANAREDE (`IO/others/anarede.py`)
- RTE (`IO/others/rte_parser.py`)

**Export formats:**
- Native VeraGrid (`.veragrid`, `.ejson`, `.xlsx`)
- CGMES
- PSS/e RAW/RAWX

**pandapower interop:** The parser (`IO/others/pandapower_parser.py`) requires pandapower to be installed. It can read pandapower pickles, JSON, SQLite, and Excel files and convert them to `MultiCircuit`. Auto-detection functions (`is_pandapower_pickle()`, etc.) are provided.

**PyPSA interop:** The parser (`IO/others/pypsa_parser.py`) converts a `pypsa.Network` object into a `MultiCircuit`, handling buses, lines, transformers, generators, loads, HVDC links, batteries, and shunts. It handles coordinate projection (EPSG conversion) and time series profiles. PyPSA must be installed as an optional dependency.

Source: `VeraGridEngine/IO/others/pandapower_parser.py`, `VeraGridEngine/IO/others/pypsa_parser.py`

### Dynamic Simulation Framework

The `Devices/Dynamic/` module provides a block-diagram-based RMS (Root Mean Square) dynamic simulation framework:
- `DynamicModelHost` — container for block diagram models
- `BlockDiagramNode` / `BlockDiagramConnection` — graph structure for dynamic model topology
- `RmsModelTemplate` — templates for dynamic component models
- Templates in `Templates/Rms/` for generators, loads, lines, buses

The `Utils/Symbolic/` module provides a custom symbolic math engine for generating numba-compiled dynamic equations from block diagrams, enabling user-defined dynamic models.

Source: `VeraGridEngine/Devices/Dynamic/dynamic_model_host.py`, `VeraGridEngine/Utils/Symbolic/`

## Sources

1. VeraGridEngine 5.6.28 source code installed at `/workspace/evaluations/gridcal/.venv/lib/python3.12/site-packages/VeraGridEngine/`
2. [VeraGrid GitHub Repository](https://github.com/SanPen/VeraGrid)
3. [VeraGrid Documentation — Structure](https://veragrid.readthedocs.io/en/latest/md_source/structure.html)
4. [VeraGrid Documentation — Plugins](https://veragrid.readthedocs.io/en/latest/md_source/plugins.html)
5. [VeraGrid Documentation — User Interface](https://veragrid.readthedocs.io/en/stable/md_source/user_interface.html)
6. [VeraGrid Documentation — Main Page](https://veragrid.readthedocs.io/en/latest/)
7. [VeraGrid README.md](https://github.com/SanPen/VeraGrid/blob/master/README.md)
8. [GridCal API Demo](https://gridcal.readthedocs.io/en/latest/rst_source/getting_started/api_demo.html)

## Gaps and Uncertainties

- **Plugin system details in the GUI package are not inspectable** from the engine-only install (`VeraGridEngine`). The full plugin loader, registry, and lifecycle management presumably reside in the `VeraGrid` GUI package, which is not installed in this evaluation environment.
- **Custom constraint injection for OPF** appears unsupported without source modification. This should be verified during testing by attempting to subclass or wrap the OPF formulation.
- **No Graphs.jl interoperability** — GridCal is Python-only; there is no Julia interface or bridge. NetworkX is the graph library.
- **The multi-engine backends (Bentayga, NewtonPA, PGM, GSLV)** are optional commercial or third-party packages. Their availability and integration depth should be tested, but the compilers exist in source.
- **DataFrame export from the data model** (as opposed to results) is limited. There is no `MultiCircuit.buses_to_df()` or similar. Users would need to iterate device lists manually or use the `registered_properties` metadata to construct DataFrames. The `export_profiles()` method provides DataFrame-based profile export but not full model export.
- **The symbolic/block-diagram dynamic simulation framework** appears to be a newer addition. Its maturity and completeness relative to the static analysis features is unclear from code inspection alone.
- **Version context:** This analysis is based on VeraGridEngine 5.6.28. The project was renamed from GridCal/GridCalEngine to VeraGrid/VeraGridEngine. Some documentation URLs still reference "gridcal" in their paths.
