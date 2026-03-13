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
