# PyPSA -- Research: API Surface, Problem Formulations, Solver Interfaces, Data Model, I/O Formats

**Tool version evaluated:** PyPSA 1.1.2 (installed), linopy 0.6.4
**Date:** 2026-03-05

## Key Findings

- PyPSA's central object is `pypsa.Network`, which holds all components (buses, generators, lines, links, etc.) as pandas DataFrames with a parallel `_t` suffix dict-of-DataFrames for time-varying data.
- The primary optimization entry point is `n.optimize()` (replaced legacy `n.lopf()` in v0.22+), which builds a linopy model internally and returns `(status, condition)`.
- **No nonlinear (AC) OPF is supported.** Optimization uses linearized power flow only (DC approximation). Full nonlinear power flow is available separately via `n.pf()` (Newton-Raphson) for validation after optimization.
- Four LOPF formulations are available: `angles`, `ptdf`, `kirchhoff`, and `cycles`. The `kirchhoff` formulation is recommended (averaging 3x faster than `angles`).
- Unit commitment is supported via `committable=True` on generators/links, introducing binary status variables, min up/down times, and start-up/shut-down costs. A `linearized_unit_commitment` relaxation is also available.
- Solver interface is through linopy. In the devcontainer, available solvers are HiGHS and SCIP. Linopy also supports Gurobi, CPLEX, Xpress, MOSEK, COPT, Cbc, GLPK, and cuPDLPx when installed.
- I/O formats: native netCDF (recommended), CSV folder, HDF5, plus importers for PyPower (ppc v2) and pandapower networks. No direct MATPOWER `.m` file import.
- The `Link` component is the key multi-energy-carrier coupling mechanism, supporting multiple outputs (bus2, bus3, ...) with configurable efficiencies, enabling sector-coupled models.
- v1.0 introduced stochastic optimization (two-stage with scenarios), a new Components API layer, interactive visualization, and a statistics/plotting module.

## Detailed Notes

### 1. Network Object and Component Model

The `pypsa.Network` is the top-level container. Components cannot exist outside a network. The data model uses a dual-storage approach [source: design docs]:

**Static data** -- pandas DataFrames indexed by component name:
- `n.buses`, `n.generators`, `n.loads`, `n.lines`, `n.transformers`, `n.links`, `n.storage_units`, `n.stores`, `n.carriers`, `n.global_constraints`, `n.shunt_impedances`, `n.shapes`, `n.sub_networks`, `n.line_types`, `n.transformer_types`

**Time-varying data** -- dict-of-DataFrames with `_t` suffix (columns = component names, index = snapshots):
- `n.generators_t.p_max_pu`, `n.generators_t.p`, `n.loads_t.p_set`, `n.buses_t.marginal_price`, etc.

Input and output data are strictly separated: inputs are never overwritten by outputs. For example, generators have `p_set` (input set-point) vs `p` (calculated output).

**Component taxonomy:**

| Category | Components |
|---|---|
| One-port (single bus) | Generator, Load, StorageUnit, Store, ShuntImpedance |
| Branch (two buses) | Line, Transformer, Link |
| Infrastructure | Bus, Carrier, SubNetwork, GlobalConstraint, Shape |
| Standard types | LineType, TransformerType |

