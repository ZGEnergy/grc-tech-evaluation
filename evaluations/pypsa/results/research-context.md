# PyPSA — Research Context (Merged)

> Auto-merged from 4 research agents on 2026-03-24.
> Protocol v11, Skill v2.

---

# Section 1: API & Formulations

---
tool: pypsa
version: 1.1.2
linopy_version: 0.6.4
research_date: 2026-03-13
## research_focus: API surface, supported problem formulations, solver interfaces, data model, input/output formats

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

---

# Section 2: Extensions & Architecture

---

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

---

# Section 3: Limitations & Ecosystem

---

# pypsa — Research: Limitations & Ecosystem

Applies to: **PyPSA 1.1.2** (installed 2026-03-11; this is the current latest release).

---

## Key Findings

- PyPSA is **MIT-licensed** and has strong community adoption: ~1,898 GitHub stars, 617 forks, 99+ contributors, ~969K total PyPI downloads, and an active PyPSA-Eur ecosystem model (545 stars, 380 forks).
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

#### FAQ-Documented Limitations (from official docs)

The PyPSA FAQ (`docs/user-guide/faq.md`) explicitly documents several limitations relevant to the evaluation:

1. **No AC OPF in optimization**: "AC power flow can only be computed post-optimization for analysis, not incorporated into the optimization itself." The optimization uses linear approximations only; full nonlinear AC constraints are not in the optimization formulation. ([source: faq.md](https://raw.githubusercontent.com/PyPSA/PyPSA/master/docs/user-guide/faq.md))

2. **No Monte Carlo generation adequacy**: Unplanned outage simulations (EENS, LOLP) are not built in — "must be built in an outer loop around PyPSA." Open issue [#1490](https://github.com/PyPSA/PyPSA/issues/1490) tracks adding robustness requirements.

3. **No ancillary service co-optimization**: Frequency control reserves, spinning reserves co-optimized with dispatch require custom work. Open issue [#1542](https://github.com/PyPSA/PyPSA/issues/1542) tracks reserve margin approximation.

4. **No CES demand functions**: Constant Elasticity of Substitution demand modeling requires custom modifications.

5. **No GUI**: Python scripts or Jupyter notebooks required for all model building. Open issue [#1479](https://github.com/PyPSA/PyPSA/issues/1479) tracks a UI proposal.

6. **MATPOWER conversion requires PYPOWER intermediate**: No direct `.m` file reader — must go through PYPOWER's `loadcase()` first, then `n.import_from_pypower_ppc()`.

7. **No multi-stage stochastic optimization**: Only two-stage stochastic programming is supported natively (v1.0.0+). Multi-stage scenario trees are not supported. Open issue [#1477](https://github.com/PyPSA/PyPSA/issues/1477).

8. **Optimization uses only LP/MILP/QP**: The Linopy backend "has a reduced set of optimization problem types" compared to Pyomo. Nonlinear programming (NLP) formulations are not available through the optimization API.

#### Optimization Power Flow Linearization Details

The optimization module uses linearized Kirchhoff's Voltage Law (KVL) constraints via a cycle-basis formulation that is "substantially faster than other formulations due to its sparsity." Two loss approximation modes are available:
- **Secant-based**: overestimates losses (conservative)
- **Tangent-based**: underestimates losses, uses 2-4 tangent segments

Loss approximation is **not enabled by default** and must be explicitly activated. The `n.statistics.transmission` method does not account for losses (open issue [#787](https://github.com/PyPSA/PyPSA/issues/787)).

When transmission capacity is optimized (expansion planning), series impedance does not automatically adjust — iterative methods are required, which is a known limitation for integrated TEP+OPF workflows.

([source: docs/user-guide/optimization/power-flow.md](https://raw.githubusercontent.com/PyPSA/PyPSA/master/docs/user-guide/optimization/power-flow.md))

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
| [#1477](https://github.com/PyPSA/PyPSA/issues/1477) | Support for Multi-Stage Stochastic Optimization | Open, `gap` | Stochastic optimization (only 2-stage supported) |
| [#1490](https://github.com/PyPSA/PyPSA/issues/1490) | Add robustness requirements (EENS, LOLP) | Open, `gap` | Generation adequacy studies |
| [#1542](https://github.com/PyPSA/PyPSA/issues/1542) | Approximation of reserve market via reserve margin | Open | Reserve/ancillary services |
| [#787](https://github.com/PyPSA/PyPSA/issues/787) | n.statistics.transmission does not consider losses | Open | Loss reporting in statistics |
| [#1315](https://github.com/PyPSA/PyPSA/issues/1315) | StorageUnit withdrawal not correctly assigned in expressions | Open | Storage dispatch correctness |
| [#1516](https://github.com/PyPSA/PyPSA/issues/1516) | Incorrect n.objective when components have p_nom and p_nom_extendable=TRUE | Open | Objective value reporting accuracy |
| [#1399](https://github.com/PyPSA/PyPSA/issues/1399) | Store marginal cost does not seem symmetric | Open | Storage cost modeling |
| [#488](https://github.com/PyPSA/PyPSA/issues/488) | For storage units p_min_pu cannot have positive values | Open | Storage dispatch bounds |

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
- **One GPL dependency**: `Levenshtein` (GPL-2.0-or-later) is a core runtime dependency (used for fuzzy string matching in component lookups). All other core dependencies are BSD/MIT/Apache. The GPL-2.0-or-later license on `Levenshtein` may require legal review for proprietary distribution scenarios, though it does not affect PyPSA's own MIT license.

---

### Community & Documentation

#### Community Size

- **GitHub**: 1,898 stars, 617 forks, 125 open issues, 99+ code contributors (GitHub contributor page reports 99 when paginated at 100 per page, actual count may be higher). 68 watchers.
- **PyPI downloads**: ~969K total downloads as of March 2026 ([source: pepy.tech/projects/pypsa](https://pepy.tech/projects/pypsa)). v1.0.7 is the most-downloaded recent version.
- **Ecosystem**: pypsa-eur alone has 545 stars and 380 forks, indicating significant real-world usage. pypsa-earth has 326 stars and 307 forks (under `pypsa-meets-earth` org).
- **Academic citations**: 895+ citations for the core PyPSA paper (Brown et al., 2018, "PyPSA: Python for Power System Analysis", JOSS). ([source: pypsa.org](https://pypsa.org))
- **Industry users**: TenneT, d-fine, Fraunhofer ISI, AGGM (Austrian Gas Grid), Serentica listed in official `users.md` as of v1.1.x
- **Commercial support**: OET (Open Energy Transition), d-fine, Energynautics, and CLIMACT offer paid support services. ([source: pypsa.org](https://pypsa.org))
- **Institutional backing**: Led by Technische Universitat Berlin (TU Berlin), Department of Digital Transformation in Energy Systems. PyPSA-USA led by Stanford University. ([source: pypsa.org](https://pypsa.org))

#### Operational Deployment Evidence

- **PyPSA-Eur**: Used for European Commission energy system studies and national energy planning. Snakemake-based workflow covering all EU member states.
- **PyPSA-USA**: Stanford-led model covering US energy system modeling.
- **PyPSA-Earth**: Global energy system model (326 stars, 307 forks under pypsa-meets-earth org), used for developing-country energy planning.
- **PyPSA-DE**: German national energy system model.
- No evidence found of direct use by ISOs/RTOs for operational dispatch or market clearing. Usage appears concentrated in academic research, energy policy analysis, and consulting.

#### Community Channels

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
21. PyPI download statistics: `https://pepy.tech/projects/pypsa` — ~969K total downloads as of March 2026
22. PyPSA FAQ (official): `https://raw.githubusercontent.com/PyPSA/PyPSA/master/docs/user-guide/faq.md` — documented limitations
23. PyPSA design document: `https://raw.githubusercontent.com/PyPSA/PyPSA/master/docs/user-guide/design.md` — architectural constraints
24. PyPSA optimization power flow docs: `https://raw.githubusercontent.com/PyPSA/PyPSA/master/docs/user-guide/optimization/power-flow.md` — KVL formulation, loss approximation
25. PyPSA power flow docs: `https://raw.githubusercontent.com/PyPSA/PyPSA/master/docs/user-guide/power-flow.md` — Newton-Raphson ACPF details
26. PyPSA release notes: `https://raw.githubusercontent.com/PyPSA/PyPSA/master/docs/release-notes.md` — full changelog v0.x through v1.1.2
27. Dependency license audit: `importlib.metadata` runtime check of all core dependencies — identified `Levenshtein` as GPL-2.0-or-later
28. pypsa-earth repo: `https://github.com/pypsa-meets-earth/pypsa-earth` — 326 stars, 307 forks
29. PyPSA project website: `https://pypsa.org` — institutional backing, commercial support, ecosystem overview

---

## Gaps and Uncertainties

- **AC OPF with Ipopt**: Could not be tested. If Ipopt is installed (`apt install coinor-libipopt-dev` + `pip install cyipopt`), `n.optimize.optimize_and_run_non_linear_powerflow()` should work. Convergence behavior at scale is unknown.
- **PTDF accuracy (issue #604)**: The PTDF calculation issue (#604) has 13 comments but no resolution — the nature of the inaccuracy is unclear. Whether `calculate_PTDF()` produces correct values for all network topologies requires direct numerical verification.
- **Largest networks successfully run**: No official benchmark numbers were found for maximum bus count. PyPSA-Eur uses 50–250 clustered nodes in practice; full-resolution European transmission networks are in the thousands. The 30k-bus MATPOWER FNM case has not been documented as tested. The dense PTDF matrix at 30k buses × 35k lines would require ~30k × 35k × 8 bytes ≈ 8 GB of RAM per SubNetwork.
- **PyPI download statistics**: ~969K total downloads as of March 2026 (pepy.tech). v1.0.7 is the most popular recent version with 200-700+ daily downloads.
- **Discourse forum accessibility**: `pypsa.discourse.group` was unreachable during this research session (ECONNREFUSED). The GitHub Discussions page shows moderate activity with unanswered questions.
- **gencost type 1 (piecewise) import**: The exact behavior when a MATPOWER case with piecewise linear gencosts is imported is not tested — whether it silently drops costs or raises an error needs empirical verification.
- **pandas ≥ 3.0 compatibility**: Issue #1585 (ArrowStringArray from NetCDF breaks optimize()) is open and was confirmed on `pandas >= 2.0`. The exact pandas version boundary for this bug is unclear.
- **GPL dependency**: The `Levenshtein` package (GPL-2.0-or-later) is a core runtime dependency introduced for fuzzy matching in component name lookups. This is the only GPL-licensed package in PyPSA's core dependency tree. Whether this creates a copyleft obligation for proprietary applications that embed PyPSA requires legal analysis.
- **ISO/RTO operational use**: No evidence found that any ISO, RTO, or utility uses PyPSA for operational dispatch or market clearing. All documented deployments are for planning, policy analysis, or academic research.

---

# Section 4: Version & Capability Report

---

---
tool: pypsa
installed_version: 1.1.2
release_date: 2026-02-23
latest_version: 1.1.2
latest_release_date: 2026-02-23
## research_date: 2026-03-13

# pypsa — Version & Capability Report

## Version Summary

PyPSA (Python for Power System Analysis) v1.1.2 is the installed and latest stable release, published on 23 February 2026. This version sits on the v1.x line, which debuted with v1.0.0 on 14 October 2025 — a milestone release that introduced stochastic optimization, a new components API, brand-new documentation, and removed all previously deprecated v0.x APIs. The v1.1.0 release (17 February 2026) added temporal clustering, secant-based transmission loss approximation, pandas v3 support, and combined committable+extendable component support. v1.1.2 is a bugfix patch on top of v1.1.0.

PyPSA has been under active development since January 2016 (v0.3.0). Its optimization backend transitioned from Pyomo (removed in v0.29.0, released 2024) to linopy, and the default solver changed from GLPK to HiGHS at that same transition. The installed version uses linopy 0.6.4 as its optimization modeling layer and supports solvers including HiGHS, Gurobi, CPLEX, GLPK, and others via linopy's solver interface.

## Capability Table

| Feature | Supported | Since Version | Notes |
|---------|-----------|---------------|-------|
| DC Power Flow (DCPF) | yes | 0.3.0 | `n.lpf()` — linear power flow using PTDF/B-matrix. Available since initial release (Jan 2016). |
| AC Power Flow (ACPF) | yes | 0.3.0 | `n.pf()` — full Newton-Raphson non-linear power flow. Supports distributed slack, configurable tolerance (`x_tol`), seeded initial guess. |
| DC Optimal Power Flow (DC OPF) | yes | 0.3.0 | `n.optimize()` — linear OPF via linopy. Originally `n.lopf()` (removed in v0.29.0). Kirchhoff voltage law constraints, nodal balance, transmission losses (secant/tangent approximation since v1.1.0). |
| AC Optimal Power Flow (AC OPF) | partial | 0.20.0 | `n.optimize.optimize_and_run_non_linear_powerflow()` — iterative approach: runs linear OPF then non-linear PF in a loop until convergence. Not a native non-linear AC OPF formulation. |
| Security-Constrained Unit Commitment (SCUC) | partial | 0.4.0 | Unit commitment via `committable=True` with `min_up_time`, `min_down_time`, `start_up_cost`, `shut_down_cost`, `ramp_limit_*` attributes. Linearized UC formulation (`linearized_unit_commitment=True`). Security constraints can be added via `extra_functionality` callback but no built-in SCUC formulation combining N-1 contingency with UC in a single optimization. |
| Security-Constrained Economic Dispatch (SCED) | partial | 0.4.0 | The `pypsa.contingency` module (introduced v0.4.0) provides SCLOPF (Security-Constrained Linear OPF). Economic dispatch is the DC OPF with fixed capacities. Security constraints can be injected via `extra_functionality`. No dedicated single-call SCED API. |
| PTDF / Shift Factor Extraction | yes | 0.3.0 | `sub_network.calculate_PTDF()` computes the Power Transfer Distribution Factor matrix. Also computes BODF (Branch Outage Distribution Factor) via `lpf_contingency`. Stored as `sub_network.PTDF` (sparse matrix). |
| Contingency Analysis (N-1) | yes | 0.4.0 | `n.lpf_contingency(snapshots, branch_outages)` — computes linear power flow for all specified branch outages using PTDF/BODF. Returns DataFrame of new power flows. The `pypsa.contingency` module was introduced in v0.4.0 (March 2016). |
| Custom Constraint Injection | yes | 0.3.0 | `extra_functionality` callback in `n.optimize()` — called after model build, before solve. Provides full access to the linopy model (`n.model`) to add/modify variables, constraints, and objective terms. Also supports `global_constraints` component for carrier-level emission/capacity limits. |
| Network Graph Access | yes | 0.3.0 | `n.graph()` returns a NetworkX graph. Also: `n.adjacency_matrix()`, `n.incidence_matrix()`, `n.cycle_matrix()`, `n.determine_network_topology()`. The `pypsa.graph` module (v0.5.0) uses scipy.sparse for performance. |
| CSV Data Import | yes | 0.3.0 | `n.import_from_csv_folder()` / `n.export_to_csv_folder()`. Also supports HDF5 (`import_from_hdf5`), NetCDF (`import_from_netcdf`), and Excel (`import_from_excel`). |
| MATPOWER Case Import | yes | 0.3.0 | `n.import_from_pypower_ppc(ppc)` imports from PYPOWER PPC dict format (version 2). Requires converting MATPOWER `.m` files to PPC dicts first (e.g. via `matpowercaseframes` or `pandapower`). Also: `n.import_from_pandapower_net()`. No direct `.m` file reader. |
| Multi-Period / Time Series | yes | 0.3.0 | Snapshots (`n.set_snapshots()`) drive time-series dispatch and power flow. Multi-investment-period pathway optimization added in v0.18.0 (Aug 2021) with `multi_investment_periods=True`. Temporal clustering added in v1.1.0 (resample, downsample, segment). `snapshot_weightings` DataFrame controls objective/generator/storage weights. |
| Warm Start / Solution Reuse | partial | 0.21.0 | Supported at the linopy layer: `linopy.Model.solve()` accepts `warmstart_fn` and `basis_fn` parameters for LP basis files. PyPSA does not expose these directly in `n.optimize()` but they can be passed via `solver_options` or by accessing `n.model.solve()` directly. Solver-dependent (HiGHS, Gurobi, CPLEX support basis files). |
| Parallel Computation | partial | 1.0.0 | MGA (Modeling to Generate Alternatives) module supports parallel direction solving via `multiprocessing` (up to `max_parallel` processes). No built-in parallelism for standard OPF or power flow across snapshots. linopy `Model` accepts a `chunk` kwarg for chunked variable construction. |

## Breaking Changes

| Version | Change | Impact on Evaluation |
|---------|--------|----------------------|
| v0.29.0 (2024) | Removed `n.lopf()` (Pyomo and nomopyomo optimization). HiGHS became default solver. | All optimization must use `n.optimize()` with linopy backend. Old tutorials/examples using `lopf` are outdated. |
| v0.31.0 (2024) | Deprecated `n.madd()` and `n.mremove()` in favor of generalized `n.add()`. | Bulk component addition syntax changed. |
| v1.0.0 (Oct 2025) | Removed all v0.x deprecated APIs. Changed `Network.add()` to return `None` by default. Renamed statistics parameters (`comps` to `components`, `aggregate_groups` to `groupby_method`, `aggregate_time` to `groupby_time`). Changed storage cycling defaults (`cyclic_state_of_charge_per_period` and `e_cyclic_per_period` from `True` to `False`). DataFrame index names unified to `name`. Inactive components excluded from optimization. | Significant API surface change. Code written for v0.x requires migration. The v1.0 migration guide documents all changes. |
| v1.1.0 (Feb 2026) | Ramp limit defaults changed from `1` to `NaN`. Ramp constraint names simplified. | Minor: only affects code relying on implicit ramp limit defaults of 1. |

## Changelog Analysis

The installed version (v1.1.2) is the latest release. There are no newer versions to upgrade to. The progression from v1.0.0 to v1.1.2 spans five months:

- **v1.0.0** (14 Oct 2025): Major release. Stochastic optimization (two-stage with CVaR), NetworkCollection, new Components API, risk-averse optimization, MGA module, complete documentation rewrite. Removed all v0.x deprecations.
- **v1.0.1–v1.0.7** (Oct 2025–Jan 2026): Bugfix releases addressing snapshot synchronization, ramp limits in rolling horizon, storage unit handling, clustering, and NetCDF export. v1.0.7 added overnight cost / FOM cost splitting and Python 3.14 support.
- **v1.1.0** (17 Feb 2026): Feature release. Temporal clustering (`n.cluster.temporal.*`), secant-based transmission loss approximation, environment variable configuration, pandas v3 support, combined committable+extendable components, `p_init` for ramp constraints.
- **v1.1.1** (23 Feb 2026): Yanked due to CI pipeline error.
- **v1.1.2** (23 Feb 2026): Bugfix for `log_to_console` breaking CPLEX, `at_port` statistics fix, release pipeline fix.

Key upcoming features (in master, unreleased): Process component (multi-port with explicit rates), weighted-time delays for Link outputs, `meshed_thresholds` parameter for memory optimization in large networks.

## Sources

1. PyPSA GitHub releases: https://github.com/PyPSA/PyPSA/releases
2. PyPSA release notes (docs/release-notes.md in repository): https://github.com/PyPSA/PyPSA/blob/master/docs/release-notes.md
3. PyPSA v1.0 migration guide: https://docs.pypsa.org/latest/user-guide/v1-guide/
4. Installed package source inspection (`pypsa.__version__`, method signatures, module contents) via devcontainer
5. linopy documentation (warmstart/basis support): inspected `linopy.Model.solve` signature (v0.6.4)
6. PyPSA contingency module source: `pypsa/network/power_flow.py` (PTDF, BODF, lpf_contingency)
7. PyPSA optimization module source: `pypsa/optimization/constraints.py`, `pypsa/optimization/optimize.py`

## Gaps and Uncertainties

1. **AC OPF**: PyPSA does not have a native non-linear AC OPF formulation. The iterative `optimize_and_run_non_linear_powerflow` alternates between linear OPF and non-linear PF, which may not converge to the true AC OPF solution for all cases. The extent of this limitation versus a true AC OPF solver (e.g., Ipopt-based) needs empirical testing.

2. **SCUC/SCED**: While PyPSA supports unit commitment constraints and contingency analysis separately, there is no single integrated SCUC formulation that embeds N-1 contingency constraints within the unit commitment optimization. Users must manually implement this via `extra_functionality`.

3. **Warm Start**: The warm start capability exists at the linopy layer but is not directly exposed via `n.optimize()` parameters. The practical effectiveness depends on the solver and problem structure. Testing is needed to confirm it works end-to-end through PyPSA's optimization accessor.

4. **MATPOWER Import**: PyPSA imports PYPOWER PPC dictionaries, not MATPOWER `.m` files directly. The evaluation project includes `matpowercaseframes` as a dependency which can bridge this gap, but the fidelity of the conversion chain (`.m` -> PPC dict -> PyPSA Network) and whether all MATPOWER case features are preserved is uncertain.

5. **Parallel Computation**: Beyond MGA parallel solving, PyPSA does not parallelize standard operations (power flow across snapshots, optimization). Large-scale parallelism typically requires external orchestration (e.g., Dask, multiprocessing) by the user.

6. **Feature Introduction Dates**: For features present since v0.3.0 (the earliest documented release, January 2016), the exact introduction version cannot be determined from available release notes — they were part of PyPSA's initial public release. The v0.3.0 release notes describe the pandas.Panel interface introduction but reference pre-existing PF and OPF capabilities.
