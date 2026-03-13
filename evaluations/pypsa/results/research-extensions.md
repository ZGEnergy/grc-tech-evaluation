# pypsa — Research: Extensions & Architecture

Applies to: **PyPSA 1.1.2** (installed at
`/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/`).

---

## Key Findings

- The primary extension point for optimization is the `extra_functionality` callable passed to `n.optimize()`. It receives `(n, snapshots)` after the Linopy model is built but before the solver runs, giving full access to add/modify variables, constraints, and the objective via `n.model`.
- Model building and solving are cleanly separated: `n.optimize.create_model()` builds the Linopy model into `n.model`; `n.optimize.solve_model()` invokes the solver and writes results back. The two steps can be called independently.
- Custom component *types* can be registered globally via `pypsa.components.types.add_component_type()`, but there is a gap: the `Network.components` property initializes from `component_types_df` (the static CSV-loaded default list), not from the live `all_components` registry. Custom types registered after module import do not automatically appear in new Network instances — integration requires workarounds.
- Graph access is first-class: `n.graph()` returns a `networkx.MultiGraph` (`OrderedGraph` subclass); `n.adjacency_matrix()` and `n.incidence_matrix()` return sparse/dense matrices. All accept a `branch_components` filter.
- PTDF matrices are computed on a per-`SubNetwork` basis via `sub_network.calculate_PTDF()`. The result is stored as a dense numpy array at `sub_network.PTDF`.
- Multi-energy carrier support is native via the `Link` component: a single Link can have up to N ports (`bus0`…`busN`) with corresponding `efficiency`…`efficiencyN` parameters, enabling CHP, electrolysis, heat pump, and other sector-coupling topologies.
- All component data is exposed as pandas DataFrames (`c.static`, `c.dynamic`). The `n.add()` method accepts scalar values, lists, numpy arrays, and DataFrames (for time-varying attributes).
- Serialization formats: CSV folder, netCDF (xarray-backed, recommended), HDF5, Excel. `import_from_pandapower_net()` and `import_from_pypower_ppc()` provide interoperability bridges. The Linopy model is NOT persisted with the network; save separately via `n.model.to_netcdf()`.
- Architecture is mixin-based: `Network` inherits from eight focused mixins (`NetworkComponentsMixin`, `NetworkDescriptorsMixin`, `NetworkTransformMixin`, `NetworkIndexMixin`, `NetworkConsistencyMixin`, `NetworkGraphMixin`, `NetworkPowerFlowMixin`, `NetworkIOMixin`) plus four accessor objects (`optimize`, `cluster`, `statistics`, `plot`).
- PyPSA v1.0 introduced an opt-in new Components Class API (`n.c.generators.static`, `n.c.generators.dynamic`) that will become default in v2.0; existing `n.generators` / `n.generators_t` patterns still work but emit deprecation warnings.

---

## Detailed Notes

### Extension Mechanisms

#### `extra_functionality` callback

The primary supported extension pattern. Signature:

```python
def extra_functionality(n: pypsa.Network, snapshots: pd.Index) -> None:
    m = n.model  # linopy.Model, already built
    # add variables
    new_var = m.add_variables(lower=0, name="MyVar-p")
    # add constraints
    m.add_constraints(new_var >= 0, name="MyConstraint")
    # modify objective
    m.objective += new_var.sum()
```

Called at line 537 of `optimize.py` inside `OptimizationAccessor.__call__()`, after `create_model()` but before `m.solve()`. Also supported in `solve_model()` (line 824–825).

```python
n.optimize(extra_functionality=extra_functionality)
```

This is also available when using the step-by-step API:

```python
m = n.optimize.create_model(...)
extra_functionality(n, n.snapshots)
n.optimize.solve_model(solver_name="highs")
```

#### Model building / solving separation

`OptimizationAccessor` (defined in `optimization/optimize.py`) exposes:

- `n.optimize.create_model(snapshots, ...)` — builds and stores Linopy model at `n.model`
- `n.optimize.solve_model(solver_name, ...)` — solves `n.model`, assigns solution
- `n.optimize(...)` — convenience wrapper that calls both plus post-processing

Advanced variants: `optimize_with_rolling_horizon()`, `optimize_security_constrained()`, `optimize_transmission_expansion_iteratively()`, `optimize_mga()` (Modeling to Generate Alternatives).

