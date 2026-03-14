# pandapower — Research: Limitations & Ecosystem

## Key Findings

- **OPF solver is internal (PIPS/PYPOWER fork):** pandapower's native OPF uses a bundled interior-point solver from PYPOWER. It cannot natively interface with Ipopt, HiGHS, or other external solvers. External solver access requires the PandaModels.jl Julia bridge (`runpm_ac_opf`), which adds a Julia dependency.
- **No unit commitment / SCUC capability:** pandapower has no built-in unit commitment formulation. Binary on/off decisions for generators, min up/down times, and startup costs are not supported natively. PandaModels.jl does not add UC either.
- **No native stochastic optimization:** No built-in scenario-based or chance-constrained optimization. Stochastic analysis must be implemented manually by looping over scenarios.
- **Time series module is sequential PF, not multi-period OPF:** `run_timeseries()` runs independent power flows per timestep with controller callbacks. It does not formulate or solve inter-temporal optimization (e.g., storage dispatch across hours).
- **MATPOWER converter has known bugs:** Transformer round-trip conversion loses data (#2643), multiple generators on the same bus can fail (#2685), and files with non-standard voltage levels produce zero vn_kv (#2516). The shared `matpower_loader` mitigates some issues.
- **tolerance_mva is likely in per-unit, not MVA:** Confirmed bug (#2750) — the convergence tolerance parameter is documented as MVA but compared against per-unit mismatches internally. Unfixed as of v3.4.0.
- **Active development, frequent releases:** 10 releases in the past 12 months (v3.0.0 through v3.4.0). v3.0.0 was a major release adding VSC/HVDC, CGMES v3.0 support, and DER controllers.
- **Moderate community:** ~1,118 GitHub stars, 556 forks, 135 contributors, 157 open issues (47 labeled bug). ~2.2M total PyPI downloads. Development concentrated at University of Kassel / Fraunhofer IEE.
- **Contingency analysis requires lightsim2grid:** The `run_contingency` and `run_contingency_ls2g` functions live in a module that depends on lightsim2grid for performant execution. lightsim2grid is available (v0.12.2) in the eval environment.
- **BSD 3-Clause license.** All core dependencies (numpy, scipy, pandas, networkx) are permissively licensed.

## Detailed Notes

### OPF Solver Architecture

pandapower's OPF (`runopp` for AC, `rundcopp` for DC) uses a bundled fork of PYPOWER's PIPS (Primal-dual Interior Point Solver). The DC OPF uses `qps_pypower`, also from the PYPOWER fork. These are pure-Python/NumPy/SciPy solvers — no compiled solver binaries.

There is no mechanism to swap in external solvers (Ipopt, HiGHS, GLPK) for the native OPF. The only path to external solvers is `runpm_ac_opf()` / `runpm_dc_opf()`, which calls PowerModels.jl via PandaModels.jl through the `juliacall` Python package. This requires a full Julia installation and the PandaModels.jl package.

**Implications for evaluation:**
- Suite A OPF tests (A-3, A-4) can use the native PIPS solver for small cases
- Scalability of OPF (Suite C) will be limited by the pure-Python PIPS solver
- Custom constraint injection (A-9 flowgates, B-1) via PYPOWER's `add_userfcn` is possible but underdocumented

**Sources:**
- `pandapower/pypower/pipsopf_solver.py` (PIPS solver source)
- `pandapower/pypower/dcopf_solver.py` (DC OPF, uses `qps_pypower`)
- `pandapower/runpm.py` (PandaModels.jl bridge, line 1-40)

### Unit Commitment and Multi-Period Optimization

pandapower has **no unit commitment capability**. There is no binary commitment variable, no min up/down time constraint, no startup cost modeling. The `run_timeseries()` function performs sequential independent power flows (or OPFs if a custom `run` function is passed), but these are decoupled across timesteps — there is no inter-temporal linking.

The `create_storage` element exists for modeling batteries, but it is only used in sequential power flow with controller-based SoC tracking — not in an optimization formulation that dispatches storage optimally across time periods.

**Implications for evaluation:**
- Tests A-5 (SCUC) and A-6 (multi-period with storage) will likely fail or require external tooling
- Test A-12 (full multi-period DCOPF with BESS) cannot be expressed natively

**Sources:**
- `pandapower/timeseries/run_time_series.py` (sequential PF/OPF runner)
- No UC-related attributes found in `dir(pandapower)`

### MATPOWER File Loading and Conversion Bugs

The MATPOWER converter (`from_mpc`, `from_ppc`) has several known open bugs:

| Issue | Description | Status |
|-------|-------------|--------|
| [#2643](https://github.com/e2nIEE/pandapower/issues/2643) | `to_ppc()` sets transformer ratio to 1.0; round-trip via `from_ppc()` loses transformer data | Open |
| [#2685](https://github.com/e2nIEE/pandapower/issues/2685) | Multiple generators on the same bus from MATPOWER .m file parsed incorrectly | Open |
| [#2516](https://github.com/e2nIEE/pandapower/issues/2516) | MATPOWER files with various voltage levels produce zero `vn_kv` | Open |
| [#2614](https://github.com/e2nIEE/pandapower/issues/2614) | `from_ppc()` reduces line count during conversion | Open |
| [#2620](https://github.com/e2nIEE/pandapower/issues/2620) | `to_mpc()` converts transformers to impedances; `from_mpc()` cannot reverse | Open |
| [#2392](https://github.com/e2nIEE/pandapower/issues/2392) | Zero-resistance lines interpreted as transformers in IEEE14 | Open |

The shared `matpower_loader` in the evaluation repo (`evaluations/shared/matpower_loader.py`) uses `matpowercaseframes` to parse MATPOWER files and `from_ppc` to convert to pandapower format. This path is classified as LOSSLESS in the evaluation protocol.

**Sources:**
- GitHub issues linked above
- `evaluations/shared/LOADING_NOTES.md`

### Convergence and Numerical Issues

| Issue | Description |
|-------|-------------|
| [#2750](https://github.com/e2nIEE/pandapower/issues/2750) | `tolerance_mva` is compared in per-unit despite being documented as MVA. Confirmed by maintainer, unfixed. |
| [#2557](https://github.com/e2nIEE/pandapower/issues/2557) | Behavior mismatch between pp2 and pp3 on IEEE cases — transformer impedance splitting changed |
| [#114](https://github.com/e2nIEE/pandapower/issues/114) | Algorithms for ill-conditioned problems — open since 2017 |
| [#2609](https://github.com/e2nIEE/pandapower/issues/2609) | Simbench network AC OPF not converging with native or PandaModels solver |
| [#1101](https://github.com/e2nIEE/pandapower/issues/1101) | OPF non-convergence regression in versions > 2.2.0 |
| [#2692](https://github.com/e2nIEE/pandapower/issues/2692) | Ideal 3-winding transformers with tap at HV side malfunction |

### Short Circuit Analysis

pandapower implements IEC 60909 short circuit calculations via `pandapower.shortcircuit.calc_sc()`. Known open issues:

| Issue | Description |
|-------|-------------|
| [#2646](https://github.com/e2nIEE/pandapower/issues/2646) | NaN bus voltages during single-phase short circuit |
| [#2621](https://github.com/e2nIEE/pandapower/issues/2621) | Thermal current values don't vary with topology |
| [#2292](https://github.com/e2nIEE/pandapower/issues/2292) | Possibly incorrect Ik'' results |
| [#2484](https://github.com/e2nIEE/pandapower/issues/2484) | Missing kappa value for Type 4 wind generators |

### State Estimation

pandapower includes WLS, IRWLS, LP, and AF-WLS state estimation algorithms. Known issues:

| Issue | Description |
|-------|-------------|
| [#2700](https://github.com/e2nIEE/pandapower/issues/2700) | `zero-injection="no_inj_bus"` produces IndexError |
| [#1451](https://github.com/e2nIEE/pandapower/issues/1451) | `remove_bad_data` fails with linear algebra errors |

### Contingency Analysis

pandapower has a contingency analysis module (`pandapower.contingency`) with two implementations:
- `run_contingency()` — pure-Python sequential N-1
- `run_contingency_ls2g()` — accelerated via lightsim2grid (C++ backend)

Open issues:
- [#2715](https://github.com/e2nIEE/pandapower/issues/2715): Parallel contingency analysis not yet implemented
- [#2910](https://github.com/e2nIEE/pandapower/issues/2910): lightsim2grid issue with case14 (future compatibility)
- [#2438](https://github.com/e2nIEE/pandapower/issues/2438): `run_contingency_ls2g` fails with redundant buses
- [#2684](https://github.com/e2nIEE/pandapower/issues/2684): Ambiguity in `max_loading_percent` requirement

### DC Line / HVDC Modeling

v3.0.0 added VSC elements, DC buses, DC lines, and hybrid AC/DC power flow. Known issues:
- [#2716](https://github.com/e2nIEE/pandapower/issues/2716): Bidirectional DC lines bug
- [#2712](https://github.com/e2nIEE/pandapower/issues/2712): Distributed slack not supported for DC power flow
- [#2235](https://github.com/e2nIEE/pandapower/issues/2235): DC lines not correctly displayed in `res_bus.p_mw`

### Ecosystem Packages

| Package | Stars | Description | Relationship |
|---------|-------|-------------|--------------|
| [pandapipes](https://github.com/e2nIEE/pandapipes) | 210 | Pipeflow calculation (gas, heat, water) | Official companion (same team) |
| [simbench](https://github.com/e2nIEE/simbench) | 128 | Benchmark distribution grids | Official companion |
| [PandaModels.jl](https://github.com/e2nIEE/PandaModels.jl) | 13 | Julia bridge to PowerModels.jl | Official companion |
| [pandahub](https://github.com/e2nIEE/pandahub) | 15 | MongoDB data hub for networks | Official companion |
| [pandapower-qgis](https://github.com/e2nIEE/pandapower-qgis) | 2 | QGIS plugin | Official companion |
| [lightsim2grid](https://github.com/BDonnot/lightsim2grid) | ~100 | C++ power flow backend (RTE) | Third-party, officially supported |

**lightsim2grid** is particularly notable: it provides a compiled C++ Newton-Raphson solver that pandapower can use as a drop-in replacement for its pure-Python solver (`pp.runpp(net, algorithm='gs')` → lightsim2grid). It offers 10-100x speedup on power flow and is critical for performant contingency analysis.

### Performance / Scalability

The optional `performance` extras add:
- **lightsim2grid** (~0.12.2): C++ power flow backend, 10-100x faster than native Newton-Raphson
- **numba** (~0.61): JIT compilation for select numerical routines
- **ortools** (~9.14): Google OR-Tools (unclear integration point)

Scalability concerns:
- Native Newton-Raphson (pure Python/NumPy) is slow for large networks (>5k buses)
- Native OPF (PIPS) is a pure-Python interior point solver — likely impractical for 10k+ bus OPF
- [#851](https://github.com/e2nIEE/pandapower/issues/851): Feature request for GraphBLAS-accelerated graph algorithms (open since 2019)
- [#1635](https://github.com/e2nIEE/pandapower/issues/1635): Temperature-dependent power flow performance issues
- No parallel processing support for contingency analysis ([#2715](https://github.com/e2nIEE/pandapower/issues/2715))

### Release History

| Version | Date | Highlights |
|---------|------|------------|
| v3.4.0 | 2026-02-09 | DC elements in DC powerflow, Python 3.14 support, lightsim2grid 0.12.2 |
| v3.3.2 | 2026-01-15 | Bug fixes |
| v3.3.0 | 2025-12-16 | (details not retrieved) |
| v3.2.1 | 2025-10-27 | Bug fixes |
| v3.2.0 | 2025-10-08 | (details not retrieved) |
| v3.1.2 | 2025-06-16 | Bug fixes |
| v3.1.1 | 2025-05-26 | Bug fixes |
| v3.0.0 | 2025-03-06 | **Major:** VSC/HVDC, CGMES v3.0, DER controllers, station controllers, pandera schemas, JAO/UCTE converters |
| v2.14.11 | 2024-08-07 | Last v2 release |

Release cadence: approximately monthly during active development periods. Major version bumps (2→3) introduce breaking API changes (controller parameter renames, geodata format changes).

### Documentation Quality

- **Platform:** ReadTheDocs (Sphinx-based), covers v3.4.0
- **Coverage:** Comprehensive across core features (power flow, OPF, short circuit, state estimation, controllers, time series, plotting, converters)
- **Gaps identified:**
  - Protection module coverage is minimal (only overcurrent relay and fuse)
  - No dedicated troubleshooting/debugging guide
  - Limited scalability/performance guidance
  - Transformer documentation has known equation errors ([#2847](https://github.com/e2nIEE/pandapower/issues/2847))
  - Some tutorials have deprecation warnings ([#2734](https://github.com/e2nIEE/pandapower/issues/2734))
  - Missing plots in asymmetric tutorial ([#2733](https://github.com/e2nIEE/pandapower/issues/2733))
- **Tutorials:** Jupyter notebooks in the repo, tested via CI (nbmake)
- **API reference:** Auto-generated from docstrings (numpydoc style)

### Academic Citation

Primary paper: L. Thurner, A. Scheidler, F. Schäfer et al., "pandapower — An Open-Source Python Tool for Convenient Modeling, Analysis, and Optimization of Electric Power Systems," *IEEE Transactions on Power Systems*, vol. 33, no. 6, pp. 6510-6521, 2018. DOI: [10.1109/TPWRS.2018.2829021](https://doi.org/10.1109/TPWRS.2018.2829021)

### License and Dependencies

- **pandapower license:** BSD 3-Clause
- **Copyright:** University of Kassel and Fraunhofer IEE (2016-2026)
- **Core dependencies (all permissive):** pandas (~2.3), networkx (~3.4), scipy (<1.17), numpy (>=1.26), packaging, tqdm, deepdiff, geojson, typing_extensions, pandera (~0.26.1)
- **Performance extras:** lightsim2grid (MPL-2.0), numba (BSD-2), ortools (Apache-2.0)
- **Converter extras:** matpowercaseframes (MIT), lxml (BSD-3)
- **PandaModels bridge:** juliacall (MIT) → requires Julia runtime + PowerModels.jl (BSD-3)

No GPL or copyleft dependencies in the core or performance extras.

### Operational Deployment Evidence

No direct evidence of utility, ISO, or government operational deployments was found on the website, documentation, or GitHub. The project is developed by University of Kassel and Fraunhofer IEE (a German applied research institute). Fraunhofer IEE works with European TSOs/DSOs, which suggests indirect industrial use, but no specific deployments are publicly documented.

The simbench companion project provides standardized benchmark networks modeled after German distribution grid characteristics, suggesting primary use in European grid planning contexts.

## Sources

1. GitHub repository: https://github.com/e2nIEE/pandapower (1,118 stars, 556 forks, 135 contributors)
2. PyPI: https://pypi.org/project/pandapower/ (v3.4.0, 2026-02-09)
3. Documentation: https://pandapower.readthedocs.io/en/latest/
4. Download stats: https://pepy.tech/projects/pandapower (~2.2M total downloads)
5. Primary paper: IEEE TPWRS 2018, DOI 10.1109/TPWRS.2018.2829021
6. Official website: https://www.pandapower.org
7. PandaModels.jl: https://github.com/e2nIEE/PandaModels.jl
8. lightsim2grid: https://github.com/BDonnot/lightsim2grid
9. simbench: https://github.com/e2nIEE/simbench
10. Installed source code: `/workspace/evaluations/pandapower/.venv/lib/python3.12/site-packages/pandapower/`

## Gaps and Uncertainties

- **OPF scalability:** Not yet tested — unclear how PIPS performs on 2k and 10k bus networks. May need PandaModels.jl bridge for larger cases.
- **Custom constraint injection:** PYPOWER's `add_userfcn` exists but is underdocumented in pandapower context. Unclear if flowgate constraints (test B-1) can be expressed without PandaModels.jl.
- **lightsim2grid PF accuracy:** lightsim2grid is a separate C++ implementation — need to verify results match native pandapower on test networks.
- **MATPOWER loading fidelity:** Known bugs in converter may affect ACTIVSg 2k/10k loading. The shared `matpower_loader` may mitigate, but needs testing.
- **Pandas 3.0 compatibility:** Listed as a future goal (#2861) for pandapower v4.0. Current v3.4.0 pins pandas ~2.3.
- **Three-phase / unbalanced power flow:** pandapower has `runpp_3ph` but its maturity is unclear — asymmetric tutorial has missing plots (#2733).
- **PandaModels.jl integration reliability:** Issue #1740 reports discrepancies between OPF solutions via PandaModels vs direct PowerModels.jl usage.
- **No evidence of US utility/ISO deployment.** All known development is European (German). Unclear if pandapower handles US-specific conventions (US ISO market data, reliability standards) out of the box.
