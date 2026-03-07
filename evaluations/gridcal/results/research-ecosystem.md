# GridCal (VeraGrid) — Research: Limitations & Ecosystem

## Key Findings

- **Project renamed from GridCal to VeraGrid in early 2026.** The PyPI package `GridCalEngine` (200k+ total downloads) is frozen at v5.4.1 with a deprecation notice. The new package is `veragridengine` (~23k total downloads as of March 2026). No compatibility shim exists; all import paths changed. ([install-findings.md](../notes/install-findings.md))
- **Extreme contributor concentration (bus factor = 1).** Santiago Penate Vera (SanPen) accounts for 9,522 of 13,551 total commits (70.3%). The next two contributors combined have ~1,700 commits. Only 30 contributors lifetime. ([GitHub contributors API](https://github.com/SanPen/GridCal))
- **OPF has open correctness issues.** Issue [#397](https://github.com/SanPen/GridCal/issues/397): "Optimal power flow not fulfilling the constraints" (ramp rate and min up/down time constraints ignored). Issue [#430](https://github.com/SanPen/GridCal/issues/430): "ACOPF does not handle well non-dispatchable generation results" (solver crashes). Both open as of March 2026.
- **SCOPF is under development, not production-ready.** Issue [#364](https://github.com/SanPen/GridCal/issues/364) describes a workflow for running SCOPF with numerical circuits, posted by the maintainer as a roadmap item (April 2025, still open).
- **No native SCUC/unit commitment formulation.** The tool has an OPF with "unit commitment" option but ramp constraints do not compile with it (per issue #397). No standalone SCUC solver exists.
- **Heavy dependency tree (30+ runtime dependencies)** including opencv-python, windpowerlib, pvlib, geopy, rdflib, websockets -- many unrelated to core power flow. Dependency version conflicts produce runtime warnings (urllib3/chardet).
- **License changed from LGPL to MPL-2.0** in v5.2.0 (November 2024). MPL-2.0 is permissive with file-level copyleft -- generally government-friendly.
- **Documentation is broad but shallow.** ReadTheDocs covers many topics conceptually but API reference is auto-generated with minimal method-level documentation. Many code examples reference the old `GridCalEngine` import paths.
- **Active development with rapid release cadence.** 2,434 commits in the last 12 months. 10 tagged releases in the last 24 months. CI runs on GitHub Actions (scheduled + push).
- **Commercial backing via eRoots Analytics** (Barcelona), which sells GSLV (C++ accelerated version) and consulting services. The primary developer is CTO of eRoots.

## Detailed Notes

### Repository Statistics

| Metric | Value | Source |
|--------|-------|--------|
| GitHub stars | 516 | [GitHub API](https://github.com/SanPen/GridCal) |
| GitHub forks | 123 | [GitHub API](https://github.com/SanPen/GridCal) |
| Open issues | 29 | [GitHub API](https://github.com/SanPen/GridCal) |
| Total contributors | 30 | [GitHub API](https://github.com/SanPen/GridCal) |
| License | MPL-2.0 | [GitHub API](https://github.com/SanPen/GridCal) |
| Created | 2016-01-13 | [GitHub API](https://github.com/SanPen/GridCal) |
| Last push | 2026-02-24 | [GitHub API](https://github.com/SanPen/GridCal) |
| Commits (last 12 months) | ~2,434 | [GitHub API](https://github.com/SanPen/GridCal) |
| PyPI downloads (GridCalEngine, total) | ~200,570 | [pepy.tech](https://pepy.tech/projects/gridcalengine) |
| PyPI downloads (VeraGridEngine, total) | ~22,736 | [pepy.tech](https://pepy.tech/projects/veragridengine) |
| Installed version (this eval) | 5.6.28 | [pyproject.toml](../pyproject.toml) |
| Latest PyPI version | 5.6.30 | [PyPI](https://pypi.org/project/VeraGridEngine/) |

### Contributor Concentration

| Contributor | Commits | Percentage |
|-------------|---------|------------|
| SanPen (Santiago Penate) | 9,522 | 70.3% |
| JosepFanals | 1,223 | 9.0% |
| Carlos-Alegre | 478 | 3.5% |
| benceszirbik | 466 | 3.4% |
| alexblancoeroots | 286 | 2.1% |
| All others (25 contributors) | ~1,576 | 11.6% |

Top 3 contributors account for 82.8% of all commits. Several of the top contributors have "eroots" or appear to be eRoots employees. The bus factor is effectively 1.

Source: [GitHub contributors API](https://github.com/SanPen/GridCal)

### Package Rename: GridCal to VeraGrid

The project was renamed in early 2026. Key details:

- **v5.4.0** (tagged 2026-02-02) is labeled "Last GridCal" on GitHub releases.
- **v5.6.20** (tagged 2026-02-02) is the first VeraGrid-branded release.
- The PyPI package `GridCalEngine` is frozen at 5.4.1 and prints a deprecation warning on every import.
- The deprecation message contains a typo: "witch" instead of "which".
- The new package is `veragridengine` (import as `VeraGridEngine`).
- No backward-compatibility shim or migration tool exists.
- All documentation URLs shifted from `gridcal.readthedocs.io` to `veragrid.readthedocs.io`.
- The GitHub repository URL remains `SanPen/GridCal` (not renamed, but README now says "VeraGrid").

Source: [install-findings.md](../notes/install-findings.md), [GitHub releases](https://github.com/SanPen/GridCal/releases)

### Release History (Last 24 Months)

| Version | Date | Key Changes |
|---------|------|-------------|
| 5.6.20 | 2026-02-02 | First VeraGrid-branded release |
| v5.4.0 | 2026-02-02 | "Last GridCal" -- final release under old name |
| v5.3.0 | 2025-01-08 | Better topology and ACDC power flow |
| v5.2.0 | 2024-11-11 | Relicensed to MPL-2.0 |
| v5.1.20 | 2024-07-23 | "End of Siroco" |
| v5.1.10 | 2024-05-31 | Bug fixes |
| v5.1.7 | 2024-04-16 | Bug fixes |
| 5.1.0 | 2024-04-01 | ACOPF and sparse profiles |
| 5.0.11 | 2024-01-05 | Added fluid transport problem |
| 5.0.2 | 2023-11-18 | "The great split" -- GridCal (GUI) / GridCalEngine (engine) |

The project releases frequently but versioning does not strictly follow semver (multiple 5.x.y releases with significant changes).

Source: [GitHub releases](https://github.com/SanPen/GridCal/releases)

### Open Issues Related to Evaluation Tests

**OPF correctness (A-3, A-5, A-6, A-9 relevant):**
- [#397](https://github.com/SanPen/GridCal/issues/397) — "Optimal power flow not fulfilling the constraints": Ramp up/down constraints and min up/down time constraints are not enforced. UC mode disables ramp constraints entirely. Load shedding cannot be disabled. (Open, created 2025-06-04)
- [#430](https://github.com/SanPen/GridCal/issues/430) — "ACOPF does not handle well non-dispatchable generation results": Solver crashes when generators are set to `enabled_dispatch = False`. (Open, created 2025-09-17, zero comments)
- [#413](https://github.com/SanPen/GridCal/issues/413) — "Function add_linear_branches_contingencies_formulation should be reviewed" (Open)

**SCOPF (A-9 relevant):**
- [#364](https://github.com/SanPen/GridCal/issues/364) — "Run SCOPF with numerical circuit": Maintainer-authored roadmap issue describing the intended SCOPF workflow. Not yet implemented. (Open, created 2025-04-14)

**Other evaluation-relevant issues:**
- [#328](https://github.com/SanPen/GridCal/issues/328) — "Add AC-PTDF to Linear Analysis" (Open, feature request)
- [#386](https://github.com/SanPen/GridCal/issues/386) — "Load shedding": Unable to disable automatic load shedding in OPF (Open)
- [#414](https://github.com/SanPen/GridCal/issues/414) — "PSSE Exporting is not working" (Open)
- [#425](https://github.com/SanPen/GridCal/issues/425) — "Three-phase transformers - Combining star and delta connections" (Open)

### Dependency Tree

VeraGridEngine v5.6.28 has 29 direct runtime dependencies:

**Core numerical:** numpy, scipy, pandas, numba, scikit-learn, autograd
**Optimization:** highspy (HiGHS), pulp (CBC/GLPK interface), pymoo (multi-objective)
**File I/O:** xlwt, xlrd, openpyxl, pyarrow, h5py, chardet, rdflib
**Visualization:** matplotlib, opencv-python
**Domain-specific:** windpowerlib, pvlib, geopy, pyproj
**Networking:** websockets, brotli
**Build system (in runtime deps):** setuptools, wheel

Notable concerns:
- **opencv-python** is a large compiled dependency (>50MB) unusual for a power systems engine. Its presence in runtime deps rather than optional is questionable.
- **windpowerlib and pvlib** are domain-specific renewable energy libraries -- useful for some workflows but heavy for core power flow use cases.
- **setuptools and wheel in runtime deps** is non-standard.
- **urllib3/chardet version conflict** produces warnings on every import.

Source: `importlib.metadata.distribution('veragridengine').requires` inside devcontainer

### Features Claimed (from README)

- AC/DC multi-grid power flow
- 3-phase unbalanced power flow and short circuit
- AC/DC multi-grid linear optimal power flow
- AC linear analysis (PTDF & LODF)
- AC linear net transfer capacity calculation
- AC+HVDC optimal net transfer capacity calculation
- AC/DC Stochastic power flow
- AC Short circuit
- AC Continuation power flow
- Contingency analysis (Power flow and LODF variants)
- Sigma analysis (one-shot stability analysis)
- Investments analysis
- Time series and snapshot for most simulations
- Import: PSSe .raw/.rawx, epc, dgs, matpower, pypsa, json, cim, cgmes
- Export: veragrid .xlsx/.veragrid/.json, cgmes, psse .raw/.rawx

**Not claimed:** SCUC, unit commitment as a standalone formulation, stochastic OPF (stochastic power flow exists but is Monte Carlo simulation, not stochastic programming), LMP decomposition, distributed slack OPF, lossy DC OPF.

Source: [GitHub README](https://github.com/SanPen/VeraGrid/blob/master/README.md)

### Documentation Quality

**Strengths:**
- ReadTheDocs site exists at [veragrid.readthedocs.io](https://veragrid.readthedocs.io)
- Grid modeling tutorial covers bus creation, line definitions, transformer connections
- Changelog is maintained in documentation
- README has inline code examples for common tasks (load file, power flow, save)
- FOSDEM 2026 talk provides architectural context

**Weaknesses:**
- API reference is auto-generated from docstrings with minimal method-level documentation
- Many tutorials still reference `GridCalEngine` import paths (pre-rename)
- No dedicated OPF tutorial or optimization example in official docs
- No example for contingency analysis via the API
- Documentation version on ReadTheDocs (5.6.20) may lag PyPI (5.6.30)
- The "old" docs at `gridcal-wip.readthedocs.io` still exist with v3.5.3 content, creating confusion

Source: [veragrid.readthedocs.io](https://veragrid.readthedocs.io), [gridcal.readthedocs.io](https://gridcal.readthedocs.io)

### Commercial Context and Institutional Backing

- **eRoots Analytics** (Barcelona, Spain) is the commercial entity behind GridCal/VeraGrid.
- Santiago Penate Vera is CTO of eRoots and primary developer.
- eRoots sells **GSLV** (Grid SoLVer), a C++ accelerated commercial variant claiming "10x faster" performance.
- Santiago previously worked at DNV, Indra, and Red Electrica (Spain's TSO).
- The project has presented at **LF Energy Summit 2024** (Brussels) and **FOSDEM 2026**.
- GridCal received a **Solar Impulse Efficient Solution** label (certification for clean/profitable solutions).
- Academic testimonials from CIRCE (Spain), Rensselaer Polytechnic Institute (USA), and CITCEA-UPC (Spain).
- No evidence of utility/ISO operational deployment or government procurement.
- Listed on the **Open Energy Modelling Initiative** forum.
- Has a Zenodo DOI for academic citation.
- Discord server exists for community chat.

Source: [eroots.tech](https://eroots.tech/veragrid-gslv), [LF Energy](https://lfenergy.org/lf-energy-summit-recap-and-video-vision-for-power-systems-planning-the-gridcal-example/), [FOSDEM 2026](https://fosdem.org/2026/schedule/event/7ARG7Y-making_of_a_modern_power_systems_software/)

### CI and Testing

- GitHub Actions CI exists with scheduled runs and push-on-master triggers.
- Most recent scheduled run: 2026-03-02 (success).
- Most recent push run: 2026-02-24 (success).
- `pytest` is listed as a runtime dependency (unusual -- should be dev-only).
- Test suite exists in `src/tests/` in the repo.
- No visible test coverage metrics or badges.
- Codacy badge is present but its current grade is unknown.

Source: [GitHub Actions](https://github.com/SanPen/GridCal/actions)

### Accessibility Observations (from install-findings.md)

- DC power flow is invoked via `SolverType.Linear` -- the terms "DC" or "DCPF" do not appear in enum names.
- `EngineType` enum contains `Bentayga`, `GSLV`, `NewtonPA`, `PGM`, `VeraGrid` -- not self-explanatory.
- Native MATPOWER .m file reading works well: `vge.open_file("case39.m")`.
- No `__version__` attribute on the package (must use `importlib.metadata`).

Source: [install-findings.md](../notes/install-findings.md)

## Sources

1. [GitHub: SanPen/GridCal](https://github.com/SanPen/GridCal) -- repository, issues, releases, contributors
2. [PyPI: VeraGridEngine](https://pypi.org/project/VeraGridEngine/) -- package metadata
3. [pepy.tech: VeraGridEngine downloads](https://pepy.tech/projects/veragridengine)
4. [pepy.tech: GridCalEngine downloads](https://pepy.tech/projects/gridcalengine)
5. [VeraGrid ReadTheDocs](https://veragrid.readthedocs.io) -- official documentation
6. [eRoots: VeraGrid & GSLV](https://eroots.tech/veragrid-gslv) -- commercial context
7. [LF Energy Summit: GridCal presentation](https://lfenergy.org/lf-energy-summit-recap-and-video-vision-for-power-systems-planning-the-gridcal-example/)
8. [FOSDEM 2026: Making of a modern power systems software](https://fosdem.org/2026/schedule/event/7ARG7Y-making_of_a_modern_power_systems_software/)
9. [GitHub Issue #397: OPF not fulfilling constraints](https://github.com/SanPen/GridCal/issues/397)
10. [GitHub Issue #430: ACOPF crashes with non-dispatchable gen](https://github.com/SanPen/GridCal/issues/430)
11. [GitHub Issue #364: Run SCOPF with numerical circuit](https://github.com/SanPen/GridCal/issues/364)
12. [evaluations/gridcal/notes/install-findings.md](../notes/install-findings.md) -- local install findings
13. [Open Energy Modelling Initiative: GridCal](https://forum.openmod.org/t/gridcal-project/2420)

## Gaps and Uncertainties

- **SCUC capability unclear.** The tool claims OPF with unit commitment option, but issue #397 reports constraints are not enforced. Needs hands-on testing to determine if a working SCUC formulation exists.
- **Stochastic OPF vs stochastic power flow.** The README claims "stochastic power flow" which is Monte Carlo simulation, not stochastic programming. Whether scenario-tree-based stochastic OPF is possible needs testing.
- **LMP extraction.** No documentation or issues mention LMP decomposition. Needs source code inspection to determine if shadow prices are accessible from OPF results.
- **Distributed slack.** The changelog mentions "distributed slack" was added in v3.5.8, but no documentation explains API usage. Needs testing.
- **PTDF extraction.** PTDF analysis is a listed feature and has its own driver. Quality and API accessibility need testing.
- **Contingency analysis API.** Feature is listed and has a driver, but no API example exists in docs. Need to verify if N-1 can be run programmatically without the GUI.
- **Discord community size unknown.** The Discord server exists but member count is not publicly visible.
- **GSLV relationship to VeraGrid unclear.** Whether GSLV uses proprietary code that could affect VeraGrid's open-source completeness is not documented.
- **Test coverage metrics unavailable.** No coverage badges or reports are published.
- **Lossy DC OPF.** Not mentioned anywhere in docs, changelog, or issues. Likely unsupported.
- **Custom constraint API.** No documentation on adding user-defined constraints to OPF. Needs source code investigation.
