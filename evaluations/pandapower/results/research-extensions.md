# pandapower — Research: Extensions & Architecture

## Key Findings

- **pandapowerNet is a dict-of-DataFrames**: The core data structure (`pandapowerNet`) inherits from `ADict` (attribute-accessible dict). Every element type (bus, line, load, gen, trafo, etc.) is a pandas DataFrame, making the entire network natively interoperable with the pandas ecosystem. Users can freely add columns to existing tables or add entirely new keys to the dict without breaking power flow.
- **Controller framework provides the primary extension point**: Custom controllers inherit from `Controller` (or `BasicCtrl`) and override lifecycle methods (`time_step`, `initialize_control`, `control_step`, `is_converged`, `finalize_step`, etc.). Controllers are stored in `net.controller` DataFrame and auto-participate in time-series simulations and the control loop.
- **No formal plugin/registration API for new element types**: There is no `register_element()` or plugin system. Adding a new element type that participates in power flow requires modifying the internal `pd2ppc` conversion pipeline and result extraction — effectively forking the core code.
- **PYPOWER userfcn callback system for OPF constraints**: The inherited PYPOWER `add_userfcn`/`run_userfcn` mechanism supports callbacks at 5 stages (`ext2int`, `formulation`, `int2ext`, `printpf`, `savecase`). The `formulation` stage allows adding custom linear constraints and variables to the OPF model via `om.add_constraints()` and `om.add_vars()`.
- **NetworkX graph is a first-class output**: `pandapower.topology.create_nxgraph()` converts any network to a NetworkX `MultiGraph` with buses as nodes and branches as edges. Edge attributes include impedance data. An alternative `graph-tool` backend is also supported via `GraphToolInterface`.
- **Multiple solver backends**: Power flow supports NumPy/SciPy (default), Numba JIT acceleration, lightsim2grid (C++ backend, ~20x speedup), and power-grid-model (C++ steady-state solver). These are selected via `runpp()` kwargs, not a formal backend abstraction.
- **Rich serialization**: Networks can be saved/loaded as JSON, pickle, Excel, SQLite, PostgreSQL, and MATPOWER `.mat` files. JSON serialization handles custom controllers via `JSONSerializableClass`.
- **Converter ecosystem**: Bidirectional converters exist for PYPOWER/MATPOWER format, CIM (IEC 61970), PowerFactory (DIgSILENT), UCTE-DEF, and PowerModels.jl (via PandaModels.jl). pandapipes provides multi-energy coupling.
- **Architecture is modular but tightly coupled**: The codebase is organized into clear subpackages (control, topology, timeseries, opf, estimation, protection, etc.), but the power flow pipeline (`runpp` -> `_powerflow` -> `_pd2ppc` -> `_run_pf_algorithm` -> `_extract_results`) has hardcoded element-type handling throughout, limiting extensibility for new element types.
- **Time-series data sources are extensible**: The `DataSource` base class (`timeseries/data_source.py`) can be subclassed to provide custom time-series inputs. The `OutputWriter` class (`timeseries/output_writer.py`) accepts custom logging functions for arbitrary result extraction during simulations.
- **User power flow options allow persistent configuration**: `set_user_pf_options(net, ...)` stores options in `net.user_pf_options` that override internal defaults for all subsequent `runpp()` calls, enabling per-network persistent configuration without modifying function calls.
- **No Graphs.jl interop**: pandapower is pure Python. There is no Julia graph library interop beyond the PowerModels.jl OPF integration (which serializes to JSON, not graph objects).

## Detailed Notes

### Data Structure: pandapowerNet

The `pandapowerNet` class (defined in `auxiliary.py`, line 342) inherits from `ADict`, which itself is a dict subclass allowing attribute-style access (`net.bus` == `net["bus"]`). Every element type is a pandas DataFrame with typed columns defined in `network_structure.py`.

An empty network contains ~120+ keys including element tables, result tables (`res_*`), empty result templates (`_empty_res_*`), internal state (`_ppc`, `_pd2ppc_lookups`), and metadata (`version`, `f_hz`, `sn_mva`).

Users can add arbitrary keys: `net["my_custom_data"] = pd.DataFrame(...)` — this is preserved through serialization (JSON/pickle) and does not interfere with power flow. Existing element tables can also receive additional columns freely.

