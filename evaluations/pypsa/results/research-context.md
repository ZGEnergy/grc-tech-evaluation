# PyPSA — Consolidated Research Context

**Version evaluated:** PyPSA 1.1.2 | **Date:** 2026-03-06

---

## Section 1: API & Formulations

## Key Findings

- PyPSA's central abstraction is `pypsa.Network`, a container holding all components as pandas DataFrames (static) and dicts-of-DataFrames (time-varying `_t` suffix). Components cannot exist outside a Network.
- The tool supports **linear power flow** (`n.lpf()`), **non-linear AC power flow** via Newton-Raphson (`n.pf()`), and **linear optimal power flow** (`n.optimize()`). There is no native AC OPF (non-convex NLP) solver — optimization is LP/MILP/QP only.
- Optimization uses **Linopy** as the backend (not Pyomo since v0.27+). Linopy supports 13 solvers; only **HiGHS** is installed in the evaluation environment. Supported solvers include Gurobi, CPLEX, GLPK, CBC, SCIP, Xpress, Knitro, Mosek, COPT, MindOpt, PIPS, and cuPDLPx.
- Unit commitment is supported via `committable=True` on generators/links, producing MILP problems with min up/down time, start-up/shut-down costs, and ramp constraints.
- Security-constrained OPF is available via `n.optimize.optimize_security_constrained()`, and contingency-based linear PF via `n.lpf_contingency()`.
- I/O supports CSV folders, NetCDF, HDF5, Excel, plus import-only from PyPOWER PPC dicts and pandapower networks. No direct MATPOWER `.m` file reader — requires conversion through PyPOWER or pandapower first.
- The data model uses 15 component types organized as one-port (Generator, Load, Store, StorageUnit, ShuntImpedance), branch (Line, Transformer, Link), and structural (Bus, SubNetwork, Carrier, GlobalConstraint, Shape, LineType, TransformerType).
- Results are written back onto the same DataFrames: `n.buses_t.marginal_price` for LMPs, `n.generators_t.p` for dispatch, `n.lines_t.p0`/`p1` for flows.
- Multi-period investment planning, stochastic optimization (scenarios), MGA, rolling horizon, and iterative transmission expansion are all supported as first-class optimize sub-methods.
- Network visualization via `n.explore()` (interactive Pydeck maps) and matplotlib-based `n.plot()`. Graph-theoretic utilities include `n.graph()` (NetworkX), `n.adjacency_matrix()`, `n.incidence_matrix()`, and `n.cycle_matrix()`.

## Key API Entry Points

| Operation | Method | Problem Type |
|-----------|--------|-------------|
| DC Power Flow | `n.lpf()` | Direct solve |
| AC Power Flow (NR) | `n.pf()` | Newton-Raphson |
| DC OPF / LOPF | `n.optimize()` | LP |
| Unit Commitment | `n.optimize()` with `committable=True` | MILP |
| SCOPF | `n.optimize.optimize_security_constrained()` | LP |
| Contingency LPF | `n.lpf_contingency()` | Direct solve |
| LOPF + AC PF | `n.optimize.optimize_and_run_non_linear_powerflow()` | LP + NR |

## Solver Support (via Linopy 0.6.4)

HiGHS (installed), Gurobi, CPLEX, GLPK, CBC, SCIP, Xpress, Knitro, Mosek, COPT, MindOpt, PIPS, cuPDLPx. Solver selected via `solver_name` parameter. Options via `solver_options` dict.

## Results Access

| Result | Access |
|--------|--------|
| LMPs | `n.buses_t.marginal_price` |
| Generator dispatch | `n.generators_t.p` |
| Line flows | `n.lines_t.p0`, `n.lines_t.p1` |
| Line shadow prices | `n.lines_t.mu_upper`, `n.lines_t.mu_lower` |
| UC status | `n.generators_t.status` |
| Objective | `n.objective` |
| Voltage magnitudes (PF) | `n.buses_t.v_mag_pu` |
| Voltage angles (PF) | `n.buses_t.v_ang` |

## MATPOWER Import Path

