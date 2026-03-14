---
tool: pypsa
version: 1.1.2
linopy_version: 0.6.4
research_date: 2026-03-13
research_focus: API surface, supported problem formulations, solver interfaces, data model, input/output formats
---

# PyPSA v1.1.2 — API & Formulations Research

## 1. Data Model

### 1.1 Central Object: `pypsa.Network`

All components exist within a single `Network` container. A network cannot contain orphan components — every generator, line, load, etc. is attached to the network and indexed by a unique string name.

**Source:** `pypsa/networks.py`, design docs at `docs/user-guide/design.md` ([GitHub](https://github.com/PyPSA/PyPSA/blob/master/docs/user-guide/design.md))

```python
import pypsa
n = pypsa.Network()
n.set_snapshots(pd.date_range("2024-01-01", periods=24, freq="h"))
```

### 1.2 Component Taxonomy

PyPSA defines 15 component types in `pypsa/data/components.csv` ([source](https://github.com/PyPSA/PyPSA/blob/master/pypsa/data/components.csv)):

| Component | Category | Description |
|-----------|----------|-------------|
| **Bus** | (fundamental) | Node where all components attach. Carries `v_nom`, `carrier` (AC/DC/heat/gas), `x`/`y` coordinates. |
| **Carrier** | (metadata) | Energy carrier label (AC, DC, hydrogen, heat) or technology label (wind, gas turbine). |
| **Generator** | `controllable_one_port` | Power source at a bus. Supports `p_nom`, `p_min_pu`/`p_max_pu` time series, `marginal_cost`, `committable` UC, ramp limits. |
| **Load** | `controllable_one_port` | Demand at a bus (`p_set`, `q_set`). |
| **StorageUnit** | `controllable_one_port` | Inter-temporal storage with fixed energy-to-power ratio (`max_hours`). Separate `p_dispatch`/`p_store` variables, `state_of_charge`, `efficiency_store`/`efficiency_dispatch`, `standing_loss`, `inflow`, `spill_cost`. |
| **Store** | `controllable_one_port` | Generic inter-temporal storage without power limits. Sized by `e_nom` (MWh) not `p_nom`. |
| **Link** | `controllable_branch` | Controllable directed flow between 2+ buses with arbitrary carriers. Supports multi-output (bus2, bus3, ...) with separate efficiencies. Models HVDC, converters, heat pumps, electrolysers. |
| **Line** | `passive_branch` | AC transmission/distribution. Impedance parameters `r`, `x`, `b`, `g` (Ohms/Siemens). Standard types via `type` attribute. Flow determined by physics. |
| **Transformer** | `passive_branch` | 2-winding transformer with tap ratio and phase shift. Standard types available. |
| **LineType** / **TransformerType** | `standard_type` | Per-length/per-unit impedance templates. |
| **ShuntImpedance** | `passive_one_port` | Voltage-dependent admittance element. |
| **GlobalConstraint** | (constraint) | System-wide constraints (emission caps, capacity limits). |
| **Shape** | (geo) | Geographic shapes for visualization. |
| **SubNetwork** | (topology) | Connected sub-graphs of buses and passive branches (synchronous areas). Auto-detected by `n.determine_network_topology()`. |

**Source:** `pypsa/data/components.csv`, individual attribute CSVs in `pypsa/data/component_attrs/`

### 1.3 Static vs. Dynamic Data

Each component type has two data stores:

- **Static** (`n.generators`, `n.buses`, `n.lines`, ...): `pandas.DataFrame` indexed by component name. Contains time-invariant attributes.
- **Dynamic** (`n.generators_t`, `n.buses_t`, `n.lines_t`, ...): `dict[str, pd.DataFrame]` keyed by attribute name, each DataFrame indexed by snapshot. Contains time-varying attributes marked as `"static or series"` in the component attribute CSVs.

Access patterns:
```python
n.generators                  # static DataFrame (p_nom, bus, carrier, ...)
n.generators_t                # dict of time-series DataFrames
n.generators_t["p"]           # dispatch results: DataFrame(snapshots x generators)
n.generators_t["p_max_pu"]    # time-varying availability: DataFrame(snapshots x generators)
n.buses_t["marginal_price"]   # LMPs from optimization: DataFrame(snapshots x buses)
```

**Source:** `pypsa/network/abstract.py`, `pypsa/components/store.py`

### 1.4 Bus Attributes (Complete)

From `pypsa/data/component_attrs/buses.csv`:

| Attribute | Type | Unit | Default | Status |
|-----------|------|------|---------|--------|
| `v_nom` | float | kV | 1 | Input |
| `carrier` | string | — | "AC" | Input |
| `x`, `y` | float | — | 0 | Input (geo) |
| `v_mag_pu_set` | series | p.u. | 1 | Input |
| `control` | string | — | PQ | Output (from generators) |
| `p`, `q` | series | MW/MVar | 0 | Output |
| `v_mag_pu`, `v_ang` | series | p.u./rad | 1/0 | Output |
| `marginal_price` | series | currency/MWh | 0 | Output (shadow price) |

### 1.5 Generator Attributes (Key Fields)

From `pypsa/data/component_attrs/generators.csv`:

| Attribute | Type | Unit | Default | Status |
|-----------|------|------|---------|--------|
| `bus` | string | — | — | Input (required) |
| `p_nom` | float | MW | 0 | Input |
| `p_nom_extendable` | bool | — | False | Input |
| `p_min_pu`, `p_max_pu` | series | p.u. | 0 / 1 | Input |
| `marginal_cost` | series | curr/MWh | 0 | Input |
| `marginal_cost_quadratic` | series | curr/MWh | 0 | Input |
| `efficiency` | series | p.u. | 1 | Input |
| `committable` | bool | — | False | Input |
| `start_up_cost`, `shut_down_cost` | float | currency | 0 | Input |
| `stand_by_cost` | series | curr/h | 0 | Input |
| `min_up_time`, `min_down_time` | int | snapshots | 0 | Input |
| `ramp_limit_up`, `ramp_limit_down` | series | p.u. | NaN | Input |
| `capital_cost` | float | curr/MW | 0 | Input |
| `p` | series | MW | 0 | Output (dispatch) |
| `p_nom_opt` | float | MW | 0 | Output (optimized capacity) |
| `status` | series | — | 1 | Output (UC only) |
| `mu_upper`, `mu_lower` | series | curr/MWh | — | Output (dual) |

### 1.6 Line Attributes (Key Fields)

From `pypsa/data/component_attrs/lines.csv`:

| Attribute | Type | Unit | Default | Status |
|-----------|------|------|---------|--------|
| `bus0`, `bus1` | string | — | — | Input (required) |
| `r`, `x` | float | Ohm | 0 | Input (required) |
| `b`, `g` | float | Siemens | 0 | Input |
| `s_nom` | float | MVA | 0 | Input |
| `s_nom_extendable` | bool | — | False | Input |
| `s_max_pu` | series | p.u. | 1 | Input (dynamic rating) |
| `type` | string | — | — | Input (standard type lookup) |
| `length` | float | km | 0 | Input (used with `type`) |
| `num_parallel` | float | — | 1 | Input (parallel circuits) |
| `p0`, `p1` | series | MW | 0 | Output |
| `q0`, `q1` | series | MVar | 0 | Output |
| `x_pu`, `r_pu`, `x_pu_eff` | float | p.u. | 0 | Output (calculated) |
| `s_nom_opt` | float | MVA | 0 | Output |
| `mu_lower`, `mu_upper` | series | curr/MVA | 0 | Output (dual) |

### 1.7 Link Attributes (Multi-Bus Support)

Links connect 2 or more buses, enabling sector coupling. Additional buses (`bus2`, `bus3`, ...) are automatically expanded as needed with corresponding `efficiency2`, `efficiency3`, etc.

```python
# Model a combined heat and power (CHP) unit:
n.add("Link", "CHP",
      bus0="gas_bus",      # fuel input
      bus1="elec_bus",     # electricity output
      bus2="heat_bus",     # heat output
      efficiency=0.4,      # electricity efficiency
      efficiency2=0.45,    # heat efficiency
      p_nom=100)
```

**Source:** `pypsa/data/component_attrs/links.csv`

### 1.8 Graph and Topology

```python
n.graph()                    # NetworkX OrderedGraph
n.adjacency_matrix()         # scipy sparse or DataFrame
n.incidence_matrix()         # scipy sparse CSR
n.cycle_matrix()             # DataFrame
n.determine_network_topology()  # assigns buses to SubNetworks
```

**Source:** `pypsa/network/graph.py`

---

## 2. Supported Problem Formulations

### 2.1 Non-Linear AC Power Flow (ACPF)

**Entry point:** `n.pf(snapshots=None, skip_pre=False, x_tol=1e-6, use_seed=False, distribute_slack=False, slack_weights="p_set")`

- Full Newton-Raphson solver in `pypsa/network/power_flow.py`
- Solves S = VI* nodal power balance with full Y-bus admittance matrix
- Bus types: PQ, PV, Slack — auto-assigned from attached generators
- Distributed slack supported (`distribute_slack=True`) — proportional to `p_set`, `p_nom`, or `p_nom_opt`
- Pi-model for lines, T or Pi-model for transformers (with tap ratio and phase shift)
- Returns `Dict` with `n_iter`, `error`, `converged` per sub-network
- Results stored in: `n.buses_t["v_mag_pu"]`, `n.buses_t["v_ang"]`, `n.generators_t["p"]`, `n.generators_t["q"]`, `n.lines_t["p0"]`/`p1`/`q0`/`q1`

**Source:** `newton_raphson_sparse()` in `pypsa/network/power_flow.py` (lines 257–298), `SubNetworkPowerFlowMixin.pf()` and `.calculate_Y()`

### 2.2 Linear DC Power Flow (DCPF)

**Entry point:** `n.lpf(snapshots=None, skip_pre=False)`

- Solves P = B * theta using the B-matrix (inverse reactances)
- Assumptions: no reactive power, no voltage magnitude variation, small angle differences, r << x
- Returns `None` (results stored in-place)
- Results in: `n.buses_t["v_ang"]`, `n.lines_t["p0"]`/`p1`

**Source:** `SubNetworkPowerFlowMixin.lpf()`, `SubNetworkPowerFlowMixin.calculate_B_H()` in `pypsa/network/power_flow.py`

### 2.3 Contingency Analysis (N-1)

**Entry point:** `n.lpf_contingency(snapshots=None, branch_outages=None) -> pd.DataFrame`

- Computes PTDF matrix via `sub_network.calculate_PTDF()`
- Derives BODF (Branch Outage Distribution Factors) from PTDF
- Post-outage flow: `p_b^(c) = p_b + BODF_bc * p_c`
- Returns DataFrame of post-contingency flows

**Source:** `pypsa/network/power_flow.py`, contingency section of docs ([GitHub](https://github.com/PyPSA/PyPSA/blob/master/docs/user-guide/optimization/contingencies.md))

### 2.4 Linear Optimal Power Flow (LOPF / DC OPF)

**Entry point:** `n.optimize(solver_name="highs", solver_options=None, ...)`

Full signature:
```python
n.optimize(
    snapshots=None,
    multi_investment_periods=False,
    transmission_losses=False,          # int (segments) or dict per component
    linearized_unit_commitment=False,
    model_kwargs=None,
    extra_functionality=None,           # callback(n, snapshots)
    assign_all_duals=False,
    solver_name=None,                   # "highs", "gurobi", "glpk", "cplex", ...
    solver_options=None,                # dict passed to solver
    log_to_console=False,
    compute_infeasibilities=False,
    include_objective_constant=None,
    committable_big_m=None,
    **kwargs
) -> tuple[str, str]                    # (status, termination_condition)
```

**What it solves:**
- Minimizes total system cost (marginal costs + capital costs + UC costs)
- Subject to: nodal power balance, Kirchhoff voltage law (cycle constraints), branch flow limits, generator dispatch limits, storage constraints, ramp limits, global constraints
- Automatically determines LP vs QP vs MILP based on component attributes

**Transmission losses** (since v1.1.0): Piecewise-linear approximation via tangent or secant methods. Enabled with `transmission_losses=N` where N is the number of linear segments.

**Results stored in:**
- `n.generators_t["p"]` — dispatch
- `n.buses_t["marginal_price"]` — LMPs (nodal shadow prices from energy balance constraint)
- `n.lines_t["p0"]`, `n.lines_t["p1"]` — branch flows
- `n.lines_t["mu_upper"]`, `n.lines_t["mu_lower"]` — branch congestion shadow prices
- `n.generators["p_nom_opt"]` — optimized capacities (if `p_nom_extendable=True`)
- `n.objective` — optimal objective value
- `n.objective_constant` — fixed-cost portion of objective

**Source:** `pypsa/optimization/optimize.py`, specifically `OptimizationAccessor.__call__()` and `OptimizationAccessor.create_model()`

### 2.5 Security-Constrained LOPF (SCLOPF)

**Entry point:** `n.optimize.optimize_security_constrained(snapshots=None, branch_outages=None, multi_investment_periods=False, model_kwargs=None, **kwargs)`

- Adds N-1 contingency constraints to the LOPF: for each specified branch outage, post-outage flows on all other branches must remain within limits
- Uses BODF matrix: `|p_b + BODF_bc * p_c| <= s_nom_b` for all branches b, outages c, snapshots t
- Computationally expensive: constraint count = branches x outages x snapshots

**Source:** `pypsa/optimization/optimize.py` (the `optimize_security_constrained` method), docs at `docs/user-guide/optimization/contingencies.md`

### 2.6 Unit Commitment (MILP)

**Activation:** Set `committable=True` on Generator or Link components.

- Introduces binary status variable `u_{n,t}` (on/off) plus binary start-up/shut-down indicators
- Dispatch bounded by: `u * p_min_pu * p_nom <= p <= u * p_max_pu * p_nom`
- Constraints: `min_up_time`, `min_down_time`, `start_up_cost`, `shut_down_cost`, `stand_by_cost`, `ramp_limit_start_up`, `ramp_limit_shut_down`
- **Linearized relaxation:** `n.optimize(linearized_unit_commitment=True)` relaxes binary to continuous [0,1] with tightening constraints (Hua et al. 2017)
- Output: `n.generators_t["status"]`, `n.generators_t["start_up"]`, `n.generators_t["shut_down"]`

**Source:** `pypsa/optimization/constraints.py` (`define_operational_constraints_for_committables`, `define_committability_variables_constraints_with_fixed_upper_limit`), `pypsa/optimization/variables.py` (`define_status_variables`, `define_start_up_variables`, `define_shut_down_variables`)

### 2.7 Economic Dispatch (ED)

No separate API — economic dispatch is the LOPF with:
- Fixed capacities (`p_nom_extendable=False`, the default)
- No network constraints (set `s_nom` high or remove lines)
- Or equivalently, use a single-bus network (copper plate)

```python
n.optimize(solver_name="highs")  # with fixed p_nom, minimizes dispatch cost
```

### 2.8 Capacity Expansion Planning (CEP)

Set `p_nom_extendable=True` (or `s_nom_extendable`, `e_nom_extendable`) on components. Optimization simultaneously determines optimal dispatch and capacity.

**Multi-period pathway planning:**
```python
n.set_investment_periods([2025, 2030, 2035])
n.optimize(multi_investment_periods=True)
```

Components have `build_year`, `lifetime`, and `capital_cost` attributes. The objective weights investment costs by period via `n.investment_period_weightings.objective`.

**Source:** `docs/user-guide/optimization/pathway-planning.md`

### 2.9 Stochastic Optimization

**Entry point:**
```python
n.set_scenarios({"low_wind": 0.3, "high_wind": 0.7})  # scenario names → probabilities
n.optimize()
```

Two-stage stochastic program: investment decisions are first-stage (shared across scenarios), dispatch is second-stage (scenario-dependent). Risk-averse optimization via CVaR:
```python
n.set_risk_preference(alpha=0.05, omega=0.5)  # 5% CVaR, 50% weight on risk
```

**Source:** `docs/user-guide/optimization/stochastic.md`, `pypsa/optimization/variables.py` (`define_cvar_variables`)

### 2.10 Modelling-to-Generate-Alternatives (MGA)

**Entry points:**
```python
n.optimize.optimize_mga(weights={"Generator-p_nom": {"wind": 1}}, sense="max", slack=0.05)
n.optimize.optimize_mga_in_direction(direction, dimensions, slack=0.05)
n.optimize.optimize_mga_in_multiple_directions(directions, dimensions, slack=0.05, max_parallel=4)
```

Explores near-optimal solutions within a cost slack of the optimum. Supports parallel evaluation of multiple directions via `multiprocessing`.

**Source:** `pypsa/optimization/mga.py`

### 2.11 Rolling Horizon Optimization

**Entry point:** `n.optimize.optimize_with_rolling_horizon(snapshots=None, horizon=100, overlap=0, **kwargs)`

Solves sequential optimization windows with configurable overlap for inter-temporal coupling (storage state handoff).

### 2.12 Iterative Transmission Expansion

**Entry point:** `n.optimize.optimize_transmission_expansion_iteratively(snapshots=None, msq_threshold=0.05, min_iterations=1, max_iterations=100, ...)`

Iteratively solves LOPF and rounds line/link capacities to discrete unit sizes.

### 2.13 AC OPF (Iterative Approximation)

**Entry point:** `n.optimize.optimize_and_run_non_linear_powerflow(snapshots=None, ...)`

Not a native non-linear AC OPF. Iteratively: (1) solve linear OPF, (2) run non-linear PF, (3) check convergence. This is an approximation, not a true AC OPF formulation.

### 2.14 Summary: What PyPSA Does NOT Support Natively

| Formulation | Status |
|-------------|--------|
| True non-linear AC OPF (SDP/SOCP) | Not supported — only iterative LOPF+PF |
| SCUC as a single combined formulation | Not built-in — must compose UC + SC constraints manually via `extra_functionality` |
| SCED as a named API | Not built-in — use LOPF with fixed capacities + `optimize_security_constrained()` |
| Unbalanced three-phase power flow | Not supported |
| Dynamic/transient stability | Not supported |
| Distribution system analysis (radial) | Not specialized — can model but no dedicated algorithms |

---

## 3. Solver Interface

### 3.1 Architecture: PyPSA → Linopy → Solver

PyPSA does **not** interface with solvers directly. The chain is:

1. `n.optimize()` calls `n.optimize.create_model()` → builds a `linopy.Model`
2. The model is stored as `n.model`
3. `n.optimize.solve_model(solver_name=..., solver_options=...)` calls `n.model.solve()`
4. Linopy dispatches to the appropriate solver backend

**Source:** `pypsa/optimization/optimize.py`, linopy v0.6.4 (`linopy/solvers.py`)

### 3.2 Supported Solvers (via Linopy)

From `linopy.solvers.SolverName` (linopy v0.6.4):

| Solver | LP | MILP | QP | Open Source | Notes |
|--------|----|------|----|-------------|-------|
| **HiGHS** | yes | yes | yes | yes | Default solver. Installed in devcontainer. |
| **GLPK** | yes | yes | no | yes | Installed in devcontainer. |
| **CBC** | yes | yes | no | yes | |
| **Gurobi** | yes | yes | yes | no (commercial) | |
| **CPLEX** | yes | yes | yes | no (commercial) | |
| **Xpress** | yes | yes | yes | no (commercial) | |
| **SCIP** | yes | yes | yes | yes (academic) | |
| **Mosek** | yes | yes | yes | no (commercial) | |
| **COPT** | yes | yes | yes | no (commercial) | |
| **MindOpt** | yes | yes | yes | no (commercial) | |
| **Knitro** | yes | yes | yes | no (commercial) | |
| **PIPS** | yes | ? | ? | ? | Parallel Interior Point Solver |
| **cuPDLP-x** | yes | no | no | yes | GPU-accelerated LP solver |

Quadratic objective support (from `linopy.solvers.QUADRATIC_SOLVERS`): gurobi, highs, cplex, xpress, knitro, scip, mosek, copt, mindopt.

**Currently available in devcontainer:** HiGHS, GLPK (confirmed via `linopy.solvers.available_solvers`).

### 3.3 Solver Configuration

```python
# Direct specification
n.optimize(solver_name="highs", solver_options={"solver": "ipm", "time_limit": 300})

# Or via two-step workflow
n.optimize.create_model()
n.optimize.solve_model(
    solver_name="gurobi",
    solver_options={"MIPGap": 0.01, "Threads": 4},
    log_to_console=True
)
```

Solver options are passed through directly to the underlying solver via linopy. The option keys are solver-specific (e.g., `"solver": "ipm"` for HiGHS interior point, `"MIPGap"` for Gurobi).

### 3.4 Accessing the Linopy Model

```python
m = n.optimize.create_model()   # or: n.optimize(); m = n.model
m.variables                      # dict-like: "Generator-p", "Line-s", etc.
m.constraints                    # dict-like: "Bus-nodal_balance", "Line-mu_upper", etc.
m.objective                      # linopy.LinearExpression or QuadExpr
m.to_netcdf("model.nc")         # persist model
m.solve(solver_name="highs")    # solve directly via linopy
```

**Source:** linopy documentation, `pypsa/optimization/optimize.py`

### 3.5 Warm Start / Basis Reuse

Linopy's `Model.solve()` accepts `warmstart_fn` and `basis_fn` parameters for LP basis files. PyPSA does not expose these directly in `n.optimize()` but they can be accessed by calling `n.model.solve()` directly. Support is solver-dependent (HiGHS, Gurobi, CPLEX support basis files).

---

## 4. Input/Output Formats

### 4.1 Programmatic Construction

The primary input method is programmatic via `n.add()`:

```python
n = pypsa.Network()
n.set_snapshots(pd.date_range("2024-01-01", periods=24, freq="h"))

n.add("Bus", "bus0", v_nom=110)
n.add("Bus", "bus1", v_nom=110)

# Bulk add with sequences
n.add("Generator", ["gen0", "gen1"],
      bus=["bus0", "bus1"],
      p_nom=[100, 200],
      marginal_cost=[30, 50])

n.add("Line", "line01", bus0="bus0", bus1="bus1", x=0.1, s_nom=150)
```

The `n.add()` method accepts:
- Single component: `n.add("Generator", "gen0", bus="bus0", p_nom=100)`
- Multiple components: `n.add("Generator", ["g1", "g2"], bus=["b1", "b2"], p_nom=[100, 200])`
- Time-series via kwargs: `n.add("Generator", "wind", p_max_pu=wind_cf_series)`
- Returns `pd.Index` of added component names (if `return_names=True`)

**Source:** `pypsa/network/components.py`

### 4.2 File Formats

| Format | Import | Export | Method |
|--------|--------|--------|--------|
| **CSV folder** | yes | yes | `n.import_from_csv_folder(path)` / `n.export_to_csv_folder(path)` |
| **NetCDF** | yes | yes | `n.import_from_netcdf(path)` / `n.export_to_netcdf(path)` — preferred format |
| **HDF5** | yes | yes | `n.import_from_hdf5(path)` / `n.export_to_hdf5(path)` |
| **Excel** | yes | yes | `n.import_from_excel(path)` / `n.export_to_excel(path)` — requires `pypsa[excel]` |
| **PYPOWER PPC** | yes | no | `n.import_from_pypower_ppc(ppc)` — PPC dict version 2 only |
| **pandapower** | yes | no | `n.import_from_pandapower_net(net)` |
| **Constructor** | yes | — | `pypsa.Network(path)` auto-detects CSV folder, NetCDF, HDF5 |
| **Cloud (S3/GCS/Azure)** | yes | yes | Via `cloudpathlib`, for CSV/NetCDF/HDF5 |

**Source:** `pypsa/network/io.py`

### 4.3 CSV Folder Structure

```
network/
  buses.csv                     # static attributes
  generators.csv
  lines.csv
  loads.csv
  generators-p_max_pu.csv      # time-series: snapshots x component names
  generators-p_set.csv
  loads-p_set.csv
  snapshots.csv                 # snapshot index + weightings
  network.csv                   # metadata (name, crs, pypsa_version)
```

### 4.4 MATPOWER / PYPOWER Import

PyPSA has **no native MATPOWER `.m` file reader**. The import path requires an intermediate step:

```python
# Option 1: via pypower
from pypower.api import case30
ppc = case30()
n.import_from_pypower_ppc(ppc)

# Option 2: via matpowercaseframes (third-party)
from matpowercaseframes import CaseFrames
cf = CaseFrames("case30.m")
ppc = cf.to_dict()
n.import_from_pypower_ppc(ppc)

# Option 3: via pandapower
import pandapower.converter as pc
net = pc.from_mpc("case30.m")
n.import_from_pandapower_net(net)
```

**Limitations of PYPOWER import** (from source code warning):
- Does not import: areas, gencosts, component status
- PPC version must be 2
- Export back to PYPOWER is not supported

**Source:** `pypsa/network/io.py` lines ~1962–2080

### 4.5 Network Serialization (Constructor)

```python
# Load from file
n = pypsa.Network("path/to/network.nc")       # NetCDF
n = pypsa.Network("path/to/csv_folder/")      # CSV
n = pypsa.Network("path/to/network.h5")       # HDF5
n = pypsa.Network("https://url/to/file.nc")   # Remote (if network requests enabled)

# Save
n.export_to_netcdf("network.nc")
ds = n.export_to_netcdf()  # returns xr.Dataset without writing
```

---

## 5. Output Access Patterns

### 5.1 After Power Flow (`n.pf()` or `n.lpf()`)

```python
result = n.pf()                          # returns Dict(n_iter, error, converged)
n.buses_t["v_mag_pu"]                    # voltage magnitudes (snapshots x buses)
n.buses_t["v_ang"]                       # voltage angles in radians
n.buses_t["p"]                           # net active power injection
n.buses_t["q"]                           # net reactive power injection
n.generators_t["p"]                      # generator active power output
n.generators_t["q"]                      # generator reactive power output
n.lines_t["p0"], n.lines_t["p1"]         # line active power at each end
n.lines_t["q0"], n.lines_t["q1"]         # line reactive power at each end
n.transformers_t["p0"], ...              # transformer flows
```

### 5.2 After Optimization (`n.optimize()`)

```python
status, condition = n.optimize()
# status: "ok" or "warning" or "infeasible"
# condition: "optimal" or solver-specific string

n.objective                               # float: optimal objective value
n.objective_constant                      # float: fixed cost component

# Dispatch
n.generators_t["p"]                       # generator dispatch (MW)
n.storage_units_t["p_dispatch"]           # storage discharge
n.storage_units_t["p_store"]              # storage charge
n.storage_units_t["state_of_charge"]      # SOC trajectory
n.links_t["p0"], n.links_t["p1"]          # link flows

# Prices / Duals
n.buses_t["marginal_price"]               # LMPs (shadow price of nodal balance)
n.generators_t["mu_upper"]                # dispatch upper bound shadow price
n.generators_t["mu_lower"]                # dispatch lower bound shadow price
n.lines_t["mu_upper"]                     # line congestion price (upper)
n.lines_t["mu_lower"]                     # line congestion price (lower)

# Capacity expansion results
n.generators["p_nom_opt"]                 # optimized generator capacity
n.lines["s_nom_opt"]                      # optimized line capacity
n.storage_units["p_nom_opt"]              # optimized storage power capacity
n.stores["e_nom_opt"]                     # optimized store energy capacity

# Unit commitment
n.generators_t["status"]                  # binary on/off (if committable)
n.generators_t["start_up"]                # binary start-up indicator
n.generators_t["shut_down"]               # binary shut-down indicator

# Linopy model access
n.model.variables                         # all optimization variables
n.model.constraints                       # all constraints
n.model.dual                              # all dual values
```

### 5.3 Statistics Accessor

Post-optimization aggregate statistics via `n.stats`:

```python
n.stats.energy_balance()           # energy balance by component/carrier
n.stats.supply()                   # total supply by component
n.stats.withdrawal()               # total withdrawal
n.stats.capacity_factor()          # capacity factors
n.stats.curtailment()              # curtailed energy
n.stats.installed_capacity()       # installed/existing capacity
n.stats.optimal_capacity()         # optimized capacity
n.stats.capex()                    # capital expenditure
n.stats.opex()                     # operational expenditure
n.stats.revenue()                  # revenue
n.stats.market_value()             # market value
n.stats.prices()                   # average prices
n.stats.transmission()             # transmission volumes
n.stats.system_cost()              # total system cost
```

**Source:** `pypsa/statistics/expressions.py`

---

## 6. Custom Constraints and Extensibility

### 6.1 `extra_functionality` Callback

```python
def my_constraints(n, snapshots):
    m = n.model
    # Access variables
    gen_p = m.variables["Generator-p"]
    # Build constraint: total wind generation >= 30% of demand
    wind_gen = gen_p.sel(name=["wind1", "wind2"]).sum("name")
    total_demand = n.loads_t["p_set"].sum(axis=1)
    m.add_constraints(wind_gen >= 0.3 * total_demand, name="min_wind_share")

n.optimize(extra_functionality=my_constraints)
```

### 6.2 Two-Step Workflow

```python
n.optimize.create_model()
m = n.model

# Add custom variables
m.add_variables(lower=0, upper=100, coords=[n.snapshots], name="custom_var")

# Add custom constraints
m.add_constraints(m.variables["custom_var"] <= 50, name="custom_limit")

# Solve
n.optimize.solve_model(solver_name="highs")
n.optimize.assign_solution()
```

### 6.3 Global Constraints

Built-in system-wide constraints without custom code:

```python
n.add("GlobalConstraint", "co2_limit",
      carrier_attribute="co2_emissions",
      sense="<=",
      constant=1e6)  # total CO2 <= 1 million tons
```

**Source:** `pypsa/optimization/global_constraints.py`, `pypsa/data/component_attrs/global_constraints.csv`

---

## 7. Key Implementation Details

### 7.1 Optimization Variable Naming Convention

Linopy variables follow the pattern `"{Component}-{attribute}"`:
- `Generator-p` — generator dispatch
- `Generator-p_nom` — generator capacity (if extendable)
- `Line-s` — line flow
- `StorageUnit-p_dispatch` — storage discharge
- `StorageUnit-state_of_charge` — state of charge

The full variable lookup table is in `pypsa/data/variables.csv`.

### 7.2 Constraint Naming Convention

Key constraint names in the linopy model:
- `Bus-nodal_balance` — KCL at each bus
- `Line-kirchhoff_voltage` — KVL around cycles
- `Generator-fix-p-upper` / `Generator-fix-p-lower` — dispatch limits (non-extendable)
- `Generator-ext-p-upper` / `Generator-ext-p-lower` — dispatch limits (extendable)
- `StorageUnit-energy_balance` — SOC evolution
- `Generator-com-status-con` — commitment status constraints

### 7.3 Kirchhoff Voltage Law Implementation

For meshed networks, KVL is enforced via cycle constraints rather than PTDF:
- `n.determine_network_topology()` identifies independent cycles
- Cycle matrix C is computed
- Constraint: sum of voltage drops around each cycle = 0
- This is equivalent to PTDF-based formulation but uses fewer constraints for sparse networks

**Source:** `pypsa/optimization/constraints.py` (`define_kirchhoff_voltage_constraints`), `pypsa/network/graph.py` (`cycle_matrix`)

### 7.4 Nodal Balance (Energy Balance Constraint)

For each bus b and snapshot t:
```
sum(generator dispatch at b) + sum(storage discharge at b)
- sum(load at b) - sum(storage charge at b)
+ sum(link flows into b) - sum(link flows out of b)
+ sum(line flows into b) - sum(line flows out of b)
= 0
```

The shadow price of this constraint is the LMP: `n.buses_t["marginal_price"]`.

**Source:** `pypsa/optimization/constraints.py` (`define_nodal_balance_constraints`)

---

## 8. Version-Specific Notes

### 8.1 v1.1.2 (Installed Version)

- Linopy backend (not Pyomo) — all `n.lopf()` references in older tutorials are obsolete
- Default solver: HiGHS (if available), fallback to GLPK
- `n.add()` replaces deprecated `n.madd()` (removed in v1.0.0)
- Ramp limit defaults changed from `1` to `NaN` in v1.1.0 — NaN means no ramp constraint
- `include_objective_constant` defaults transitioning from `True` to `False` in v2.0 (FutureWarning emitted)

### 8.2 Contradictions / Gaps

1. **No true AC OPF**: Despite documentation mentioning "optimal power flow," PyPSA only supports *linear* OPF. The `optimize_and_run_non_linear_powerflow` is an iterative heuristic, not a mathematically rigorous non-convex AC OPF solver.

2. **MATPOWER import is indirect**: Documentation says "MATPOWER Case Import: yes" but there is no `.m` file parser. Users must convert via pypower or pandapower first.

3. **No SCUC as unified formulation**: Unit commitment and security constraints exist separately but there is no single API call that combines N-1 contingency analysis with binary commitment decisions. Users must compose this manually.

4. **Warm start not directly exposed**: The `n.optimize()` API does not have a `warmstart` parameter. Users must call `n.model.solve()` directly with linopy's warmstart arguments.

5. **`v_mag_pu_min` / `v_mag_pu_max` on buses**: Documented as "Placeholder attribute not currently used by any functions" — voltage limits are not enforced in optimization or power flow.
