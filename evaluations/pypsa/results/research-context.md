# PyPSA — Research Context

Merged from three research agents. Date: 2026-03-05. PyPSA v1.1.2 installed.

---

## Part 1: API Surface, Problem Formulations, Solver Interfaces, Data Model

### Key Findings

- PyPSA's central object is `pypsa.Network`, which holds all components (buses, generators, lines, links, etc.) as pandas DataFrames with a parallel `_t` suffix dict-of-DataFrames for time-varying data.
- The primary optimization entry point is `n.optimize()` (replaced legacy `n.lopf()` in v0.22+), which builds a linopy model internally and returns `(status, condition)`.
- **No nonlinear (AC) OPF is supported.** Optimization uses linearized power flow only (DC approximation). Full nonlinear power flow is available separately via `n.pf()` (Newton-Raphson) for validation after optimization.
- Four LOPF formulations are available: `angles`, `ptdf`, `kirchhoff`, and `cycles`. The `kirchhoff` formulation is recommended (averaging 3x faster than `angles`).
- Unit commitment is supported via `committable=True` on generators/links, introducing binary status variables, min up/down times, and start-up/shut-down costs. A `linearized_unit_commitment` relaxation is also available.
- Solver interface is through linopy. In the devcontainer, available solvers are HiGHS and SCIP. Linopy also supports Gurobi, CPLEX, Xpress, MOSEK, COPT, Cbc, GLPK, and cuPDLPx when installed.
- I/O formats: native netCDF (recommended), CSV folder, HDF5, plus importers for PyPower (ppc v2) and pandapower networks. No direct MATPOWER `.m` file import.
- The `Link` component is the key multi-energy-carrier coupling mechanism, supporting multiple outputs (bus2, bus3, ...) with configurable efficiencies, enabling sector-coupled models.
- v1.0 introduced stochastic optimization (two-stage with scenarios), a new Components API layer, interactive visualization, and a statistics/plotting module.

### Network Object and Component Model

The `pypsa.Network` is the top-level container. Components cannot exist outside a network. The data model uses a dual-storage approach:

**Static data** — pandas DataFrames indexed by component name:
- `n.buses`, `n.generators`, `n.loads`, `n.lines`, `n.transformers`, `n.links`, `n.storage_units`, `n.stores`, `n.carriers`, `n.global_constraints`, `n.shunt_impedances`, `n.shapes`, `n.sub_networks`, `n.line_types`, `n.transformer_types`

**Time-varying data** — dict-of-DataFrames with `_t` suffix (columns = component names, index = snapshots):
- `n.generators_t.p_max_pu`, `n.generators_t.p`, `n.loads_t.p_set`, `n.buses_t.marginal_price`, etc.

### Supported Problem Formulations

- **LOPF / Economic Dispatch:** `n.optimize()` with kirchhoff/angles/ptdf/cycles formulations
- **Unit Commitment:** `committable=True` per component, binary status variables, min up/down, startup/shutdown costs
- **Capacity Expansion:** `*_nom_extendable=True` on any component
- **Multi-Investment Period:** `n.optimize(multi_investment_periods=True)`
- **Stochastic Optimization (v1.0+):** Two-stage stochastic programming via `n.set_scenarios()`
- **Security-Constrained LOPF:** `n.optimize.optimize_security_constrained()`
- **Rolling Horizon:** `n.optimize.optimize_with_rolling_horizon()`
- **NOT supported: Nonlinear AC OPF** — all optimization is LP/MILP/QP only

### Power Flow (Non-Optimization)

- **AC PF (Newton-Raphson):** `n.pf()` with distributed slack support
- **DC PF:** `n.lpf()` — linearized approximation
- **Contingency Analysis:** `n.lpf_contingency()`

### Solver Interface

Via linopy. Solver selection: `n.optimize(solver_name="highs", solver_options={...})`.
Available in devcontainer: HiGHS, SCIP.
Custom model access: `n.optimize.create_model()` returns linopy.Model for direct manipulation.

### Accessing Results

| Result | Access pattern |
|---|---|
| LMPs | `n.buses_t.marginal_price` |
| Generator dispatch | `n.generators_t.p` |
| Line flows | `n.lines_t.p0`, `n.lines_t.p1` |
| Line shadow prices | `n.lines.mu_lower`, `n.lines.mu_upper` |
| UC status | `n.generators_t.status` |
| Objective value | `n.objective` |
| Bus voltages (PF) | `n.buses_t.v_mag_pu`, `n.buses_t.v_ang` |