No direct `.m` import. Use: `matpowercaseframes` → PPC dict → `n.import_from_pypower_ppc(ppc)`. Alternatively: pandapower `from_mpc()` → `n.import_from_pandapower_net(net)` (beta).

---

## Section 2: Extensions & Architecture

## Key Findings

- PyPSA has **no formal plugin/callback/hook system**. Extension is done through compositional patterns.
- The primary extension mechanism is the **`extra_functionality` callback** in `n.optimize()`, which receives `(n, snapshots)` after model creation but before solving. For full control, users can call `create_model()` and `solve_model()` separately.
- Custom constraints are added by accessing the **Linopy model** at `n.model` and calling `m.add_constraints()` / `m.add_variables()`.
- **Custom component types** can be registered via `pypsa.components.types.add_component_type()`, but they are **not automatically wired into the optimizer** (GitHub issue #856).
- The Network class is built via **mixin composition** (8+ mixins), not inheritance. This provides separation of concerns but makes subclassing fragile.
- **NetworkX graph** access is built-in via `n.graph()`, returning an `OrderedGraph` (a `networkx.MultiGraph` subclass). Adjacency and incidence matrices also available.
- All component data is stored as **pandas DataFrames**, with an additional **xarray DataArray accessor** for N-D operations.
- Import/export supports netCDF, HDF5, CSV folders, Excel, PyPower PPC dicts, and pandapower networks. No native Julia/Graphs.jl bridge.

## Architecture

| Mixin | Responsibility |
|-------|---------------|
| `NetworkComponentsMixin` | Component store, property accessors |
| `NetworkDescriptorsMixin` | Computed properties |
| `NetworkTransformMixin` | Add/remove/copy components |
| `NetworkIndexMixin` | Snapshot/period index management |
| `NetworkConsistencyMixin` | Data validation |
| `NetworkGraphMixin` | NetworkX graph, adjacency/incidence matrices |
| `NetworkPowerFlowMixin` | PF calculations |
| `NetworkIOMixin` | Import/export |

Accessor objects: `n.optimize`, `n.cluster`, `n.statistics`, `n.plot`

Optimization subsystem modules: `optimize.py`, `variables.py`, `constraints.py`, `global_constraints.py`, `expressions.py`, `mga.py`, `abstract.py`

---

## Section 3: Limitations & Ecosystem

## Key Findings

- 87 transitive dependencies installed; core runtime requires numpy, scipy, pandas, xarray, linopy, matplotlib, geopandas, networkx, highspy.
- No native MATPOWER `.m` file parser — ingestion requires conversion.
- AC power flow uses Newton-Raphson with flat start only; no warm-starting. Convergence not guaranteed.
- No native nonlinear AC OPF — optimization is LP/MILP/QP only.
- SCLOPF has an open, confirmed intermittent bug (issue #1356) — overloads up to 7%.
- StorageUnit `committable=True` crashes in v1.1.2 (issue #1602).
- ArrowStringArray incompatibility (issue #1585) can silently break optimize after NetCDF round-trip.

## Open Bugs Relevant to Evaluation

| Issue | Impact |
|-------|--------|
| #1356 | SCLOPF intermittent overloads (up to 7%) |
| #1602 | StorageUnit committable crash |
| #1585 | ArrowStringArray breaks optimize after NetCDF round-trip |
| #1607 | ConsistencyError on p_min_pu = p_max_pu |
| #40 | DC network PF requires AC workaround |
| #1282 | Ramping conflicts during start-up with min part loads |

## Ecosystem & Community

- 1,887 GitHub stars, 614 forks, 104 contributors
- 12 releases in past year, including v1.0.0 milestone
- MIT license throughout the stack
- Notable users: IEA, ACER, Shell, TransnetBW, ENTSO-E, 50+ universities
- Ecosystem packages: PyPSA-Eur, PyPSA-USA, linopy, atlite, powerplantmatching

## Gaps and Uncertainties for Testing

- MATPOWER import fidelity for ACTIVSg cases
- 10k-bus scalability (no published benchmarks)
- SCLOPF intermittent failure reproducibility
- Solver compatibility with SCIP, Ipopt, GLPK via linopy
- Reactive power modeling in LOPF (ignored entirely)
