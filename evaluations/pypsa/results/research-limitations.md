# PyPSA -- Research: Limitations & Ecosystem

Research conducted 2026-03-06 against PyPSA v1.1.2 (installed in evaluations/pypsa/).

## Key Findings

- PyPSA v1.1.2 has 87 transitive dependencies installed; core runtime requires numpy, scipy, pandas, xarray, linopy, matplotlib, geopandas, networkx, and highspy (open-source LP/MILP solver).
- No native MATPOWER `.m` file parser -- ingestion requires conversion through PYPOWER (`import_from_pypower_ppc`) or pandapower (`import_from_pandapower_net`). The `matpowercaseframes` package (v2.0.1) is installed alongside, which can parse `.m` files into DataFrames for bridging.
- AC power flow uses Newton-Raphson with flat start only; no warm-starting, and convergence is not guaranteed. Documentation explicitly acknowledges NR may fail even for solvable systems.
- No native nonlinear AC OPF -- optimization is limited to linear (LOPF) and mixed-integer linear (MILP) formulations. AC OPF is approximated via iterative LOPF + nonlinear PF (`optimize_and_run_non_linear_powerflow`).
- Security-constrained LOPF (SCLOPF) exists but has an open, confirmed intermittent bug (issue #1356) where post-contingency flows exceed thermal limits by up to 7%.
- Unit commitment for StorageUnits is broken in v1.1.2 (issue #1602, opened 2026-03-04) -- setting `committable=True` on StorageUnits crashes `create_model()`.
- ArrowStringArray incompatibility (issue #1585) can silently break `optimize()` after NetCDF round-trip on pandas >= 2.0.
- Extremely active release cadence: 12 releases from 2025-03-03 to 2026-02-23, including v1.0.0 (2025-10-14) as a major milestone.
- Large, research-driven community: 1,887 GitHub stars, 614 forks, 104 contributors, 97 open issues. Used by ACER, IEA, Shell, TransnetBW, ENTSO-E, and 50+ universities.
- MIT license throughout the stack (PyPSA, linopy, highspy). No copyleft or proprietary dependencies in the core chain.

## Detailed Notes

### MATPOWER Case File Import

PyPSA cannot directly read MATPOWER `.m` files. The supported import paths are:

1. **PYPOWER ppc dict**: `n.import_from_pypower_ppc(ppc)` accepts a PYPOWER-format Python dict. PYPOWER's format is nearly identical to MATPOWER's internal struct, but the `.m` file must first be parsed into this dict.
2. **pandapower net**: `n.import_from_pandapower_net(net)` converts a pandapower network object, which itself can load MATPOWER cases via `pandapower.converter.from_mpc()`.
3. **matpowercaseframes**: The package `matpowercaseframes==2.0.1` is installed in the evaluation environment. It parses `.m` files into pandas DataFrames, which can then be assembled into a PYPOWER ppc dict manually.

The original feature request is GitHub issue #21 (opened 2016, still open as of this writing).

Sources:
- [GitHub issue #21: Can PyPSA read MATPOWER case files?](https://github.com/PyPSA/PyPSA/issues/21)
- [Google Groups: MATPOWER case file conversion](https://groups.google.com/g/pypsa/c/ikl2ej-Ifz0)

### AC Power Flow (Newton-Raphson)

PyPSA implements full nonlinear AC power flow via `n.pf()` using Newton-Raphson iteration. Key characteristics:

- **Initial guess**: Flat start only (all angles = 0, all |V| = 1 p.u.). No option for warm-starting from a previous solution.
- **Convergence**: Not guaranteed. The troubleshooting docs state: "Newton-Raphson is known not to converge even for solvable problems, or the flat solution PyPSA uses as an initial guess is too far from the correction solution."
- **Workaround for non-convergence**: Docs recommend iterative load ramping -- reduce all P/Q setpoints to 10%, solve, use result as seed for 20%, etc.
- **DC network PF**: Issue #40 (open since 2018) notes that DC network power flow requires a workaround of pretending it is an AC network with zero reactance.
- **Transformer tap positions**: Issue #444 (open since 2022) reports that transformer `tap_position` is not relative to neutral tap, yielding different results from PowerFactory.

Sources:
- [PyPSA Troubleshooting docs (v0.24.0)](https://docs.pypsa.org/v0.24.0/troubleshooting.html)
- [Power Flow docs (v1.0.5)](https://docs.pypsa.org/v1.0.5/user-guide/power-flow/)
- [GitHub issue #40: DC network PF workaround](https://github.com/PyPSA/PyPSA/issues/40)
- [GitHub issue #444: Transformer tap_position](https://github.com/PyPSA/PyPSA/issues/444)

### Optimization Capabilities and Limitations

**What PyPSA can do:**
- Linear Optimal Power Flow (LOPF) with four formulations: `angles`, `cycles`, `kirchhoff`, `ptdf`
- Unit commitment (MILP) with binary commitment variables, min up/down times, start-up/shut-down costs, ramp limits
- Security-Constrained LOPF (SCLOPF) using Branch Outage Distribution Factors (BODF)
- Capacity expansion planning with multi-period investment
- Two-stage stochastic optimization (new in v1.0)
- Rolling-horizon optimization
- Modelling-to-Generate-Alternatives (MGA)

**What PyPSA cannot do natively:**
- **Nonlinear AC OPF**: No direct ACOPF formulation. The method `optimize_and_run_non_linear_powerflow` iterates between LOPF and NR power flow but this is an approximation, not a true ACOPF.
- **Quadratic cost curves in OPF**: Linopy supports QP but PyPSA's optimization interface exposes only linear (marginal_cost) and piecewise-linear costs. Issue #1473/#1603 request piecewise linear costs as a feature.
- **Full N-1 contingency analysis at scale**: SCLOPF is computationally expensive (product of lines x outages x snapshots). Approximation via security margins is the practical alternative.

**PTDF formulation**: Fully supported as one of four LOPF formulations. The `kirchhoff` formulation is recommended as default (3x faster than `angles` on average, up to 20x on large networks).

Sources:
- [Power System Optimization docs](https://pypsa.readthedocs.io/en/latest/optimal_power_flow.html)
- [Contingencies docs](https://docs.pypsa.org/latest/user-guide/optimization/contingencies/)
- [Features page](https://docs.pypsa.org/stable/home/features/)

### Open Bugs Relevant to Evaluation Tests

| Issue | Title | Status | Impact on Evaluation |
|-------|-------|--------|---------------------|
| [#1356](https://github.com/PyPSA/PyPSA/issues/1356) | SCLOPF intermittently allows post-contingency line overloads | Open (2025-09-12) | Contingency analysis tests may produce incorrect results; overloads up to 7% observed |
| [#1602](https://github.com/PyPSA/PyPSA/issues/1602) | StorageUnit committable=True crashes create_model() | Open (2026-03-04) | Unit commitment tests with storage units will fail on v1.1.2 |
| [#1585](https://github.com/PyPSA/PyPSA/issues/1585) | ArrowStringArray from NetCDF breaks optimize() | Open (2026-03-02) | Network save/load round-trip can silently corrupt optimization |
| [#1607](https://github.com/PyPSA/PyPSA/issues/1607) | ConsistencyError on p_min_pu = p_max_pu | Open (2026-03-05) | Edge case in generator limits |
| [#40](https://github.com/PyPSA/PyPSA/issues/40) | DC network n.pf() requires AC workaround | Open (2018-07-31) | DC power flow tests need workaround |
| [#1555](https://github.com/PyPSA/PyPSA/issues/1555) | Memory spikes x10 if shapes are in network | Open (2024-08-16) | Scalability tests may be affected if geographic shapes are present |
| [#1282](https://github.com/PyPSA/PyPSA/issues/1282) | Conflicts in ramping during start-up with min part loads | Open (2025-07-09) | UC ramp constraint edge cases |

### Ecosystem Packages

**Official PyPSA organization packages** (maintained by PyPSA team at github.com/pypsa):

| Package | Purpose | Stars |
|---------|---------|-------|
| [PyPSA](https://github.com/PyPSA/PyPSA) | Core power system analysis library | 1,887 |
| [PyPSA-Eur](https://github.com/PyPSA/pypsa-eur) | European energy system model | ~505 |
| [PyPSA-USA](https://github.com/PyPSA/pypsa-usa) | US energy system model | N/A |
| [linopy](https://github.com/PyPSA/linopy) | Linear optimization with labeled arrays (xarray-based) | N/A |
| [atlite](https://github.com/PyPSA/atlite) | Renewable energy resource assessment | N/A |
| [powerplantmatching](https://github.com/PyPSA/powerplantmatching) | Power plant database matching | N/A |

**Related community projects:**
- [PyPSA-Earth](https://github.com/pypsa-meets-earth/pypsa-earth) -- global energy system model (separate org)
- [Open Energy Transition (OET)](https://openenergytransition.org/tools.html) -- commercial support and consulting

**Key dependency**: linopy v0.6.4 is the optimization modeling layer. It interfaces with solvers via their Python APIs. HiGHS (highspy v1.13.1) is bundled as the default open-source solver.

Sources:
- [PyPSA GitHub organization](https://github.com/pypsa)
- [PyPSA ecosystem overview](https://pypsa.org/)
- [OET tools page](https://openenergytransition.org/tools.html)

### Community Size and Adoption

**GitHub metrics** (as of 2026-03-06):
- Stars: 1,887
- Forks: 614
- Contributors: 104
- Watchers: 68
- Open issues: 97 (plus 23 open PRs)
- Dependents: 290 packages
- Total commits: 3,233

**Communication channels:**
- Discord server (active)
- Google Groups mailing list (pypsa)
- OpenMod forum

**Notable institutional users:**
- Government/regulatory: IEA, ACER (EU), GIZ (Germany), Canada Energy Regulator
- TSOs: TransnetBW, ONTRAS, Austrian Power Grid (APG), TenneT, ENTSO-E
- Industry: Shell, Saudi Aramco, ISA (Colombia)
- Research: 27+ universities across 15+ countries, JRC (EU Commission), Fraunhofer institutes

The user base is predominantly European and research-oriented. North American adoption is growing (PyPSA-USA, Stanford, Canada Energy Regulator) but is less established than the European community.

Sources:
- [PyPSA Users page](https://docs.pypsa.org/latest/home/users/)
- [GitHub repo stats](https://github.com/PyPSA/PyPSA)

### Documentation Quality

PyPSA v1.0 (October 2025) included a complete documentation rewrite, moving from Sphinx/ReadTheDocs to MkDocs Material at <https://docs.pypsa.org>.

**Strengths:**
- Comprehensive component reference with all attributes documented in tables
- Multiple worked examples (Jupyter notebooks) covering PF, OPF, UC, sector coupling
- Migration guide for v0.x to v1.0 API changes
- Mathematical formulations provided for power flow and optimization

**Weaknesses:**
- API reference is auto-generated (mkdocstrings) -- some methods lack docstrings or have sparse parameter descriptions
- Troubleshooting section is limited (last substantive update was v0.24.0 era)
- No formal validation report comparing PyPSA results against commercial tools (PSSE, PowerWorld) or reference implementations
- The v1.0 API introduced a new "Components Class" alongside the legacy API; both are documented but the dual-API situation creates confusion

Sources:
- [PyPSA docs home](https://docs.pypsa.org/latest/)
- [v1.0 migration guide](https://docs.pypsa.org/latest/user-guide/v1-guide/)
- [Troubleshooting (v0.24.0)](https://docs.pypsa.org/v0.24.0/troubleshooting.html)

### Release History

PyPSA has maintained a rapid release cadence. Recent releases:

| Version | Date | Significance |
|---------|------|-------------|
| v1.1.2 | 2026-02-23 | Bug fixes (CPLEX compat, statistics) |
| v1.1.1 | 2026-02-23 | Docs fixes (same day as 1.1.2) |
| v1.1.0 | 2026-02-17 | Temporal clustering, split capital/FOM costs, pandas v3 compat |
| v1.0.7 | 2026-01-13 | Bug fixes |
| v1.0.6 | 2025-12-22 | Bug fixes |
| v1.0.5 | 2025-12-04 | Bug fixes |
| v1.0.4 | 2025-11-21 | Bug fixes |
| v1.0.3 | 2025-11-06 | Bug fixes |
| v1.0.2 | 2025-10-24 | Bug fixes |
| v1.0.1 | 2025-10-20 | Bug fixes |
| v1.0.0 | 2025-10-14 | Major release: new docs, Components API, stochastic optimization, CVaR |
| v1.0.0rc1 | 2025-08-15 | Release candidate |
| v0.35.2 | 2025-08-15 | Last v0.x maintenance release |

The project has been active since 2016 (first commit) with no extended periods of inactivity. The v0.x to v1.0 transition is the largest breaking change in the project's history.

Sources:
- [GitHub releases](https://github.com/PyPSA/PyPSA/releases)
- [PyPI](https://pypi.org/project/pypsa/)

### License and Supply Chain

- **PyPSA**: MIT
- **linopy**: MIT
- **highspy** (HiGHS solver): MIT
- **numpy, scipy, pandas, xarray**: BSD-3-Clause
- **networkx**: BSD-3-Clause
- **matplotlib**: PSF (BSD-compatible)
- **geopandas, shapely**: BSD-3-Clause

No copyleft (GPL/LGPL) dependencies in the core runtime chain. The entire stack is permissively licensed.

Total dependency count: 87 packages installed in the evaluation environment (including transitive dependencies). Notable large dependencies include geopandas/shapely (geographic features), plotly/pydeck (visualization), and the Google Cloud Storage SDK (for cloud path support).

## Sources

1. [PyPSA GitHub repository](https://github.com/PyPSA/PyPSA) -- stars, forks, issues, releases
2. [PyPSA documentation](https://docs.pypsa.org/latest/) -- features, API, user guide
3. [PyPSA Power Flow docs](https://docs.pypsa.org/v1.0.5/user-guide/power-flow/) -- NR implementation details
4. [PyPSA Optimization docs](https://pypsa.readthedocs.io/en/latest/optimal_power_flow.html) -- LOPF, UC, SCLOPF
5. [PyPSA Contingencies docs](https://docs.pypsa.org/latest/user-guide/optimization/contingencies/) -- SCLOPF implementation
6. [PyPSA Troubleshooting (v0.24.0)](https://docs.pypsa.org/v0.24.0/troubleshooting.html) -- NR convergence guidance
7. [PyPSA Features page](https://docs.pypsa.org/stable/home/features/) -- capability summary
8. [PyPSA Users page](https://docs.pypsa.org/latest/home/users/) -- institutional adopters
9. [PyPSA v1.0 migration guide](https://docs.pypsa.org/latest/user-guide/v1-guide/) -- breaking changes
10. [GitHub issue #21](https://github.com/PyPSA/PyPSA/issues/21) -- MATPOWER import request
11. [GitHub issue #40](https://github.com/PyPSA/PyPSA/issues/40) -- DC network PF workaround
12. [GitHub issue #1356](https://github.com/PyPSA/PyPSA/issues/1356) -- SCLOPF flaky overloads
13. [GitHub issue #1555](https://github.com/PyPSA/PyPSA/issues/1555) -- Memory spike with shapes
14. [GitHub issue #1585](https://github.com/PyPSA/PyPSA/issues/1585) -- ArrowStringArray breaks optimize
15. [GitHub issue #1602](https://github.com/PyPSA/PyPSA/issues/1602) -- StorageUnit committable crash
16. [PyPSA arXiv paper (1707.09913)](https://arxiv.org/abs/1707.09913) -- original publication
17. [PyPSA PyPI page](https://pypi.org/project/pypsa/) -- package metadata
18. [Open Energy Transition tools](https://openenergytransition.org/tools.html) -- ecosystem overview
19. Installed package inspection: `/workspace/evaluations/pypsa/.venv/` -- dependency tree, version verification

## Gaps and Uncertainties

- **ACOPF accuracy**: No published validation of PyPSA's iterative LOPF+NR approach against true ACOPF solvers (Ipopt, KNITRO). Need to test during evaluation whether the approximation converges and how far results deviate from reference ACOPF solutions.
- **MATPOWER import fidelity**: Unclear whether conversion through pandapower or matpowercaseframes preserves all data fields (cost curves, branch limits, generator limits). Must verify during Gate tests.
- **Large network performance**: No published benchmarks for 10k-bus networks. The ACTIVSg 10k scalability test will be the first empirical measurement for this evaluation.
- **SCLOPF reliability**: Issue #1356 reports intermittent failures (1-in-30 runs). Need to determine if this affects evaluation results or is solver-seed-dependent.
- **Solver compatibility**: HiGHS is the bundled solver. Evaluation protocol also requires testing with SCIP, Ipopt, and GLPK. PyPSA's linopy layer should support these but this needs verification.
- **Reactive power modeling in LOPF**: The linear OPF formulations ignore reactive power entirely. If evaluation tests require Q-flow results from optimization, PyPSA cannot provide them without the iterative NR post-processing step.
- **pandapower bridge version**: pandapower v3.4.0 is installed. Need to verify its MATPOWER converter handles the specific ACTIVSg case formats used in the evaluation.
