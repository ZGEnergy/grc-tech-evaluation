# PyPSA — Research: Limitations, Ecosystem, Community, Documentation

## Key Findings

- **No full AC OPF:** PyPSA supports nonlinear power flow (Newton-Raphson) and linear OPF (LOPF), but optimization with full nonlinear AC power flow constraints is not supported. Only LP/MILP/QP optimization is available via linopy. ([docs](https://pypsa.readthedocs.io/en/latest/optimal_power_flow.html))
- **SCOPF is branch-only:** Security-constrained optimization (`optimize_security_constrained()`) handles N-1 branch outages but not generator outages. Generator contingencies must be modeled through stochastic optimization workarounds. ([docs](https://docs.pypsa.org/latest/user-guide/optimization/contingencies/))
- **Stochastic optimization is built-in (v1.1.0+):** Two-stage stochastic programming with scenario weights is now a first-party feature, though earlier versions required the external PyPSA-stochUC package. ([features](https://docs.pypsa.org/latest/home/features/))
- **Lossy OPF via piecewise-linear approximation only:** Transmission losses default to zero; `n.optimize(transmission_losses=N)` uses N-segment piecewise-linear loss curves — not exact quadratic losses. ([docs](https://pypsa.readthedocs.io/en/latest/optimal_power_flow.html))
- **Broken pandapower importer in v1.1.2:** `import_from_pandapower_net()` crashes on networks with multiple generators at the same bus (e.g., IEEE 39-bus case39). The pypower import path works but requires manual dict construction. (See `evaluations/pypsa/notes/install-findings.md`)
- **No native MATPOWER .m file reader:** Importing standard test cases requires pandapower or matpowercaseframes as intermediaries, adding friction and supply-chain dependencies that competitors (PowerModels.jl, MATPOWER) avoid. (See `evaluations/pypsa/notes/install-findings.md`)
- **Large dependency footprint:** 89 packages in the resolved lock file including dask, geopandas, google-cloud-storage, polars, shapely, and matplotlib — many unrelated to core power system analysis. (See `evaluations/pypsa/uv.lock`)
- **Very active release cadence:** 10+ releases in the last 5 months (v1.0.2 through v1.1.2), with patch releases every 2-4 weeks. v1.0.0 marked the first "stable" API with backward-compatibility guarantees through v2.0. ([releases](https://github.com/PyPSA/PyPSA/releases))
- **Strong institutional adoption:** Used by ENTSO-E, TransnetBW, TenneT, Canada Energy Regulator, IEA, ACER, Saudi Aramco, Shell, Rocky Mountain Institute, and 30+ universities worldwide. ([users](https://docs.pypsa.org/latest/home/users/))
- **Large community:** ~1.9k GitHub stars, ~614 forks, 94 open issues, 290 dependent projects, Discord community, maintained by TU Berlin with DFG funding. ([GitHub](https://github.com/PyPSA/PyPSA))

## Detailed Notes

### Optimization Limitations

**No nonlinear AC OPF optimization.** PyPSA can run full AC power flow analysis via `network.pf()` (Newton-Raphson), but all optimization formulations (LOPF, SCLOPF, capacity expansion) use linearized DC power flow or piecewise-linear approximations. The docs state: "Optimisation with the full non-linear power flow equations is not yet supported." This is a fundamental architectural limitation — the optimization layer (linopy) only handles LP/MILP/QP problems.

Source: [Power System Optimization docs](https://pypsa.readthedocs.io/en/latest/optimal_power_flow.html)

**Transmission losses are approximate.** The `transmission_losses` parameter in `n.optimize()` controls the number of piecewise-linear segments approximating the quadratic loss curve. Default is 0 (lossless). Setting `transmission_losses=3` uses 3 segments. This is a known trade-off: more segments = better accuracy but larger LP.

Source: [Power System Optimization docs](https://pypsa.readthedocs.io/en/latest/optimal_power_flow.html)

**SCOPF scope is limited to branch contingencies.** The `optimize_security_constrained()` method only considers branch (line/transformer) outages. For generator outages, the documentation recommends setting `p_max_pu=0` in specific scenarios and using stochastic optimization. Computational cost scales as O(branches x outages x snapshots).

Source: [Contingencies docs](https://docs.pypsa.org/latest/user-guide/optimization/contingencies/)

**PTDF and BODF are supported.** The PTDF (Power Transfer Distribution Factors) formulation is available for LOPF, and BODF (Branch Outage Distribution Factors) are used in SCLOPF. `sn.calculate_BODF()` computes distribution factors. Singular BODF matrices (radial branches) require special handling with independent slack buses per island.

Source: [Contingencies docs](https://docs.pypsa.org/latest/user-guide/optimization/contingencies/)

**Unit commitment is fully implemented.** Setting `committable=True` on generators/links introduces binary status variables with min up/down times, start-up/shut-down costs, and ramp constraints. Implementation follows Taylor (2015) "Convex Optimization of Power Systems" Chapter 4.3. Available since early PyPSA versions.

Source: [Power System Optimization docs](https://pypsa.readthedocs.io/en/latest/optimal_power_flow.html)

**Distributed slack is supported for power flow** (not optimization). `network.pf()` supports distributed slack for AC networks via Newton-Raphson.

Source: [Power Flow docs](https://pypsa.readthedocs.io/en/latest/power_flow.html)

### Known Bugs and Open Issues

**Pandapower importer broken on multi-generator buses (v1.1.2).** `import_from_pandapower_net()` fails with a shape mismatch in `v_mag_pu_set` assignment when multiple generators share a bus (e.g., IEEE case39 bus 31). This suggests the pandapower import path is not tested in CI against standard reference cases.

Source: `/home/joe/code/zge-workspace/grc-tech-evaluation/.claude/worktrees/eval/pypsa-2/evaluations/pypsa/notes/install-findings.md`

**SCLOPF had a bug with extendable lines** that was fixed in PR #946 — the security-constrained constraints were not correctly applied to extendable branches.

Source: [PR #946](https://github.com/PyPSA/PyPSA/pull/946)

**v1.1.1 was yanked** (Feb 23, 2026) due to incorrect CI pipeline branch detection. v1.1.2 was released the same day as a fix.

Source: [PyPI](https://pypi.org/project/pypsa/)

### Ecosystem Packages

The PyPSA organization on GitHub maintains a rich ecosystem:

| Package | Purpose | GitHub |
|---------|---------|--------|
| **linopy** | N-D labeled linear optimization (core dependency) | [PyPSA/linopy](https://github.com/PyPSA/linopy) |
| **atlite** | Renewable power potential and time-series from weather data | [PyPSA/atlite](https://github.com/PyPSA/atlite) |
| **pypsa-eur** | Sector-coupled European energy system model | [PyPSA/pypsa-eur](https://github.com/PyPSA/pypsa-eur) |
| **pypsa-earth** | Global energy system model for any country | [pypsa-meets-earth/pypsa-earth](https://github.com/pypsa-meets-earth/pypsa-earth) |
| **pypsa-usa** | US energy system model (integrates with PUDL) | [PyPSA/pypsa-usa](https://github.com/PyPSA/pypsa-usa) |
| **powerplantmatching** | Power plant database matching and cleaning | [PyPSA/powerplantmatching](https://github.com/PyPSA/powerplantmatching) |
| **technology-data** | Technology cost and efficiency assumptions | [PyPSA/technology-data](https://github.com/PyPSA/technology-data) |

The ecosystem is heavily oriented toward energy system planning and capacity expansion at continental scale. It is less focused on detailed transmission-level power system operations (protection, transient stability, EMT simulation).

### Community Size and Governance

- **GitHub stars:** ~1,900
- **GitHub forks:** ~614
- **Open issues:** 94
- **Dependent projects:** 290
- **Contributors:** Multiple (exact count not enumerated; led by TU Berlin)
- **Communication:** GitHub Issues/Discussions, Discord server
- **Funding:** German Research Foundation (DFG), TU Berlin Department of Digital Transformation in Energy Systems
- **Governance:** Academic-led open-source project, MIT license

Source: [GitHub](https://github.com/PyPSA/PyPSA)

### Documentation Quality

**Strengths:**
- Comprehensive user guide covering design principles, components, optimization formulations, and power flow
- Dedicated v1.0 migration guide with opt-in new API and `options_context` for gradual migration ([v1 guide](https://docs.pypsa.org/latest/user-guide/v1-guide/))
- Worked examples from toy models to sector-coupled continental systems
- API reference with autodoc
- Published academic paper (Brown et al., 2018, Journal of Open Research Software) provides theoretical foundation ([arXiv](https://arxiv.org/pdf/1707.09913))

**Weaknesses:**
- Contingency analysis documentation is thin — only one example, limited guidance on computational scaling
- No explicit "limitations" or "known issues" section in the docs
- The pandapower import path is documented but broken, creating a trust gap between docs and reality
- Some features (stochastic optimization, MGA) are documented at a high level but lack detailed API examples

Source: [docs.pypsa.org](https://docs.pypsa.org/latest/)

### Release History

| Version | Date | Notable Changes |
|---------|------|-----------------|
| v1.1.2 | 2026-02-23 | Fix `at_port` statistics, CPLEX compatibility |
| v1.1.0 | 2026-02-17 | Stochastic network statistics, secant transmission losses, temporal clustering, `n.sanitize()` |
| v1.0.7 | 2026-01-13 | Python 3.14 support, capital cost split (overnight + fixed O&M) |
| v1.0.6 | 2025-12-22 | `n.stats` shorthand, modular stochastic expansion |
| v1.0.5 | 2025-12-04 | Curtailment fixes, CVaR zero-cost fix, rolling-horizon xarray fix |
| v1.0.4 | 2025-11-21 | Multi-port Link clustering fix |
| v1.0.3 | 2025-11-06 | Ramp limit constraint fixes, rolling-horizon improvements |
| v1.0.2 | 2025-10-24 | Fix infinite recursion when pickling networks |
| v1.0.0 | 2025 (est.) | First stable API release, backward-compatibility guarantee through v2.0 |

Release frequency: ~2-4 weeks between patch releases. Active development with regular bug fixes. Changelog quality is good — each release note lists bug fixes, new features, and breaking changes with contributor attribution.

Source: [Release Notes](https://docs.pypsa.org/latest/release-notes/), [GitHub Releases](https://github.com/PyPSA/PyPSA/releases)

### License and Dependency Licensing

- **PyPSA:** MIT License
- **Documentation:** CC-BY-4.0
- **Python requirement:** >=3.11 (per PyPI); evaluation uses 3.12
- **Key dependencies:** pandas (BSD-3), numpy (BSD-3), scipy (BSD-3), linopy (MIT), matplotlib (PSF), networkx (BSD-3), xarray (Apache-2.0), highspy (MIT)
- **Notable transitive dependencies** pulled in via pandapower (which is BSD): geopandas, shapely, pyproj, google-cloud-storage, dask, polars, pandera — significantly expanding the attack surface and install footprint

Source: [PyPI](https://pypi.org/project/pypsa/), `evaluations/pypsa/uv.lock`

### Supply Chain Observations

The resolved dependency tree for this evaluation project (pypsa + pandapower + matpowercaseframes + highspy) contains **89 packages**. Many of these come from pandapower rather than PyPSA core. Notable heavyweight transitive dependencies:

- **google-cloud-storage** (+ google-auth, google-api-core, protobuf) — pulled in by pandapower, not needed for local power flow
- **dask** (+ distributed, cloudpickle, fsspec, locket, partd, toolz) — parallel compute framework
- **geopandas** (+ shapely, pyproj, pyogrio) — geospatial analysis
- **polars** — alternative DataFrame library
- **pandera** — DataFrame validation

If PyPSA is evaluated standalone (without pandapower for MATPOWER import), the dependency count would be significantly smaller.

### Operational Deployment Evidence

PyPSA is used in production/operational contexts by:

- **ENTSO-E:** Developing complementary open-source tool for TYNDP Scenario Building and CBA
- **TransnetBW / TenneT / Austrian Power Grid:** TSO grid planning studies
- **Canada Energy Regulator:** Canada's Energy Future 2023 report
- **IEA / ACER:** Energy regulatory analysis
- **Saudi Aramco / Shell:** Corporate energy planning
- **Rocky Mountain Institute / Agora Energiewende:** Policy analysis

Most deployments are for planning and policy analysis rather than real-time operations or day-ahead market clearing. No evidence of ISO/RTO operational use (market clearing, real-time dispatch).

Source: [Users page](https://docs.pypsa.org/latest/home/users/)

## Sources

1. [PyPSA GitHub Repository](https://github.com/PyPSA/PyPSA) — stars, forks, license, release info
2. [PyPSA Features Page](https://docs.pypsa.org/latest/home/features/) — capability list
3. [Power System Optimization Docs](https://pypsa.readthedocs.io/en/latest/optimal_power_flow.html) — OPF, UC, loss modeling
4. [Contingency Analysis Docs](https://docs.pypsa.org/latest/user-guide/optimization/contingencies/) — SCLOPF, BODF
5. [Power Flow Docs](https://pypsa.readthedocs.io/en/latest/power_flow.html) — Newton-Raphson, distributed slack
6. [PyPSA Users Page](https://docs.pypsa.org/latest/home/users/) — institutional adoption
7. [PyPSA Release Notes](https://docs.pypsa.org/latest/release-notes/) — version history
8. [PyPI pypsa](https://pypi.org/project/pypsa/) — version, license, dependencies
9. [v1.0 Migration Guide](https://docs.pypsa.org/latest/user-guide/v1-guide/) — breaking changes
10. [PR #946 SCLOPF fix](https://github.com/PyPSA/PyPSA/pull/946) — security-constrained bug fix
11. [PyPSA-stochUC](https://github.com/PPGS-Tools/PyPSA-stochUC) — external stochastic UC tool
12. [Brown et al. 2018 (arXiv)](https://arxiv.org/pdf/1707.09913) — foundational paper
13. `/home/joe/code/zge-workspace/grc-tech-evaluation/.claude/worktrees/eval/pypsa-2/evaluations/pypsa/notes/install-findings.md` — local evaluation notes
14. `/home/joe/code/zge-workspace/grc-tech-evaluation/.claude/worktrees/eval/pypsa-2/evaluations/pypsa/uv.lock` — resolved dependency tree (89 packages)

## Gaps and Uncertainties

- **Exact contributor count** not determined — GitHub contributors page was not fully scraped
- **AC OPF roadmap:** Unclear whether nonlinear OPF optimization is on the roadmap or considered out of scope by design
- **SCOPF performance at scale:** No benchmarks found for SCLOPF on large networks (1000+ buses); documentation warns about computational cost but provides no guidance on practical limits
- **Stochastic optimization maturity:** Two-stage stochastic programming was added recently (v1.1.0); unclear how battle-tested it is vs. the external PyPSA-stochUC package
- **Pandapower importer bug status:** No open GitHub issue was found for the v_mag_pu_set shape mismatch — unclear if it's been reported upstream
- **PTDF formulation details for optimization:** The PTDF-based LOPF formulation exists but documentation on when/how it's activated vs. the angle-based formulation needs verification during testing
- **Distributed slack in optimization:** Distributed slack is documented for power flow (`pf()`) but its availability in optimization (`optimize()`) needs testing
- **CVaR / risk-aware optimization:** Mentioned in release notes (v1.0.5 CVaR fix) but not prominently documented — needs exploration