#### Custom component types

PyPSA 1.1 introduced `pypsa.components.types.add_component_type()` for registering new component types at module level:

```python
import pandas as pd
import pypsa.components.types

defaults_df = pd.DataFrame({
    "attribute": ["name", "my_attr"],
    "type": ["string", "float"],
    "unit": ["n/a", "MW"],
    "default": ["n/a", 1.0],
    "description": ["Unique name", "My custom attribute"],
    "status": ["Input (required)", "Input (optional)"],
})
pypsa.components.types.add_component_type(
    name="MyComponent",
    list_name="my_components",
    description="Custom component",
    category="custom",
    defaults_df=defaults_df,
)
```

**Critical gap**: `Network.components` initializes from `component_types_df` (source:
`network/components.py` line 127), which is the static CSV-loaded snapshot taken at module
import time. The live `all_components` dict (which includes custom additions) is only consulted
by `get()` for lookup, not during `Network.__init__`. Custom components added after import do
NOT automatically appear in a new Network's `n.components` store. As of v1.1.2, integrating
custom components into network instances requires either:
  - calling `add_component_type()` before the first `import pypsa` (not practical), or
  - manually patching `network_types_df` before instantiation, or
  - using the `extra_functionality` approach with no new component type (just extra variables/constraints)

This limitation is tracked in [GitHub issue #856](https://github.com/PyPSA/PyPSA/issues/856)
which remains open as of May 2024, with no merged documentation or implementation fix.

#### Override / legacy API (pre-v1.0)

In versions before v1.0, `pypsa.Network(override_components=..., override_component_attrs=...)`
allowed replacing the built-in component CSV definitions. This API has been removed or deprecated
in v1.0+. The new `add_component_type()` function is the replacement but has the integration gap
described above.

---

### Graph Access

`Network` and `SubNetwork` both inherit from `NetworkGraphMixin`
(`network/graph.py`), providing:

| Method | Returns | Notes |
|--------|---------|-------|
| `n.graph(branch_components, weight, inf_weight, include_inactive)` | `networkx.MultiGraph` (`OrderedGraph`) | Nodes = buses; edges = branches keyed by `(component_name, branch_name)` |
| `n.adjacency_matrix(branch_components, investment_period, busorder, weights, return_dataframe)` | `pd.DataFrame` or `scipy.sparse.coo_matrix` | `return_dataframe=True` recommended (False emits `FutureWarning`) |
| `n.incidence_matrix(branch_components, busorder)` | `scipy.sparse.csr_matrix` | Directed |

`branch_components` defaults to `n.branch_components` for Network and
`n.n.passive_branch_components` for SubNetwork.

The `OrderedGraph` class is a `networkx.MultiGraph` subclass with
`OrderedDict` factories — preserving insertion order of nodes and adjacency.

NetworkX is a hard dependency of PyPSA; full NetworkX graph algorithms work on the returned objects.

#### PTDF matrix

Computed per SubNetwork:

```python
n.determine_network_topology()  # creates sub_networks
for sub in n.sub_networks.obj:
    sub.calculate_PTDF()        # sets sub.PTDF (dense numpy array, shape: branches × buses)
    sub.calculate_BODF()        # Branch Outage Distribution Factor, uses sub.PTDF
```

`calculate_PTDF()` depends on `calculate_B_H()` which itself calls
`calculate_dependent_values()` and `find_bus_controls()`.
The result is stored as `sub_network.PTDF`, a dense `(n_branches × n_buses)` numpy array.
No method exists to extract a network-wide PTDF directly; callers must iterate SubNetworks.

---

### Architecture

#### Mixin composition

```
pypsa.Network
  ├── NetworkComponentsMixin   — n.components / n.c, n.generators, n.buses, etc.
  ├── NetworkDescriptorsMixin  — property accessors, type descriptors
  ├── NetworkTransformMixin    — n.add(), n.remove(), n.madd() (bulk add)
  ├── NetworkIndexMixin        — n.snapshots, n.investment_periods, n.set_snapshots()
  ├── NetworkConsistencyMixin  — n.consistency_check()
  ├── NetworkGraphMixin        — n.graph(), n.adjacency_matrix(), n.incidence_matrix()
  ├── NetworkPowerFlowMixin    — n.pf(), n.lpf()
  └── NetworkIOMixin           — import/export: CSV, netCDF, HDF5, Excel, pandapower, pypower

Accessor objects (set in __init__):
  n.optimize    → OptimizationAccessor  (n.optimize.create_model, n.optimize.solve_model, ...)
  n.cluster     → ClusteringAccessor
  n.statistics  → StatisticsAccessor
  n.plot        → PlotAccessor
```

#### Component data model

Components are stored in a `ComponentsStore` (a dict-like container). Each entry is a
`Component` (legacy API) wrapping a `ComponentType` metadata object. Data lives in:

- `c.static` — `pd.DataFrame`, one row per component instance (static attributes)
- `c.dynamic` — dict of `pd.DataFrame` keyed by attribute name (time-varying attributes)

The v1.0 new-API equivalents are `n.c.<list_name>.static` and `n.c.<list_name>.dynamic`.

#### Optimization model construction

Optimization is entirely in the `optimization/` subpackage:
- `variables.py` — `define_*_variables()` functions (one per variable group)
- `constraints.py` — `define_*_constraints()` functions
- `global_constraints.py` — cross-component constraints
- `optimize.py` — `OptimizationAccessor` orchestrates variable → constraint → objective construction
- `mga.py` — Modeling-to-Generate-Alternatives

Constraint/variable functions are pure functions taking `(n, sns)` — they do not mutate
the network object directly beyond writing to `n.model`. This makes them straightforward
to replicate or override.

The underlying solver interface is **Linopy** (not direct Pyomo/CVXPY). Linopy wraps multiple
solvers (HiGHS default, Gurobi, CPLEX, GLPK, etc.) and uses xarray DataArrays for
vectorized constraint building.

---

### Interoperability

#### DataFrames

All component data is pandas DataFrames. `n.add()` accepts:
- scalar values (broadcast to all)
- Python lists / numpy arrays (static, per-component)
- `pd.Series` (static, indexed by component name)
- `pd.DataFrame` (time-varying, index = snapshots, columns = component names)

`n.generators`, `n.lines`, etc. are direct references to `c.static` DataFrames —
mutations to these DataFrames immediately affect the network.

`import_components_from_dataframe()` / `import_series_from_dataframe()` exist as legacy
methods for bulk DataFrame-based import.

#### NetworkX

Full NetworkX `MultiGraph` is returned by `n.graph()` — all standard NetworkX algorithms
(shortest path, connected components, spectral, etc.) work out of the box. PyPSA does not
wrap or limit the graph object post-creation.

NetworkX is a **hard dependency** of PyPSA (not optional).

#### Graphs.jl

No native Julia interoperability. PyPSA is Python-only. Cross-tool integration would require
exporting to a shared format (netCDF/CSV) and importing in Julia.

#### pandapower

`n.import_from_pandapower_net(net, extra_line_data, use_pandapower_index)` is built in.
Marked "still in beta"; unsupported features include three-winding transformers, switches,
in_service status, shunt impedances, transformer tap positions.

#### PyPower

`n.import_from_pypower_ppc(ppc)` supports MATPOWER/PyPower ppc dict format.

#### Serialization formats

| Format | Import | Export | Notes |
|--------|--------|--------|-------|
| netCDF (.nc) | `import_from_netcdf()` | `export_to_netcdf()` | Recommended; xarray-backed; supports compression |
| CSV folder | `import_from_csv_folder()` | `export_to_csv_folder()` | Human-readable; one CSV per component |
| HDF5 (.h5) | `import_from_hdf5()` | `export_to_hdf5()` | Compact binary |
| Excel (.xlsx) | `import_from_excel()` | `export_to_excel()` | Sheet name length limit (31 chars) with built-in mapping workaround |

The Linopy optimization model (`n.model`) is **not** included in any of these exports.
It must be saved separately via `n.model.to_netcdf()` if persistence is required.

Network objects can also be loaded from URLs (HTTP/HTTPS, S3, GCS, Azure via `cloudpathlib`).

#### Multi-energy carrier support

Carriers are arbitrary strings — no enumeration. Buses carry a `carrier` attribute
(e.g., `"AC"`, `"DC"`, `"heat"`, `"hydrogen"`, `"gas"`, `"methane"`).

The `Link` component is the key sector-coupling primitive:
- Supports up to N ports: `bus0` (input), `bus1`…`busN` (outputs)
- Each output port has an `efficiencyK` scalar controlling the conversion ratio
- Example CHP: `bus0="gas_bus"`, `bus1="elec_bus"`, `bus2="heat_bus"`, `efficiency=0.4`, `efficiency2=0.4`
- Negative efficiency2 values model energy inputs at a secondary bus (e.g., CO₂ in methanation)
- Dispatch variable `p0` is the primary flow; `p1 = efficiency * p0`, `p2 = efficiency2 * p0`, etc.

---

## Sources

1. PyPSA source — `components/types.py`: `add_component_type()` function with docstring and implementation
   - `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/components/types.py`
2. PyPSA source — `network/components.py`: `NetworkComponentsMixin.components` property (line 127, uses `component_types_df`)
   - `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/network/components.py`
3. PyPSA source — `optimization/optimize.py`: `OptimizationAccessor.__call__()` with `extra_functionality` (lines 418–538) and `solve_model()` (lines 765–825)
   - `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/optimization/optimize.py`
4. PyPSA source — `network/graph.py`: `NetworkGraphMixin` with `graph()`, `adjacency_matrix()`, `incidence_matrix()`
   - `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/network/graph.py`
5. PyPSA source — `network/power_flow.py`: `SubNetwork.calculate_PTDF()` (line 1043)
   - `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/network/power_flow.py`
6. PyPSA source — `networks.py`: `Network` class mixin inheritance (lines 81–89) and accessor initialization (lines 173–187)
   - `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/networks.py`
7. PyPSA source — `network/io.py`: serialization methods (`import_from_netcdf`, `export_to_netcdf`, etc.) and `import_from_pandapower_net()`
   - `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/network/io.py`
8. PyPSA source — `data/components.csv`: built-in component type registry
   - `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/data/components.csv`
9. PyPSA documentation — Custom Constraints
   - https://docs.pypsa.org/latest/user-guide/optimization/custom-constraints/
10. PyPSA documentation — v1.0 migration guide
    - https://docs.pypsa.org/latest/user-guide/v1-guide/
11. PyPSA documentation — Optimize API reference
    - https://docs.pypsa.org/latest/api/networks/optimize/
12. PyPSA documentation — Link component
    - https://docs.pypsa.org/latest/user-guide/components/links/
13. GitHub — Issue #856: Defining custom components compatible with Linopy optimization (open, May 2024)
    - https://github.com/PyPSA/PyPSA/issues/856
14. GitHub — PR #1075: feat: introduce component class
    - https://github.com/PyPSA/PyPSA/pull/1075

---

## Gaps and Uncertainties

- **Custom component + optimization integration**: The `add_component_type()` API registers metadata but there is no supported path to have custom components automatically included in the Linopy optimization model. Issue #856 describes this gap and remains open. Needs live testing to confirm workarounds (subclassing `Network`, monkey-patching `component_types_df`) actually work in 1.1.2.

- **`component_types_df` vs `all_components` discrepancy**: The `Network.components` property uses `component_types_df` (static CSV snapshot) not `all_components` (live registry). It is unclear if this was an oversight or intentional (to keep networks deterministic). Needs verification whether calling `add_component_type()` before any `Network()` instantiation is sufficient.

- **PTDF as a dense array**: `sub_network.PTDF` is documented as a dense numpy array. For large networks this could be memory-intensive. No sparse PTDF option was found in the source; needs confirmation at scale.

- **Linopy model persistence**: `n.model.to_netcdf()` is mentioned as the path to persist the Linopy model, but round-trip fidelity (re-loading and re-solving) is not documented. Needs empirical testing.

- **Excel 31-char sheet name limitation**: Built-in mapping covers two known cases (`storage_units-state_of_charge_set`, `storage_units-efficiency_dispatch`). Whether other long attribute names silently fail needs testing.

- **pandapower bridge beta status**: Three-winding transformers, switches, in_service status, shunt impedances, and tap positions are unsupported. The extent of this limitation in practice depends on network complexity.

- **`override_components` / `override_component_attrs`**: These pre-v1.0 parameters were found referenced in community discussions but are not present in the v1.1.2 source. Their removal timeline and migration path needs clarification from the changelog.

- **NetworkCollection API**: Introduced in v1.0, allows storing/operating on multiple networks. Interaction with `extra_functionality` and custom components has not been researched.