**Source:** `pandapower/auxiliary.py` lines 342-422; `pandapower/network_structure.py`

### Controller Framework (Primary Extension API)

The controller system has a two-level class hierarchy:

1. **`BasicCtrl`** (`control/basic_controller.py`): Base class with lifecycle hooks:
   - `time_step(container, time)` — called at start of each time step (time-series only)
   - `initialize_control(container)` — called after initial power flow, before control
   - `control_step(container)` — called when `is_converged()` returns False
   - `is_converged(container)` — check if controller has converged
   - `repair_control(container)` — recover from power flow divergence
   - `restore_init_state(container)` — restore pre-control state
   - `finalize_control(container)` — cleanup after control loop
   - `finalize_step(container, time)` — cleanup after each time step (time-series only)

2. **`Controller`** (subclass of `BasicCtrl`): Adds pandapower-specific registration — automatically adds itself to `net.controller` DataFrame with columns: `object`, `in_service`, `order`, `level`, `initial_run`, `recycle`.

**Predefined controllers** include:
- `ConstControl` — applies constant values from data sources to network elements
- `ContinuousTapControl`, `DiscreteTapControl` — transformer tap changers
- `DERController` — distributed energy resource voltage/var control
- `TrafoControl`, `ShuntControl`, `PQControl`, `StationControl`
- `CharacteristicControl` — piecewise-linear characteristic curves

The control loop (`run_control.py`) supports multi-level execution ordering via the `level` and `order` columns. Controllers at the same level run in a convergence loop; levels execute sequentially.

