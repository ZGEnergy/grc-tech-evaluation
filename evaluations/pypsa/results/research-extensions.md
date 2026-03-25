# PyPSA Extension Mechanisms & Internal Architecture — Research Notes

**Tool version:** PyPSA 1.1.2 (released 2026-02-23)
**Installed at:** `.venv/lib/python3.12/site-packages/pypsa/`
**License:** MIT

---

## 1. Internal Architecture & Separation of Concerns

### 1.1 Network Class — Mixin Composition

The `Network` class is assembled from eight independent mixins, each in its own module. This is the primary architectural pattern for separation of concerns:

```
class Network(
    NetworkComponentsMixin,      # network/components.py — add/remove components
    NetworkDescriptorsMixin,     # network/descriptors.py — property descriptors
    NetworkTransformMixin,       # network/transform.py — topology transforms
    NetworkIndexMixin,           # network/index.py — index helpers
    NetworkConsistencyMixin,     # consistency.py — validation checks
    NetworkGraphMixin,           # network/graph.py — NetworkX graph methods
    NetworkPowerFlowMixin,       # network/power_flow.py — PF/LPF solvers
    NetworkIOMixin,              # network/io.py — import/export
)
```

`SubNetwork` inherits from `NetworkGraphMixin` and `SubNetworkPowerFlowMixin` only.

**Source:** `pypsa/networks.py` lines 78–88.

This design means the `Network` class is a monolithic container but internally modular: each concern lives in its own file and could theoretically be tested or replaced independently. However, the mixins all share state through `self` (the Network instance), so they are tightly coupled at runtime.

### 1.2 Accessor Pattern

Functional subsystems that are not mixins are attached as **accessor objects** initialized in `Network.__init__`:

| Accessor | Class | Module |
|---|---|---|
| `n.optimize` | `OptimizationAccessor` | `optimization/optimize.py` |
| `n.cluster` | `ClusteringAccessor` | `clustering/__init__.py` |
| `n.statistics` | `StatisticsAccessor` | `statistics/expressions.py` |
| `n.plot` | `PlotAccessor` | `plot/accessor.py` |

Each accessor holds a back-reference `self._n` to the parent Network. The `OptimizationAccessor` is callable — `n.optimize(...)` invokes `OptimizationAccessor.__call__`.

**Source:** `pypsa/networks.py` lines 171–177.

### 1.3 Component System

Components are stored in a `ComponentsStore` (a `dict` subclass) at `n.c` (new API) and also exposed as direct DataFrame attributes like `n.generators` (legacy API, still supported).

Each component type is a `Components` instance assembled from its own mixin hierarchy:

```
class Components(
    ComponentsData,                # dataclass: ctype, n, static, dynamic
    ComponentsDescriptorsMixin,    # property descriptors
    ComponentsTransformMixin,      # transforms
    ComponentsIndexMixin,          # index helpers
    ComponentsArrayMixin,          # xarray accessor (.da)
)
```

Typed subclasses exist for each component (e.g., `Generators`, `Lines`, `Links`) in `components/_types/`, adding component-specific properties. These are defined with type annotations in `ComponentsStore` for IDE support.

**Source:** `pypsa/components/components.py`, `pypsa/components/store.py`.

### 1.4 Data Storage — Static and Dynamic Split

All component data is stored as pandas DataFrames:

- **Static data:** `c.static` — one row per component, columns are attributes. Accessible as `n.generators` (returns the DataFrame directly).
- **Dynamic (time-varying) data:** `c.dynamic` — a dict-like (`Dict`) of DataFrames keyed by attribute name. Accessible as `n.generators_t` (e.g., `n.generators_t.p` for dispatch time series).

This is a deliberate design choice documented in PyPSA's design philosophy: "stores data in memory using pandas DataFrames" to leverage modern RAM and computational speed.

