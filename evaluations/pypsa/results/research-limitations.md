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
