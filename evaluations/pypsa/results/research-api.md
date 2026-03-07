# PyPSA — Research: API & Formulations

**Version evaluated:** PyPSA 1.1.2 (installed via `uv sync` in devcontainer)
**Linopy version:** 0.6.4 (optimization backend)
**Date:** 2026-03-06

## Key Findings

- PyPSA's central abstraction is `pypsa.Network`, a container holding all components as pandas DataFrames (static) and dicts-of-DataFrames (time-varying `_t` suffix). Components cannot exist outside a Network.
- The tool supports **linear power flow** (`n.lpf()`), **non-linear AC power flow** via Newton-Raphson (`n.pf()`), and **linear optimal power flow** (`n.optimize()`). There is no native AC OPF (non-convex NLP) solver — optimization is LP/MILP/QP only.
- Optimization uses **Linopy** as the backend (not Pyomo since v0.27+). Linopy supports 13 solvers; only **HiGHS** is installed in the evaluation environment. Supported solvers include Gurobi, CPLEX, GLPK, CBC, SCIP, Xpress, Knitro, Mosek, COPT, MindOpt, PIPS, and cuPDLPx.
- Unit commitment is supported via `committable=True` on generators/links, producing MILP problems with min up/down time, start-up/shut-down costs, and ramp constraints.
- Security-constrained OPF is available via `n.optimize.optimize_security_constrained()`, and contingency-based linear PF via `n.lpf_contingency()`.
- I/O supports CSV folders, NetCDF, HDF5, Excel, plus import-only from PyPOWER PPC dicts and pandapower networks. No direct MATPOWER `.m` file reader — requires conversion through PyPOWER or pandapower first.
- The data model uses 15 component types organized as one-port (Generator, Load, Store, StorageUnit, ShuntImpedance), branch (Line, Transformer, Link), and structural (Bus, SubNetwork, Carrier, GlobalConstraint, Shape, LineType, TransformerType).
- Results are written back onto the same DataFrames: `n.buses_t.marginal_price` for LMPs, `n.generators_t.p` for dispatch, `n.lines_t.p0`/`p1` for flows. Input and output columns are distinct — inputs are never overwritten.
- Multi-period investment planning, stochastic optimization (scenarios), MGA (modelling-to-generate-alternatives), rolling horizon, and iterative transmission expansion are all supported as first-class optimize sub-methods.
- Network visualization via `n.explore()` (interactive Pydeck maps) and matplotlib-based `n.plot()`. Graph-theoretic utilities include `n.graph()` (NetworkX), `n.adjacency_matrix()`, `n.incidence_matrix()`, and `n.cycle_matrix()`.

## Detailed Notes

### Data Model and Component Architecture

The `pypsa.Network` object is the top-level container. All components are stored as pandas DataFrames accessible via properties:

| Component | Access (static) | Access (dynamic) | Category |
|-----------|-----------------|-------------------|----------|
| Bus | `n.buses` | `n.buses_t` | Node |
| Generator | `n.generators` | `n.generators_t` | One-port |
| Load | `n.loads` | `n.loads_t` | One-port |
| StorageUnit | `n.storage_units` | `n.storage_units_t` | One-port |
| Store | `n.stores` | `n.stores_t` | One-port |
| ShuntImpedance | `n.shunt_impedances` | `n.shunt_impedances_t` | One-port |
| Line | `n.lines` | `n.lines_t` | Passive branch |
| Transformer | `n.transformers` | `n.transformers_t` | Passive branch |
| Link | `n.links` | `n.links_t` | Controllable branch |

**Bus** is the fundamental node. Key static columns: `v_nom`, `x`, `y`, `carrier`, `unit`, `control`, `v_mag_pu_set`, `v_mag_pu_min`, `v_mag_pu_max`. Dynamic outputs: `p`, `q`, `v_mag_pu`, `v_ang`, `marginal_price`.

