# PyPSA Research Context
# Merged from 4 research agents — 2026-03-11
# Used by all evaluation agents as background context.

## Section: API & Formulations

# pypsa — Research: API & Formulations

> **Note:** The dedicated API research agent stalled on a WebFetch call and did not complete.
> Key API findings are consolidated here from the Version Capabilities and Extensions research,
> which together provide comprehensive coverage of this focus area.

## Key Findings

- **Installed version:** 1.1.2 (latest as of 2026-02-23)
- **Primary power flow entry points:** `n.pf()` (Newton-Raphson AC PF), `n.lpf()` (linear/DC PF), `n.lpf_contingency()` (N-1 DC contingency)
- **Optimization entry point:** `n.optimize()` (unified LP/MILP/UC via linopy + HiGHS); supports DC OPF, SCUC, SCED, multi-period, BESS, rolling horizon
- **AC OPF:** `n.optimize.optimize_and_run_non_linear_powerflow()` — requires Ipopt; **Ipopt not installed in devcontainer → AC OPF tests will fail with `unsupported_in_installed_version`**
- **Data model:** All components (Bus, Line, Transformer, Generator, StorageUnit, Store, Load, Link, ShuntImpedance) stored as pandas DataFrames in `n.c.<component>.static` (static) and `n.c.<component>.dynamic` (time-series)
- **Result access:** `n.buses_t.v_ang`, `n.buses_t.marginal_price`, `n.lines_t.p0`, etc. via `_t` accessors
- **Custom constraints:** `extra_functionality(n, snapshots)` callable passed to `n.optimize()`, called after model build, before solve — full linopy model accessible as `n.model`
- **PTDF:** `sub_network.calculate_PTDF()` → `sub_network.PTDF` (dense numpy array, branches × buses)
- **Solver interface:** `solver_name` and `solver_options` kwargs on `n.optimize()`; only HiGHS available
- **Pre-v1.0 API removed:** `n.madd()`, `n.lopf()`, `n.iplot()` all gone — legacy scripts must be updated

## Detailed Notes

### Power Flow API

| Method | Description | Key Parameters |
|--------|-------------|----------------|
| `n.pf(snapshots)` | Full Newton-Raphson AC PF | `x_tol=1e-6`, `distribute_slack`, `slack_weights` |
| `n.lpf(snapshots)` | Linear (DC) PF | `skip_pre` |
| `n.lpf_contingency(snapshots, branch_outages)` | N-1 DC contingency sweep | `branch_outages` = list of branch names |
| `n.sub_networks.c.calculate_PTDF()` | PTDF matrix per subnetwork | Stored at `sub_network.PTDF` |

Results allocated to `n.buses_t`, `n.lines_t`, `n.transformers_t` after solve.

### Optimization API

```python
# Basic DC OPF
status, condition = n.optimize(solver_name="highs")

# Unit commitment (linearized)
n.optimize(linearized_unit_commitment=True, solver_name="highs")

# Multi-period time-series
n.optimize(snapshots=n.snapshots, solver_name="highs")

# Custom constraints
def extra(n, snapshots):
    m = n.model
    # add linopy constraints here
n.optimize(extra_functionality=extra, solver_name="highs")

# Security-constrained OPF
n.optimize.optimize_security_constrained(snapshots, branch_outages=outage_list)
```

### Data Model

- **Network components** are registered via `pypsa.components.types` and stored as `ComponentsStore`
- **Static data:** `n.<component_name>` or `n.c.<component_name>.static` (DataFrame, one row per asset)
- **Time-series data:** `n.<component_name>_t` or `n.c.<component_name>.dynamic` (dict of DataFrames)
- **Network object:** `pypsa.Network(import_name=None)` — empty or loaded from file

### Input/Output Formats

| Format | Read | Write | Notes |
|--------|------|-------|-------|
| netCDF4 | yes | yes | Recommended (xarray-backed) |
| CSV folder | yes | yes | Human-readable |
| HDF5 | yes | yes | Legacy |
| PyPower/MATPOWER | yes (via `import_from_pypower_ppc`) | no | Type-4 bus crash; no gencost |
| pandapower | yes (beta, `import_from_pandapower_net`) | no | Beta quality |

### Solver Interface

Only HiGHS is available in the devcontainer (via `highspy 1.13.1`). Ipopt is absent.
Gurobi, CPLEX, MOSEK are supported by linopy but not installed.

## Sources

1. Version Capabilities research: `evaluations/pypsa/results/research-version.md`
2. Extensions & Architecture research: `evaluations/pypsa/results/research-extensions.md`
3. PyPSA source: `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/`
4. PyPSA docs: https://pypsa.readthedocs.io/en/latest/

## Gaps and Uncertainties

