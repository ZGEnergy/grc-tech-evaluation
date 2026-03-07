# PyPSA -- Research: Extensions & Architecture

**Version studied:** PyPSA 1.1.2
**Date:** 2026-03-06

## Key Findings

- PyPSA has **no formal plugin/callback/hook system**. A grep of the entire source tree for "hook", "plugin", "callback", and "register_" yields zero hits. Extension is done through compositional patterns instead.
- The primary extension mechanism for optimization is the **`extra_functionality` callback** passed to `n.optimize()`, which receives `(n, snapshots)` after model creation but before solving. Users can also call `n.optimize.create_model()` / `n.optimize.solve_model()` separately for full control.
- Custom constraints are added by accessing the **Linopy model** at `n.model` and calling `m.add_constraints()` / `m.add_variables()` / modifying `m.objective`. This is well-documented and is the recommended extensibility pattern.
- **Custom component types** can be registered at the module level via `pypsa.components.types.add_component_type()`, which accepts a name, category, and defaults DataFrame. However, custom components are **not automatically wired into the optimizer** -- users must handle their optimization logic via `extra_functionality`.
- The Network class is built via **mixin composition** (8+ mixins for graph, IO, power flow, optimization, etc.), not inheritance. This provides clear separation of concerns but makes subclassing fragile.
- **NetworkX graph** access is built-in via `n.graph()`, which returns an `OrderedGraph` (a `networkx.MultiGraph` subclass). Adjacency and incidence matrices are also available as pandas DataFrames or scipy sparse matrices.
- All component data is stored as **pandas DataFrames** (static) and **dicts of DataFrames** (dynamic/time-series), with an additional **xarray DataArray accessor** (`c.da`) for N-D labeled array operations.
- Import/export supports **netCDF, HDF5, CSV folders, Excel, PyPower PPC dicts, and pandapower networks**. There is no native Graphs.jl or Julia interop.
- The `NetworkCollection` class (v0.35+) enables batch operations across multiple Network instances, useful for scenario analysis.
- The options system (`pypsa.options`) provides hierarchical configuration but is limited to PyPSA internals (solver defaults, API mode, etc.) -- it is not an extension point.

## Detailed Notes

### Extension Mechanism: `extra_functionality` Callback

The primary way to extend PyPSA's optimization is through the `extra_functionality` parameter of `n.optimize()`. This callable receives the network and snapshot index after the Linopy model is fully constructed but before solving:

```python
def custom_constraints(n, sns):
    m = n.model
    gen_p = m.variables["Generator-p"]
    lhs = gen_p.sum("snapshot")
    m.add_constraints(lhs >= 100, name="MinGeneration")

n.optimize(extra_functionality=custom_constraints)
```

Alternatively, users can split the workflow for more control:

```python
m = n.optimize.create_model()
# ... modify m (add variables, constraints, change objective) ...
n.optimize.solve_model()
```