**Source:** [PyPSA Design documentation](https://docs.pypsa.org/v0.26.2/design.html); `pypsa/components/components.py` `ComponentsData` dataclass.

### 1.5 Optimization Module Structure

The optimization subsystem in `pypsa/optimization/` is cleanly separated:

| File | Responsibility | LOC |
|---|---|---|
| `optimize.py` | `OptimizationAccessor`, orchestrates model build/solve | ~48 kB |
| `variables.py` | Variable definitions (dispatch, status, start-up, etc.) | ~9 kB |
| `constraints.py` | All standard constraints (nodal balance, KVL, ramp, storage) | ~78 kB |
| `global_constraints.py` | Global constraints (emission limits, capacity expansion) | ~32 kB |
| `expressions.py` | Statistic expressions for optimization | ~29 kB |
| `mga.py` | Modeling to Generate Alternatives | ~28 kB |
| `abstract.py` | Abstract/iterative optimization methods | ~24 kB |

The `create_model` method in `OptimizationAccessor` orchestrates model construction by calling functions from `variables.py`, `constraints.py`, and `global_constraints.py` in sequence. A lookup CSV (`data/variables.csv`) drives which component/attribute combinations get variables and constraints.

**Source:** `pypsa/optimization/optimize.py` lines 561–760.

---

## 2. Extension Mechanisms

### 2.1 `extra_functionality` Callback

The primary extension mechanism is the `extra_functionality` callable parameter, accepted by both `n.optimize()` and `n.optimize.solve_model()`:

```python
def my_extra(n, snapshots):
    """Called after model building, before solving."""
    m = n.model  # linopy.Model instance
    # Add custom constraints, modify variables, change objective
    gen_p = m.variables["Generator-p"]
    m.add_constraints(gen_p.sum() >= 100, name="min_total_gen")

n.optimize(extra_functionality=my_extra)
```

The callback receives:
- `n` — the Network instance (with `n.model` already populated)
- `snapshots` — the snapshot index being optimized

The callback is invoked at exactly one point: after `create_model()` completes and before `model.solve()` is called.

**Source:** `pypsa/optimization/optimize.py` lines 457–462 (docstring), 537–538 (invocation), 776–780 and 824–825 (solve_model variant).

**Implications:**
- This is a **single hook point**, not a plugin system. There is no hook before model creation, during variable/constraint definition, or after solving.
- Only one callback can be passed; to compose multiple, the user must manually chain them.
- The callback has full access to the linopy `Model` object, so it can add/remove/modify any variable, constraint, or objective term.

### 2.2 Two-Step Model Build/Solve

An alternative to `extra_functionality` is the explicit two-step pattern:

```python
m = n.optimize.create_model()   # Build the linopy model
# ... modify m as desired ...
status, condition = n.optimize.solve_model()  # Solve and write back
```

This provides the same power as `extra_functionality` but with a clearer separation of build and modify phases. `solve_model` also accepts its own `extra_functionality` for additional last-minute modifications.

**Source:** [Custom Constraints documentation](https://docs.pypsa.org/latest/user-guide/optimization/custom-constraints/).

### 2.3 Direct Linopy Model Access

Once the model is created (via `create_model` or `optimize`), it is stored at `n.model` (a `linopy.Model` instance). The user has full programmatic access:

- `n.model.variables` — dict-like access to all decision variables (e.g., `n.model.variables["Generator-p"]`)
- `n.model.constraints` — dict-like access to all constraints
- `n.model.objective` — the objective expression
- `n.model.add_variables(...)` — add custom variables
- `n.model.add_constraints(...)` — add custom constraints
- Standard linopy expression algebra (`+`, `-`, `*`, `>=`, `<=`, `==`) for building constraint expressions

Linopy is PyPSA's own companion project ([github.com/PyPSA/linopy](https://github.com/PyPSA/linopy)), purpose-built for N-dimensional labeled optimization with xarray-based variable/constraint storage.

**Source:** [Custom Constraints docs](https://docs.pypsa.org/latest/user-guide/optimization/custom-constraints/); [Optimization with Linopy example](https://docs.pypsa.org/v0.27.1/examples/optimization-with-linopy.html).

### 2.4 Custom Components — Partial Support

Custom component support has evolved significantly. In v1.1.2, the `pypsa.components.types.add_component_type()` function allows registering new component types at the package level:

```python
import pypsa.components.types
defaults_df = pd.DataFrame({
    "attribute": ["name", "attribute_a"],
    "type": ["string", "float"],
    "unit": ["n/a", "n/a"],
    "default": ["n/a", 1],
    "description": ["Unique name", "Some custom attribute"],
    "status": ["Input (required)", "Input (optional)"],
})
pypsa.components.types.add_component_type(
    name="CustomComponent",
    list_name="custom_components",
    description="A custom component example",
    category="custom",
    defaults_df=defaults_df,
)
```

**However**, this only registers the component type for data storage. Custom components do **not** automatically participate in the optimization pipeline, because `create_model` iterates over a fixed lookup table (`data/variables.csv`) that maps component/attribute pairs to variable and constraint definitions. A custom component would need manual variable/constraint definition via `extra_functionality`.

GitHub issue [#856](https://github.com/PyPSA/PyPSA/issues/856) (still open as of 2026-03) requests better documentation and integration. A PyPSA core developer (FabianHofmann) proposed a **subclassing pattern** as the recommended approach:

```python
class MyOptimizationAccessor(pypsa.optimization.optimize.OptimizationAccessor):
    def __call__(self, *args, **kwargs):
        # Inject custom extra_functionality that handles custom component logic
        kwargs = patch_extra_functionality(kwargs)
        return super().__call__(*args, **kwargs)

class MyNetwork(pypsa.Network):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.optimize = MyOptimizationAccessor(self)
```

This pattern composes custom optimization logic with user-provided `extra_functionality`, allowing custom component variables/constraints to be added transparently.

**Source:** `pypsa/components/types.py` lines 33–130; [GitHub issue #856](https://github.com/PyPSA/PyPSA/issues/856) (includes subclass pattern); [PR #1075](https://github.com/PyPSA/PyPSA/pull/1075) introduced the new component class system.

### 2.5 Custom Statistics Groupers

The statistics module provides a limited registration mechanism for custom groupers:

```python
from pypsa.statistics.grouping import Groupers
groupers = Groupers()
groupers.add_grouper("my_region", my_region_func)
```

A custom grouper function must accept `(n, c, port, nice_names)` and return a `pd.Series` aligned with the component index. Once registered, it can be used in `n.statistics.*()` calls.

**Source:** `pypsa/statistics/grouping.py` lines 222–243.

### 2.6 No Formal Plugin/Hook System

A search of the entire PyPSA codebase (1.1.2) for patterns like "plugin", "hook", "callback", "register", "event", "signal", "listener", and "middleware" reveals:

- `register`: 1 occurrence — the statistics grouper registration described above
- `event`/`signal`: only in unrelated contexts (no event bus)
- `callback`: 0 occurrences as a formal pattern
- `plugin`/`hook`/`listener`/`middleware`: 0 occurrences

**PyPSA has no formal plugin architecture, no event bus, no middleware pipeline, and no hook registry.** Extension is achieved through:
1. The `extra_functionality` callback (single hook point)
2. Direct manipulation of the linopy Model object
3. Subclassing or monkey-patching (not officially supported)

### 2.7 Configuration System

PyPSA 1.1 includes a hierarchical options system (`pypsa.options`) with namespace-based access:

```python
pypsa.options.params.optimize.solver_name = "gurobi"
pypsa.options.params.statistics.round = 3
```

Options are managed via `OptionsNode` and `Option` classes in `pypsa/_options.py`. This is a configuration system, not an extension mechanism, but it does allow runtime customization of solver settings, numerical tolerances, and output formatting.

**Source:** `pypsa/_options.py`.

---

## 3. Graph Access & NetworkX Interoperability

### 3.1 `n.graph()` — Full NetworkX Export

The `graph()` method (from `NetworkGraphMixin`) builds a `networkx.MultiGraph` from the network topology:

```python
g = n.graph()                          # All branch components
g = n.graph(branch_components=["Line"])  # Only lines
g = n.graph(weight="x")                # Edge weights from reactance
g = n.graph(include_inactive=False)    # Skip inactive components
```

Returns an `OrderedGraph` (subclass of `nx.MultiGraph` with ordered node/adjacency dicts). Edge keys are `(component_name, branch_index)` tuples, preserving the mapping back to PyPSA components.

Once you have the NetworkX graph, the full NetworkX algorithm library is available (shortest paths, centrality, community detection, etc.).

**Source:** `pypsa/network/graph.py` lines 41–107; [API docs](https://docs.pypsa.org/v0.29.0/api/_source/pypsa.Network.graph.html).

### 3.2 Matrix Representations

Additional graph representations are available as methods:

| Method | Returns | Notes |
|---|---|---|
| `n.adjacency_matrix()` | `pd.DataFrame` or `scipy.sparse.coo_matrix` | Directed; `return_dataframe=True` for DataFrame |
| `n.incidence_matrix()` | `scipy.sparse.csr_matrix` | Directed; buses x branches |
| `n.cycle_matrix()` | (not directly, but `find_cycles()` is available) | Used internally by KVL constraints |

The adjacency and incidence matrices support filtering by branch components, investment periods, and custom weights.

**Source:** `pypsa/network/graph.py` lines 109–310.

### 3.3 PTDF/BODF/Y Matrices

Power-flow-specific matrix representations:

- `calculate_PTDF(sub_network)` — Power Transfer Distribution Factor matrix
- `calculate_BODF(sub_network)` — Branch Outage Distribution Factor matrix
- `calculate_B_H(sub_network)` — B and H matrices for DC power flow
- `calculate_Y(sub_network)` — Full nodal admittance matrix (for AC power flow)

These are methods on `SubNetwork` (via `SubNetworkPowerFlowMixin`), returning numpy arrays or scipy sparse matrices.

**Source:** `pypsa/network/power_flow.py`.

---

## 4. DataFrame & xarray Interoperability

### 4.1 Native pandas Storage

All component data is natively pandas:

```python
n.generators          # pd.DataFrame — static data (42 columns in v1.1)
n.generators_t.p      # pd.DataFrame — time-varying dispatch
n.buses               # pd.DataFrame
```

This means standard pandas operations (filtering, groupby, merge, plot) work directly on PyPSA data without any conversion step.

### 4.2 xarray DataArray View (`.da` accessor)

The v1.0+ `Components` API adds an xarray accessor that provides a lazy, labeled view over the combined static/dynamic data:

```python
n.c.generators.da.p_nom      # xr.DataArray with 'name' dim
n.c.generators.da.p_max_pu   # xr.DataArray with 'name', 'snapshot' dims
```

The xarray view merges static and dynamic data into a unified N-dimensional labeled structure. This is the format used internally by the optimization module (variables and constraints are built from xarray coordinates).

The `_from_xarray()` helper converts back to pandas format, handling scenarios and multi-index cases.

**Source:** `pypsa/components/array.py` — `_XarrayAccessor` class, `ComponentsArrayMixin`.

### 4.3 Serialization Formats

PyPSA supports multiple import/export formats:

| Method | Format | Notes |
|---|---|---|
| `n.export_to_netcdf()` | NetCDF4 (via xarray) | Default compression `zlib` level 4; primary format |
| `n.export_to_hdf5()` | HDF5 | Legacy format |
| `n.export_to_csv_folder()` | CSV folder | One CSV per component; human-readable |
| `n.export_to_excel()` | Excel workbook | One sheet per component |
| `n.import_from_pypower_ppc()` | PYPOWER PPC dict | Version 2 format; limited feature support |
| `n.import_from_pandapower_net()` | pandapower network | **Beta**; unsupported: 3-winding transformers, switches, shunt impedances, tap positions |

The `import_from_pandapower_net` method is explicitly marked as beta with known limitations, warning at runtime.

**Source:** `pypsa/network/io.py`.

### 4.4 NetworkCollection

`NetworkCollection` (v0.35+) aggregates multiple Network objects and provides unified DataFrame access:

```python
nc = pypsa.NetworkCollection([n1, n2])
nc.generators   # Multi-indexed DataFrame across all networks
nc.statistics.energy_balance()  # Cross-network statistics
```

**Source:** `pypsa/collection.py`.

---

## 5. Interoperability with External Tools

### 5.1 pandapower Import

```python
n = pypsa.Network()
n.import_from_pandapower_net(net, extra_line_data=True)
```

Converts pandapower buses, lines, generators, external grids, static generators, loads, and transformers. Missing: three-winding transformers, switches, in_service status, shunt impedances, tap positions.

**Source:** `pypsa/network/io.py` lines 2215–2260.

### 5.2 PYPOWER Import

```python
n.import_from_pypower_ppc(ppc)
```

Imports from PYPOWER PPC version 2 dict format. Missing: areas, gencosts, component status.

**Source:** `pypsa/network/io.py` lines 1962–2214.

### 5.3 No Direct Graphs.jl Interoperability

PyPSA is a Python-only package. There is no built-in bridge to Julia's Graphs.jl. However, since the NetworkX graph can be exported and NetworkX supports standard graph formats (edge lists, GraphML, GEXF, etc.), indirect interoperability is possible through file-based exchange.

### 5.4 linopy (Optimization Backend)

PyPSA delegates all optimization to [linopy](https://github.com/PyPSA/linopy), a purpose-built package by the same team. linopy provides:
- N-dimensional labeled variables and constraints (xarray-based)
- Support for multiple solvers: HiGHS, Gurobi, CPLEX, GLPK, CBC, SCIP
- LP/MIP formulation and solving
- Expression algebra for building constraints

The linopy Model is the primary extension surface for adding custom optimization behavior.

---

## 6. Findings & Gaps

### What Works Well

1. **Constraint extension via linopy** is well-documented and flexible. The `extra_functionality` callback and two-step build/solve pattern provide practical extensibility for optimization customization.
2. **Graph access** is first-class: `n.graph()` returns a standard NetworkX `MultiGraph`, and adjacency/incidence matrices are readily available.
3. **DataFrame interoperability** is native — all data is pandas. No conversion friction for data science workflows.
4. **xarray integration** (`.da` accessor) provides labeled multi-dimensional views useful for advanced analysis.

### What Is Missing or Limited

1. **No plugin/hook architecture.** There is exactly one extension hook (`extra_functionality`), and it only applies to optimization. No hooks exist for power flow, clustering, I/O, or consistency checking.
2. **Custom component support is partial.** `add_component_type()` registers new types for data storage, but they do not automatically participate in optimization. Custom variables/constraints must be added manually via `extra_functionality` or the subclassing pattern ([#856](https://github.com/PyPSA/PyPSA/issues/856)).
3. **No event/signal system.** There is no way to subscribe to lifecycle events (model created, solve started, component added, etc.).
4. **pandapower import is beta quality**, with known unsupported features and runtime warnings.
5. **No Graphs.jl interoperability** — Python-only; indirect exchange via file formats is the only option.
6. **Single-callback limitation** — `extra_functionality` accepts one callable. Composing multiple independent extensions requires manual orchestration.

### Contradictions or Surprises

- The `CustomGroupers.__setitem__` method in `statistics/grouping.py` raises `NotImplementedError` (line 130), while `add_grouper` on the same class works via `setattr`. The dict-style assignment API appears broken or intentionally disabled.
- The adjacency matrix method returns a sparse `coo_matrix` by default but issues a `FutureWarning` that it will return a DataFrame in future versions — the transition is in progress.

---

## 7. Source Links

- [PyPSA Documentation (latest)](https://docs.pypsa.org/latest/)
- [Custom Constraints Guide](https://docs.pypsa.org/latest/user-guide/optimization/custom-constraints/)
- [Design Philosophy (v0.26.2)](https://docs.pypsa.org/v0.26.2/design.html)
- [What's New in v1.0](https://docs.pypsa.org/latest/user-guide/v1-guide/)
- [Network.graph API](https://docs.pypsa.org/v0.29.0/api/_source/pypsa.Network.graph.html)
- [Components API](https://docs.pypsa.org/v1.0.3/api/components/components/)
- [Import/Export Guide](https://docs.pypsa.org/v1.0.2/user-guide/import-export/)
- [GitHub Issue #856 — Custom Components](https://github.com/PyPSA/PyPSA/issues/856)
- [GitHub PR #1075 — Component Class](https://github.com/PyPSA/PyPSA/pull/1075)
- [`add_component_type` source](pypsa/components/types.py lines 33–130)
- [linopy Repository](https://github.com/PyPSA/linopy)
- [Optimization with Linopy Example](https://docs.pypsa.org/v0.27.1/examples/optimization-with-linopy.html)
- [PyPSA Releases](https://github.com/PyPSA/PyPSA/releases)
