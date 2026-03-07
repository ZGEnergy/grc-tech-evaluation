# MATPOWER -- Research: Limitations & Ecosystem

## Key Findings

- **MOST (unit commitment/scheduling) is DC-only.** The MATPOWER Optimal Scheduling Tool supports stochastic, security-constrained unit commitment, but the current implementation is limited to DC power flow network modeling despite the formulation being general enough for AC. An AC implementation is not yet released. (Source: [MOST README](https://github.com/MATPOWER/most/blob/master/README.md))

- **No native SCOPF.** MATPOWER does not ship a built-in security-constrained OPF solver. Users must implement SCOPF by manually enumerating contingency constraints using the extensible OPF framework (userfcn callbacks, `toggle_softlims`, or the new MP-Core Extension API). This is a significant effort for test A-9.

- **No native distributed slack bus in power flow.** GitHub issues [#136](https://github.com/MATPOWER/matpower/issues/136) and [#63](https://github.com/MATPOWER/matpower/issues/63) confirm distributed slack is not implemented. The OPF does distribute generation via optimization, but the power flow solver assigns all slack to one generator at the reference bus. This is relevant to tests A-11 and B-8.

- **Single primary maintainer -- sustainability risk.** Ray Zimmerman has been the sole dominant contributor (2,556 of ~2,600 total commits, 98%+). He transitioned from Cornell to full-time at Power Analytics Software Inc. in mid-2024. NSF funding through Cornell has ended. Future development depends on expanding the contributor base and finding sustainable funding. (Source: [Transition announcement](https://matpower.org/2024/12/03/transition-for-ray-and-the-future-of-matpower/))

- **Octave-only open-source path has solver limitations.** Most commercial solvers (Gurobi, CPLEX, MOSEK, Knitro, MINOPF, TSPOPF, BPMPD) are MATLAB-only. On Octave, available solvers are: GLPK (bundled), IPOPT (requires MEX build), CLP, OSQP, and now HiGHS (new in MP-Opt-Model 5.0 / MATPOWER 8.1). No MILP solver is bundled with Octave -- HiGHS or SCIP must be installed separately for SCUC (test A-5).

- **Installation is non-scriptable by default.** The `install_matpower.m` script requires interactive `input()` prompts, making it unusable in CI/Docker/batch mode. Manual `addpath` of 5+ subdirectories is required, and the dependency on sub-packages (MIPS, MP-Opt-Model, MP-Test) is not documented outside the interactive installer. (Source: [install-findings.md](../notes/install-findings.md))

- **No package manager distribution.** MATPOWER is distributed as a GitHub release zip file (46 MB). No `pkg install`, no `apt` package, no PyPI-native install (the `matpower` PyPI package is a third-party oct2py wrapper). No published SHA256 checksums alongside releases.

- **Lossy DC OPF exists but LMP decomposition requires manual work.** MATPOWER supports loss approximation in DC OPF, but extracting decomposed LMPs (energy/congestion/loss components) requires post-processing of shadow prices from the optimization results. This is relevant to test A-10.

- **PTDF matrix computation is available and recently enhanced.** `makePTDF()` was updated in v8.0 to support per-bus slack distributions (matrix input). `makeLODF()` gained NaN handling for bridge branches. These are positive findings for tests B-9 and C-9.

- **Massive academic citation base but no evidence of production/operational deployment.** Over 750 citations in 2018 alone, 22,000+ downloads/year, used in 100+ countries. However, all evidence points to research and education use -- no documented utility, ISO, or government operational deployments were found.

## Detailed Notes

### MOST: Stochastic Unit Commitment (Tests A-5, A-6, A-8)

MOST (MATPOWER Optimal Scheduling Tool) is the primary mechanism for multi-period scheduling problems including unit commitment. Key capabilities and limitations:

**Capabilities:**
- Deterministic and stochastic optimization with scenario trees
- Security-constrained combined unit commitment and multi-period OPF
- Ramping costs/constraints, min up/down times, startup costs
- Locational contingency and load-following reserves
- Deferrable demands and lossy storage resources
- Uncertain renewable generation modeling

**Limitations:**
- **DC network model only** -- "While the problem formulation is general and incorporates a full nonlinear AC network model, the current implementation is limited to DC power flow modeling of the network." ([MOST README](https://github.com/MATPOWER/most/blob/master/README.md))
- AC implementation work exists but is not released
- Requires formulating the problem via MOST's data structures (`mdi` -- MOST Data Input), which have a learning curve
- MOST 1.3.1 is the current version (released July 12, 2025)
- MOST has 39 stars and 15 forks on GitHub -- significantly less community engagement than core MATPOWER

**Relevance to evaluation:**
- A-5 (SCUC): MOST directly supports this, but requires learning MOST-specific data structures
- A-6 (SCED): Achievable by fixing commitment in MOST or running DC OPF with fixed Pmin=Pmax
- A-8 (stochastic timeseries): MOST natively supports scenario-indexed stochastic formulations -- this is a strength

Sources:
- [MOST GitHub](https://github.com/MATPOWER/most)
- [MOST User's Manual](https://matpower.org/docs/MOST-manual.pdf)

### SCOPF: Security-Constrained OPF (Test A-9)

MATPOWER does not include a standalone SCOPF solver. Implementation options:

1. **Legacy userfcn callbacks** -- The extensible OPF framework allows adding custom constraints via callback functions. Users can enumerate N-1 contingency constraints and inject them into the OPF formulation. This is the documented approach but requires significant user effort.

2. **MP-Core Extension API (v8.0+)** -- The new flexible framework provides a more structured extension mechanism, but documentation for building custom OPF extensions is still maturing (Developer's Manual exists, User's Manual not yet updated for the flexible framework as of v8.0 release notes).

3. **toggle_softlims** -- Can relax inequality constraints with penalty costs, useful for SCOPF implementations that need soft limits.

4. **External implementation** -- Academic projects (e.g., ECE 557 at IIT) use MATPOWER as a platform for building SCOPF tools, confirming it is achievable but not turnkey.

**Relevance to evaluation:** Test A-9 will require manually building SCOPF by enumerating contingency constraints. This should be documented as a significant workaround.

Sources:
- [toggle_softlims docs](https://matpower.org/docs/ref/matpower7.0/lib/toggle_softlims.html)
- [MATPOWER OPF architecture paper](https://matpower.org/docs/MATPOWER-OPF.pdf)

### Distributed Slack Bus (Tests A-11, B-8)

**Power flow:** Not implemented. GitHub issue [#136](https://github.com/MATPOWER/matpower/issues/136) (opened Jan 2022, still open) confirms no native distributed slack power flow exists. A community member proposed a contribution but it has not been merged.

**OPF:** The OPF naturally distributes generation through optimization -- all generators participate. However, the reference bus choice still affects LMP computation in the standard formulation. The `makePTDF()` function in v8.0+ supports per-bus slack distribution via a matrix input, which could be used for distributed-slack PTDF-based analysis.

**Multiple generators at slack bus:** GitHub issue [#63](https://github.com/MATPOWER/matpower/issues/63) (opened Mar 2019, still open) documents that MATPOWER assigns all slack to the first generator at the reference bus, which is undocumented behavior. A proposal to use area participation factors (APF) has not been implemented.

**Relevance to evaluation:** Test A-11 (distributed slack OPF) may be partially achievable through DC OPF formulation manipulation, but native distributed slack power flow for comparison is unavailable.

Sources:
- [Issue #136](https://github.com/MATPOWER/matpower/issues/136)
- [Issue #63](https://github.com/MATPOWER/matpower/issues/63)

### Solver Ecosystem on Octave

| Solver | Type | Open-Source | Octave Support | Notes |
|--------|------|-------------|----------------|-------|
| MIPS | NLP | Yes (bundled) | Yes | MATPOWER's built-in interior point solver |
| GLPK | LP | Yes (bundled w/ Octave) | Yes | No QP support |
| IPOPT | NLP | Yes | Yes (requires MEX build) | Best open-source NLP option |
| CLP | LP/QP | Yes | Yes | Requires separate install |
| OSQP | QP | Yes | Yes | Operator splitting method |
| HiGHS | LP/QP/MILP | Yes | Yes (new in v8.1) | Key addition for MILP (SCUC) |
| Gurobi | LP/QP/MILP | No | **MATLAB only** | -- |
| CPLEX | LP/QP/MILP | No | **MATLAB only** | -- |
| MOSEK | LP/QP | No | **MATLAB only** | -- |
| Knitro | NLP | No | **MATLAB only** | -- |
| MINOPF | AC OPF | No | **MATLAB only** | Fortran MEX |
| TSPOPF | AC OPF | No | **MATLAB only** | C MEX |

**Key gap:** Before v8.1, there was no open-source MILP solver available through MATPOWER on Octave. HiGHS support (added in MP-Opt-Model 5.0) fills this critical gap for unit commitment problems.

Sources:
- [Optional Solvers page](https://matpower.org/download/optional-solvers/)

### Lossy DC OPF and LMP Decomposition (Test A-10)

MATPOWER supports DC OPF with quadratic loss approximation. The formulation adds loss terms to the DC power balance equations. However:

- LMP values are available as bus shadow prices from the OPF solution
- LMP **decomposition** into energy, congestion, and loss components is not a built-in function
- Users must compute the decomposition from the PTDF matrix, shift factors, and shadow prices
- The `makePTDF()` and `makeLODF()` functions provide the necessary building blocks
- Academic literature (e.g., the "Lossy DC Power Flow" paper by Coffrin & Van Hentenryck) describes the methodology

**Relevance to evaluation:** Achievable but requires manual post-processing. Not turnkey.

Sources:
- [Lossy DC Power Flow paper](https://arxiv.org/pdf/1611.05953)

### Release History

| Version | Date | Key Changes |
|---------|------|-------------|
| 8.1 | Jul 13, 2025 | Three-phase POC enhancements, HiGHS solver support (MP-Opt-Model 5.0), QCQP support, new case files |
| 8.0 | May 17, 2024 | **Major redesign:** MP-Core OO architecture, flexible framework, new PF solvers (fsolve, Implicit Z-bus Gauss), three-phase/hybrid prototypes |
| 8.0b1 | Dec 22, 2022 | Beta of MP-Core architecture |
| 7.1 | Oct 8, 2020 | MP-Opt-Model 3.0, OSQP support, 19 new distribution cases |
| 7.0 | Jun 20, 2019 | PSS/E RAW export, user-defined nonlinear constraints, Docker support |
| 7.0b1 | Oct 31, 2018 | Beta of v7.0 features |

**Release cadence:** Roughly 1 major release every 2-4 years with betas. The 8.x series represents a massive architectural overhaul. Patch releases (8.0 to 8.1) within ~14 months.

Sources:
- [GitHub releases](https://github.com/MATPOWER/matpower/releases)
- [MATPOWER history](https://matpower.org/about/history/)

### Community and Contributor Statistics

**GitHub metrics (as of research date):**
- Stars: 534
- Forks: 172
- Open issues: 16
- Contributors: 17
- Language: MATLAB

**Contributor concentration (critical risk):**
- Ray Zimmerman (`rdzman`): 2,556 commits (98%+ of total)
- Next contributor: 17 commits
- **Bus factor: 1** -- This is the single largest sustainability risk

**Community channels:**
- Two mailing lists at Cornell (matpower-l)
- GitHub issues (relatively low volume -- 16 open, ~280 total)
- No Discourse, Slack, Discord, or other modern community platform

**Academic impact:**
- 750+ citations in 2018 alone
- 22,000+ downloads/year
- Used in 100+ countries
- Among most-cited research from Cornell's Dyson School

Sources:
- [GitHub repo](https://github.com/MATPOWER/matpower)
- [About MATPOWER](https://matpower.org/about/)

### Funding and Sustainability

**Historical funding:** Research grants to Cornell University through PSERC (Power Systems Engineering Research Center). Ray Zimmerman held a Senior Research Associate position.

**Transition timeline:**
- 2022: Zimmerman reduced Cornell appointment to half-time, joined Power Analytics Software Inc. half-time
- Mid-2024: Transitioned to full-time at Power Analytics Software
- Dec 2024: Published "[Transition for Ray, and the Future of MATPOWER](https://matpower.org/2024/12/03/transition-for-ray-and-the-future-of-matpower/)" announcing:
  - NSF funding through Cornell is **closed**
  - Limited MathWorks support through MATLAB Community Toolbox program (three-phase features only)
  - Plans to expand project ownership and explore fee-based business model

**Current support:** MathWorks sponsorship for specific features. GitHub Sponsors ("Sponsor MATPOWER" initiative). No guaranteed institutional funding.

**Assessment:** High sustainability risk. The project depends almost entirely on one person who has moved away from academic funding. The proposed mitigations (expanding contributors, commercial model) are aspirational, not yet realized.

Sources:
- [Transition announcement](https://matpower.org/2024/12/03/transition-for-ray-and-the-future-of-matpower/)
- [Ray Zimmerman's Cornell page](https://www.pserc.cornell.edu/ray/)

### MATLAB vs Octave: The Licensing Question

**The core tension:** MATPOWER is BSD-3-Clause licensed (fully open source), but it runs on MATLAB (proprietary, ~$2,350/year for a commercial license) or GNU Octave (free, GPLv3).

**Octave limitations relevant to this evaluation:**
- No JIT compiler -- loops run 2-3x slower than MATLAB
- Fewer MEX-based solver bindings available
- Most commercial solvers (Gurobi, CPLEX, Knitro, MOSEK) provide only MATLAB interfaces
- MATPOWER v8.0 MP-Core requires Octave 6.2+ (the devcontainer has Octave 9.2.0, so this is fine)
- The `fsolve()`-based power flow solver works on Octave (included in base Octave)

**Octave strengths:**
- GLPK bundled with Octave (LP solver)
- MATPOWER Docker images based on GNU Octave are officially published
- HiGHS support (new in v8.1) provides open-source LP/QP/MILP on Octave
- MATPOWER explicitly tests on Octave and considers it a first-class platform

**For this evaluation:** All testing runs on Octave in the devcontainer. Performance benchmarks will reflect Octave execution times, not MATLAB. This is the relevant deployment scenario for an open-source supply chain.

### Ecosystem Packages

**Official MATPOWER packages:**
- [MATPOWER core](https://github.com/MATPOWER/matpower) -- PF, CPF, OPF
- [MOST](https://github.com/MATPOWER/most) -- Optimal scheduling / unit commitment
- [MP-Opt-Model](https://github.com/MATPOWER/mp-opt-model) -- Optimization modeling layer
- [MIPS](https://github.com/MATPOWER/mips) -- Built-in interior point solver
- [MP-Test](https://github.com/MATPOWER/mptest) -- Testing framework
- [MATPOWER Extras](https://github.com/MATPOWER/matpower-extras) -- Contributed/unsupported code (SDP relaxation, state estimation, etc.)

**Third-party ecosystem:**
- [matpower-pip](https://pypi.org/project/matpower/) (PyPI) -- Python wrapper using oct2py for calling MATPOWER from Python
- [PYPOWER](https://github.com/rwl/PYPOWER) -- Pure Python port of MATPOWER (stale, based on v4.1)
- [matpowercaseframes](https://pypi.org/project/matpowercaseframes/) -- Python parser for MATPOWER case files
- [pandapower](https://www.pandapower.org/) -- Uses MATPOWER case format as import/export format
- [PowerModels.jl](https://github.com/lanl/PowerModels.jl) -- Julia package that validates against MATPOWER results

**The `.m` case file format** is the de facto standard for power system test cases. Every tool in this evaluation either reads `.m` files natively or has a converter.

### Documentation Quality

**Strengths:**
- Comprehensive [User's Manual](https://matpower.org/docs/MATPOWER-manual.pdf) (PDF, well-structured)
- New [Documentation website](https://matpower.org/documentation/) with reference docs
- [Developer's Manual](https://matpower.org/documentation/) for MP-Core architecture
- [MOST User's Manual](https://matpower.org/docs/MOST-manual.pdf) for scheduling problems
- Technical Notes series for mathematical foundations
- Rich default output from solvers (bus, branch, generator summaries)

**Weaknesses:**
- User's Manual **not yet updated** for the new flexible framework (v8.0 release notes explicitly state this)
- FAQ is minimal (5 entries, none covering advanced topics)
- No tutorial-style getting-started guide beyond basic examples
- MOST documentation assumes significant power systems optimization background
- The new MP-Core Extension API documentation is in the Developer's Manual, which is reference-style, not tutorial-style
- Mailing list archives are the primary source for advanced usage patterns

Sources:
- [MATPOWER Documentation](https://matpower.org/documentation/)
- [v8.0 Release Notes](https://github.com/MATPOWER/matpower/blob/master/docs/relnotes/MATPOWER-Release-Notes-8.0.md)

### Open Issues Relevant to Evaluation Tests

| Issue | Status | Relevance |
|-------|--------|-----------|
| [#136](https://github.com/MATPOWER/matpower/issues/136) -- Distributed slack PF | Open (since Jan 2022) | Tests A-11, B-8 |
| [#63](https://github.com/MATPOWER/matpower/issues/63) -- Slack distribution at slack bus | Open (since Mar 2019) | Tests A-11, B-8 |
| [#233](https://github.com/MATPOWER/matpower/issues/233) -- Multiple/distributed slack question | Open (since May 2024) | Tests A-11, B-8 |
| [#127](https://github.com/MATPOWER/matpower/issues/127) -- makePTDF ext2int error | Open (since Sep 2021) | Tests B-9, C-9 |
| [#54](https://github.com/MATPOWER/matpower/issues/54) -- PSS/E RAW v34 support | Open (since Dec 2018) | Test P2-1 |
| [#24](https://github.com/MATPOWER/matpower/issues/24) -- Rate B/C not in OPF | Open (since Sep 2017) | General OPF |
| [#16](https://github.com/MATPOWER/matpower/issues/16) -- Transformer taps/phases | Open (since Jun 2017) | Expressiveness |
| [#279](https://github.com/MATPOWER/matpower/issues/279) -- CPF stuck in loop | Open (since Dec 2025) | CPF reliability |

## Sources

1. [MATPOWER GitHub repository](https://github.com/MATPOWER/matpower) -- 534 stars, 172 forks, 17 contributors
2. [MOST GitHub repository](https://github.com/MATPOWER/most) -- 39 stars, 15 forks
3. [MATPOWER 8.0 Release Notes](https://github.com/MATPOWER/matpower/blob/master/docs/relnotes/MATPOWER-Release-Notes-8.0.md)
4. [GitHub releases page](https://github.com/MATPOWER/matpower/releases)
5. [MATPOWER Optional Solvers](https://matpower.org/download/optional-solvers/)
6. [Transition for Ray, and the Future of MATPOWER](https://matpower.org/2024/12/03/transition-for-ray-and-the-future-of-matpower/) (Dec 2024)
7. [About MATPOWER](https://matpower.org/about/) -- 22,000+ downloads/year, 100+ countries
8. [MATPOWER Citing page](https://matpower.org/citing/) -- 750+ citations in 2018
9. [MOST README](https://github.com/MATPOWER/most/blob/master/README.md) -- DC-only limitation
10. [toggle_softlims documentation](https://matpower.org/docs/ref/matpower7.0/lib/toggle_softlims.html)
11. [MATPOWER OPF architecture paper](https://matpower.org/docs/MATPOWER-OPF.pdf)
12. [GitHub Issue #136 -- Distributed slack PF](https://github.com/MATPOWER/matpower/issues/136)
13. [GitHub Issue #63 -- Slack distribution](https://github.com/MATPOWER/matpower/issues/63)
14. [matpower-pip on PyPI](https://pypi.org/project/matpower/)
15. [MATPOWER Documentation site](https://matpower.org/documentation/)
16. [Ray Zimmerman at Cornell](https://www.pserc.cornell.edu/ray/)
17. [MATPOWER FAQ](https://matpower.org/doc/faq/)
18. Local file: `evaluations/matpower/notes/install-findings.md` -- install and smoke-test findings

## Gaps and Uncertainties

- **HiGHS on Octave actual performance.** HiGHS support is new in v8.1 (MP-Opt-Model 5.0). It needs to be verified that the HiGHS MEX interface actually works on Octave 9.2 in the devcontainer. If it does not, GLPK (LP only) may be the only bundled solver, and MILP tests (A-5 SCUC) would require external solver installation.

- **MOST learning curve.** The effort required to set up a MOST problem (constructing `mdi` data structures, defining scenarios, profiles, and contingencies) has not been measured. The MOST manual is the only documentation source and assumes deep domain knowledge.

- **Octave large-scale performance.** No benchmarks were found for MATPOWER on Octave with 10,000-bus systems. The 2-3x slowdown vs MATLAB is a general estimate; actual performance for sparse matrix operations (which dominate power flow) may differ. This will be measured in scalability tests C-1 through C-10.

- **MP-Core extension API maturity.** The v8.0 User's Manual has not been updated for the new flexible framework. It is unclear how stable the Extension API is for building custom formulations (e.g., SCOPF via A-9). The Developer's Manual exists but is reference-style.

- **Lossy DC OPF specifics.** The exact mechanism for enabling loss approximation in DC OPF and extracting loss-inclusive LMPs needs to be verified during testing. Documentation on this feature is sparse.

- **SCOPF implementation effort.** No turnkey SCOPF exists. The effort to build one using userfcn callbacks or the new Extension API is unknown and will be a key finding of test A-9.

- **Issue #127 (makePTDF ext2int).** This open issue may affect PTDF computation on networks that are not in internal ordering. Needs verification during tests B-9 and C-9.

- **Operational deployment evidence.** Despite extensive searching, no evidence of utility, ISO, or government operational use was found. MATPOWER appears to be exclusively a research and education tool. This is a maturity finding but not necessarily disqualifying -- the `.m` file format and algorithm implementations are widely validated.