**Source:** `pypsa/optimization/optimize.py`, class `OptimizationAccessor.__call__()` (lines showing `if extra_functionality: extra_functionality(n, sns)` between `create_model` and `m.solve`). Also [Custom Constraints docs](https://docs.pypsa.org/latest/user-guide/optimization/custom-constraints/).

### Extension Mechanism: Custom Component Types

PyPSA allows registering entirely new component types at the module level:

```python
import pypsa.components.types as ct

defaults_df = pd.DataFrame({
    "attribute": ["name", "attribute_a"],
    "type": ["string", "float"],
    "unit": ["n/a", "n/a"],
    "default": ["n/a", 1],
    "description": ["Unique name", "Some custom attribute"],
    "status": ["Input (required)", "Input (optional)"]
})
ct.add_component_type(
    name="CustomComponent",
    list_name="custom_components",
    description="A custom component",
    category="custom",
    defaults_df=defaults_df,
)
```

However, as documented in [GitHub issue #856](https://github.com/PyPSA/PyPSA/issues/856), custom components are **not automatically integrated with the Linopy optimizer**. Users must manually define variables, constraints, and objective terms for custom components via `extra_functionality`. The source code comment `# TODO better path handeling, integrate custom components` in `pypsa/components/types.py` confirms this is a known gap.

**Source:** `pypsa/components/types.py`, function `add_component_type()`.

### Architecture: Mixin-Based Composition

The `Network` class is composed of 8 mixin classes, each responsible for a distinct concern:

| Mixin | Responsibility |
|-------|---------------|
| `NetworkComponentsMixin` | Component store initialization, property accessors (`n.generators`, `n.buses`, etc.) |
| `NetworkDescriptorsMixin` | Computed properties (branch lists, component categories) |
| `NetworkTransformMixin` | Network manipulation (add/remove/copy components) |
| `NetworkIndexMixin` | Index management for snapshots, investment periods |
| `NetworkConsistencyMixin` | Data validation and consistency checks |
| `NetworkGraphMixin` | NetworkX graph construction, adjacency/incidence matrices |
| `NetworkPowerFlowMixin` | Power flow calculations (Newton-Raphson, linear PF) |
| `NetworkIOMixin` | All import/export functionality |

Extended functionality is provided through **accessor objects** instantiated on the Network:
- `n.optimize` -> `OptimizationAccessor` (Linopy model building and solving)
- `n.cluster` -> `ClusteringAccessor` (spatial and temporal clustering)
- `n.statistics` -> `StatisticsAccessor` (energy balance, cost summaries)
- `n.plot` -> `PlotAccessor` (matplotlib/cartopy visualization)

The `OptimizationAccessor` itself inherits from `OptimizationAbstractMixin` -> `OptimizationAbstractMGAMixin`, adding iterative transmission expansion and MGA (Modeling to Generate Alternatives) capabilities.

**Source:** `pypsa/networks.py` (Network class definition), `pypsa/optimization/optimize.py` (OptimizationAccessor), `pypsa/optimization/abstract.py` (abstract mixin chain).

### Graph Access and Matrix Operations

PyPSA provides first-class NetworkX integration:

- **`n.graph(branch_components, weight, inf_weight)`** returns an `OrderedGraph` (subclass of `networkx.MultiGraph`). Edges are keyed by `(component_type, component_name)` tuples. Supports filtering by branch component type and weighting by any branch attribute.
- **`n.adjacency_matrix(return_dataframe=True)`** returns a pandas DataFrame (or scipy sparse matrix for backwards compatibility). Supports per-branch weighting and investment period filtering.
- **`n.incidence_matrix()`** returns a scipy CSR sparse matrix representing the directed bus-branch incidence.

The graph module uses `OrderedDict`-based node/adjacency storage to preserve insertion order.

**Source:** `pypsa/network/graph.py`, class `NetworkGraphMixin`.

### Interoperability: DataFrames

All component data is natively pandas:
- `n.generators` (or `n.c.generators.static`) is a `pandas.DataFrame` with component names as index and attributes as columns.
- `n.generators_t` (or `n.c.generators.dynamic`) is a dict-like of DataFrames, keyed by time-varying attribute names, with snapshots as index.
- The new Components API (opt-in via `pypsa.options.api.new_components_api = True`) returns `Components` objects instead of raw DataFrames from `n.generators`, but `.static` and `.dynamic` accessors still expose the underlying DataFrames.
- An xarray accessor (`c.da`) provides N-D labeled array views for multi-dimensional operations (scenarios, investment periods).

**Source:** `pypsa/components/components.py` (ComponentsData dataclass), `pypsa/network/components.py` (property accessors).

### Interoperability: Import/Export Formats

| Format | Import | Export | Notes |
|--------|--------|--------|-------|
| netCDF (.nc) | `n.import_from_netcdf()` | `n.export_to_netcdf()` | Preferred format; supports lazy loading, cross-language access |
| HDF5 (.h5) | `n.import_from_hdf5()` | `n.export_to_hdf5()` | Legacy format |
| CSV folder | `n.import_from_csv_folder()` | `n.export_to_csv_folder()` | Human-readable; one CSV per component |
| Excel (.xlsx) | `n.import_from_excel()` | `n.export_to_excel()` | One sheet per component; 31-char sheet name limit handled |
| PyPower PPC | `n.import_from_pypower_ppc()` | -- | PYPOWER case dict format v2 |
| pandapower | `n.import_from_pandapower_net()` | -- | Beta; limited component support |
| URL | Constructor `pypsa.Network("https://...")` | -- | Auto-downloads and imports |
| Cloud (S3/GCS/Azure) | Constructor with cloudpathlib | Export with cloudpathlib | Requires `cloudpathlib` package |

The Linopy model can be saved independently via `n.model.to_netcdf()` but is **not** persisted with the network export.

**Source:** `pypsa/network/io.py` (NetworkIOMixin class).

### Interoperability: No Native Julia/Graphs.jl Bridge

There is no built-in interoperability with Julia, Graphs.jl, or any non-Python graph library. The netCDF export format is the most practical bridge for cross-language workflows, as netCDF is readable from Julia via `NCDatasets.jl`. The NetworkX graph would need to be serialized manually (e.g., via GraphML or adjacency list export from NetworkX) for consumption by other graph libraries.

### Configuration System

The `pypsa.options` system provides hierarchical configuration via `OptionsNode` objects:

- `general.allow_network_requests` -- controls URL fetching
- `params.optimize.*` -- solver name, solver options, model kwargs, log settings
- `params.statistics.*` -- output formatting defaults
- `params.add.return_names` -- whether `n.add()` returns component names
- `api.new_components_api` -- opt-in to new Components class access pattern
- `debug.runtime_verification` -- enable internal state checks

Options can be set via attribute assignment (`pypsa.options.params.optimize.solver_name = "gurobi"`), context manager (`with pypsa.option_context(...)`), or function calls (`pypsa.set_option()`). This system configures PyPSA internals only; it does not provide extension points for user code.

**Source:** `pypsa/_options.py`.

### Optimization Architecture: Linopy Backend

The optimization subsystem is cleanly separated into modules:

| Module | Responsibility |
|--------|---------------|
| `optimize.py` | `OptimizationAccessor`, `create_model()`, `__call__()`, objective definition |
| `variables.py` | All variable definitions (nominal, operational, status, spillage, loss, CVaR) |
| `constraints.py` | 14 constraint-definition functions (operational, capacity, energy balance, KVL, ramps, losses) |
| `global_constraints.py` | 7 system-wide constraint functions (growth limits, emission caps, expansion budgets) |
| `expressions.py` | Statistical expression building for the optimizer |
| `mga.py` | Modeling to Generate Alternatives (near-optimal space exploration) |
| `abstract.py` | Iterative transmission expansion, solution assignment, post-processing |

All functions follow the pattern `define_X(n, sns, ...)` -- they receive the Network, access `n.model`, and add variables/constraints to the Linopy model. This makes it straightforward to study and replicate individual constraint definitions.

**Source:** `pypsa/optimization/` directory.

### Network Merging and Copying

- `n.copy()` creates a deep copy with optional snapshot filtering.
- `n1 + n2` merges two networks (components are combined).
- `NetworkCollection([n1, n2])` (v0.35+) wraps multiple networks for batch statistics and component access without merging.

**Source:** `pypsa/networks.py` (`__add__`, `copy`), `pypsa/collection.py` (`NetworkCollection`).

## Sources

1. PyPSA source code, installed version 1.1.2: `pypsa/` package directory (inspected via devcontainer)
2. [PyPSA Custom Constraints documentation](https://docs.pypsa.org/latest/user-guide/optimization/custom-constraints/)
3. [PyPSA Constraints API reference (v1.1.2)](https://docs.pypsa.org/v1.1.2/api/networks/constraints/)
4. [PyPSA Network API reference (v1.0.2)](https://docs.pypsa.org/v1.0.2/user-guide/components/)
5. [PyPSA Design documentation (v1.0.0)](https://docs.pypsa.org/v1.0.0/user-guide/design/)
6. [GitHub issue #856: Custom components with Linopy](https://github.com/PyPSA/PyPSA/issues/856)
7. [What's new in v1.0](https://docs.pypsa.org/latest/user-guide/v1-guide/)
8. [PyPSA GitHub repository](https://github.com/PyPSA/PyPSA)
9. `pypsa/network/graph.py` -- NetworkX graph construction (OrderedGraph, adjacency_matrix, incidence_matrix)
10. `pypsa/network/io.py` -- Import/export implementations (netCDF, HDF5, CSV, Excel, PyPower, pandapower)
11. `pypsa/optimization/optimize.py` -- OptimizationAccessor with extra_functionality hook
12. `pypsa/components/types.py` -- `add_component_type()` for custom component registration
13. `pypsa/_options.py` -- Hierarchical options system
14. `pypsa/collection.py` -- NetworkCollection for multi-network workflows

## Gaps and Uncertainties

- **No formal plugin/extension API**: There is no way to register hooks that fire at specific lifecycle points (pre-solve, post-solve, component-added, etc.). The only extension point is `extra_functionality`, which is solve-time only.
- **Custom component optimizer integration is undocumented and unsupported**: `add_component_type()` registers a type but does not wire it into `create_model()`. The `# TODO` comment in `types.py` confirms this is a known limitation. Users must write all variable/constraint definitions manually.
- **Subclassing Network is fragile**: The heavy use of mixins (8+) means subclassing `Network` to override behavior requires understanding the full mixin resolution order. The maintainers have suggested this approach (GitHub #856) but have not formalized it.
- **No callback for power flow**: Unlike optimization, the power flow subsystem (`NetworkPowerFlowMixin`) has no `extra_functionality` equivalent. Custom power flow extensions require monkey-patching or forking.
- **pandapower import is beta**: The `import_from_pandapower_net()` method explicitly warns it is incomplete -- three-winding transformers, switches, in_service status, shunt impedances, and transformer tap positions are unsupported.
- **Linopy model persistence**: The Linopy model (`n.model`) is not saved with `export_to_netcdf()`. If users add custom constraints, they must re-create them after re-loading a network.
- **New Components API stability**: The opt-in `new_components_api` flag (v1.0+) changes how `n.generators` behaves (returns Components object vs DataFrame). The interaction of custom component types with this new API has not been tested or documented.
