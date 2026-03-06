# PyPSA — Research: Extension mechanisms, architecture, graph access, interoperability

Applies to PyPSA v1.0.x–v1.1.x (latest PyPI release: v1.1.2, 2026-02-23).

## Key Findings

- **No formal plugin/hook system.** PyPSA has no plugin registry, event hooks, or middleware architecture. Extension is achieved through composition: callback functions, accessor patterns, and direct manipulation of internal DataFrames and Linopy model objects.
- **`extra_functionality` callback** is the primary extension point for optimization. A user-defined function `f(network, snapshots)` is called after model creation but before solving, allowing arbitrary constraint/variable/objective additions via the Linopy API.
- **Full Linopy model access** via `n.model` exposes all decision variables, constraints, and the objective function for direct read/write manipulation after `n.optimize.create_model()`.
- **Accessor pattern** organizes subsystems (`n.optimize`, `n.statistics`, `n.cluster`, `n.plot`) as lazy-loaded namespaces on the Network object, similar to pandas' `register_accessor` convention. No public API exists for users to register custom accessors.
- **Custom statistics groupers** can be registered via `pypsa.statistics.groupers.add_grouper("name", func)`, providing a lightweight extension mechanism for analysis workflows.
- **Component data is pure pandas DataFrames** (`n.generators`, `n.generators_t`, etc.), making interoperability with the pandas/numpy/scipy ecosystem trivial. xarray views are also available via the Components class (`c.da`, `c.ds`).
- **NetworkX graph export** via `n.graph()` returns an `OrderedGraph` (NetworkX `MultiGraph` subclass). Sparse `incidence_matrix()` and `adjacency_matrix()` methods return scipy sparse matrices. PTDF/BODF are computed as dense numpy arrays.
- **Import bridges** exist for PYPOWER (`import_from_pypower_ppc`) and pandapower (`import_from_pandapower_net`), both import-only — no export to these formats.
- **Custom component attributes** are supported: v1.0 auto-extends Link attributes (bus2, bus3, etc.) when multiport links are added; earlier versions required `override_component_attrs` at Network construction.
- **Architecture is modular** with clear separation: `pypsa/components/` (data model), `pypsa/optimization/` (variable/constraint definition, solver interface), `pypsa/network/` (Network class, I/O), `pypsa/statistics/` (post-processing), `pypsa/plot/` (visualization).

## Detailed Notes

### Extension Mechanisms

#### `extra_functionality` Callback

The primary mechanism for extending PyPSA's optimization formulation. Passed as an argument to `n.optimize()`:

```python
def my_constraints(n, sns):
    m = n.model
    gen_p = m.variables["Generator-p"]
    m.add_constraints(gen_p.sum("snapshot") >= 100, name="min_total_gen")

n.optimize(extra_functionality=my_constraints)
```

The function executes after `create_model()` completes all standard variable/constraint setup but before the solver is invoked. Users have full access to `n.model.variables`, `n.model.constraints`, `n.model.objective`, and can call `m.add_variables()`, `m.add_constraints()`, `m.remove_constraints()`, and `m.add_objective(overwrite=True)`.

