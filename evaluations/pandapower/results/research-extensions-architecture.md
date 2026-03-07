# pandapower -- Research: Extensions & Architecture

**Version analyzed:** 3.4.0
**Date:** 2026-03-06

## Key Findings

- pandapower's core data structure (`pandapowerNet`) is a dict-of-DataFrames, making it trivially interoperable with pandas. Every element type (bus, line, load, gen, trafo, etc.) is a `pd.DataFrame` row-per-element. Results are stored in parallel `res_*` DataFrames.
- The controller framework (`BasicCtrl` / `Controller` base classes) provides the primary extension mechanism: users subclass `Controller` and override lifecycle hooks (`time_step`, `initialize_control`, `control_step`, `is_converged`, `finalize_control`, `finalize_step`, `repair_control`).
- NetworkX graph conversion is first-class via `pandapower.topology.create_nxgraph()`, returning a `nx.MultiGraph` with bus nodes and branch edges. An optional `graph_tool` backend exists via `GraphToolInterface`.
- The inherited PYPOWER `userfcn` callback system provides five hook stages for the OPF pipeline: `ext2int`, `formulation`, `int2ext`, `printpf`, `savecase`. Custom linear constraints can be added to the OPF model via `opf_model.add_constraints()`.
- The internal architecture follows a two-layer pattern: user-facing pandas DataFrames (pandapower) are converted to MATPOWER-style numpy arrays (`ppc`/`ppci`) for computation. Post-solve, results are mapped back to DataFrames.
- PTDF, LODF, and OTDF matrices are available via `pandapower.pypower.makePTDF` and `pandapower.pypower.makeLODF`, operating on internal `ppc` arrays.
- Multiple solver backends are supported: native PYPOWER Newton-Raphson (with optional numba JIT), lightsim2grid (C++ backend), backward/forward sweep, Gauss-Seidel, fast-decoupled, and power-grid-model.
- Julia/PowerModels.jl integration via `runpm()` with a `pp_to_pm_callback` parameter for injecting custom data into the PowerModels data structure.
- Serialization supports JSON, pickle, Excel, SQLite, and PostgreSQL. Custom objects (controllers) use `JSONSerializableClass` with a registry-based deserialization system.
- Format converters exist for MATPOWER (.m), PYPOWER (ppc dict), CIM/CGMES, PowerFactory, UCTE, and JAO formats.
- There is **no formal plugin registry** or plugin discovery mechanism. Extension is via subclassing, monkey-patching, or callback parameters.

## Detailed Notes

### Internal Architecture: Separation of Concerns

pandapower follows a clear two-layer architecture:

1. **User-facing layer** (`pandapowerNet`): A `dict`-subclass (`ADict`) where each key maps to a `pd.DataFrame` for an element type (bus, line, trafo, load, gen, etc.). This is what users interact with.

2. **Solver layer** (`ppc`/`ppci`): MATPOWER-compatible numpy arrays used internally by the power flow and OPF solvers. The conversion pipeline is:
   ```
   pandapowerNet -> _pd2ppc() -> ppc (full) -> _ppc2ppci() -> ppci (in-service only) -> solver -> results back to net.res_*
   ```

Key internal data structures accessible after `runpp()`:
- `net._ppc` -- full MATPOWER-format dict with keys: `bus`, `gen`, `branch`, `baseMVA`, `internal`
- `net._ppc['internal']` -- contains `Ybus`, `Yf`, `Yt`, `V`, `J` (Jacobian), `Sbus`, `ref`, `pv`, `pq` arrays
- `net._pd2ppc_lookups` -- mapping from pandapower indices to ppc indices