---

## Part 2: Extension Mechanisms, Architecture, Graph Access, Interoperability

### Key Findings

- **No formal plugin/hook system.** Extension via composition: callback functions, accessor patterns, direct DataFrame/Linopy manipulation.
- **`extra_functionality` callback** is the primary extension point — called after model creation but before solving, allows arbitrary constraint/variable additions via Linopy API.
- **Full Linopy model access** via `n.model` after `n.optimize.create_model()`.
- **Component data is pure pandas DataFrames**, making interoperability trivial.
- **NetworkX graph export** via `n.graph()` returns OrderedGraph. Sparse incidence/adjacency matrices via scipy.
- **PTDF/BODF computed** as dense numpy arrays on SubNetwork objects.
- **Architecture is modular:** `pypsa/components/`, `pypsa/optimization/`, `pypsa/network/`, `pypsa/statistics/`, `pypsa/plot/`.

### Extension Mechanisms

**`extra_functionality` callback:**

```python
def my_constraints(n, sns):
    m = n.model
    gen_p = m.variables["Generator-p"]
    m.add_constraints(gen_p.sum("snapshot") >= 100, name="min_total_gen")
n.optimize(extra_functionality=my_constraints)
```

**Two-phase workflow:**
1. `n.optimize.create_model()` — builds Linopy model
2. User modifies `n.model` (add/remove variables, constraints)
3. `n.optimize.solve_model()` — solves and writes results back

### Graph Access

- `n.graph()` → NetworkX OrderedGraph (buses as nodes, branches as edges)
- `n.incidence_matrix()`, `n.adjacency_matrix()` → scipy sparse
- `sub_network.calculate_PTDF()` → sets `sub_network.PTDF` (dense numpy)
- `sub_network.calculate_BODF()` → sets `sub_network.BODF` (dense numpy)
- `n.determine_network_topology()` required before SubNetwork methods

### Interoperability

All data natively as pandas DataFrames. Export to CSV/netCDF/HDF5/Excel. Import from PyPower ppc and pandapower. No direct MATPOWER .m import.

---

## Part 3: Limitations, Ecosystem, Community, Documentation

### Key Findings

- **No full AC OPF** — fundamental architectural limitation (linopy is LP/MILP/QP only)
- **SCOPF is branch-only:** `optimize_security_constrained()` handles N-1 branch outages but not generator outages
- **Lossy OPF via piecewise-linear approximation only:** `n.optimize(transmission_losses=N)` uses N-segment PW-linear loss curves
- **Broken pandapower importer in v1.1.2:** crashes on multi-generator buses (e.g., IEEE 39-bus)
- **No native MATPOWER .m file reader**
- **Large dependency footprint:** 89 packages (many from pandapower)
- **Very active release cadence:** 10+ releases in last 5 months
- **Strong institutional adoption:** ENTSO-E, TransnetBW, TenneT, IEA, Saudi Aramco, Shell, etc.
- **Large community:** ~1.9k stars, ~614 forks, MIT license, DFG-funded at TU Berlin

### Known Limitations for Evaluation

- Distributed slack documented for `pf()` but availability in `optimize()` needs testing
- SCOPF performance at scale not benchmarked in docs
- Stochastic optimization is new (v1.1.0) — maturity unclear
- No PSS/E RAW format parser

### Documentation Quality

- Comprehensive user guide with worked examples
- v1.0 migration guide
- Published academic paper (Brown et al., 2018)
- Weaknesses: thin contingency analysis docs, broken pandapower import path documented but not working, some features (stochastic, MGA) lack detailed API examples

### Release History (Recent)

| Version | Date | Notes |
|---------|------|-------|
| v1.1.2 | 2026-02-23 | Fix at_port statistics, CPLEX compat |
| v1.1.0 | 2026-02-17 | Stochastic stats, secant losses, temporal clustering |
| v1.0.0 | 2025 | First stable API release |

### License

- PyPSA: MIT License
- Key deps: pandas (BSD-3), numpy (BSD-3), scipy (BSD-3), linopy (MIT), networkx (BSD-3)

### Operational Deployment

Mostly planning/policy analysis (ENTSO-E, TSOs, regulators). No evidence of ISO/RTO operational use for market clearing or real-time dispatch.