**Generator** attaches to one bus. Notable static columns include `p_nom`, `p_nom_extendable`, `p_nom_min`, `p_nom_max`, `marginal_cost`, `marginal_cost_quadratic`, `capital_cost`, `efficiency`, `committable`, `start_up_cost`, `shut_down_cost`, `min_up_time`, `min_down_time`, `ramp_limit_up`, `ramp_limit_down`, `build_year`, `lifetime`. Dynamic inputs: `p_max_pu`, `p_min_pu`, `marginal_cost`. Dynamic outputs: `p`, `q`, `status`, `start_up`, `shut_down`, `mu_upper`, `mu_lower`.

**Line** connects `bus0` to `bus1` with PI-model parameters: `x` (reactance), `r` (resistance), `g` (conductance), `b` (susceptance), `s_nom` (thermal limit). Supports `s_nom_extendable` for capacity expansion. Dynamic outputs: `p0`, `q0`, `p1`, `q1`, `mu_lower`, `mu_upper`.

**Link** is a controllable, multi-purpose directed connection between buses with `efficiency` and `p_nom`. Supports unit commitment attributes identical to Generator. Can model HVDC, sector-coupling converters, or any directed energy conversion.

**StorageUnit** has `max_hours`, `efficiency_store`, `efficiency_dispatch`, `standing_loss`, `inflow`, `cyclic_state_of_charge`. Dynamic outputs include `p_dispatch`, `p_store`, `state_of_charge`, `spill`.

**Store** is a simpler energy buffer without power constraints — must be paired with a Link to control power flow.