Source: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/pd2ppc.py`, `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/powerflow.py`

### Module Organization

The package is organized into ~18 subpackages, each addressing a specific concern:

| Module | Purpose |
|--------|---------|
| `create/` | Element creation functions (`create_bus`, `create_line`, etc.) |
| `pf/` | Power flow solvers (Newton-Raphson, BFSW, DC) |
| `opf/` | Optimal power flow setup |
| `pypower/` | MATPOWER-derived solver internals (idx_bus, idx_brch, opf_model, etc.) |
| `control/` | Controller framework and predefined controllers |
| `timeseries/` | Time series simulation loop |
| `topology/` | NetworkX graph creation and graph search algorithms |
| `estimation/` | State estimation |
| `converter/` | Format converters (MATPOWER, PYPOWER, CIM, PowerFactory, UCTE, JAO) |
| `shortcircuit/` | Short circuit calculations |
| `contingency/` | N-1 contingency analysis |
| `grid_equivalents/` | Ward/REI network equivalents |
| `protection/` | Protection device modeling |
| `diagnostic/` | Network diagnostics with extensible function registry |
| `plotting/` | Matplotlib and Plotly visualization |
| `networks/` | Predefined test/benchmark networks |
| `toolbox/` | Utility functions (element selection, grid modification, comparison) |

Source: `pandapower/__init__.py`

### Controller Extension Framework

The controller framework is the primary extension mechanism. It uses an OOP inheritance pattern:

```
JSONSerializableClass
  -> BasicCtrl (base with lifecycle hooks)
    -> Controller (adds net integration, ordering, levels)
      -> ConstControl, TrafoController, DERController, etc.
```

**Lifecycle hooks** (called in order during `run_control`):

1. `time_step(container, time)` -- called at start of each time step (timeseries only)
2. `initialize_control(container)` -- called after initial power flow, before control loop
3. `control_step(container)` -- called when `is_converged()` returns False
4. `is_converged(container)` -- checks if controller has converged
5. `repair_control(container)` -- called if power flow diverges
6. `finalize_control(container)` -- called at end of control loop
7. `finalize_step(container, time)` -- cleanup after each time step (timeseries only)
8. `restore_init_state(container)` -- restore net state on failure

Controllers support **ordering** (`order` parameter) and **levels** (`level` parameter) for controlling execution sequence. Multiple controllers can run at different levels, with each level triggering a separate power flow.

Controllers are stored in `net.controller` DataFrame, with the controller object in the `'object'` column.

Source: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/control/basic_controller.py`, `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/control/run_control.py`

### PYPOWER User Function Callbacks (OPF)

The inherited PYPOWER `userfcn` system provides callback hooks at five stages of the OPF pipeline:

1. **`ext2int`** -- called after external-to-internal index conversion; for reordering custom data
2. **`formulation`** -- called after OPF model initialization but before solver; for adding custom variables, constraints, or costs
3. **`int2ext`** -- called before internal-to-external conversion; for converting custom results
4. **`printpf`** -- called after standard output printing; for custom result display
5. **`savecase`** -- called when saving; for writing custom data fields

Registration via `add_userfcn(ppc, stage, fcn, args)`.

**Custom OPF constraints** can be added through the `formulation` callback using `opf_model.add_constraints(name, A, l, u, varsets)` for linear constraints of the form `l <= A * x <= u`. Nonlinear constraints are internally supported but not exposed to users.

pandapower itself uses this mechanism: `_add_dcline_constraints` adds DC line coupling constraints via `om.add_constraints('dcline', Adc, nL0, nL0, ['Pg'])`.

