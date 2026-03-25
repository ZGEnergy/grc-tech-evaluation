---
tool: matpower
research_date: 2026-03-24
focus: Known limitations, open issues, ecosystem, community size, documentation quality, release history
version_evaluated: "8.1"
prior_research: 2026-03-13
---

# MATPOWER — Limitations, Ecosystem & Community Research

## 1. Known Limitations

### 1.1 MOST Limited to DC Network Model

MOST (MATPOWER Optimal Scheduling Tool) provides multi-period OPF, unit commitment, and storage
optimization but is restricted to DC power flow network constraints. The MOST README states that
"some work has been done on an AC implementation, but it is not yet ready for release." This has
been the case since MOST's inception (~2014). Multi-period AC OPF is not available in the open-source
MATPOWER ecosystem.

**Evaluation impact:** Tests A-5 (SCUC), A-6 (SCED), and A-12 (multi-period DCOPF with storage)
use DC formulations and are unaffected. However, any future requirement for AC multi-period
optimization would be unmet.

*Source: [MOST README](https://github.com/MATPOWER/most/blob/master/README.md)*

### 1.2 No Native SCOPF Function

MATPOWER does not ship a standalone security-constrained OPF (SCOPF) function. MOST can model
contingency states with probability weighting in a stochastic framework, but there is no turnkey
`runSCOPF()` or equivalent. Users must either:
- Use MOST's contingency/scenario framework (DC only)
- Manually construct contingency constraints via the MP-Opt-Model Extension API
- Script iterative contingency screening by running `rundcopf()` in a loop with LODF-based
  post-contingency flow checks

**Evaluation impact:** Test A-9 (SCOPF) will require either the MOST approach or manual constraint
assembly, both of which are non-trivial. This is a qualified pass scenario at best.

*Source: Open issue survey; MATPOWER User's Manual lacks SCOPF section*

### 1.3 Scalability of MOST Model Construction

GitHub issue [MOST #7](https://github.com/MATPOWER/most/issues/7) documents that building a MOST
model for 8,760 periods (1 year) took 7 hours on a high-performance cluster before solving. The
bottleneck is in `add_named_set` and `params_lin_constraint` routines. A user-contributed patch
achieved ~20% speedup by optimizing sparse matrix operations. Workarounds include building
time-sliced sub-models and connecting them.

**Evaluation impact:** Suite C scalability tests use 24-hour horizons on MEDIUM (10k buses), which
is far smaller than 8,760 periods. This limitation is unlikely to affect Phase 1 but is relevant
for production deployment at annual planning horizons.

*Source: [MOST issue #7](https://github.com/MATPOWER/most/issues/7)*

### 1.4 No Native CSV Import

MATPOWER's `loadcase()` supports only `.m` and `.mat` files natively, plus PSS/E `.raw` via
`psse2mpc()`. There is no built-in CSV reader. Time-series data for MOST (load profiles, wind/solar
forecasts, storage parameters) must be loaded via custom MATLAB/Octave scripts.

**Evaluation impact:** Tests requiring augmented data (A-5, A-6, A-12) will need custom loading
scripts to read CSV files from `data/timeseries/case39/`.

### 1.5 No Built-In Parallel Computation

MATPOWER has no native parallel execution support. MATLAB users can wrap calls in `parfor`
(requires the commercial Parallel Computing Toolbox), but this has known issues with MATPOWER's
use of global variables. GNU Octave's `parallel` package is not equivalent and is not recommended
by the MATPOWER team.

**Evaluation impact:** Scalability tests (Suite C) will reflect single-threaded performance only.

### 1.6 No Distributed Slack in OPF (Standard API)

MATPOWER issue [#136](https://github.com/MATPOWER/matpower/issues/136) (open since 2022) requests
distributed slack bus support for power flow. The `makePTDF()` function accepts a custom slack
distribution vector, but the standard OPF formulation uses a single slack bus. Distributed slack
OPF would require custom constraint injection.

**Evaluation impact:** Test A-11 (distributed slack OPF) will require workaround construction.

*Source: [Issue #136](https://github.com/MATPOWER/matpower/issues/136)*

### 1.7 No LMP Decomposition API

MATPOWER's OPF produces nodal LMPs (shadow prices on bus power balance constraints), but does
not natively decompose them into energy, congestion, and loss components. Users must extract
shadow prices from the optimization result and perform the decomposition manually using PTDFs
and constraint multipliers.

**Evaluation impact:** Test A-10 (lossy DC OPF / LMP decomposition) will require manual
post-processing of solver output.

### 1.8 MOST Pro — Commercial Extension

The MATPOWER 8.1 release notes mention "MOST Pro 1.4.1" as a paid upgrade that adds DC
transmission line support. MOST Pro is not open-source and is available only by contacting
info@matpower.org. The open-source MOST 1.3.1 included with MATPOWER 8.1 does not include
DC line support.

**Evaluation impact:** Per protocol, only open-source packages are evaluated. MOST Pro
capabilities are excluded.

*Source: [MATPOWER 8.1 release notes](https://github.com/MATPOWER/matpower/releases/tag/8.1)*

### 1.9 Octave vs. MATLAB Compatibility

MATPOWER officially supports both MATLAB and GNU Octave. However, some edge cases exist:
- Issue [#270](https://github.com/MATPOWER/matpower/issues/270): `test_matpower` unrecognized
  field name "optimstatus" under MATLAB (fixed in 8.1)
- HiGHS solver integration works on both platforms as of 8.1
- Three-phase features are proof-of-concept and may have platform-specific behavior
- Performance differs: MATLAB's JIT compiler is generally faster than Octave's interpreter

**Evaluation impact:** Evaluation uses GNU Octave (devcontainer). Performance measurements
reflect Octave execution speed, not MATLAB.

## 2. Open Issues Relevant to Evaluation Tests

| Issue | Repo | Relevance | Status |
|-------|------|-----------|--------|
| [#136](https://github.com/MATPOWER/matpower/issues/136) — Distributed slack bus PF | matpower | A-11 (distributed slack OPF) | Open (since 2022) |
| [#104](https://github.com/MATPOWER/matpower/issues/104) — Extend zonal reserves | matpower | A-5 (SCUC reserve requirements) | Open (since 2020) |
| [#24](https://github.com/MATPOWER/matpower/issues/24) — Rate B/C not in OPF | matpower | Emergency ratings for SCOPF | Open (since 2017) |
| [#127](https://github.com/MATPOWER/matpower/issues/127) — makePTDF ext2int error | matpower | PTDF extraction (B-5) | Open (since 2021) |
| [#279](https://github.com/MATPOWER/matpower/issues/279) — CPF stuck in loop | matpower | Not directly tested in Phase 1 | Open (since 2025) |
| [MOST #5](https://github.com/MATPOWER/most/issues/5) — DC transmission lines | most | Multi-period with DC lines | Open (since 2019) |
| [MOST #50](https://github.com/MATPOWER/most/issues/50) — Downward reserve | most | Reserve requirements in UC | Open (since 2025-03) |
| [MOST #52](https://github.com/MATPOWER/most/issues/52) — Update to mp.opt_model | most | Internal refactoring to new API | Open (since 2025-06) |
| [#269](https://github.com/MATPOWER/matpower/issues/269) — Update to mp.opt_model | matpower | Internal refactoring to new API | Open (since 2025-06) |

## 3. Ecosystem Packages

MATPOWER's ecosystem is a set of modular packages maintained under the MATPOWER GitHub organization,
all by the same core team (primarily Ray Zimmerman at Cornell / PSERC).

| Package | Description | Version | Stars | Forks | License | Last Push |
|---------|-------------|---------|-------|-------|---------|-----------|
| [matpower](https://github.com/MATPOWER/matpower) | Core PF/OPF engine | 8.1 | 545 | 173 | BSD 3-Clause | 2026-03-11 |
| [most](https://github.com/MATPOWER/most) | Multi-period scheduling, UC, storage | 1.3.1 | 39 | — | BSD 3-Clause | 2026-02-16 |
| [mp-opt-model](https://github.com/MATPOWER/mp-opt-model) | Optimization modeling layer | 5.0 | 10 | — | BSD 3-Clause | 2025-12-11 |
| [mips](https://github.com/MATPOWER/mips) | Interior point solver | 1.5.2 | 16 | — | BSD 3-Clause | 2025-07-12 |
| [mptest](https://github.com/MATPOWER/mptest) | Unit testing framework | — | 1 | — | BSD 3-Clause | 2025-07-08 |
| [mp-element](https://github.com/MATPOWER/mp-element) | New element modeling layer (merged into matpower 8.0) | — | 4 | — | BSD 3-Clause | 2023-02-02 |

### Additional MATPOWER Organization Packages

| Package | Description | Stars | Last Push |
|---------|-------------|-------|-----------|
| [mx-se](https://github.com/MATPOWER/mx-se) | State estimation (contributed by Rui Bo) | 10 | 2024-05-14 |
| [mx-sdp_pf](https://github.com/MATPOWER/mx-sdp_pf) | SDP relaxation of power flow (Dan Molzahn) | 7 | 2024-05-14 |
| [mx-syngrid](https://github.com/MATPOWER/mx-syngrid) | Synthetic grid creation | 14 | 2024-05-21 |
| [mx-maxloadlim](https://github.com/MATPOWER/mx-maxloadlim) | OPF extension for max loadability limits | 1 | 2024-05-14 |
| [mx-reduction](https://github.com/MATPOWER/mx-reduction) | Network reduction toolbox | 0 | 2019-06-20 |
| [mx-simulink_matpower](https://github.com/MATPOWER/mx-simulink_matpower) | Simulink interface | 1 | 2024-05-14 |
| [mpsim](https://github.com/MATPOWER/mpsim) | Simulator framework | 4 | 2024-05-14 |
| [mpng](https://github.com/MATPOWER/mpng) | MATPOWER Natural Gas extension | 11 | 2023-09-13 |
| [wy-wind-model](https://github.com/MATPOWER/wy-wind-model) | Wind model for MOST | 1 | 2022-11-16 |
| [tpc-form](https://github.com/MATPOWER/tpc-form) | Approx PF in transformed polar coordinates | 0 | 2025-11-12 |
| [matpower-extras](https://github.com/MATPOWER/matpower-extras) | Contributed/unsupported code | 12 | 2025-07-13 |

### Third-Party Ecosystem

- **[matpower-pip](https://github.com/yasirroni/matpower-pip)** — Python wrapper via oct2py,
  installable via `pip install matpower[octave]`. Third-party, not evaluated.
- **SimulinkMATPOWER** — Simulink interface, included in MATPOWER Extras (requires MATLAB +
  Simulink). Not relevant for Octave-based evaluation.
- **matpowercaseframes** — Python package for reading/writing MATPOWER case files as DataFrames.
  Third-party, not evaluated.
- **GMLC-TDC/MATPOWER-wrapper** — HELICS co-simulation wrapper for transmission system
  simulation. Used for ISO-DSO co-simulation research.

### Dependency Composition

MATPOWER's dependency tree is minimal and entirely self-contained:
- MIPS (bundled) — only solver that ships with MATPOWER
- MP-Opt-Model (bundled) — optimization abstraction layer
- MP-Test (bundled) — testing framework
- MOST (bundled) — scheduling/UC extension

External optional solvers: IPOPT, GLPK, HiGHS, Knitro, CPLEX, Gurobi, MOSEK, SDPT3, SeDuMi.
The evaluation devcontainer provides IPOPT, GLPK, and HiGHS.

**Supply chain finding:** All bundled dependencies are BSD 3-Clause licensed and maintained by
the same team. No transitive dependency risk. External solvers have their own licenses (IPOPT:
EPL-2.0; GLPK: GPL-3.0; HiGHS: MIT).

## 4. Community Size

| Metric | Value | Date |
|--------|-------|------|
| GitHub stars | 545 | 2026-03-24 |
| GitHub forks | 173 | 2026-03-24 |
| Contributors (GitHub) | 17 | 2026-03-24 |
| Open issues (non-PR) | 16 | 2026-03-24 |
| Closed issues (non-PR) | ~260 | 2026-03-24 (estimated from pagination) |
| Annual downloads | 22,000+ | per matpower.org/about (updated figure) |
| Google Scholar citations | 750+ per year (as of 2018) | per matpower.org/about |
| Countries using | 100+ | per matpower.org/about |

### Community Characteristics

- **Small core team, large user base:** 17 GitHub contributors but 40,000+ annual downloads.
  The project is primarily maintained by Ray Zimmerman (Cornell/PSERC) with occasional
  contributions from the community.
- **Academic-dominant user base:** Widely used in power systems education and research at
  universities worldwide. Referenced extensively in IEEE/PSCC conference papers.
- **Government and industry use:** matpower.org lists Cornell, IIT, ANL (Argonne National Lab),
  University of Washington, and RTE (French TSO) as users.
- **Low issue volume:** Only 14 open issues across 9+ years of GitHub hosting suggests either
  high code quality or low community engagement on GitHub (likely both — much support happens
  via the MATPOWER mailing list, not GitHub issues).
- **Mailing list activity:** The primary support channel is the MATPOWER discussion mailing list,
  not GitHub. Issue counts underrepresent community engagement.

## 5. Documentation Quality

### Available Documentation

| Document | Format | Quality |
|----------|--------|---------|
| [MATPOWER User's Manual](https://matpower.org/docs/MATPOWER-manual.pdf) | PDF (247 pages) | Comprehensive; covers data format, PF, OPF, extensions, options; not yet fully updated for 8.x flexible framework |
| [MATPOWER Developer's Manual](https://matpower.org/doc/) | HTML (Sphinx) | New in 8.0; covers MP-Core architecture, extension API |
| [MATPOWER Reference Manual](https://matpower.org/doc/) | HTML (Sphinx) | Function and class reference; generated from source |
| [MOST User's Manual](https://matpower.org/docs/MOST-manual.pdf) | PDF | Covers MOST problem formulation, data structures, examples |
| [MP-Opt-Model User's Manual](https://matpower.org/doc/) | HTML | Optimization modeling API documentation |
| Technical Notes (TN1-TN5) | PDF | Detailed mathematical derivations |
| How-To Guides | HTML | Practical guides (adding constraints, creating elements, three-phase PF) |
| In-code help | `help <function>` | Every function has a help block |

### Documentation Strengths

- **Mathematical rigor:** Technical notes provide full derivations of power flow equations,
  derivatives, and OPF formulations. Useful for verification against reference results.
- **Comprehensive options reference:** All solver and algorithm options documented in the
  User's Manual.
- **Case file format specification:** Detailed specification of the MATPOWER case format
  (version 1 and 2), enabling third-party interoperability.
- **DOI-registered releases:** Zenodo DOIs for reproducible research citation.

### Documentation Gaps

- **User's Manual not fully updated for 8.x:** The flexible framework (`run_pf`, `run_opf`)
  is documented in the Developer's Manual but the User's Manual still primarily covers the
  legacy framework. Users must consult multiple documents.
- **MOST documentation is sparse:** The MOST manual exists but lacks worked examples for
  common workflows (e.g., "add storage to a multi-period UC"). Users often resort to reading
  test scripts in `most/lib/t/` for guidance.
- **No tutorial/quickstart for Octave users:** Documentation assumes MATLAB. Octave-specific
  differences (e.g., package loading, solver availability) are not covered.
- **Extension API examples are minimal:** The 8.x Extension API is powerful but the how-to
  guides cover only basic cases. Complex extensions (e.g., custom element types with new
  state variables) require reading the Developer's Manual and MP-Core source code.

## 6. Release History

| Version | Date | Cadence |
|---------|------|---------|
| 8.1 | 2025-07-12 | 14 months after 8.0 |
| 8.0 | 2024-05-17 | 17 months after 8.0b1 |
| 8.0b1 | 2022-12-23 | 27 months after 7.1 |
| 7.1 | 2020-10-08 | 16 months after 7.0 |
| 7.0 | 2019-06-21 | 8 months after 7.0b1 |
| 7.0b1 | 2018-11-01 | — |

### Release Cadence Analysis

- **Irregular cadence:** 8-27 months between releases. No fixed release schedule.
- **Active development:** Last push to `master` was 2026-03-11 (2 days before research date).
  The project is actively maintained.
- **Long-lived major versions:** Major versions (7.x, 8.x) span multiple years. The 8.0 rewrite
  took 2+ years from beta to release.
- **Stability-oriented:** Long release cycles suggest emphasis on stability over rapid feature
  delivery. Suitable for production/research use where API stability matters.

### MOST Release History

| Version | Date | Notes |
|---------|------|-------|
| 1.3.1 | 2025-07-12 | Bundled with MATPOWER 8.1 |
| 1.3 | 2024-05-15 | TLMP calculation, improved speed/memory |
| 1.2 | 2022-12-13 | — |
| 1.1 | 2020-10-08 | — |
| 1.0.2 | 2019-06-20 | — |

MOST releases are synchronized with MATPOWER major releases.

## 7. Evaluation-Specific Risk Assessment

| Test | Risk Level | Key Finding |
|------|-----------|-------------|
| A-1 (DCPF) | Low | Core capability since 1997 |
| A-2 (ACPF) | Low | Core capability; multiple solvers available |
| A-3 (DC OPF) | Low | Core capability; cost curves and line limits well-supported |
| A-4 (AC feasibility) | Low | Standard workflow: solve DC OPF, then run ACPF on dispatch |
| A-5 (SCUC) | Medium | Via MOST; requires non-trivial setup; DC network model only |
| A-6 (SCED) | Medium | Via MOST; commitment schedule from A-5 can be fixed |
| A-9 (SCOPF) | High | No native SCOPF; requires MOST contingency framework or manual constraint construction |
| A-10 (Lossy DC OPF) | High | Loss approximation available but LMP decomposition requires manual post-processing |
| A-11 (Distributed slack) | High | Not natively supported in OPF; requires workaround via PTDF-based reformulation |
| A-12 (Multi-period DCOPF + storage) | Medium | Via MOST; storage and multi-period are supported but setup is manual |
| B-1 (Custom constraints) | Low | MP-Opt-Model Extension API well-documented |
| B-3 (Contingency analysis) | Low | Scriptable via loop over `rundcpf()` with branch removal |
| B-4 (Stochastic scenarios) | Medium | MOST supports stochastic scenarios; setup is complex |
| B-5 (PTDF/LODF) | Low | `makePTDF()` is a core function |

## 8. Gaps and Uncertainties

- **Citation count:** matpower.org states "over 750 citations in 2018." Current citation count
  is likely significantly higher but could not be verified via automated web search (Google
  Scholar blocks scraping). The primary paper (Zimmerman et al., 2011, IEEE TPWRS) has a
  Zenodo DOI (10.5281/zenodo.3236535) for version-neutral citation.
- **Download count discrepancy:** matpower.org/about states "more than 22,000 times per year"
  (as of 2026-03-24 fetch). A prior version of the site stated 40,000+. The lower figure may
  reflect a change in counting methodology or the current accurate number.
- **MOST Pro feature set:** Only one feature (DC transmission lines) is documented in the 8.1
  release notes. Full MOST Pro capabilities are unknown without contacting info@matpower.org.
- **Octave performance baseline:** No published benchmarks comparing MATPOWER performance on
  Octave vs. MATLAB. Anecdotal reports suggest 2-5x slower on Octave for large problems.
  pandapower's benchmarking paper (Thurner et al., 2018) found pandapower faster than MATPOWER
  on large networks (>1000 buses), but that comparison used PYPOWER (Python port), not MATPOWER
  on MATLAB directly.
- **Mailing list activity metrics:** The MATPOWER mailing list (MATPOWER-L at Cornell) is the
  primary support channel. Archive available at
  https://www.mail-archive.com/matpower-l@cornell.edu/. GitHub issue counts underrepresent
  community engagement. A developer list (MATPOWER-DEV-L) also exists.
- **RTE/utility deployment details:** matpower.org lists RTE as a user but no details on how
  MATPOWER is used in operational settings (research vs. production). No evidence found of
  MATPOWER in ISO/RTO production dispatch. Primary use case appears to be research and education.
- **Three-phase support maturity:** MATPOWER 8.1 added prototype three-phase conversion, shunt
  models, and off-nominal transformer taps. These are described as "prototype" — maturity and
  correctness for production use are unverified.
- **MATPOWER 8.x MP-Core adoption:** The 8.0 release introduced a completely rewritten
  object-oriented core (MP-Core) with a "flexible framework" alongside the "legacy framework."
  The User's Manual still primarily documents the legacy framework. Real-world adoption of the
  new flexible framework is unclear.
- **HiGHS solver integration:** MP-Opt-Model 5.0 (bundled with MATPOWER 8.1) added support for
  the open-source HiGHS solver for LP, QP, and MILP. This is notable as it provides a
  high-performance open-source alternative to commercial solvers for MILP (needed for UC in MOST).
- **QCQP support:** MP-Opt-Model 5.0 added quadratic constraints and QCQP solver support,
  expanding optimization modeling capabilities beyond LP/QP/NLP.

## Sources

1. [MATPOWER GitHub repository](https://github.com/MATPOWER/matpower) — stars, forks, issues, releases
2. [MOST GitHub repository](https://github.com/MATPOWER/most) — issues, releases, README
3. [MP-Opt-Model GitHub](https://github.com/MATPOWER/mp-opt-model) — metadata
4. [MIPS GitHub](https://github.com/MATPOWER/mips) — metadata
5. [MP-Test GitHub](https://github.com/MATPOWER/mptest) — metadata
6. [MP-Element GitHub](https://github.com/MATPOWER/mp-element) — metadata
7. [matpower.org](https://matpower.org) — download statistics, about page, documentation index
8. [matpower.org/about](https://matpower.org/about/) — capabilities, citation metrics, usage statistics (fetched 2026-03-24)
9. [matpower.org/license](https://matpower.org/license/) — licensing history (BSD 3-Clause since v5.1; GPL for v4.0-5.0)
10. [matpower.org/doc](https://matpower.org/doc/) — documentation index
11. [MATPOWER 8.1 release notes](https://github.com/MATPOWER/matpower/releases/tag/8.1)
12. [MATPOWER 8.0 release notes](https://github.com/MATPOWER/matpower/releases/tag/8.0)
13. [MATPOWER 8.1 launch page](https://matpower.org/matpower-8-1-launch/) — detailed feature list
14. [MOST issue #7 — Large models](https://github.com/MATPOWER/most/issues/7) — scalability limitation
15. [MOST issue #3 — AC multi-period](https://github.com/MATPOWER/most/issues/3) — AC OPF limitation
16. [MOST issue #50 — Downward reserve](https://github.com/MATPOWER/most/issues/50) — open since 2025-03
17. [MOST issue #52 — Update to mp.opt_model](https://github.com/MATPOWER/most/issues/52) — refactoring
18. [MATPOWER issue #134 — Python interop](https://github.com/MATPOWER/matpower/issues/134) — matpower-pip
19. [MATPOWER issue #136 — Distributed slack](https://github.com/MATPOWER/matpower/issues/136)
20. [MATPOWER issue #104 — Zonal reserves](https://github.com/MATPOWER/matpower/issues/104)
21. [MATPOWER issue #24 — Rate B/C in OPF](https://github.com/MATPOWER/matpower/issues/24)
22. [MATPOWER issue #279 — CPF stuck in loop](https://github.com/MATPOWER/matpower/issues/279) — open since 2025-12
23. [matpower.org/citing](https://matpower.org/citing/) — citation format and DOIs
24. [matpower.org/mailing-lists](https://matpower.org/mailing-lists/) — community channels
25. [MATPOWER-L archive](https://www.mail-archive.com/matpower-l@cornell.edu/) — mailing list archive
26. [MATPOWER User's Manual v8.1](https://matpower.org/docs/MATPOWER-manual.pdf)
27. [MATPOWER Reference Manual v8.1](https://matpower.org/doc/_downloads/13f33e22ecbbad1ede2ee92dbf7e51ac/matpower_ref_manual.pdf)
28. [NSF Award #1931421](https://www.nsf.gov/awardsearch/showAward?AWD_ID=1931421) — NSF funding for MATPOWER
29. [pandapower paper (Thurner et al., 2018)](https://arxiv.org/pdf/1709.06743) — performance comparison
30. [PyPSA comparable software](https://docs.pypsa.org/v0.19.1/comparable_software.html) — tool comparison
31. [GMLC-TDC/MATPOWER-wrapper](https://github.com/GMLC-TDC/MATPOWER-wrapper) — HELICS co-simulation
32. [MATPOWER GitHub LICENSE](https://github.com/MATPOWER/matpower/blob/master/LICENSE) — BSD 3-Clause + case file caveat