**Source:** `pandapower/control/basic_controller.py`; `pandapower/control/run_control.py`; [Building a Controller tutorial](https://github.com/e2nIEE/pandapower/blob/develop/tutorials/building_a_controller.ipynb)

### PYPOWER User Function Callbacks (OPF Extension)

pandapower inherits PYPOWER's `userfcn` callback mechanism for extending the OPF:

```python
from pandapower.pypower.add_userfcn import add_userfcn
ppci = add_userfcn(ppci, 'formulation', my_callback, args=my_data)
```

Five callback stages:
1. **`ext2int`** — after external-to-internal index conversion
2. **`formulation`** — after OPF model setup, before solving (add constraints/vars/costs here)
3. **`int2ext`** — before converting results back to external indexing
4. **`printpf`** — after result pretty-printing
5. **`savecase`** — when saving case to file

The `formulation` callback receives the OPF model object (`om`) which exposes:
- `om.add_constraints(name, A, l, u, varsets)` — add linear constraints `l <= A*x <= u`
- `om.add_vars(name, N, v0, vl, vu)` — add optimization variables
- `om.get_ppc()` — access the PYPOWER case dict

pandapower uses this internally for DC line constraints (see `_add_dcline_constraints` in `optimal_powerflow.py`).

**Limitation:** Only linear constraints can be added by users. Nonlinear constraint support exists in the data structure but has no public user-facing API.

**Source:** `pandapower/pypower/add_userfcn.py`; `pandapower/pypower/run_userfcn.py`; `pandapower/pypower/opf_model.py` lines 176-255; `pandapower/optimal_powerflow.py`

### PowerModels.jl Integration (Advanced OPF Extension)

The `runpm()` function provides a bridge to PowerModels.jl via PandaModels.jl:
- Supports custom Julia optimization files (`julia_file` parameter)
- Accepts a `pp_to_pm_callback` function to inject additional data into the PowerModels JSON data structure before solving
- Configurable model type (`pm_model="ACPPowerModel"`, `"DCPPowerModel"`, etc.)
- Configurable solver (`pm_solver="ipopt"`, `"juniper"` for MINLP, etc.)

This is the most flexible OPF extension path, as PowerModels.jl supports arbitrary nonlinear formulations, but requires Julia runtime.

**Source:** `pandapower/runpm.py`; `pandapower/opf/run_pandamodels.py`

### Network Graph Access (NetworkX)

`pandapower.topology.create_nxgraph()` provides comprehensive graph conversion:

```python
import pandapower.topology as top
mg = top.create_nxgraph(net, respect_switches=True)
```

Parameters control which elements become edges:
- `include_lines`, `include_trafos`, `include_trafo3ws`, `include_impedances`
- `include_dclines`, `include_tcsc`, `include_vsc`, `include_line_dc`
- `calc_branch_impedances=True` adds `r_ohm`, `x_ohm`, `z_ohm` edge attributes
- `branch_impedance_unit="ohm"` or `"pu"`
- `multi=True` returns `MultiGraph` (allows parallel edges), `False` returns `Graph`
- `library="networkx"` (default) or `"graph_tool"` (if graph-tool installed)

Graph analysis functions in `topology/graph_searches.py`:
- `connected_component(mg, bus)` / `connected_components(mg)`
- `calc_distance_to_bus(mg, bus)`
- `unsupplied_buses(net)`
- `determine_stubs(net)`
- `lines_on_path(mg, path)` / `elements_on_path(mg, path, element)`
- `find_basic_graph_characteristics(g, roots, characteristics)`
- `get_2connected_buses(g, roots)`

The `graph-tool` backend (`GraphToolInterface`) wraps `graph_tool.Graph` with a NetworkX-compatible API for performance on large networks.

**Source:** `pandapower/topology/create_graph.py`; `pandapower/topology/graph_searches.py`; `pandapower/topology/graph_tool_interface.py`

### Power Flow Pipeline Architecture

The power flow execution chain:

1. `runpp(net, ...)` — public API, validates options, delegates
2. `_powerflow(net, ...)` — creates auxiliary elements, initializes results
3. `_pd2ppc(net, ...)` — converts pandapower DataFrames → PYPOWER case dict (ppc)
   - `_build_bus_ppc()` — bus table
   - `_build_gen_ppc()` — generator table
   - `_build_branch_ppc()` — line/trafo/impedance → branch table
   - `_calc_pq_elements_and_add_on_ppc()` — loads/sgens → bus injections
   - `_build_svc_ppc()`, `_build_tcsc_ppc()`, `_build_vsc_ppc()` — FACTS devices
4. `_ppc2ppci(ppc, net)` — remove out-of-service elements
5. `_run_pf_algorithm(ppci, options)` — dispatch to solver:
   - `_run_newton_raphson_pf()` (default "nr")
   - `_run_bfswpf()` (backward/forward sweep)
   - `_run_dc_pf()` (DC approximation)
   - `_runpf_pypower()` (Gauss-Seidel, fast-decoupled)
6. `_extract_results(net, result)` — writes results back to `net.res_*` DataFrames

Each step has hardcoded handling for known element types. Adding a new element type requires changes in `pd2ppc.py`, `build_bus.py`/`build_branch.py`/`build_gen.py`, `results.py`/`results_bus.py`/`results_branch.py`, and `network_structure.py`.

**Source:** `pandapower/run.py`; `pandapower/powerflow.py`; `pandapower/pd2ppc.py`

### Solver Backend Options

pandapower v3.4.0 supports these solver backends via `runpp()` parameters:

| Backend | Activation | Notes |
|---------|-----------|-------|
| NumPy/SciPy (PYPOWER) | Default | Pure Python, Numba-optional |
| Numba JIT | `numba=True` (default if available) | JIT-compiles matrix construction |
| lightsim2grid | `lightsim2grid=True` | C++ backend, ~20x speedup |
| power-grid-model | Via `PandaPowerConverter` | C++ steady-state solver |

These are not a pluggable backend abstraction — each requires specific code paths in the power flow function.

**Source:** `pandapower/run.py` lines 60-95; [pandapower AC power flow docs](https://pandapower.readthedocs.io/en/latest/powerflow/ac.html)

### Serialization and Interoperability

**File I/O formats** (`file_io.py`, `sql_io.py`):
- `to_json()` / `from_json()` — JSON with `PPJSONEncoder`/`PPJSONDecoder`, handles DataFrames, numpy arrays, custom objects. Supports encryption.
- `to_pickle()` / `from_pickle()` — Python pickle (protocol 2)
- `to_excel()` / `from_excel()` — one sheet per element table
- `to_sqlite()` / `from_sqlite()` — SQLite database
- `to_postgresql()` / `from_postgresql()` — PostgreSQL database

**Format converters** (`converter/` package, 7 subpackages in v3.4.0):
- **MATPOWER**: `from_mpc()` / `to_mpc()` — reads `.mat` and `.m` files via `matpowercaseframes` or `scipy.io`
- **PYPOWER**: `from_ppc()` / `to_ppc()` — direct ppc dict conversion
- **CIM** (IEC 61970): `from_cim()` with full CGMES profile support (detailed converter classes per element type)
- **PowerFactory**: `export_pfd_to_pp()` — DIgSILENT PowerFactory export (requires PowerFactory Engine mode or GUI tool)
- **UCTE-DEF**: `from_ucte()` — European transmission network format
- **JAO**: JAO Static Grid Model converter (European grid operator data format)
- **PowerModels.jl**: `to_pm()` / `from_pm()` — JSON-based bridge to Julia (PandaModels.jl)

**Source:** `pandapower/file_io.py`; `pandapower/sql_io.py`; `pandapower/converter/` subpackages

### Time-Series Extensibility

The time-series framework (`timeseries/`) has two extensible components:

1. **DataSource** (`timeseries/data_source.py`): Abstract base class (inherits `JSONSerializableClass`) with a `get_time_step_value(time_step, profile_name, scale_factor)` method. Users can subclass to provide custom data feeds (e.g., from databases, APIs, or simulation models). The built-in `DFData` class wraps a pandas DataFrame as the default data source.

2. **OutputWriter** (`timeseries/output_writer.py`): Stores results during time-series runs. Beyond the standard `log_variable(table, column)` for logging result table values, it accepts custom functions via `output_list` that are called at each time step. Custom functions can perform arbitrary computations on the network state (e.g., compute max line loading, aggregate costs).

**Source:** `pandapower/timeseries/data_source.py`; `pandapower/timeseries/output_writer.py`

### User Power Flow Options

`set_user_pf_options(net, ...)` provides persistent per-network power flow configuration stored in `net.user_pf_options`. These options (tolerance, algorithm, solver backend, etc.) override internal defaults but are themselves overridden by explicit `runpp()` keyword arguments. Non-standard parameters are accepted with a warning, allowing custom options to be passed through to extension code.

**Source:** `pandapower/run.py` lines 28-65

### Multi-Energy Coupling (pandapipes)

pandapipes is a companion package that provides:
- Pipe flow simulation (gas, water, district heating)
- `MultiNet` container holding multiple pandapower/pandapipes networks
- Coupling controllers (e.g., `P2GControlMultiEnergy`) for power-to-gas, gas-to-power, heat pump scenarios
- Same controller framework as pandapower (`BasicCtrl` inheritance)

**Source:** [pandapipes Multi Energy Networks docs](https://pandapipes.readthedocs.io/en/latest/multi_energy_nets.html); [pandapipes GitHub](https://github.com/e2nIEE/pandapipes)

### Additional Analysis Modules

pandapower includes several domain-specific extension modules:
- **State estimation** (`estimation/`): WLS and LAV estimators
- **Short-circuit analysis** (`shortcircuit/`): IEC 60909 calculations
- **Protection** (`protection/`): Fuse and overcurrent relay modeling
- **Grid equivalents** (`grid_equivalents/`): Ward and REI network reduction
- **Contingency analysis** (`contingency/`): N-1/N-k security assessment
- **Diagnostics** (`diagnostic/`): Network validation and error detection

These are all internal modules, not third-party plugins — there is no plugin discovery mechanism.

### DataFrame Interoperability

Since all element data lives in pandas DataFrames, interoperability is seamless:
- Direct access: `net.bus`, `net.line`, `net.res_bus`, etc. are standard `pd.DataFrame` objects
- Standard pandas operations work: filtering, groupby, merge, vectorized math
- Results are immediately available as DataFrames after `runpp()`: `net.res_bus.vm_pu`, `net.res_line.loading_percent`, etc.
- Can export any table to CSV, Parquet, HDF5 via standard pandas methods
- Integration with NumPy/SciPy for custom analysis on result data

**Source:** `pandapower/auxiliary.py` (pandapowerNet class definition)

## Sources

1. `pandapower/auxiliary.py` — pandapowerNet class, ADict base class
2. `pandapower/network_structure.py` — element table schema definitions
3. `pandapower/control/basic_controller.py` — BasicCtrl and Controller classes
4. `pandapower/control/run_control.py` — control loop execution
5. `pandapower/topology/create_graph.py` — NetworkX graph creation
6. `pandapower/topology/graph_searches.py` — graph analysis functions
7. `pandapower/topology/graph_tool_interface.py` — graph-tool backend
8. `pandapower/powerflow.py` — power flow pipeline
9. `pandapower/pd2ppc.py` — DataFrame-to-PYPOWER conversion
10. `pandapower/run.py` — runpp public API, user_pf_options
11. `pandapower/optimal_powerflow.py` — OPF with userfcn callbacks
12. `pandapower/pypower/add_userfcn.py` — callback registration API
13. `pandapower/pypower/run_userfcn.py` — callback execution
14. `pandapower/pypower/opf_model.py` — OPF model (add_constraints, add_vars)
15. `pandapower/runpm.py` — PowerModels.jl integration
16. `pandapower/file_io.py` — JSON/pickle/Excel serialization
17. `pandapower/sql_io.py` — SQLite/PostgreSQL I/O
18. `pandapower/converter/` — MATPOWER, CIM, PYPOWER, PowerFactory, UCTE converters
19. `pandapower/timeseries/data_source.py` — DataSource base class
20. `pandapower/timeseries/output_writer.py` — OutputWriter class
21. [pandapower documentation](https://pandapower.readthedocs.io/en/latest/)
22. [pandapower GitHub](https://github.com/e2nIEE/pandapower)
23. [Building a Controller tutorial](https://github.com/e2nIEE/pandapower/blob/develop/tutorials/building_a_controller.ipynb)
24. [Internal Data Structure tutorial](https://github.com/e2nIEE/pandapower/blob/develop/tutorials/internal_datastructure.ipynb)
25. [pandapipes Multi-Energy Networks](https://pandapipes.readthedocs.io/en/latest/multi_energy_nets.html)
26. [lightsim2grid benchmarks](https://lightsim2grid.readthedocs.io/en/latest/benchmarks.html)
27. [pandapower AC power flow docs](https://pandapower.readthedocs.io/en/latest/powerflow/ac.html)
28. [Converter documentation](https://pandapower.readthedocs.io/en/latest/converter.html)
29. [Save and Load Networks docs](https://pandapower.readthedocs.io/en/latest/file_io.html)
30. [Optimization with PandaModels.jl docs](https://pandapower.readthedocs.io/en/v2.10.1/opf/powermodels.html)

## Gaps and Uncertainties

- **No documented API for adding new element types**: The process of adding a new element type (e.g., a custom FACTS device or novel storage model) that participates in power flow is not documented. It requires modifying multiple internal modules (`pd2ppc.py`, `build_*.py`, `results*.py`, `network_structure.py`). Whether this is intentionally left as "fork the code" or an accidental gap in documentation is unclear.
- **Controller framework vs power flow decoupling**: Controllers operate in an outer loop around power flow, not within it. A controller that needs to modify the admittance matrix or add custom equations to the Newton-Raphson system cannot do so through the controller API — it would need to modify internal PYPOWER structures.
- **graph-tool backend completeness**: The `GraphToolInterface` wraps graph-tool with a NetworkX-like API, but the wrapper appears incomplete (e.g., `add_edge_data` is a TODO stub). Unclear how well-tested this is in practice.
- **lightsim2grid and power-grid-model feature parity**: Not all pandapower features may be supported when using these alternative backends (e.g., 3-phase power flow, FACTS devices, distributed slack). The exact feature matrix needs testing.
- **User function callbacks are PYPOWER-inherited, not pandapower-native**: The `userfcn` system works at the ppc/ppci level, not the pandapower DataFrame level. Users must understand the internal PYPOWER data representation to use it effectively.
- **No event/signal system**: There is no publish/subscribe or event system. Extensions cannot hook into arbitrary points in the power flow pipeline without modifying source code.
- **Multi-energy coupling via pandapipes**: The coupling mechanism relies on the shared controller framework. Whether this extends to other energy carriers beyond gas/heat/water (e.g., hydrogen) needs verification.
- **Custom cost functions in OPF**: While polynomial and piecewise-linear costs are supported natively, adding a fully custom nonlinear objective function requires the PowerModels.jl pathway or modifying PYPOWER internals.