Source: [Custom Constraints docs](https://docs.pypsa.org/latest/user-guide/optimization/custom-constraints/)

#### Two-Phase Model Manipulation

An alternative to `extra_functionality` is the two-phase workflow:

1. `n.optimize.create_model()` — builds the Linopy model, assigns to `n.model`
2. User modifies `n.model` programmatically (add/remove variables, constraints, modify objective)
3. `n.optimize.solve_model()` — solves and writes results back to the network

This gives identical power but separates model building from solving, useful for inspection or conditional modification.

Source: [Custom Constraints docs](https://docs.pypsa.org/latest/user-guide/optimization/custom-constraints/)

#### Custom Statistics Groupers

The statistics module allows registering custom grouper functions:

```python
import pypsa

def group_by_voltage(n, c, port=""):
    # Must return pd.Series with same length as component index
    return n.df(c)["v_nom"]

pypsa.statistics.groupers.add_grouper("voltage", group_by_voltage)
n.statistics.installed_capacity(groupby="voltage")
```

Built-in groupers: `"carrier"`, `"bus_carrier"`, `"name"`, `"bus"`, `"country"`, `"unit"`.

Source: [Statistics docs](https://docs.pypsa.org/stable/user-guide/statistics/), [PR #1078](https://github.com/PyPSA/PyPSA/pull/1078)

#### No Plugin Registry or Hook System

PyPSA does not have:
- A plugin discovery mechanism (entry points, registry)
- Pre/post hooks for power flow or optimization steps
- Event emitters or signal/slot patterns
- Middleware or pipeline customization

All extension is achieved by direct code composition — subclassing, monkey-patching, or callback injection. This is a design choice consistent with PyPSA's philosophy of being a library (not a framework).

### Internal Architecture (Separation of Concerns)

#### Module Layout (v1.1.x)

```
pypsa/
├── __init__.py
├── _options.py          # Global options (e.g., new_components_api toggle)
├── components/          # Component definitions, ComponentsStore, filtering
├── clustering/          # Spatial clustering (k-means, Voronoi)
├── constants.py         # Physical constants
├── consistency.py       # Network consistency checks
├── costs.py             # Cost calculations
├── data/                # CSV lookup tables (variables.csv, components.csv, component_attrs/*.csv)
├── definitions/         # Component type definitions
├── deprecations.py      # Backward-compat shims
├── descriptors.py       # Descriptor classes for component filtering
├── examples.py          # Built-in example networks
├── geo.py               # Geographic utilities
├── guards.py            # Input validation
├── network/             # Network class, I/O (CSV, netCDF, HDF5, Excel)
├── networks.py          # Network + SubNetwork classes, graph mixin
├── optimization/        # Linopy model building, variables, constraints, solver
│   ├── variables.py     # Variable definition functions
│   ├── constraints.py   # Constraint definition functions
│   └── ...
├── plot/                # Matplotlib/pydeck visualization
├── statistics/          # Post-optimization analysis, groupers
├── type_utils.py        # Type helpers
└── version.py
```

Source: [GitHub repo tree](https://github.com/PyPSA/PyPSA/tree/master/pypsa), [DeepWiki](https://deepwiki.com/PyPSA/PyPSA)

#### Network Class Design

`Network` is the central container. It inherits from multiple mixins:
- `NetworkGraphMixin` — graph construction, adjacency/incidence matrices
- `SubNetworkPowerFlowMixin` — power flow calculations (on SubNetwork)

Data is organized hierarchically:

```
Network
├── ComponentsStore (n.components / n.c)
│   ├── Component("Generator") → .static (pd.DataFrame), .dynamic (dict of pd.DataFrame)
│   ├── Component("Bus") → ...
│   └── ...
├── Accessor properties: n.optimize, n.statistics, n.cluster, n.plot
├── Snapshots (pd.Index or pd.MultiIndex for multi-period)
└── n.model (linopy.Model, populated after create_model())
```

Source: [DeepWiki architecture](https://deepwiki.com/PyPSA/PyPSA), [v1 guide](https://docs.pypsa.org/latest/user-guide/v1-guide/)

#### Accessor Pattern

Subsystems are accessed as properties on Network:

| Accessor | Module | Purpose |
|----------|--------|---------|
| `n.optimize` | `pypsa.optimization` | Model building, solving, LOPF |
| `n.statistics` | `pypsa.statistics` | Energy balance, costs, capacity factors |
| `n.cluster` | `pypsa.clustering` | Spatial aggregation |
| `n.plot` | `pypsa.plot` | Visualization |

These follow the pandas accessor convention but there is no documented public API for users to register their own accessors on Network.

Source: [DeepWiki](https://deepwiki.com/PyPSA/PyPSA)

#### Optimization Module Internals

The optimization subsystem uses a **lookup-table-driven** architecture:

1. `pypsa/data/variables.csv` maps component types to variable/constraint definitions
2. Modular functions in `variables.py` (`define_nominal_variables()`, `define_status_variables()`, etc.) and `constraints.py` (`define_nodal_balance_constraints()`, `define_kirchhoff_voltage_constraints()`, etc.) are called during `create_model()`
3. Activity filtering via descriptor methods (`.extendables`, `.fixed`, `.committables`, `.active_assets`) ensures variables/constraints are only created for relevant components
4. All variables and constraints are Linopy objects, decoupled from any specific solver

Source: [DeepWiki constraints](https://deepwiki.com/PyPSA/PyPSA/4.2-constraints-and-variables)

#### Component Descriptor System

Components expose filtered views without data duplication:
- `c.extendables` — components with `p_nom_extendable=True`
- `c.fixed` — fixed-capacity components
- `c.committables` — components with `committable=True`
- `c.active_assets` — components active in a given investment period

The nominal attribute mapping (`p_nom`, `s_nom`, `e_nom`) enables generic code that works across component types.

Source: [DeepWiki](https://deepwiki.com/PyPSA/PyPSA)

### Graph Access

#### NetworkX Graph Export

```python
G = n.graph(
    branch_components=None,   # defaults to all branch_components
    weight=None,              # branch attribute for edge weight
    inf_weight=False,         # handling of infinite weights
    include_inactive=True     # include inactive components
)
# Returns OrderedGraph (nx.MultiGraph subclass)
```

The returned graph has buses as nodes and branches (Lines, Transformers, Links) as edges. Edge attributes include the branch component type and name.

Source: [Network.graph docs](https://docs.pypsa.org/v0.29.0/api/_source/pypsa.Network.graph.html)

#### Sparse Matrix Methods

On both `Network` and `SubNetwork`:

- **`incidence_matrix(branch_components, busorder)`** → `scipy.sparse.csr_matrix` (directed)
- **`adjacency_matrix(branch_components, busorder, weights, return_dataframe)`** → `scipy.sparse.coo_matrix` or `pd.DataFrame`

On `SubNetwork` only:

- **`calculate_PTDF(skip_pre)`** → sets `sub_network.PTDF` as dense `numpy.ndarray`
- **`calculate_BODF(skip_pre)`** → sets `sub_network.BODF` as dense `numpy.ndarray`
- **`calculate_B_H(skip_pre)`** → B and H matrices for DC/AC analysis
- **`calculate_Y(skip_pre)`** → bus admittance matrix (AC only)

Source: [SubNetwork API](https://docs.pypsa.org/stable/api/networks/subnetwork/)

#### Topology Detection

`n.determine_network_topology()` identifies connected sub-networks (AC and DC islands), populates `n.sub_networks`, and assigns buses to sub-networks. This must be called before using SubNetwork-level methods.

### Interoperability

#### DataFrame / numpy / scipy

All component data is natively stored as pandas DataFrames:
- `n.generators` → `pd.DataFrame` (static attributes: bus, carrier, p_nom, marginal_cost, ...)
- `n.generators_t["p"]` → `pd.DataFrame` (time-varying: index=snapshots, columns=generator names)
- v1.0 Components class: `n.c.generators.static`, `n.c.generators.dynamic`

xarray views available via Components class:
- `c.da` — DataArray views over pandas structures (lazy, no data duplication)
- `c.ds` — Dataset views

No conversion needed — data is already in pandas/numpy format.

Source: [Components docs](https://docs.pypsa.org/latest/user-guide/components/)

#### Serialization Formats

| Format | Import | Export | Method |
|--------|--------|--------|--------|
| CSV folder | Yes | Yes | `import_from_csv_folder()` / `export_to_csv_folder()` |
| netCDF | Yes | Yes | `import_from_netcdf()` / `export_to_netcdf()` |
| HDF5 | Yes | Yes | `import_from_hdf5()` / `export_to_hdf5()` |
| Excel | Yes | Yes | `import_from_excel()` / `export_to_excel()` (requires `pypsa[excel]`) |
| Cloud (S3/GCS/Azure) | Yes | Yes | Via `cloudpathlib`, same methods with cloud paths |

Source: [Import/Export docs](https://docs.pypsa.org/latest/user-guide/import-export/)

#### Tool Interoperability

| Tool | Import | Export | Notes |
|------|--------|--------|-------|
| PYPOWER | Yes (`import_from_pypower_ppc()`) | No | Accepts ppc dict (version 2 format) |
| pandapower | Yes (`import_from_pandapower_net()`) | No | Beta; missing 3-winding transformers, switches, tap positions |
| NetworkX | Yes (`n.graph()` export) | No direct import | Returns `OrderedGraph` for analysis |
| MATPOWER | Indirect | No | Via PYPOWER ppc format conversion |

Source: [Import/Export docs](https://docs.pypsa.org/latest/user-guide/import-export/)

#### Linopy Model Export

The Linopy model (`n.model`) can be saved independently:
- `n.model.to_netcdf("model.nc")` — saves full LP formulation
- `n.model.to_file("model.lp")` — exports LP/MPS for external solvers

The model is **not** retained when exporting the Network itself (CSV/netCDF/HDF5).

Source: [Custom Constraints docs](https://docs.pypsa.org/latest/user-guide/optimization/custom-constraints/)

### Custom Components (v1.0+)

#### Multiport Links (Auto-Extension)

In v1.0+, adding a Link with `bus2`, `bus3`, etc. automatically extends the Link component attributes. No `override_component_attrs` needed:

```python
n.add("Link", "chp", bus0="gas", bus1="elec", bus2="heat",
      efficiency=0.4, efficiency2=0.45)
```

Source: [v1.0 guide](https://docs.pypsa.org/latest/user-guide/v1-guide/)

#### Legacy Custom Components (pre-v1.0)

For older versions, custom attributes required explicit override at Network construction:

```python
override = pypsa.component_attrs.copy()
override["Link"].loc["bus2"] = ["string", np.nan, np.nan, "2nd bus", "Input"]
n = pypsa.Network(override_component_attrs=override)
```

Entirely new component types could be added via `override_components` (a DataFrame with `list_name` and `description` columns).

Source: [Components docs (v0.24)](https://docs.pypsa.org/v0.24.0/components.html)

## Sources

1. [PyPSA Custom Constraints documentation](https://docs.pypsa.org/latest/user-guide/optimization/custom-constraints/)
2. [PyPSA Import/Export documentation](https://docs.pypsa.org/latest/user-guide/import-export/)
3. [PyPSA Components documentation](https://docs.pypsa.org/latest/user-guide/components/)
4. [PyPSA v1.0 guide](https://docs.pypsa.org/latest/user-guide/v1-guide/)
5. [PyPSA SubNetwork API](https://docs.pypsa.org/stable/api/networks/subnetwork/)
6. [PyPSA Network API](https://docs.pypsa.org/stable/api/networks/network/)
7. [PyPSA Statistics documentation](https://docs.pypsa.org/stable/user-guide/statistics/)
8. [PyPSA GitHub repository](https://github.com/PyPSA/PyPSA)
9. [DeepWiki — PyPSA architecture](https://deepwiki.com/PyPSA/PyPSA)
10. [DeepWiki — Variables and Constraints](https://deepwiki.com/PyPSA/PyPSA/4.2-constraints-and-variables)
11. [Network.graph API (v0.29)](https://docs.pypsa.org/v0.29.0/api/_source/pypsa.Network.graph.html)
12. [Linopy migration examples](https://docs.pypsa.org/v0.26.3/examples/optimization-with-linopy-migrate-extra-functionalities.html)
13. [PyPSA on PyPI](https://pypi.org/project/pypsa/) — latest v1.1.2 (2026-02-23)
14. [Statistics groupers PR #1078](https://github.com/PyPSA/PyPSA/pull/1078)

## Gaps and Uncertainties

- **No public accessor registration API confirmed.** The accessor pattern (`n.optimize`, `n.statistics`) is used internally, but whether users can register custom accessors via a public API was not found in documentation. Likely requires monkey-patching or subclassing Network.
- **Custom component types in v1.0+.** The v1.0 docs focus on multiport Links auto-extension. Whether `override_components` (for entirely new component types) still works in v1.0+ needs verification by testing.
- **Linopy solver callbacks.** Linopy may support solver-level callbacks (e.g., Gurobi lazy constraints, cut callbacks), but this was not documented in PyPSA's docs. Would need to check Linopy's own API.
- **No Graphs.jl interoperability.** PyPSA is Python-only; no bridge to Julia's Graphs.jl ecosystem exists. Interoperability would require manual conversion through adjacency matrices or edge lists.
- **pandapower import completeness.** The import is flagged as beta with known gaps (three-winding transformers, switches, tap positions). The exact set of supported components needs testing.
- **`extra_functionality` vs two-phase workflow.** Documentation does not clarify whether `extra_functionality` receives the same `n.model` object as the two-phase approach, or whether there are subtle sequencing differences. Needs code verification.
- **Performance of `n.graph()`.** Unknown whether the NetworkX graph is cached or rebuilt on each call. For large networks, this could matter.