Source: PyPSA v1.1.2 source code introspection; [Components documentation](https://docs.pypsa.org/v1.0.2/user-guide/components/)

### Adding Components

Components are added via `n.add(class_name, name, **kwargs)`:

```python
n.add("Bus", "bus0", v_nom=110)
n.add("Generator", "gen0", bus="bus0", p_nom=100, marginal_cost=30)
n.add("Line", ["line0", "line1"], bus0=["b0", "b0"], bus1=["b1", "b2"], x=[0.1, 0.2], s_nom=100)
```

Bulk addition accepts sequences for all parameters. Components are removed with `n.remove(class_name, name)`.

Source: `n.add()` signature from source introspection

### Network Constructor

```python
pypsa.Network(import_name="", name="Unnamed Network", ignore_standard_types=False)
```

The `import_name` parameter accepts a path to a CSV folder, NetCDF file, HDF5 file, or Excel file and auto-detects the format.

Source: `Network.__init__` signature from source introspection

### Power Flow Analysis

#### Non-linear AC Power Flow (`n.pf()`)

```python
n.pf(snapshots=None, skip_pre=False, x_tol=1e-06, use_seed=False,
     distribute_slack=False, slack_weights='p_set')
```

Uses Newton-Raphson iteration. Bus control types: Slack (reference voltage), PV (voltage-controlled), PQ (load). Supports distributed slack where active power imbalance is shared across generators proportionally to `slack_weights`.

Results written to: `n.buses_t.v_mag_pu`, `n.buses_t.v_ang`, `n.generators_t.p`, `n.generators_t.q`, `n.lines_t.p0`, `n.lines_t.q0`, etc.

Source: [Power Flow documentation](https://docs.pypsa.org/latest/user-guide/power-flow/); source introspection

#### Linear (DC) Power Flow (`n.lpf()`)

```python
n.lpf(snapshots=None, skip_pre=False)
```

Standard DC approximation: lossless, flat voltage, small angle differences. Results in `n.buses_t.v_ang` and branch `p0`/`p1`.

Source: source introspection

#### Contingency Analysis (`n.lpf_contingency()`)

```python
n.lpf_contingency(snapshots=None, branch_outages=None)
```

Runs linear power flow for each specified branch outage scenario. Returns a DataFrame of results.

Source: source introspection

### Optimization (LOPF)

#### Main Entry Point (`n.optimize()`)

```python
n.optimize(
    snapshots=None,
    multi_investment_periods=False,
    transmission_losses=False,           # bool or int (piecewise linear segments) or dict
    linearized_unit_commitment=False,
    model_kwargs=None,
    extra_functionality=None,            # callable for custom constraints
    assign_all_duals=False,
    solver_name=None,                    # default: 'highs'
    solver_options=None,
    log_to_console=None,
    compute_infeasibilities=False,
    include_objective_constant=None,
    committable_big_m=None,
)
```

Returns `(status, termination_condition)` tuple. The optimization is a **Linear Optimal Power Flow (LOPF)** — it minimizes total system cost (marginal costs + capital costs for extendable components) subject to energy balance, capacity limits, and network constraints.

**Problem types produced:**
- **LP** — standard dispatch/expansion without unit commitment
- **MILP** — when any component has `committable=True` (unit commitment) or `p_nom_extendable=True` with discrete `p_nom_mod`
- **QP** — when `marginal_cost_quadratic > 0` on any generator/link (requires a QP-capable solver)

Source: [Optimize API](https://docs.pypsa.org/latest/api/networks/optimize/); source introspection

#### Two-Step Workflow (`create_model` + `solve_model`)

```python
m = n.optimize.create_model(...)   # returns linopy.Model, stored at n.model
# User can inspect/modify m (add constraints, variables)
status, condition = n.optimize.solve_model(solver_name="highs", solver_options={})
```

This split allows injecting custom constraints between model creation and solving.

Source: source introspection

#### `extra_functionality` Callback

A callable `extra_functionality(n, snapshots)` can be passed to `n.optimize()` to add custom constraints/variables to the linopy model before solving. The model is accessible at `n.model`.

Source: [Optimization documentation](https://docs.pypsa.org/latest/user-guide/network-optimization/)

### Specialized Optimization Methods

| Method | Description |
|--------|-------------|
| `optimize_security_constrained()` | SCLOPF: adds branch flow limits under N-1 contingencies |
| `optimize_with_rolling_horizon(horizon, overlap)` | Segments long time series into windows, solves sequentially |
| `optimize_transmission_expansion_iteratively()` | Iterative LOPF with discrete line expansion (unit sizes) |
| `optimize_mga()` | Modelling-to-generate-alternatives: finds near-optimal solutions |
| `optimize_mga_in_direction()` | MGA in a specified direction vector |
| `optimize_mga_in_multiple_directions()` | Parallel MGA across multiple directions |
| `optimize_and_run_non_linear_powerflow()` | LOPF followed by AC power flow validation |
| `fix_optimal_capacities()` | Locks expansion results for subsequent operational runs |
| `fix_optimal_dispatch()` | Fixes dispatch solution for PF initialization |
| `add_load_shedding()` | Adds high-cost shedding generators to prevent infeasibility |

Source: source introspection; [Optimize API](https://docs.pypsa.org/latest/api/networks/optimize/)

### Solver Interfaces

PyPSA delegates solving to **Linopy** (v0.6.4), which supports 13 solver backends:

| Solver | LP | MILP | QP | Direct API | GPU | Installed |
|--------|----|----- |----|------------|-----|-----------|
| HiGHS | Yes | Yes | Yes | Yes | No | **Yes** |
| Gurobi | Yes | Yes | Yes | Yes | No | No |
| CPLEX | Yes | Yes | Yes | No | No | No |
| GLPK | Yes | Yes | No | No | No | No |
| CBC | Yes | Yes | No | No | No | No |
| SCIP | Yes | Yes | Yes | No | No | No |
| Xpress | Yes | Yes | Yes | No | No | No |
| Knitro | Yes | Yes | Yes | No | No | No |
| Mosek | Yes | Yes | Yes | Yes | No | No |
| COPT | Yes | Yes | Yes | No | No | No |
| MindOpt | Yes | Yes | Yes | No | No | No |
| PIPS | Yes | Yes | No | No | No | No |
| cuPDLPx | Yes | No | No | Yes | **Yes** | No |

Solver is selected via `solver_name="highs"` parameter. Solver-specific options passed as `solver_options={"threads": 4}`.

Source: Linopy 0.6.4 `SolverName` enum and `SolverFeature` introspection

### Input/Output Formats

#### Native Formats (read + write)

| Format | Import | Export | Notes |
|--------|--------|--------|-------|
| CSV folder | `n.import_from_csv_folder(path)` | `n.export_to_csv_folder(path)` | One CSV per component type + time series |
| NetCDF | `n.import_from_netcdf(path)` | `n.export_to_netcdf(path)` | Compact, supports lazy loading via xarray |
| HDF5 | `n.import_from_hdf5(path)` | `n.export_to_hdf5(path)` | Binary format |
| Excel | `n.import_from_excel(path)` | `n.export_to_excel(path)` | Resource-intensive, small networks only |

All four can be loaded directly via `Network(import_name="path/to/file_or_folder")`.

#### Import-Only Formats

| Format | Method | Notes |
|--------|--------|-------|
| PyPOWER PPC v2 dict | `n.import_from_pypower_ppc(ppc)` | Standard bus/branch/gen arrays |
| pandapower net | `n.import_from_pandapower_net(net)` | Beta; no 3-winding transformers, switches, or tap positions |

**MATPOWER `.m` files** are not directly importable. The recommended path is via `matpowercaseframes` (installed in evaluation env) to parse `.m` to a PPC dict, then `import_from_pypower_ppc()`. Alternatively, pandapower can load MATPOWER cases and then be imported.

#### Cloud Storage

CSV, NetCDF, and HDF5 support cloud paths (S3, GCS, Azure) via `cloudpathlib`.

Source: [Import/Export documentation](https://docs.pypsa.org/v1.0.2/user-guide/import-export/); source introspection

### Results Access Patterns

After optimization (`n.optimize()` returns `("ok", "optimal")`):

| Result | Access |
|--------|--------|
| Objective value | `n.objective` |
| Bus marginal prices (LMPs) | `n.buses_t.marginal_price` (DataFrame: snapshots x buses) |
| Generator dispatch | `n.generators_t.p` |
| Generator reactive power | `n.generators_t.q` |
| UC status | `n.generators_t.status` (binary, if committable) |
| Line active power flow | `n.lines_t.p0`, `n.lines_t.p1` |
| Line shadow prices | `n.lines_t.mu_upper`, `n.lines_t.mu_lower` |
| Storage state of charge | `n.storage_units_t.state_of_charge` |
| Optimal capacities | `n.generators.p_nom_opt`, `n.lines.s_nom_opt` |
| Is solved? | `n.is_solved` (bool property) |

After power flow (`n.pf()`):

| Result | Access |
|--------|--------|
| Bus voltage magnitudes | `n.buses_t.v_mag_pu` |
| Bus voltage angles | `n.buses_t.v_ang` |
| Active/reactive injections | `n.buses_t.p`, `n.buses_t.q` |

Source: source introspection of `_t` attribute keys

### Statistics Accessor (`n.stats`)

Post-solve analytics via `n.stats.<method>()`, each returning a DataFrame:

`capacity_factor`, `capex`, `curtailment`, `energy_balance`, `expanded_capacity`, `expanded_capex`, `fom`, `installed_capacity`, `installed_capex`, `market_value`, `opex`, `optimal_capacity`, `overnight_cost`, `prices`, `revenue`, `supply`, `system_cost`, `transmission`, `withdrawal`

Source: source introspection

### Graph and Topology Utilities

| Method | Returns | Description |
|--------|---------|-------------|
| `n.graph()` | `OrderedGraph` (NetworkX) | Full network graph |
| `n.adjacency_matrix()` | scipy sparse matrix | Bus adjacency |
| `n.incidence_matrix()` | scipy sparse CSR matrix | Bus-branch incidence |
| `n.cycle_matrix()` | matrix | Independent cycles |
| `n.determine_network_topology()` | Network | Identifies connected sub-networks |

Source: source introspection

### Clustering

PyPSA 1.1.2 includes spatial and temporal clustering as accessor classes:

- `SpatialClusteringAccessor` — network reduction by aggregating buses
- `TemporalClusteringAccessor` — snapshot reduction by representative periods

Source: `pypsa.clustering` module introspection

### Built-in Example Networks

Available via `pypsa.examples`:

- `ac_dc_meshed` — AC/DC meshed network
- `scigrid_de` — German transmission network (SciGRID)
- `storage_hvdc` — Storage with HVDC links
- `stochastic_network` — Stochastic optimization example
- `carbon_management` — Carbon capture/storage
- `model_energy` — Generic energy model

Source: `pypsa.examples` module introspection

### New Components API (v1.0+)

PyPSA v1.0 introduced an optional new components API enabled via:

```python
pypsa.options.api.new_components_api = True
```

This changes access from `n.generators`/`n.generators_t` to `n.components.generators.static`/`.dynamic`, adding type-hinted `add()` and `rename_component_names()`.

Source: [Components documentation](https://docs.pypsa.org/v1.0.2/user-guide/components/)

## Sources

1. PyPSA v1.1.2 installed source code (introspected in devcontainer)
2. Linopy v0.6.4 installed source code (solver enumeration)
3. [PyPSA Documentation Home](https://docs.pypsa.org/latest/)
4. [Optimize API Reference](https://docs.pypsa.org/latest/api/networks/optimize/)
5. [Power Flow Documentation](https://docs.pypsa.org/latest/user-guide/power-flow/)
6. [Design Documentation](https://docs.pypsa.org/latest/user-guide/design/)
7. [Components Documentation](https://docs.pypsa.org/v1.0.2/user-guide/components/)
8. [Import/Export Documentation](https://docs.pypsa.org/v1.0.2/user-guide/import-export/)
9. [Optimization Overview](https://docs.pypsa.org/v1.0.2/user-guide/optimization/overview/)
10. [PyPSA GitHub Repository](https://github.com/PyPSA/PyPSA)
11. [PyPSA Paper (arXiv)](https://arxiv.org/pdf/1707.09913)

## Gaps and Uncertainties

- **No native AC OPF.** PyPSA cannot solve non-convex AC optimal power flow. The `optimize()` method produces LP/MILP/QP problems only. The `optimize_and_run_non_linear_powerflow()` method runs LOPF then validates with AC PF, but does not jointly optimize with AC constraints.
- **No direct MATPOWER `.m` import.** Requires an intermediate conversion step through `matpowercaseframes` or pandapower. The evaluation environment has `matpowercaseframes` installed, so this path should work but needs testing.
- **pandapower import is beta.** Missing support for three-winding transformers, switches, in_service status, and transformer tap positions. Needs testing to see what data is lost for the evaluation case files.
- **LOPF formulation options unclear for v1.1.2.** Older docs reference `formulation="kirchhoff"` parameter on `lopf()`. The current `optimize()` API does not expose this parameter directly — it may be handled internally or via `model_kwargs`. Needs verification.
- **Transmission losses in LOPF.** The `transmission_losses` parameter accepts `bool | int | dict` for piecewise-linear loss approximation, but exact behavior (number of segments, secant vs tangent modes) needs testing.
- **QP support scope.** Quadratic marginal costs are supported (`marginal_cost_quadratic`), but whether full QCQP or only QP-with-linear-constraints is supported needs clarification from Linopy docs.
- **SCUC/SCED terminology.** PyPSA does not use the terms SCUC or SCED explicitly. Unit commitment is modeled via `committable=True` on generators. Security-constrained optimization is a separate method (`optimize_security_constrained`). Whether these compose to produce a true SCUC needs testing.
- **Solver option passthrough.** The extent to which solver-specific options (e.g., HiGHS IPM vs simplex, Gurobi method selection) are forwarded needs testing.
