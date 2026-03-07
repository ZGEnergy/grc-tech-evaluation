# pandapower — Research: Limitations & Ecosystem

## Key Findings

- **No built-in SCUC, SCOPF, or stochastic OPF.** pandapower's optimization is limited to single-period AC/DC OPF via PYPOWER's interior-point method. Unit commitment, security-constrained OPF, and stochastic formulations are absent from the core library. Tests A-5, A-6, A-8, A-9 will require significant workarounds or external formulation.
- **OPF convergence is a documented weakness.** The PYPOWER-based `runopp()` has poor convergence properties acknowledged in official docs. Many built-in test networks fail OPF without manual parameter adjustments. The developers themselves describe their support for the PYPOWER OPF interface as "minimal."
- **LMP / dual value extraction is not straightforward.** pandapower does not expose shadow prices or LMP decomposition natively. Users must dig into the internal `net["_ppc_opf"]` PYPOWER case structure. Tests A-10 and A-11 (lossy DC OPF with LMP decomposition, distributed slack OPF) will be challenging.
- **PTDF/LODF functions exist but are inherited from PYPOWER**, not natively exposed in the pandapower API (`pandapower.pypower.makePTDF.makePTDF()`). A feature request to expose sensitivity measures (Issue #2290) remains open.
- **Distributed slack is supported** via `distributed_slack=True` parameter and `slack_weight` on generators/ext_grids, but has reported behavioral inconsistencies (Issue #1399).
- **N-1 contingency analysis is supported** with both native and lightsim2grid-accelerated variants, but no SCOPF (contingency constraints embedded in optimization) exists.
- **No PSS/E RAW import.** Supported converters: MATPOWER, PYPOWER, PowerFactory, CIM CGMES, UCTE-DEF, JAO. PSS/E is absent.
- **Active development with strong release cadence.** 10 releases in the past 12 months, v3.0.0 (March 2025) was a major breaking-change release. Latest is v3.4.0 (Feb 2026).
- **Primarily academic/research tool.** Backed by University of Kassel and Fraunhofer IEE. No evidence of utility/ISO production deployment. ~1,100 GitHub stars, ~90 contributors, ~3,600 weekly PyPI downloads.
- **BSD 3-Clause license.** Permissive, no copyleft concerns. Core dependencies (numpy, scipy, pandas, PYPOWER) are also permissively licensed.

## Detailed Notes

### OPF Convergence and Known Problems

The official documentation page "Known Problems" (v3.2.0+) states:

> "Optimal power flows do not converge on all networks, in contrast to power flow analyses. The majority of the networks provided by pandapower was not created for optimization studies."
>
> "The support of the pandapower developers for the function made usable from pypower is minimal."

Many built-in MATPOWER cases require manual adjustments (voltage limits, generator limits, branch limits) before OPF will converge. Even with adjustments, convergence is not guaranteed.

Relevant GitHub issues:
- Issue #88: "OPF don't converge" (2017, early report)
- Issue #106: "Opf can't converge on the build-in test cases"
- Issue #1016: "OPF fails in simbench nets" (regression between v2.2 and v2.3/v2.4)
- Issue #1020: "DC OPF does not converge"
- Issue #1377: "pp.runopp is not working with a trafo included"
- Issue #1486: "Optimal power flow convergence issue"
- Issue #1526: "optimal power flow does not converge"

**Source:** [Known Problems docs](https://pandapower.readthedocs.io/en/develop/opf/known_problems.html), [GitHub issues](https://github.com/e2nIEE/pandapower/issues)

### Missing Formulations (SCUC, SCOPF, Stochastic OPF)

pandapower's OPF is a single-period, steady-state optimization using PYPOWER's interior-point method. The following are absent:

| Feature | Status | Impact on Evaluation |
|---------|--------|---------------------|
| SCUC (unit commitment) | Not supported | Test A-5 will fail or require external MILP formulation |
| SCED (economic dispatch with ramps) | Not supported natively | Test A-6 depends on A-5 |
| SCOPF (security-constrained OPF) | Not supported | Test A-9 requires manual constraint enumeration |
| Stochastic OPF | Not supported | Test A-8 requires external scenario framework |
| Multi-period OPF | Not natively supported | Tests A-5, A-6, A-8 affected |
| Piecewise-linear cost curves | Supported via PYPOWER | Test P2-2 likely achievable |

pandapower does support `pandamodels` integration with PowerModels.jl for more advanced optimization, but this adds Julia as a runtime dependency and has its own convergence challenges.

**Source:** [OPF formulation docs](https://pandapower.readthedocs.io/en/v2.4.0/opf/formulation.html), [PyPI extras](https://pypi.org/project/pandapower/)

### LMP and Dual Value Extraction

pandapower does not provide a native API for extracting LMPs, shadow prices, or constraint duals from OPF results. The PYPOWER internal case structure (`net["_ppc_opf"]`) contains the raw solver output, but:
- Extracting bus marginal prices requires understanding the PYPOWER data format
- LMP decomposition into energy/congestion/loss components is not provided
- Per-line congestion rent computation is entirely manual

This affects tests A-3 (LMP extraction from DC OPF), A-10 (lossy DC OPF with LMP decomposition), and A-11 (distributed slack LMP comparison).

**Source:** [PYPOWER OPF docs](https://pandapower.readthedocs.io/en/latest/opf/pypower_run.html)

### PTDF and Sensitivity Analysis

PTDF/LODF computation is available through inherited PYPOWER functions:
- `pandapower.pypower.makePTDF.makePTDF()`
- `pandapower.pypower.makeLODF.makeLODF()`

These are not part of the documented pandapower API surface. Users must convert between pandapower's element-based model and PYPOWER's bus-branch format to use them. Issue #2290 requests native exposure of sensitivity measures.

Issue #1572 (closed 2022): User confirmed custom PTDF computation works using PYPOWER internals.
Issue #1419 (closed 2022): Maintainer Roman Bolgaryn confirmed makePTDF/makeLODF functions exist.

**Source:** [Issue #1572](https://github.com/e2nIEE/pandapower/issues/1572), [Issue #1419](https://github.com/e2nIEE/pandapower/issues/1419)

### Distributed Slack

pandapower supports distributed slack via:
- `pp.runpp(net, distributed_slack=True)` for power flow
- `slack_weight` parameter on `ext_grid` and `gen` elements

Issue #1399 reports "inconsistent behaviour when multiple slacks on the grid" when `distributed_slack=True` is not explicitly set. The feature exists but has edge cases.

**Source:** [Ext Grid docs](https://pandapower.readthedocs.io/en/latest/elements/ext_grid.html), [Issue #1399](https://github.com/e2nIEE/pandapower/issues/1399)

### Contingency Analysis

pandapower provides N-1 contingency analysis via:
- `run_contingency()` — native Python implementation
- `run_contingency_ls2g()` — accelerated via lightsim2grid (C++)

Results include loading percentages, voltage magnitudes, and identification of overloading causes. However:
- No SCOPF (contingency constraints in optimization)
- lightsim2grid variant does not support 3-winding transformers
- lightsim2grid requires continuous bus indices starting from 0
- Branch flows in lightsim2grid valid only for from_bus (lines) and hv_bus (transformers)

**Source:** [Contingency docs](https://pandapower.readthedocs.io/en/latest/contingency.html)

### Converter and Format Support

| Format | Import | Export | Notes |
|--------|--------|--------|-------|
| MATPOWER (.m) | Yes | Yes | Requires `matpowercaseframes` (undocumented dep) |
| MATPOWER (.mat) | Yes | Yes | Uses scipy |
| PYPOWER (ppc dict) | Yes | Yes | Native |
| PowerFactory | Yes | No | Via Python automation |
| CIM CGMES | Yes | No | v3.0 support added in v3.3.0 |
| UCTE-DEF | Yes | No | Added in v3.0.0 |
| JAO Static Grid | Yes | No | Added in v3.0.0 |
| PSS/E RAW | **No** | No | Community workarounds only |

The MATPOWER .m import path has a known issue in v3.4.0: the documented API `pp.converter.from_mpc()` does not work; the actual path is `pandapower.converter.matpower.from_mpc.from_mpc`. See install-findings.md.

**Source:** [Converter docs](https://pandapower.readthedocs.io/en/latest/converter.html), local `notes/install-findings.md`

### Ecosystem Packages

The e2nIEE organization maintains these ecosystem packages:

| Package | Stars | Description | Last Updated |
|---------|-------|-------------|--------------|
| **pandapower** | 1,113 | Power system modeling & analysis | Mar 2026 |
| **pandapipes** | 209 | Pipe network simulation (gas, heat, water) | Feb 2026 |
| **simbench** | 129 | Benchmark network datasets | Oct 2025 |
| **pandahub** | 15 | MongoDB data hub for networks | Dec 2025 |
| **PandaModels.jl** | 13 | Julia/PowerModels.jl bridge | Sep 2025 |
| **pandapower-qgis** | 2 | QGIS plugin | Feb 2026 |
| **pandaprosumer** | 3 | Prosumer modeling | Mar 2026 |
| **pandaict** | — | ICT network modeling | Feb 2026 |

pandapipes is the most significant ecosystem package, enabling multi-energy grid simulation (coupled electric + gas/heat networks). simbench provides standardized benchmark datasets with time-series profiles.

**Source:** [e2nIEE GitHub](https://github.com/e2nIEE)

### Community Size and Activity

| Metric | Value |
|--------|-------|
| GitHub stars | ~1,100 |
| GitHub forks | ~550 |
| Contributors | ~90 |
| Total commits | ~10,700 |
| Open issues | 123 |
| Open PRs | 33 |
| PyPI weekly downloads | ~3,600 |
| Dependent projects (GitHub) | 487 |

The project has 50 total releases. Development is concentrated at University of Kassel / Fraunhofer IEE with community contributions.

**Source:** [GitHub repo](https://github.com/e2nIEE/pandapower), [PyPI](https://pypi.org/project/pandapower/)

### Release History (Last 12 Months)

| Version | Date | Highlights |
|---------|------|------------|
| 3.4.0 | 2026-02-09 | `enforce_p_lims`, DC elements in DCPF, Python 3.14 support |
| 3.3.2 | 2026-01-14 | scipy version pin fix |
| 3.3.1 | 2026-01-13 | Short circuit calculation fix (scipy Ybus inversion) |
| 3.3.0 | 2025-12-16 | SVC control, CIM v3.0, juliacall migration, diagnostics restructuring |
| 3.2.1 | 2025-10-27 | Back-to-Back VSC, DC load/source, Plotly Maplibre migration, Python 3.13 |
| 3.2.0 | 2025-10-08 | Parallel contingency analysis (multiprocessing) |
| 3.1.2 | 2025-06-16 | State estimation optimization, sparse matrices, iteration count output |
| 3.1.1 | 2025-05-26 | URL fix for digital attestation |
| 3.1.0 | 2025-05-26 | Q capability curves, allocation factor WLS estimator |
| 3.0.0 | 2025-03-06 | **Major breaking release**: MW/MVAr units (was kW/kVAr), generation-reference signing, trafo param renames, pyproject.toml, VSC/DC elements |

v3.0.0 was a major breaking change that altered unit systems, sign conventions, and parameter names. This means code written for v2.x requires migration.

**Source:** [Changelog](https://pandapower.readthedocs.io/en/latest/about/changelog.html), [Releases](https://github.com/e2nIEE/pandapower/releases)

### Documentation Quality

**Strengths:**
- Comprehensive ReadTheDocs documentation covering all element types, power flow, and OPF
- Jupyter notebook tutorials for getting started, network creation, and basic analyses
- Element-level API reference with parameter descriptions
- Changelog is detailed and well-maintained
- Validation against commercial software is documented

**Weaknesses:**
- MATPOWER converter API path is broken in v3.4.0 (docs say `pp.converter.from_mpc()`, actual path differs)
- `matpowercaseframes` dependency for .m files is undocumented
- OPF dual value / LMP extraction is not documented
- PTDF/LODF functions are inherited from PYPOWER but not documented in pandapower's API reference
- Advanced optimization topics (multi-period, stochastic, SCOPF) are absent from docs because the features do not exist
- Some tutorials may be outdated relative to v3.0.0 breaking changes

**Source:** [pandapower docs](https://pandapower.readthedocs.io/), local `notes/install-findings.md`

### Institutional Backing and Adoption

**Developers:**
- University of Kassel, Department for Sustainable Electrical Energy Systems (e2n)
- Fraunhofer Institute for Energy Economics and Energy System Technology (IEE), Kassel

**Known deployments:**
- Verteilnetzstudie Hessen (2018): Distribution network study for the Hesse region, Germany (BearingPoint + Fraunhofer IEE)
- National University of Singapore: undergraduate curriculum
- Numerous academic papers (primarily European distribution grid studies)

**No evidence found of:**
- ISO/RTO production use
- North American utility deployment
- Government procurement or certification

**Source:** [References page](https://www.pandapower.org/references/), [About page](https://www.pandapower.org/about/)

### License and Dependencies

pandapower is **BSD 3-Clause** licensed. Key runtime dependencies and their licenses:

| Dependency | License | Notes |
|------------|---------|-------|
| pandas | BSD 3-Clause | Core data structure |
| numpy | BSD 3-Clause | Numerical operations |
| scipy | BSD 3-Clause | Sparse matrices, linear algebra |
| PYPOWER | BSD-like | Power flow engine (bundled) |
| networkx | BSD 3-Clause | Graph operations |
| lightsim2grid | MPL 2.0 | Optional C++ solver (performance extra) |
| numba | BSD 2-Clause | Optional JIT compilation (performance extra) |
| power-grid-model | MPL 2.0 | Optional C++ backend (pgm extra) |
| ortools | Apache 2.0 | Optional for state estimation (performance extra) |

All dependencies are permissively licensed. No copyleft (GPL) components in the standard installation.

**Source:** [PyPI](https://pypi.org/project/pandapower/), [LICENSE](https://github.com/e2nIEE/pandapower/blob/master/LICENSE)

## Sources

1. [pandapower GitHub repository](https://github.com/e2nIEE/pandapower)
2. [pandapower ReadTheDocs (v3.4.0)](https://pandapower.readthedocs.io/)
3. [pandapower PyPI page](https://pypi.org/project/pandapower/)
4. [Known OPF Problems documentation](https://pandapower.readthedocs.io/en/develop/opf/known_problems.html)
5. [Contingency analysis documentation](https://pandapower.readthedocs.io/en/latest/contingency.html)
6. [Converter documentation](https://pandapower.readthedocs.io/en/latest/converter.html)
7. [Changelog](https://pandapower.readthedocs.io/en/latest/about/changelog.html)
8. [GitHub releases](https://github.com/e2nIEE/pandapower/releases)
9. [e2nIEE GitHub organization](https://github.com/e2nIEE)
10. [pandapower references page](https://www.pandapower.org/references/)
11. [pandapower about page](https://www.pandapower.org/about/)
12. [PTDF Issue #1572](https://github.com/e2nIEE/pandapower/issues/1572)
13. [PTDF/LODF Issue #1419](https://github.com/e2nIEE/pandapower/issues/1419)
14. [Distributed slack Issue #1399](https://github.com/e2nIEE/pandapower/issues/1399)
15. [OPF convergence Issue #1526](https://github.com/e2nIEE/pandapower/issues/1526)
16. [OPF simbench Issue #1016](https://github.com/e2nIEE/pandapower/issues/1016)
17. Local file: `evaluations/pandapower/notes/install-findings.md`

## Gaps and Uncertainties

- **LMP extraction mechanics**: It is unclear whether PYPOWER's internal `bus` array in `net["_ppc_opf"]` contains marginal prices (column 14 in MATPOWER format). This needs verification during testing.
- **DC OPF solver options**: pandapower uses PYPOWER's interior-point method by default. It is unclear whether HiGHS or GLPK can be used as alternative solvers for DC OPF without the PowerModels.jl bridge. The eval-config specifies these solvers for tests A-3, C-3, C-7.
- **Multi-period capability via controllers**: pandapower has a "controller" framework and time-series module (`pandapower.timeseries`) that may support sequential time-step simulation. Whether this can be used for multi-period OPF (as opposed to sequential power flow) needs investigation.
- **Custom constraint API**: It is unclear whether pandapower exposes an API for adding arbitrary linear constraints to the OPF formulation (needed for tests B-1, A-9 SCOPF workaround). The PYPOWER OPF may support user-defined constraints via callback functions.
- **PowerModels.jl bridge maturity**: The `pandamodels` extra provides a bridge to PowerModels.jl (Julia), which does support SCOPF, multi-period OPF, and more formulations. The maturity and reliability of this bridge in v3.4.0 (now using `juliacall` per v3.3.0 changelog) needs evaluation.
- **v3.0.0 migration impact on tutorials**: Many pandapower tutorials and community examples were written for v2.x. The unit system change (kW to MW) and sign convention change in v3.0.0 may cause silent errors if old examples are run on v3.x.
- **Bus factor risk**: Contributor concentration at Kassel/Fraunhofer needs quantification during E-3 testing.