Source: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/pypower/add_userfcn.py`, `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/optimal_powerflow.py`, `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/pypower/opf_model.py`

### NetworkX Graph Access and Topology Analysis

`pandapower.topology.create_nxgraph(net)` converts a pandapower network to a `networkx.MultiGraph`:

- **Nodes** = buses (in-service only by default)
- **Edges** = lines, transformers, impedances, DC lines, TCSC, VSC elements
- Edge keys are tuples like `('line', 0)` identifying the element type and index
- Edge data includes `weight` (line length in km) and optionally branch impedances (`r_ohm`, `x_ohm`, `z_ohm` or per-unit equivalents)

Parameters for customization:
- `respect_switches` -- honor open switches (default True)
- `include_lines`, `include_trafos`, etc. -- selective element inclusion
- `calc_branch_impedances` -- add impedance weights for shortest-path analysis
- `library="graph_tool"` -- use graph-tool backend instead of NetworkX (via `GraphToolInterface` adapter class)

Built-in graph search functions in `pandapower.topology`:
- `connected_component(mg, bus)` / `connected_components(mg)`
- `calc_distance_to_bus(mg, bus)`
- `unsupplied_buses(net)`
- `find_basic_graph_characteristics(mg)` / `find_graph_characteristics(mg)`
- `determine_stubs(net)` -- find stub lines/buses
- `elements_on_path(mg, path)` / `lines_on_path(mg, path)`

Source: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/topology/create_graph.py`, `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/topology/graph_searches.py`

### PTDF / LODF / OTDF Matrix Computation

Available via PYPOWER-derived functions operating on internal `ppc` arrays:

- `makePTDF(baseMVA, bus, branch, slack)` -- DC Power Transfer Distribution Factor matrix (nbr x nb)
  - Supports sparse solvers (`using_sparse_solver=True`)
  - Supports distributed slack (weight vector or matrix)
  - Can compute for subset of branches (`branch_id` parameter)
- `makeLODF(branch, PTDF)` -- Line Outage Distribution Factor matrix (nbr x nbr)
- `makeOTDF(PTDF, LODF, outage_branches)` -- Outage Transfer Distribution Factor matrix

These require converting the pandapower net to ppc format first, then extracting `bus` and `branch` arrays.

Source: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/pypower/makePTDF.py`, `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/pypower/makeLODF.py`

### Solver Backend Architecture

pandapower supports multiple solver backends, selectable via `runpp()` parameters:

| Backend | Parameter | Notes |
|---------|-----------|-------|
| PYPOWER Newton-Raphson | `algorithm='nr'` (default) | With optional numba JIT acceleration |
| Iwamoto Newton-Raphson | `algorithm='iwamoto_nr'` | More robust, potentially slower |
| Backward/Forward Sweep | `algorithm='bfsw'` | For radial/weakly-meshed networks |
| Gauss-Seidel | `algorithm='gs'` | PYPOWER implementation |
| Fast-Decoupled (BX/XB) | `algorithm='fdbx'`/`'fdxb'` | PYPOWER implementation |
| lightsim2grid | `lightsim2grid=True` | C++ backend, significantly faster |
| power-grid-model | Via `PGM_IMPORTED` flag | Alternative backend from Alliander |
| DC power flow | `rundcpp()` | Linearized DC approximation |

The solver selection happens in `run.py`/`powerflow.py`; the Newton-Raphson implementation switches between Python/numba and lightsim2grid at runtime based on the `lightsim2grid` option.

Source: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/run.py`, `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/pf/run_newton_raphson_pf.py`

### Julia/PowerModels.jl Integration

`pandapower.runpm()` provides OPF via Julia's PowerModels.jl through PandaModels.jl:

- Converts pandapower net to PowerModels JSON format via `convert_pp_to_pm()`
- Supports many PM models: `ACPPowerModel`, `DCPPowerModel`, `SOCWRPowerModel`, etc.
- Supports multiple solvers: ipopt, HiGHS, juniper (for mixed-integer)
- **`pp_to_pm_callback`** parameter: a Python function called during conversion to inject custom data into the PowerModels data structure
- Specialized run functions: `runpm_dc_opf`, `runpm_ac_opf`, `runpm_tnep` (transmission network expansion), `runpm_ots` (optimal transmission switching), `runpm_storage_opf`, `runpm_vstab` (voltage stability)

