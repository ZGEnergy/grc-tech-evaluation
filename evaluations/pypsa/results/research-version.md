---
tool: pypsa
installed_version: 1.1.2
release_date: 2026-02-23
latest_version: 1.1.2
latest_release_date: 2026-02-23
research_date: 2026-03-13
---

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