- Detailed ACPF convergence behavior (tolerance handling, non-convergence codes) — verify during A-2 testing
- Exact `buses_t.marginal_price` units (MW vs pu) — verify during OPF testing (unit-mismatch watch)
- `n.statistics()` output format — verify during expressiveness testing

---

## Section: Extensions & Architecture

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

---

## Section: Limitations & Ecosystem

# pypsa — Research: Limitations & Ecosystem

Applies to: **PyPSA 1.1.2** (installed 2026-03-11; this is the current latest release).

---

## Key Findings

- PyPSA is **MIT-licensed** and has strong community adoption: ~1,897 GitHub stars, 616 forks, 99+ contributors, and an active PyPSA-Eur ecosystem model (545 stars, 379 forks).
- **AC OPF is implemented but requires Ipopt**, which is absent from the devcontainer — this test path is unavailable without installing Ipopt. The Newton-Raphson AC power flow (`n.pf()`) works without Ipopt and is robust (100-iteration limit, configurable tolerance).
- **Unit commitment (MILP) is supported** via binary/integer `status` variables on Generators and Links, but StorageUnit UC constraints (min-up/down time, start-up cost on storage) are **not yet implemented** (open issue #1280). There is also an active bug (#1602) where committable StorageUnits cause a variable-collision crash in the current release.
- **SCLOPF (security-constrained linear OPF) has a known intermittent test failure** (#1356, open): post-contingency line flows can exceed thermal limits by up to 7% on the SciGrid-DE example. This is attributed to solution degeneracy in the core `abstract.py` code and breaks CI on master intermittently.
- **MATPOWER import is a two-step bridge** with documented unsupported features: areas, gencosts (piecewise cost curves), and component status flags are silently dropped. Pypower is not installed in the environment; the pandapower bridge is available as a workaround.
- **Memory spikes x10 when shape geometries are stored in the network** (#1555, open, assigned). Loading a 50-node network with embedded shapes requires ~10.6 GB vs. ~120 MB without shapes.
- **Piecewise linear generator cost curves are not natively supported** as a generator input attribute. The `marginal_cost_quadratic` attribute enables quadratic costs but piecewise linear offer curves (MATPOWER gencost type 1) have no dedicated support — tracked as a gap in issue #1473.
- **Custom component type integration with the optimization model has an unresolved gap** (#856): `add_component_type()` registers metadata but new types do not automatically participate in model building.
- The release cadence is high: **11 releases between October 2025 and February 2026** (v1.0.0 through v1.1.2), with 6 patch releases in the v1.0 series alone, indicating active bug-fixing and some rough edges at the v1.0.0 boundary.
- Documentation is comprehensive and recently overhauled (new site at docs.pypsa.org for v1.0); Discourse forum activity is moderate with many unanswered Q&A threads.

---

## Detailed Notes

### Known Limitations

#### AC OPF — Ipopt dependency

PyPSA implements non-linear AC OPF via `n.optimize.optimize_and_run_non_linear_powerflow()`, which runs a linear OPF, then fixes dispatch and runs the non-linear power flow, iterating until feasibility. This requires Ipopt as the nonlinear solver. The method exists in v1.1.2 but Ipopt is not installed in the devcontainer (`which ipopt` returns nothing). As of 2026-03-11, AC OPF via this path is unavailable without installing Ipopt explicitly.

The AC power flow (`n.pf()`) does NOT require Ipopt — it uses `scipy.sparse.linalg.spsolve` inside a Newton-Raphson loop (100-iteration limit, default x_tol=1e-6). The solver is pure Python/SciPy, not pluggable.

Source: `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/network/power_flow.py`, `newton_raphson_sparse()` lines 257–298; `optimize.py` `optimize_and_run_non_linear_powerflow()`.

#### Unit commitment — StorageUnit gap

Generators and Links support full UC constraints: `min_up_time`, `min_down_time`, `start_up_cost`, `shut_down_cost`, `ramp_limit_start_up`, `ramp_limit_shut_down`. These use binary variables (`is_binary=True` in linopy) for non-modular units or integer variables for modular units. Linearized UC (continuous relaxation) is also supported via `linearized_unit_commitment=True`.

However, StorageUnits do NOT support UC constraints — there is no `committable` attribute for StorageUnit. This is a documented gap in issue #1280 (open, no milestone). Issue #1602 (open, confirmed on latest release) documents a crash when StorageUnit is set committable in rolling-horizon optimization: `ValueError: Variable 'StorageUnit-status' already assigned to model`.

Source: `optimization/constraints.py` `define_operational_constraints_for_committables()` — only Generator and Link are in scope.

#### SCLOPF intermittent test failure

Security-constrained LOPF (`n.optimize.optimize_security_constrained()`) passes contingency constraints through PTDF-based flow limits. On the SciGrid-DE example with two line outages, post-contingency flows occasionally exceed thermal limits by up to 7% (e.g., Line 673: 1.073 p.u.). This is confirmed on both latest release (v1.1.2) and master. Reproduction rate is ~1 in 30 runs. The root cause is believed to be solution degeneracy exposing a bug in `abstract.py` constraint formulation, not just numerical tolerance. Test `test_sclopf_scigrid.py::test_optimize_security_constrained` is "flaky" in CI.

Source: GitHub issue #1356 (open, created 2024, 5 comments, no fix).

#### MATPOWER / PyPower import limitations

`n.import_from_pypower_ppc(ppc)` explicitly warns at runtime:

> "Warning: Note that when importing from PYPOWER, some PYPOWER features not supported: areas, gencosts, component status"

Specific unsupported features confirmed in source code:
1. **gencosts** (piecewise linear or polynomial cost curves) — the entire `gencost` array is ignored; generator `marginal_cost` must be set separately.
2. **component status** (generator/branch in-service flags) — all components are imported as active regardless of MATPOWER status bit.
3. **areas** — area assignments dropped.
4. **Bus type 4** (isolated buses) — the `controls` list maps types 1–3 (`PQ`, `PV`, `Slack`); type 4 maps to index 4 which would raise an `IndexError` or silently corrupt if any isolated buses are present. No explicit guard exists in the source.
5. **Three-winding transformers** — labeled `wontfix` in issue #643. Only two-winding transformers are supported.
6. **Phase-shifting transformers** — no dedicated PST component (issue #456, open). Links can approximate PST behavior but require manual formulation.

Source: `pypsa/network/io.py` `import_from_pypower_ppc()` full source; GitHub issues #643, #456.

#### Memory scaling — shape geometries

When a network contains `n.shapes` (geometry data for spatial visualization), loading from NetCDF triggers a 10x–80x memory spike. For a 50-node network: 10.6 GB with shapes vs. 120 MB without. This was introduced in PyPSA-Eur when shape files were embedded in network files for convenient plotting. The underlying cause is `xr.open_dataset()` loading all geometry data eagerly. This issue is more severe for large networks (100+ nodes with embedded geometries).

Source: GitHub issue #1555 (open, assigned to FabianHofmann).

#### Piecewise linear generator costs

No native piecewise linear cost curve (`marginal_cost_offer_curve` or similar) for generators. `marginal_cost_quadratic` (scalar, added in a recent release) allows quadratic costs but is incompatible with CVaR optimization (documented in `optimize.py` line 351–357). An open high-priority issue #1020 ("Add Option for Marginal Cost Offer Curve") is labeled `high priority`. Issue #1473 ("Piecewise costs and constraints") is also open.

#### Constraint matrix scaling

No automatic constraint matrix scaling is implemented. For large mixed-integer programs, poorly scaled constraint matrices degrade solver performance. Issue #309 (open, `gap` label, 8 comments) discusses adding AnyMOD-style matrix scaling. This can require solver-side workarounds for large models.

#### DC network power flow (non-linear)

`n.pf()` requires a workaround for meshed DC networks (set all reactive components to zero, treat as AC). Native non-linear DC power flow using correct equations is not implemented. Issue #40 (open since early project history, `help wanted`). This primarily affects HVDC mesh modeling.

#### pandas 3.x compatibility

PyPSA v1.1.0 added Pandas v3 compatibility improvements but the installed environment uses pandas 2.3.3. The `uv.lock` should be checked if pandas ≥ 3.0 is ever required; some optimization tests may break.

#### Rolling horizon + linearized UC bugs

Multiple point-release fixes were needed for rolling horizon optimization combined with linearized unit commitment:
- v1.0.3: ramp + rolling horizon logic fix
- v1.0.5: rolling horizon broadcast bug in linearized UC scenarios
- v1.0.6: rolling horizon logic with linearized UC and ramp limits

This suggests rolling horizon UC is a complex, recently stabilized feature that warrants extra test coverage.

---

### Open Issues Relevant to Evaluation

| Issue | Title | Status | Relevance |
|-------|-------|--------|-----------|
| [#1602](https://github.com/PyPSA/PyPSA/issues/1602) | ValueError: StorageUnit-status already assigned when committable=True | Open (confirmed on 1.1.2) | MILP/UC tests with committable storage |
| [#1585](https://github.com/PyPSA/PyPSA/issues/1585) | ArrowStringArray from NetCDF loading breaks optimize() on pandas ≥ 2.0 | Open | MATPOWER import → optimize workflow |
| [#1356](https://github.com/PyPSA/PyPSA/issues/1356) | SCLOPF intermittently allows post-contingency line overloads | Open, flaky CI | N-1 security constrained OPF tests |
| [#1280](https://github.com/PyPSA/PyPSA/issues/1280) | Unit commitment constraints on storage units | Open (no milestone) | Full SCUC with storage |
| [#1273](https://github.com/PyPSA/PyPSA/issues/1273) | Account for snapshot weightings in ramp limits | Open, `breaking` label | Ramp constraint accuracy |
| [#1282](https://github.com/PyPSA/PyPSA/issues/1282) | Conflicts in ramping conditions during start-up with minimum part loads | Open | UC ramp + min-load interactions |
| [#1281](https://github.com/PyPSA/PyPSA/issues/1281) | Approximate MILP UC prices with optimize_and_resolve_fixed_unit_commitment() | Open | Price recovery post-UC |
| [#1555](https://github.com/PyPSA/PyPSA/issues/1555) | Memory spikes x10 if shapes are in a network | Open (assigned) | Large network scalability |
| [#856](https://github.com/PyPSA/PyPSA/issues/856) | Defining custom components compatible with Linopy optimization | Open (May 2024) | Extensibility tests |
| [#604](https://github.com/PyPSA/PyPSA/issues/604) | PTDF calculation | Open (13 comments) | PTDF accuracy/correctness |
| [#309](https://github.com/PyPSA/PyPSA/issues/309) | Constraint matrix scaling | Open, `gap` | Large-scale MILP performance |
| [#1020](https://github.com/PyPSA/PyPSA/issues/1020) | Add Option for Marginal Cost Offer Curve | Open, `high priority` | Piecewise cost expressiveness |
| [#643](https://github.com/PyPSA/PyPSA/issues/643) | Three-Winding Transformers | Open, `wontfix` | Network import completeness |
| [#456](https://github.com/PyPSA/PyPSA/issues/456) | Phase Shifting Transformers (PST) | Open | Advanced branch modeling |
| [#40](https://github.com/PyPSA/PyPSA/issues/40) | Support DC networks in n.pf() without workaround | Open, `help wanted` | DC power flow correctness |

---

### Ecosystem Packages

The PyPSA organization (github.com/PyPSA) publishes a suite of tools that form a complete modeling ecosystem:

| Package | Stars | Forks | Purpose | License |
|---------|-------|-------|---------|---------|
| **PyPSA** | 1,897 | 616 | Core framework | MIT |
| **pypsa-eur** | 545 | 379 | European energy system model (Snakemake workflow) | MIT |
| **atlite** | 374 | 126 | Renewable potential from ERA5/MERRA weather data | MIT |
| **linopy** | 239 | 75 | Linear optimization interface (xarray-based, wraps HiGHS/Gurobi/CPLEX/GLPK/MOSEK/COPT/cuPDLP) | MIT |
| **powerplantmatching** | 214 | 71 | Open power plant database tool | MIT |
| **technology-data** | 115 | 55 | Technology cost and efficiency assumptions database | CC-BY-4.0 |
| **pypsa-usa** | 121 | 44 | US energy system model | MIT |
| **pypsa-eur-sec** | 105 | 54 | Legacy European sector-coupling model (superseded by pypsa-eur) | MIT |

**Key dependency chain**: PyPSA → Linopy → HiGHS (open-source LP/MILP solver bundled via highspy).

**Solver support via Linopy** (from `linopy.readthedocs.io`):
- Open-source: HiGHS (default, bundled), GLPK, CBC
- Commercial: Gurobi, CPLEX, MOSEK, Xpress, COPT, MindOpt
- Specialized: cuPDLPx (GPU-accelerated LP)

In the devcontainer only HiGHS is available (`linopy.available_solvers == ['highs']`).

**All core packages use MIT license**. Dependency licenses:
- numpy (BSD 3-Clause), scipy (BSD 3-Clause), pandas (BSD 3-Clause), xarray (Apache-2.0), networkx (BSD 3-Clause), geopandas (BSD 3-Clause), shapely (BSD 3-Clause), linopy (MIT), highspy (MIT)
- No GPL-licensed dependencies in the core stack — safe for proprietary integrations.

---

### Community & Documentation

#### Community Size

- **GitHub**: 1,897 stars, 616 forks, 121 open issues, 99+ code contributors (GitHub contributor page reports 99 when paginated at 100 per page, actual count may be higher)
- **Ecosystem**: pypsa-eur alone has 545 stars and 379 forks, indicating significant real-world usage
- **Industry users**: TenneT, d-fine, Fraunhofer ISI, AGGM (Austrian Gas Grid), Serentica listed in official `users.md` as of v1.1.x
- **Forum**: A Discourse forum at `pypsa.discourse.group` exists but appears to have intermittent connectivity issues. GitHub Discussions are available with Q&A, General, Show-and-Tell, and Ideas categories. Many Q&A threads remain unanswered.
- **Discord**: Active Discord community mentioned on the project website.
- **Mailing list**: Legacy Google Groups mailing list still referenced in older issues.

#### Documentation Quality

The v1.0.0 release included a complete documentation overhaul with a new site (`docs.pypsa.org`). The site uses MkDocs Material and covers:

- **User Guide**: Components reference (Buses, Generators, Loads, Links, StorageUnits, Lines, Transformers, ShuntImpedances, Carriers, GlobalConstraints), optimization formulations, power flow theory, clustering, statistics, plotting, I/O
- **Examples**: Organized into operational problems, planning problems, sector coupling, advanced topics, complexity management — with Jupyter notebooks
- **API Reference**: Class and function docstrings auto-generated via mkdocstrings-python
- **Contributing guide**: Code of conduct, security policy, contributor list

**Strengths**: Formulation documentation is detailed (LaTeX equations for constraints); examples are numerous and cover real use cases (negative prices, sensitivity analysis, water values).

**Gaps observed**:
- `docs.pypsa.org/en/latest/` and `docs.pypsa.org/en/stable/` both returned 404 during this research session (possible hosting issue or URL structure change since v1.0 migration). The redirects from readthedocs.io also failed.
- Statistics module documentation has an open issue (#1559: "Improve documentation and conventions on statistics module")
- Global constraint operational limit documentation flagged as gap (#1111)
- More forms of `Line` limits documentation flagged as gap (#1481)

---

### Release History

**Recent Release Cadence** (GitHub Releases API):

| Version | Date | Key Changes |
|---------|------|-------------|
| **v1.1.2** | 2026-02-23 | Bug: CPLEX `log_to_console` incompatibility; statistics `at_port` fix |
| **v1.1.1** | 2026-02-23 | Same (release pipeline fix) |
| **v1.1.0** | 2026-02-17 | Capital cost split (investment + fom_cost); temporal clustering; `.env` config support; StorageUnit `p_set` time series; Pandas v3 compatibility improvements; SALib sensitivity analysis example; water values example |
| **v1.0.7** | 2026-01-13 | Pin netcdf!=1.7.4; Python 3.14 support; revert annuity calc change |
| **v1.0.6** | 2025-12-22 | `n.stats` accessor; rolling horizon + linearized UC + ramp limit bug fixes; stochastic network fixes |
| **v1.0.5** | 2025-12-04 | CVaR fix; inactive generator in global carrier constraints; rolling horizon UC broadcast bug |
| **v1.0.4** | 2025-11-21 | Inactive storage component constraints fix; KVL NaN masking fix; busmap clustering fix |
| **v1.0.3** | 2025-11-06 | Ramp + rolling horizon logic fix |
| **v1.0.2** | 2025-10-24 | Path type support in I/O; `max_relative_growth` unit fix |
| **v1.0.1** | 2025-10-20 | v1.0 follow-up fixes; consistency checking improvements |
| **v1.0.0** | 2025-10-14 | **Major release**: new optimization module, stochastic networks, risk-averse optimization, new documentation, removed all v0.x deprecations |
| **v0.35.2** | 2025-08-15 | Last v0.x patch release (concurrent with v1.0.0rc1) |
| **v0.35.1** | 2025-07-03 | |
| **v0.35.0** | 2025-06-22 | |
| **v0.34.x** | 2025-03–2025-04 | |
| **v0.33.x** | 2025-02–2025-03 | |
| **v0.32.x** | 2024-12–2025-01 | |

**Release cadence**: Monthly or more frequent in 2024–2026. The v1.0 series had 7 patch releases in 3 months, indicating the major rewrite required significant stabilization effort.

**Breaking changes in v1.0.0** (relevant to new code):
1. `n.madd()` / `n.mremove()` removed → use `n.add()` / `n.remove()` with lists
2. `n.lopf()` removed → use `n.optimize()`
3. `n.iplot()` removed → use `n.explore()`
4. `n.add()` now returns `None` by default (pass `return_names=True`)
5. Statistics API renamed (`comps` → `components`, etc.)
6. `ramp_limit_start_up/shut_down` defaults changed to `NaN`
7. `override_components` / `override_component_attrs` constructor params removed

All tests in this evaluation are written against v1.1.2, so these are only relevant for upgraders.

---

## Sources

1. GitHub Releases API: `https://api.github.com/repos/PyPSA/PyPSA/releases?per_page=30` — release history
2. GitHub Issues API: `https://api.github.com/repos/PyPSA/PyPSA/issues` — open issues, filtered by topic
3. GitHub Repo API: `https://api.github.com/repos/PyPSA/PyPSA` — stars, forks, open_issues, license
4. GitHub Org API: `https://api.github.com/orgs/PyPSA/repos` — ecosystem package stats
5. GitHub issue #1356: SCLOPF flaky test — `gh issue view 1356 --repo PyPSA/PyPSA`
6. GitHub issue #1602: StorageUnit committable crash — `gh issue view 1602 --repo PyPSA/PyPSA`
7. GitHub issue #1280: UC constraints on storage units — `gh issue view 1280 --repo PyPSA/PyPSA`
8. GitHub issue #1555: Memory spikes x10 with shapes — `gh issue view 1555 --repo PyPSA/PyPSA`
9. GitHub issue #643: Three-winding transformers (wontfix) — `gh issue view 643 --repo PyPSA/PyPSA`
10. GitHub issue #309: Constraint matrix scaling — `gh issue view 309 --repo PyPSA/PyPSA`
11. Installed source: `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/network/power_flow.py` — Newton-Raphson implementation, convergence logic
12. Installed source: `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/optimization/optimize.py` — `optimize_and_run_non_linear_powerflow`, objective construction, quadratic cost
13. Installed source: `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/optimization/constraints.py` — unit commitment constraints scope, piecewise loss approximation
14. Installed source: `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/optimization/variables.py` — binary/integer variable selection for UC
15. Installed source: `pypsa.Network.import_from_pypower_ppc` — source obtained via `inspect.getsource()`; confirmed unsupported features list
16. Runtime checks: `importlib.metadata`, `linopy.available_solvers`, `linopy.solver_capabilities` — solver availability and dependency versions
17. pypsa.org project website: `https://pypsa.org/` — ecosystem overview, community info
18. PyPSA release v1.0.0: `https://github.com/PyPSA/PyPSA/releases/tag/v1.0.0` — breaking changes summary
19. linopy documentation: `https://linopy.readthedocs.io/en/latest/` — solver support matrix
20. Cross-reference with prior research in `evaluations/pypsa/results/research-version.md` and `evaluations/pypsa/results/research-extensions.md`

---

## Gaps and Uncertainties

- **AC OPF with Ipopt**: Could not be tested. If Ipopt is installed (`apt install coinor-libipopt-dev` + `pip install cyipopt`), `n.optimize.optimize_and_run_non_linear_powerflow()` should work. Convergence behavior at scale is unknown.
- **PTDF accuracy (issue #604)**: The PTDF calculation issue (#604) has 13 comments but no resolution — the nature of the inaccuracy is unclear. Whether `calculate_PTDF()` produces correct values for all network topologies requires direct numerical verification.
- **Largest networks successfully run**: No official benchmark numbers were found for maximum bus count. PyPSA-Eur uses 50–250 clustered nodes in practice; full-resolution European transmission networks are in the thousands. The 30k-bus MATPOWER FNM case has not been documented as tested. The dense PTDF matrix at 30k buses × 35k lines would require ~30k × 35k × 8 bytes ≈ 8 GB of RAM per SubNetwork.
- **PyPI download statistics**: Not researched; would provide clearer adoption signal than GitHub stars alone.
- **Discourse forum accessibility**: `pypsa.discourse.group` was unreachable during this research session (ECONNREFUSED). The GitHub Discussions page shows moderate activity with unanswered questions.
- **gencost type 1 (piecewise) import**: The exact behavior when a MATPOWER case with piecewise linear gencosts is imported is not tested — whether it silently drops costs or raises an error needs empirical verification.
- **pandas ≥ 3.0 compatibility**: Issue #1585 (ArrowStringArray from NetCDF breaks optimize()) is open and was confirmed on `pandas >= 2.0`. The exact pandas version boundary for this bug is unclear.

---

## Section: Version Capabilities

# pypsa — Research: Version Capabilities

## Key Findings

- Installed version: **1.1.2** (the current latest as of 2026-02-23)
- Latest version: **1.1.2** — no delta; installed version IS the latest
- HiGHS: **yes** (highspy 1.13.1, available via linopy)
- Ipopt: **no** (binary not found on PATH; AC OPF with Ipopt is not available)
- GLPK: **no** (glpsol binary not found)
- PyPSA 1.x is a major rewrite vs. 0.x; all pre-1.0 method aliases (`n.madd`, `n.lopf`, `n.iplot`) were **removed** in 1.0.0
- PTDF matrix extraction confirmed working via `SubNetwork.calculate_PTDF()`
- N-1 contingency analysis available via `n.lpf_contingency()`
- Custom constraint injection supported via `extra_functionality` callback
- MATPOWER `.m` ingestion requires a two-step bridge (matpowercaseframes → pypower ppc dict → `n.import_from_pypower_ppc()`), but **pypower is not installed** in the environment; pandapower (installed as 3.4.0) can serve as an intermediate

## Installed Environment

### Package Versions

| Package | Version |
|---------|---------|
| pypsa | 1.1.2 |
| linopy | 0.6.4 |
| highspy | 1.13.1 |
| pandas | 2.3.3 |
| numpy | 2.3.5 |
| scipy | 1.16.3 |
| networkx | 3.6.1 |
| matplotlib | 3.10.8 |
| xarray | 2026.2.0 |
| pandapower | 3.4.0 |
| matpowercaseframes | 2.0.1 |
| geopandas | 1.1.2 |
| plotly | 6.6.0 |
| dask | 2026.1.2 |
| seaborn | 0.13.2 |

Full environment obtained via `importlib.metadata` inside the devcontainer with
`.devcontainer/dc-exec -C /workspace/evaluations/pypsa uv run python`.

### Solver Availability

| Solver | Available | How |
|--------|-----------|-----|
| HiGHS | **yes** | highspy 1.13.1 via linopy; confirmed by `linopy.solvers.available_solvers == ['highs']` |
| Ipopt | **no** | Binary not on PATH (`which ipopt` returns nothing) |
| GLPK | **no** | Binary not on PATH (`which glpsol` returns nothing) |
| CPLEX | not checked | Not expected in container |
| Gurobi | not checked | Not expected in container |

Source: devcontainer checks run 2026-03-11.

## Version Delta Analysis

### Changes Between Installed and Latest

The installed version (1.1.2) **is** the latest PyPSA release on PyPI as of 2026-02-23.
There is no delta to analyze. Recent version history:

| Version | Date | Key Changes |
|---------|------|-------------|
| 1.1.2 | 2026-02-23 | Bug fix: `log_to_console` breaking CPLEX; statistics `at_port` fix |
| 1.1.1 | 2026-02-23 | Same fixes minus release pipeline patch |
| 1.1.0 | 2026-02-17 | Split `capital_cost` into `investment` + `fom_cost`; temporal clustering; `include_objective_constant` param added to `optimize`; `StorageUnit` gains `p_set` time series; ramp limit constraint consolidation; Pandas v3 support pinned (pandas <3.0 for now) |
| 1.0.7 | 2026-01-13 | netCDF pin, Python 3.14 support |
| 1.0.6 | 2025-12-22 | `n.stats` accessor added; rolling horizon UC + ramp limit bug fixes; stochastic network fixes |
| 1.0.5 | 2025-12-04 | CVaR fix; inactive generator in global carrier constraint fix; rolling horizon linearized UC broadcast bug fix |
| 1.0.4 | 2025-11-21 | Inactive storage component handling fix; KVL NaN constraint masking fix |
| 1.0.3 | 2025-11-06 | Ramp + rolling horizon logic fix |
| 1.0.0 | 2025-10-14 | **Major v1 release**: new optimization module, stochastic networks, removed all 0.x deprecations |

Sources: GitHub Releases API `https://api.github.com/repos/PyPSA/PyPSA/releases`

### Breaking Changes Affecting Tests (relative to 0.x)

These are relevant only if any test scripts were written for PyPSA < 1.0:

1. **`n.madd()` removed** — use `n.add()` with a list/index of names instead.
2. **`n.mremove()` removed** — use `n.remove()`.
3. **`n.lopf()` removed** — use `n.optimize()`.
4. **`n.iplot()` removed** — use `n.explore()` or plotly-based plotting.
5. **`n.add()` return value changed** — now returns `None` by default; pass `return_names=True` to get names.
6. **`ramp_limit_start_up` / `ramp_limit_shut_down` defaults** — changed from implicit `1` to `NaN`; scripts setting these fields are unaffected, but code relying on the old default will silently behave differently.
7. **`cyclic_state_of_charge_per_period` / `e_cyclic_per_period` defaults** — changed from `True` to `False`; affects multi-investment-period BESS tests.
8. **Statistics API renamed** — `comps` → `components`, `aggregate_groups` → `groupby_method`, `aggregate_time` → `groupby_time`.
9. **`meshed_threshold` kwarg deprecated** — use `meshed_thresholds=[...]` in `n.optimize`.

Since all test scripts are being written fresh against 1.1.2, none of these are blockers.

## Test Capability Matrix

| Test Type | Supported in 1.1.2 | Notes |
|-----------|--------------------|-------|
| DCPF | **yes** | `n.lpf(snapshots)` — DC linear power flow on entire network; `sub_network.lpf(snapshots)` also available |
| ACPF | **yes** | `n.pf(snapshots)` — Newton-Raphson AC power flow; converges to tolerance `x_tol=1e-6`; returns convergence dict |
| DC OPF | **yes** | `n.optimize(solver_name='highs')` — linear OPF via linopy + HiGHS; both single-period and multi-period |
| AC OPF | **no** | `n.optimize.optimize_and_run_non_linear_powerflow()` exists but requires Ipopt, which is **not installed** |
| SCUC | **yes (binary)** | `n.optimize(linearized_unit_commitment=False)` with `committable=True` generators uses binary variables + HiGHS; big-M formulation available via `committable_big_m` param |
| SCUC (linearized) | **yes** | `n.optimize(linearized_unit_commitment=True)` — continuous relaxation of UC |
| SCED | **yes** | Standard `n.optimize()` without committable generators is pure SCED |
| Multi-period OPF | **yes** | Pass a multi-timestep `snapshots` to `n.optimize()`; investment periods via `n.set_investment_periods()` |
| BESS arbitrage | **yes** | `StorageUnit` with `marginal_cost_storage`, `efficiency_store/dispatch`, `cyclic_state_of_charge`; `p_set` time series now supported (1.1.0+) |
| N-1 contingency | **yes** | `n.lpf_contingency(snapshots, branch_outages)` returns line flows under each outage; security-constrained OPF via `n.optimize.optimize_security_constrained()` |
| PTDF | **yes** | `sub_network.calculate_PTDF()` populates `sub_network.PTDF` (branches × buses numpy array); BODF also available |
| Custom constraints | **yes** | `extra_functionality(n, snapshots)` callback passed to `n.optimize()` or `n.optimize.solve_model()`; called after model build, before solve; full linopy model exposed via `n.model` |
| Graph access | **yes** | `n.graph()` returns `networkx.Graph` (or `OrderedGraph`); `n.adjacency_matrix()`, `n.incidence_matrix()`, `n.cycle_matrix()` also available |
| Large network (MEDIUM ~10k buses) | **yes (expected)** | No hard bus limit; memory scales with O(buses × timesteps); `meshed_thresholds` parameter controls nodal balance grouping for memory efficiency |
| FNM ingestion (~30k buses via MATPOWER) | **partial** | `n.import_from_pypower_ppc(ppc_dict)` is available; `matpowercaseframes` (2.0.1) can parse `.m` files to a dict; however **pypower is not installed**, so the ppc dict must be constructed manually or via pandapower's MATPOWER reader. Pandapower 3.4.0 is installed and `n.import_from_pandapower_net(net)` is available as a bridge. |

## Unsupported Features

1. **AC OPF with Ipopt**: `n.optimize.optimize_and_run_non_linear_powerflow()` is implemented in 1.1.2 but the Ipopt solver binary is absent from the devcontainer. This test type cannot be run as-is.
2. **Direct MATPOWER `.m` file import**: No native `.m` parser in PyPSA. Requires a bridge: (a) `matpowercaseframes.CaseFrames` to parse `.m` → DataFrame → pypower ppc dict, but `pypower` package is not installed; (b) alternative: pandapower's MATPOWER reader → `n.import_from_pandapower_net()`.
3. **GLPK solver**: Not available; not needed since HiGHS covers LP/MILP.
4. **Stochastic two-stage optimization**: Available in 1.1.2 (`n.set_scenarios()`), but not required by current test protocol.

## Sources

1. PyPI JSON API: `https://pypi.org/pypi/pypsa/json` — confirmed 1.1.2 is latest
2. GitHub Releases API: `https://api.github.com/repos/PyPSA/PyPSA/releases?per_page=15` — release notes for 1.0.0–1.1.2
3. PyPSA docs release notes: `https://docs.pypsa.org/latest/release-notes/` — breaking changes summary
4. Installed source code: `/home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/`
   - `network/power_flow.py` — `pf`, `lpf`, `lpf_contingency` implementations
   - `optimization/optimize.py` — `optimize`, `create_model`, `solve_model`, `extra_functionality` hook
   - `optimization/constraints.py` — constraint definitions
5. Runtime introspection via devcontainer: `importlib.metadata`, `inspect.signature`, direct API calls — 2026-03-11

## Gaps and Uncertainties

1. **AC OPF path**: If Ipopt becomes available (installable in the container), `n.optimize.optimize_and_run_non_linear_powerflow()` should work without code changes. The method signature exists in 1.1.2.
2. **MATPOWER FNM ingestion at 30k buses**: The `import_from_pypower_ppc` path has a documented warning that areas, gencosts, and component status are not imported. For large transmission networks this may drop important data. The pandapower bridge (`import_from_pandapower_net`) may preserve more detail but pandapower's own MATPOWER reader behavior should be verified separately.
3. **Memory scaling at 10k+ buses**: No benchmark has been run yet. The `meshed_thresholds` feature in 1.1.x mitigates nodal balance memory usage, but PTDF computation (`calculate_PTDF`) produces a dense (branches × buses) matrix that may be large at FNM scale (~30k buses × ~35k lines).
4. **pandas < 3.0 pin**: The 1.1.0 release notes pin `pandas < 3.0.0`. The installed pandas is 2.3.3 which satisfies this. If pandas 3.0 is ever upgraded in the lockfile, optimization tests may break.
5. **`include_objective_constant` FutureWarning**: The 1.1.0 release adds this parameter with a FutureWarning that the default will change to `False` in v2.0. Tests should explicitly pass this argument to suppress noise in test output.

---