Source: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/runpm.py`, `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/converter/pandamodels/to_pm.py`

### Serialization and Interoperability

**File I/O formats:**
- JSON: `pp.to_json(net)` / `pp.from_json(path)` -- primary format, human-readable
- Pickle: `pp.to_pickle(net)` / `pp.from_pickle(path)` -- binary, fast
- Excel: `pp.to_excel(net)` / `pp.from_excel(path)` -- one sheet per element table
- SQLite: `pp.to_sqlite(net)` / `pp.from_sqlite(path)` -- database storage
- PostgreSQL: `pp.to_postgresql(net)` / `pp.from_postgresql(path)` -- remote database

**Format converters** (in `pandapower.converter`):
- MATPOWER: `from_mpc(path)` / `to_mpc(net, path)` -- .m and .mat files
- PYPOWER: `from_ppc(ppc)` / `to_ppc(net)` -- Python dict format
- CIM/CGMES: import from CIM XML
- PowerFactory: import from DIgSILENT PowerFactory
- UCTE: import from UCTE-DEF format
- JAO: import from JAO format

**Custom object serialization:**
Controllers and other custom objects extend `JSONSerializableClass`, which provides `to_json()` / `to_dict()` methods. Deserialization uses a registry pattern (`FromSerializableRegistry` / `FromSerializable`) with `@from_serializable.register()` decorators to dispatch by class name and module name.

Source: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/file_io.py`, `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/io_utils.py`

### Diagnostic Extension Pattern

The `Diagnostic` class provides a registration-based extension pattern:

```python
diag = Diagnostic(add_default_functions=False)
diag.register_function(MyCustomDiagnostic(), argument_names=None, name="my_check")
result = diag.diagnose_network(net)
```

Users can implement the `DiagnosticFunction` base class and register it. This is one of the few places where pandapower uses an explicit registration pattern rather than inheritance.

Source: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/diagnostic/diagnostic.py`

### Timeseries Simulation Architecture

The time series loop (`run_timeseries`) orchestrates controllers and data sources:

1. `init_time_series()` -- initialize controllers, output writers, time steps
2. For each time step:
   - `control_time_step()` -- call `time_step()` on all controllers
   - `run_time_step()` -- run power flow with `run_control`
   - `output_writer_routine()` -- write results via `OutputWriter`
   - `finalize_step()` -- cleanup
3. `cleanup()` -- final cleanup

The `run` parameter in `run_timeseries(net, run=my_custom_pf)` allows replacing the default `runpp` with a custom function, enabling integration of custom solvers.

`OutputWriter` is a controller subclass that stores selected results at each time step, supporting CSV, Excel, JSON, and pickle output.

Source: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/timeseries/run_time_series.py`

### Standard Types Library

pandapower includes a library of standard equipment types (lines, transformers) that can be extended:

- `pp.create_std_type(net, data, name, element)` -- add a custom standard type
- `pp.create_std_types(net, data, element)` -- add multiple standard types
- `pp.available_std_types(net, element)` -- list available types
- `pp.load_std_type(net, name, element)` -- load type parameters

Standard types are stored in `net.std_types` (a dict of dicts), not in DataFrames.

Source: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/std_types.py`

### Contingency Analysis

Built-in N-1 contingency analysis via `run_contingency(net)` and `run_contingency_ls2g(net)` (using lightsim2grid for speed). Results include element limit checking and violation reporting.

The PTDF/LODF-based approach (`makePTDF` + `makeLODF` + `makeOTDF`) provides a faster DC approximation for contingency screening.

Source: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/contingency/contingency.py`

### DataFrame Interoperability

Since all network data is stored in pandas DataFrames, interoperability with the pandas ecosystem is native:

- Direct column access: `net.bus.vn_kv`, `net.line.r_ohm_per_km`
- Results as DataFrames: `net.res_bus.vm_pu`, `net.res_line.loading_percent`
- Standard pandas operations work: filtering, grouping, merging, plotting
- Integration with pandera for schema validation (pandapower uses pandera internally)