Source: [PyPSA Design docs](https://docs.pypsa.org/v0.26.2/design.html), [Components docs](https://docs.pypsa.org/v0.26.2/components.html)

### 2. Key Component Attributes

**Bus** -- fundamental node enforcing KCL:
- Inputs: `v_nom` (kV), `carrier`, `x`/`y` (coordinates), `v_mag_pu_set`
- Outputs: `v_mag_pu`, `v_ang`, `marginal_price` (from optimization), `p`, `q`

**Generator:**
- Inputs: `bus`, `p_nom` (MW), `p_max_pu`/`p_min_pu` (per-unit dispatch limits, can be time-varying), `marginal_cost` (currency/MWh), `capital_cost` (currency/MW), `carrier`, `efficiency`, `committable` (bool), `min_up_time`, `min_down_time`, `start_up_cost`, `shut_down_cost`, `ramp_limit_up`/`ramp_limit_down`
- Outputs: `p`, `q`, `p_nom_opt` (optimal capacity if extendable), `status` (if committable)

**Line** (passive AC branch):
- Inputs: `bus0`, `bus1`, `x` (ohms, reactance), `r` (ohms, resistance), `b` (siemens, shunt susceptance), `s_nom` (MVA), `length` (km), `type` (standard type reference), `s_nom_extendable`
- Outputs: `p0`, `p1`, `q0`, `q1`, `s_nom_opt`, `mu_lower`, `mu_upper` (shadow prices)

**Transformer** (passive AC branch):
- Inputs: `bus0`, `bus1`, `x`, `r`, `s_nom`, `tap_ratio`, `phase_shift` (degrees), `model` ("t" or "pi")
- Outputs: `p0`, `p1`, `q0`, `q1`, `s_nom_opt`

**Link** (controllable branch, key for multi-energy coupling):
- Inputs: `bus0`, `bus1` (and optionally `bus2`, `bus3`, ... for multiple outputs), `p_nom` (MW), `efficiency` (and `efficiency2`, `efficiency3`, ...), `marginal_cost`, `p_min_pu`/`p_max_pu`, `committable`
- Outputs: `p0`, `p1`, `p_nom_opt`

**StorageUnit** (combined power + energy):
- Inputs: `bus`, `p_nom` (MW), `max_hours` (energy/power ratio), `efficiency_store`/`efficiency_dispatch`, `standing_loss`, `state_of_charge_initial`, `cyclic_state_of_charge` (bool), `inflow`
- Outputs: `p`, `p_dispatch`, `p_store`, `state_of_charge`, `p_nom_opt`

**Store** (energy-only, must attach via Link for power control):
- Inputs: `bus`, `e_nom` (MWh), `e_nom_extendable`, `e_min_pu`/`e_max_pu`, `e_initial`, `standing_loss`, `e_cyclic`
- Outputs: `e`, `p`, `e_nom_opt`

**GlobalConstraint:**
- Inputs: `type` (e.g. `"primary_energy"`), `carrier_attribute` (e.g. `"co2_emissions"`), `sense` (<=, =, >=), `constant` (RHS)
- Outputs: `mu` (shadow price, e.g. CO2 price)

Source: [Components reference](https://docs.pypsa.org/v0.26.2/components.html), installed source v1.1.2

### 3. Adding Components Programmatically

```python
n = pypsa.Network()
n.set_snapshots(pd.date_range("2024-01-01", periods=24, freq="h"))

# Single component
n.add("Bus", "bus0", v_nom=345)

# Multiple components at once
n.add("Generator", ["gen0", "gen1"],
      bus=["bus0", "bus0"],
      p_nom=[100, 200],
      marginal_cost=[30, 50])

# Time-varying data
n.generators_t.p_max_pu = pd.DataFrame(...)  # or set via add() kwargs
```

Signature: `n.add(class_name, name, suffix='', overwrite=False, return_names=None, **kwargs) -> pd.Index | None`

Legacy `n.madd()` and `n.mremove()` also exist for bulk operations.

Source: installed PyPSA v1.1.2 `inspect.signature(n.add)`

### 4. Supported Problem Formulations

#### 4a. Linear Optimal Power Flow (LOPF) / Economic Dispatch

Entry point: `n.optimize(...)` returning `(status, condition)` tuple.

**Objective function:** Minimize total system cost = capital costs (for extendable components) + operational/marginal costs + start-up/shut-down costs (if UC enabled). Snapshot weightings (`n.snapshot_weightings`) allow representing multiple hours per snapshot.

**Flow formulations** (set via model_kwargs or network-level config):
- `kirchhoff` -- recommended, graph-theoretic spanning tree, ~3x faster than angles
- `angles` -- standard textbook voltage-angle based
- `ptdf` -- Power Transfer Distribution Factor
- `cycles` -- graph-theoretic cycle decomposition

All four are mathematically equivalent for the linear approximation.

**Key constraints:**
- Nodal power balance (KCL) at each bus/snapshot -- dual = LMP at `n.buses_t.marginal_price`
- Generator dispatch bounds: `p_min_pu * p_nom <= p <= p_max_pu * p_nom`
- Branch flow limits: `|f| <= s_nom` (or `p_nom` for links)
- Storage state-of-charge evolution with efficiencies and standing losses
- Ramping constraints (up/down/start-up/shut-down ramp rates)
- Global constraints (e.g. CO2 emission caps)

Source: [Power System Optimization docs](https://docs.pypsa.org/v0.25.0/optimal_power_flow.html)

#### 4b. Unit Commitment

Enabled per-component by setting `committable=True` on generators or links. Introduces:
- Binary `status` variables (on/off per snapshot)
- Minimum up-time / down-time constraints
- Start-up and shut-down costs
- Dispatch forced to zero when status=0

A linearized relaxation is available via `n.optimize(linearized_unit_commitment=True)` which relaxes the binary variables to continuous [0, 1].

Source: [UC example](https://pypsa-docs-staging.readthedocs.io/en/latest/examples/unit-commitment.html), installed v1.1.2

#### 4c. Capacity Expansion Planning

Any component with `*_nom_extendable=True` (e.g. `p_nom_extendable`, `s_nom_extendable`, `e_nom_extendable`) becomes a decision variable. The optimizer determines `*_nom_opt` to minimize total cost including `capital_cost`.

Source: [Optimization docs](https://docs.pypsa.org/v0.25.0/optimal_power_flow.html)

#### 4d. Multi-Investment Period Optimization

`n.optimize(multi_investment_periods=True)` with `n.investment_periods` set as monotonically increasing years. Uses annualized costs, tracks asset build-year and lifetime, and supports perfect-foresight planning across decades.

Source: [v1.0 guide](https://docs.pypsa.org/latest/user-guide/v1-guide/)

#### 4e. Stochastic Optimization (new in v1.0)

Two-stage stochastic programming via `n.set_scenarios(...)`:
- First stage: investment decisions robust across scenarios
- Second stage: operational decisions per scenario
- Risk-neutral (default) or risk-averse (CVaR) formulations via `n.set_risk_preference()`

Source: [v1.0 release announcement](https://forum.openmod.org/t/release-of-pypsa-v1-0/5467)

#### 4f. Security-Constrained LOPF

`n.optimize.optimize_security_constrained(...)` ensures no branch overloading under specified N-1 (or N-k) outage scenarios.

#### 4g. Rolling Horizon Optimization

`n.optimize.optimize_with_rolling_horizon(horizon=100, overlap=0)` for sequential time-window optimization.

#### 4h. Transmission Expansion with Impedance Updates

`n.optimize.optimize_transmission_expansion_iteratively(...)` iteratively updates passive branch impedances based on expansion results.

#### 4i. Modelling-to-Generate-Alternatives (MGA)

`n.optimize.optimize_mga(weights, sense, slack=0.05)` explores near-optimal solution space within a cost tolerance.

#### 4j. NOT supported: Nonlinear AC OPF

**PyPSA does not support optimization with full nonlinear AC power flow equations.** All optimization uses the DC/linear approximation. The recommended workflow for AC validation is: optimize with LOPF, then validate with `n.pf()`.

Source: [OPF docs](https://docs.pypsa.org/v0.25.0/optimal_power_flow.html), confirmed via multiple doc versions

### 5. Power Flow (Non-Optimization)

#### 5a. Full AC Power Flow (Newton-Raphson)

```python
n.pf(snapshots=None, skip_pre=False, x_tol=1e-6, use_seed=False,
     distribute_slack=False, slack_weights='p_set') -> Dict
```

- Solves nonlinear AC power flow equations via Newton-Raphson
- Bus types: Slack (V, theta fixed), PV (P, |V| fixed), PQ (P, Q fixed)
- Bus control inherited from attached generators
- Results: `n.buses_t.v_mag_pu`, `n.buses_t.v_ang`, `n.lines_t.p0/p1/q0/q1`, etc.
- Requirement: `r + jx` must be non-zero for all branches
- Can process multiple snapshots efficiently in one call

Source: [Power Flow docs](https://docs.pypsa.org/v1.0.5/user-guide/power-flow/), installed v1.1.2

#### 5b. Linear (DC) Power Flow

```python
n.lpf(snapshots=None, skip_pre=False) -> None
```

- Linearized approximation: no reactive power, no voltage magnitude variation, small angle differences
- Good for overhead transmission lines; less accurate for distribution networks
- Much faster than full NR power flow

Source: [Linear PF docs](https://docs.pypsa.org/v1.0.0/user-guide/linear-power-flow/), installed v1.1.2

#### 5c. Contingency Analysis

`n.lpf_contingency(...)` performs linear power flow under contingency (N-1) conditions.

### 6. Solver Interface

PyPSA uses **linopy** (v0.6.4 installed) as its optimization modeling layer, which replaced direct Pyomo usage starting around v0.22.

**Solver selection:** `n.optimize(solver_name="highs", solver_options={...})`

**Linopy-supported solvers:**

| Solver | Type | License |
|---|---|---|
| HiGHS | LP/MIP/QP | Open source (MIT) |
| SCIP | LP/MIP | Open source (Apache 2.0) |
| Cbc | LP/MIP | Open source (EPL) |
| GLPK | LP/MIP | Open source (GPL) |
| Gurobi | LP/MIP/QP | Commercial |
| CPLEX | LP/MIP/QP | Commercial |
| Xpress | LP/MIP/QP | Commercial |
| MOSEK | LP/MIP/QP/SOCP/SDP | Commercial |
| COPT | LP/MIP/QP | Commercial |
| cuPDLPx | LP (GPU) | Open source |

In the devcontainer environment, only **HiGHS** and **SCIP** are available.

**Custom model access:**

```python
m = n.optimize.create_model()   # linopy.Model object
gen_p = m.variables["Generator-p"]
m.add_constraints(...)          # add custom constraints
n.optimize.solve_model(solver_name="highs")
```

Source: [linopy GitHub](https://github.com/PyPSA/linopy), installed linopy v0.6.4, [HiGHS forum post](https://forum.openmod.org/t/open-source-highs-solver-performance-boost-for-energy-system-models/2922)

### 7. Input/Output Formats

#### Native formats:

| Format | Import | Export | Notes |
|---|---|---|---|
| netCDF | `n.import_from_netcdf()` or `pypsa.Network("file.nc")` | `n.export_to_netcdf()` | Recommended. Clean structure, cross-language, supports lazy loading, float precision control. |
| CSV folder | `n.import_from_csv_folder()` | `n.export_to_csv_folder()` | One CSV per component type + time-series CSVs. Human-readable. |
| HDF5 | `n.import_from_hdf5()` or `pypsa.Network("file.h5")` | `n.export_to_hdf5()` | Binary, fast for large networks. |
| Excel | `n.import_from_excel()` | `n.export_to_excel()` | Convenience for small networks. |

#### External tool importers (import only, no export):

| Source | Method | Limitations |
|---|---|---|
| PyPower (ppc v2) | `n.import_from_pypower_ppc()` | NumPy array format only |
| pandapower | `n.import_from_pandapower_net()` | Partial: no 3-winding transformers, no switches, no in_service status, no tap positions |
| MATPOWER `.m` files | **Not supported directly** | Must convert via PyPower or pandapower first |

#### Cloud storage:

CSV, netCDF, and HDF5 in cloud object storage (S3, GCS, Azure Blob) supported via optional `cloudpathlib` dependency.

#### Programmatic I/O:

- `n.add()` / `n.remove()` -- single component
- Legacy `n.madd()` / `n.mremove()` -- bulk operations
- `n.import_components_from_dataframe()` / `n.import_series_from_dataframe()` -- DataFrame injection

Source: [Import/Export docs](https://docs.pypsa.org/v0.30.0/user-guide/import-export.html)

### 8. Accessing Results

After `n.optimize()` or `n.pf()`:

| Result | Access pattern |
|---|---|
| LMPs (locational marginal prices) | `n.buses_t.marginal_price` |
| Generator dispatch | `n.generators_t.p` |
| Optimal capacity | `n.generators.p_nom_opt` |
| Line flows | `n.lines_t.p0`, `n.lines_t.p1` |
| Line shadow prices | `n.lines.mu_lower`, `n.lines.mu_upper` |
| Storage state of charge | `n.storage_units_t.state_of_charge` |
| UC status | `n.generators_t.status` |
| CO2 shadow price | `n.global_constraints.mu` |
| Objective value | `n.objective` |
| Bus voltages (PF) | `n.buses_t.v_mag_pu`, `n.buses_t.v_ang` |

The `n.statistics` accessor provides aggregate metrics: `n.statistics.energy_balance()`, `n.statistics.optimal_capacity()`, `n.statistics.capex()`, `n.statistics.opex()`, `n.statistics.curtailment()`, `n.statistics.capacity_factor()`, `n.statistics.market_value()`, `n.statistics.revenue()`, `n.statistics.supply()`, `n.statistics.withdrawal()`, `n.statistics.transmission()`, `n.statistics.prices()`, `n.statistics.system_cost()`.

### 9. Additional API Surface

**Clustering:** `n.cluster.cluster_spatially_by_kmeans()`, `n.cluster.cluster_spatially_by_hac()`, `n.cluster.cluster_spatially_by_greedy_modularity()`, `n.cluster.temporal()`, `n.cluster.spatial()` -- for network reduction.

**Topology:** `n.determine_network_topology()`, `n.adjacency_matrix()`, `n.incidence_matrix()`, `n.cycle_matrix()`, `n.graph()` (returns NetworkX graph).

**Visualization:** `n.plot()` (static matplotlib), `n.explore()` (interactive map).

**Consistency:** `n.consistency_check()`, `n.sanitize()`.

**Merging/Slicing:** `n.merge()`, `n.slice_network()`, `n.copy()`.

### 10. Units and Conventions

- Power: MW, MVA, MVar
- Energy: MWh
- Time: hours
- Voltage: kV (phase-to-phase) or per-unit
- Angles: radians (except transformer phase_shift in degrees)
- Impedance: Ohms or per-unit (1 MVA base)
- Sign convention: generator p > 0 = injecting; load p > 0 = consuming; branch p0 > 0 = power flowing from bus0 into branch

Source: [Design docs](https://docs.pypsa.org/v0.26.2/design.html)

## Sources

1. [PyPSA Design docs (v0.26.2)](https://docs.pypsa.org/v0.26.2/design.html)
2. [PyPSA Components docs (v0.26.2)](https://docs.pypsa.org/v0.26.2/components.html)
3. [Power System Optimization docs (v0.25.0)](https://docs.pypsa.org/v0.25.0/optimal_power_flow.html)
4. [Optimize API reference (latest)](https://docs.pypsa.org/latest/api/networks/optimize/)
5. [Power Flow docs (v1.0.5)](https://docs.pypsa.org/v1.0.5/user-guide/power-flow/)
6. [Linear Power Flow docs (v1.0.0)](https://docs.pypsa.org/v1.0.0/user-guide/linear-power-flow/)
7. [Import/Export docs (v0.30.0)](https://docs.pypsa.org/v0.30.0/user-guide/import-export.html)
8. [What's new in v1.0](https://docs.pypsa.org/latest/user-guide/v1-guide/)
9. [linopy GitHub](https://github.com/PyPSA/linopy)
10. [PyPSA GitHub](https://github.com/PyPSA/PyPSA)
11. [HiGHS solver forum post](https://forum.openmod.org/t/open-source-highs-solver-performance-boost-for-energy-system-models/2922)
12. [PyPSA v1.0 release announcement](https://forum.openmod.org/t/release-of-pypsa-v1-0/5467)
13. [Unit commitment example](https://pypsa-docs-staging.readthedocs.io/en/latest/examples/unit-commitment.html)
14. Installed source: PyPSA 1.1.2 at `/workspace/evaluations/pypsa/.venv/lib/python3.12/site-packages/pypsa/`
15. Installed linopy 0.6.4 -- available solvers in devcontainer: `['highs', 'scip']`

## Gaps and Uncertainties

- **AC OPF:** Confirmed absent. No nonlinear OPF exists in PyPSA; only linearized LOPF. This is a fundamental design choice, not a missing feature.
- **MATPOWER import:** No direct `.m` file reader. Would need an intermediate conversion step (e.g., via Octave/PyPower to ppc format, then `import_from_pypower_ppc()`). The exact workflow for MATPOWER case files needs testing.
- **Formulation selection mechanism in v1.x:** The docs reference `kirchhoff`/`angles`/`ptdf`/`cycles` but the exact parameter to pass in v1.1.2's `n.optimize()` call (likely via `model_kwargs`) needs testing to confirm.
- **Transmission losses:** The `transmission_losses` parameter in `n.optimize()` accepts `bool | int | dict` but the exact piecewise-linear loss approximation levels need testing.
- **Quadratic objectives:** linopy supports QP, but it is unclear whether PyPSA exposes quadratic cost terms (e.g., for AC OPF-like formulations or polynomial cost curves). The linopy GitHub has an open issue about quadratic terms with HiGHS.
- **SCUC/SCED as named formulations:** PyPSA does not use these terms explicitly. UC is a per-component toggle, and ED is implicit in LOPF without capacity expansion. Whether the UC implementation matches formal SCUC (with network constraints) needs verification.
- **pandapower import fidelity:** Many pandapower features are unsupported (3-winding transformers, switches, tap positions). The exact mapping quality needs testing with real networks.
- **Performance of stochastic optimization:** The v1.0 scenario support is new; scalability with many scenarios is untested in this evaluation.