The `pandapowerNet` class itself inherits from `dict`, so `net.keys()`, iteration, and dict-like access all work.

### Custom Network Elements

There is **no formal custom element API**. pandapower's element set is fixed in the source code. To add a truly new element type:

1. Add a DataFrame to `net` for the new element
2. Write conversion logic to map it into the `ppc` arrays in `_pd2ppc()`
3. Write result extraction logic

This requires modifying pandapower internals. The practical alternative is to model custom elements using existing element types (e.g., model a battery as a `storage` or `sgen` with a controller).

### Ecosystem: pandapipes and pandahub

- **pandapipes**: Sibling project for pipe networks (gas, heat, water), sharing the same architecture and controller framework. Multi-energy systems can couple pandapower and pandapipes networks.
- **pandahub**: MongoDB-based data hub for storing/sharing pandapower and pandapipes networks, with REST API and authentication.
- **pandaplan**: Commercial extension (not open source) referenced in some imports.

Source: [e2nIEE GitHub](https://github.com/e2nIEE), [pandahub PyPI](https://pypi.org/project/pandahub/)

## Sources

1. pandapower source code v3.4.0 at `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/`
2. [pandapower documentation - Datastructure and Elements](https://pandapower.readthedocs.io/en/develop/elements.html)
3. [pandapower documentation - Create networkx graph](https://pandapower.readthedocs.io/en/latest/topology/create_graph.html)
4. [pandapower documentation - Predefined Controllers](https://pandapower.readthedocs.io/en/latest/control/controller.html)
5. [pandapower documentation - Optimization with PYPOWER](https://pandapower.readthedocs.io/en/latest/opf/pypower_run.html)
6. [pandapower documentation - Save and Load Networks](https://pandapower.readthedocs.io/en/latest/file_io.html)
7. [pandapower documentation - Timeseries Example](https://pandapower.readthedocs.io/en/latest/timeseries/timeseries_example.html)
8. [pandapower documentation - Changelog](https://pandapower.readthedocs.io/en/latest/about/changelog.html)
9. [pandapower GitHub repository](https://github.com/e2nIEE/pandapower)
10. [pandahub GitHub repository](https://github.com/e2nIEE/pandahub)
11. [Power Grid Model IO - PandaPower conversion](https://power-grid-model-io.readthedocs.io/en/stable/examples/pandapower_example.html)
12. [pandapower PyPI](https://pypi.org/project/pandapower/)

## Gaps and Uncertainties

- **No formal plugin API**: pandapower has no plugin discovery, plugin registry, or plugin packaging mechanism. Extension is via subclassing controllers or modifying source code. This limits the ability to distribute reusable third-party extensions.
- **Custom element creation is unsupported**: Adding new element types (beyond the ~25 built-in ones) requires modifying pandapower's `_pd2ppc()` conversion pipeline. There is no documented or public API for this.
- **OPF custom constraints**: While linear constraints can be added via `add_constraints()`, this operates at the PYPOWER level (numpy arrays), not the pandapower level (DataFrames). Users must understand the internal ppc indexing. Nonlinear user constraints are not supported.
- **graph_tool backend**: The `GraphToolInterface` adapter exists but its completeness and testing status are unclear. It wraps graph_tool to look like NetworkX but may not support all topology functions.
- **lightsim2grid integration depth**: It's unclear whether all pandapower features (FACTS elements, distributed slack, TDPF) work with the lightsim2grid backend, or only basic Newton-Raphson.
- **PandaModels.jl callback**: The `pp_to_pm_callback` is documented only as a function signature; examples of custom callback usage are sparse.
- **Version-specific behavior**: The `pandapowerNet` data structure has evolved across versions (format versioning via `__format_version__`), and `convert_format` handles backward compatibility. The extent of breaking changes between major versions is unclear.
- **Pandera schema validation**: pandapower imports pandera but the extent to which schemas are enforced at runtime (vs. just type annotations) needs verification during testing.
