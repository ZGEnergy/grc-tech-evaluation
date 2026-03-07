# Synthesis Report — MATPOWER v8.1

**Contract:** FA714626C0006 | Grid Research Company LLC
**Tool version:** MATPOWER 8.1 (12-Jul-2025)
**Runtime:** GNU Octave 9.2 on Ubuntu 24.04 (devcontainer, 128 GB RAM, 16 cores)
**Protocol version:** v4
**Date:** 2026-03-07

---

## 1. Executive Summary

MATPOWER 8.1 is the gold standard for power systems research — a 28-year-old BSD-3-licensed tool with unmatched inspectability, zero compiled dependencies, and a clean mathematical foundation that serves as the reference implementation other tools validate against. Its companion package MOST provides native SCUC, SCED, stochastic optimization, and preventive SCOPF in a single framework. However, MATPOWER hits hard scalability walls on MOST-based analyses beyond small networks due to monolithic problem formulations paired with limited open-source solvers on Octave. The project's bus factor of 1 (Ray Zimmerman, 98.5% of commits, left Cornell mid-2024 with no institutional successor) is the most serious sustainability risk of any tool evaluated. Supply chain gate: **PASS** — MATPOWER achieves near-perfect supply chain scores across all sub-questions. Scale cap: **MEDIUM** (all three gate tiers passed).

---

## 2. Grade Recommendations Table

| Criterion | Grade | Confidence | Key Evidence |
|-----------|-------|------------|--------------|
| Problem Expressiveness | **A-** | High | 9/11 A-tests pass (2 qualified); all problem types expressible; lossy DC OPF and distributed slack require manual formulation |
| Extensibility | **A-** | High | 8/9 B-tests pass (1 qualified); strong architecture, userfcn callbacks, mutable struct, native PTDF; no graph primitives |
| Scalability | **B-** | High | Core PF/OPF fast at MEDIUM; 3 MOST-based tests fail (SCUC, stochastic, SCOPF) due to monolithic formulation + solver limits |
| Workforce Accessibility | **B** | Medium | Core API clean and well-documented; MOST learning curve steep; 65% example pass rate; mixed error quality |
| Maturity & Sustainability | **C+** | High | Bus factor 1, no funding, no institutional backing, zero production deployment; offset by 462 test files, CI, 28-year track record |
| Supply Chain (Gate) | **A** | High | BSD-3, zero deps, zero compiled extensions, 100% .m source, fully air-gap installable |

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness

#### Strengths

- Native single-call API for DCPF, ACPF, DCOPF with structured output ([A-1](expressiveness/A-1_dcpf_TINY.md), [A-2](expressiveness/A-2_acpf_TINY.md), [A-3](expressiveness/A-3_dcopf_TINY.md))
- AC feasibility check on DC OPF dispatch requires only 5 lines of domain logic, no format conversion ([A-4](expressiveness/A-4_ac_feasibility_TINY.md))
- MOST provides native SCUC with all standard UC constraints (min up/down, ramp rates, startup costs, reserves) as built-in primitives ([A-5](expressiveness/A-5_scuc_TINY.md))
- Clean two-stage UC+ED separation with commitment injection via `mdi.UC.CommitSched` ([A-6](expressiveness/A-6_sced_TINY.md))
- Native stochastic optimization via MOST with scenario-indexed timeseries embedded in a single QP formulation ([A-8](expressiveness/A-8_stochastic_timeseries_TINY.md))
- Preventive SCOPF via MOST contingency table — contingency constraints inside the optimization, not post-hoc ([A-9](expressiveness/A-9_scopf_TINY.md))
- Exact lossless LMP decomposition into energy + congestion components with PTDF verification ([A-10](expressiveness/A-10_lossy_dcopf_lmp_TINY.md))
- Native piecewise-linear cost curves (MODEL=1 gencost) with CCV formulation ([P2-2](p2_readiness/P2-2_piecewise_linear_costs.md))

#### Weaknesses

- No native lossy DC OPF — `rundcopf()` is strictly lossless and this is undocumented ([A-10](expressiveness/A-10_lossy_dcopf_lmp_TINY.md))
- No native distributed slack OPF — open GitHub issues #136, #63, #233 confirm this is unimplemented ([A-11](expressiveness/A-11_distributed_slack_opf_TINY.md))
- MOST setup requires 180-350 LOC of boilerplate for xGenData, profiles, transition matrices, even for simple problems ([D-5](accessibility/D-5_code_volume_comparison.md))
- No built-in BFS/graph utility despite topology being central to power systems analysis ([A-7](expressiveness/A-7_contingency_sweep_TINY.md))

#### Workarounds Required

- **A-5 (SCUC):** GLPK cannot handle MIQP; polynomial costs must be converted to piecewise-linear (~25 LOC). — **stable** (PWL conversion is standard practice; unnecessary with HiGHS)
- **A-10 (Lossy DC OPF):** Loss component requires manual post-hoc computation from branch impedances and flows. Energy + congestion decomposition is exact and native. — **stable**
- **A-11 (Distributed slack OPF):** Requires manual PTDF-based DC OPF construction using `opt_model` (~100 LOC). `makePTDF(mpc, weights)` provides the distributed-slack PTDF; the OPF wrapper does not accept it. — **stable**

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | LOC |
|------|---------|--------|------------|------|-----|
| A-1  | TINY | pass | -- | 0.17s | 104 |
| A-2  | TINY | pass | -- | 0.20s | 150 |
| A-3  | TINY | pass | -- | 0.19s | 143 |
| A-4  | TINY | pass | -- | 0.30s | 201 |
| A-5  | TINY | pass | stable (PWL for GLPK) | 1.67s | 377 |
| A-6  | TINY | pass | stable (PWL for GLPK) | 4.94s | 387 |
| A-7  | TINY | pass | -- | 21.4s | 288 |
| A-8  | TINY | pass | -- | 1.02s | 316 |
| A-9  | TINY | pass | -- | 1.26s | 339 |
| A-10 | TINY | qualified_pass | stable (manual loss computation) | 0.24s | 293 |
| A-11 | TINY | qualified_pass | stable (manual opt_model OPF) | 0.31s | 324 |

#### Grade Rationale

MATPOWER achieves native expressiveness for all 8 original problem types (DCPF, ACPF, DCOPF, AC feasibility, SCUC, SCED, contingency sweep, stochastic optimization) plus preventive SCOPF. The two Phase 2 readiness sub-questions (lossy DC OPF, distributed slack) receive qualified passes with stable workarounds. Per rubric: "A: All target problem types expressible natively... SCOPF expressible natively or through documented extension API. Loss-inclusive OPF supported with LMP decomposition... Distributed slack OPF supported natively." The tool meets the A standard on sub-questions 1-9 but falls short on 10 (no native lossy DC OPF) and 11 (no native distributed slack). This warrants A- per rubric guidance: "Strong overall but with one minor caveat that doesn't affect core workflows." The caveats here are two Phase 2 readiness gaps, not core workflow limitations.

---

### 3.2 Extensibility

#### Strengths

- Documented extension API via `toggle_iflims`/`toggle_reserves`/`toggle_softlims` callback pattern for custom constraints ([B-1](extensibility/B-1_custom_constraints_TINY.md))
- Mutable `mpc` struct enables zero-overhead contingency loops — toggle `BR_STATUS`, call solver, no rebuild ([B-3](extensibility/B-3_contingency_loop_TINY.md))
- MOST profile system accepts timeseries programmatically as numeric arrays; scenario wrapping requires only changing profile values between iterations ([B-4](extensibility/B-4_stochastic_wrapping_TINY.md))
- Unified `mpc` struct across all analysis types enables seamless workflow composition (DC OPF -> AC PF) without format conversion ([B-7](extensibility/B-7_ac_feasibility_extension_TINY.md))
- `makePTDF(mpc)` is a single zero-friction function call with distributed slack weight support; PTDF verified to machine precision ([B-9](extensibility/B-9_ptdf_extraction_TINY.md))
- Strong three-layer architecture in new MP-Core framework (data model, network model, mathematical model) with `opt_model` as clean solver abstraction boundary ([B-6](extensibility/B-6_code_architecture.md))
- Results export to CSV is trivial — plain numeric matrices, no serialization barriers ([B-5](extensibility/B-5_interoperability_TINY.md))

#### Weaknesses

- No native graph object or traversal functions — adjacency must be constructed manually from branch matrix (~60 LOC for BFS) ([B-2](extensibility/B-2_graph_access_TINY.md))
- Distributed slack in OPF requires manual PTDF-based reformulation; `rundcopf` does not accept distributed slack weights ([B-8](extensibility/B-8_reference_bus_config_TINY.md))
- New MP-Core extension documentation is incomplete (User's Manual not updated for flexible framework) ([B-6](extensibility/B-6_code_architecture.md))

#### Workarounds Required

- **B-2 (Graph access):** Manual adjacency list construction + BFS from `branch(:, [F_BUS T_BUS])`. ~60 LOC. — **stable** (branch matrix format unchanged for 25+ years)
- **B-8 (Distributed slack OPF):** `makePTDF(mpc, weights)` provides distributed-slack PTDF natively, but OPF requires manual `opt_model` construction. — **stable**

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | LOC |
|------|---------|--------|------------|------|-----|
| B-1  | TINY | pass | -- | 0.24s | 95 |
| B-2  | TINY | pass | stable (manual BFS) | 0.03s | 60 |
| B-3  | TINY | pass | -- | 2.38s | 75 |
| B-4  | TINY | pass | -- | 5.24s | 140 |
| B-5  | TINY | pass | -- | 0.15s | 18 |
| B-6  | N/A  | informational | -- | -- | -- |
| B-7  | TINY | pass | -- | 0.26s | 50 |
| B-8  | TINY | qualified_pass | stable (manual PTDF OPF) | 0.25s | 80 |
| B-9  | TINY | pass | -- | 0.14s | 70 |

#### Grade Rationale

MATPOWER provides a documented extension API (`userfcn` callbacks, `toggle_*` extensions, `opt_model` class), a traversable network topology (via stable branch matrix workaround), contingency loops without model reconstruction, straightforward stochastic wrapping, trivial results export, clean architecture, API-level reference bus configuration, and native PTDF extraction. The two gaps are the absence of native graph primitives (B-2, stable workaround) and distributed slack in OPF (B-8, stable workaround). Per rubric: "A: Documented extension API for custom constraints. Network exposed as a traversable graph. Contingency loops buildable without model reconstruction... Reference bus configurable via API. PTDF matrix accessible as a structured output." The graph traversal gap (requires manual BFS) is a meaningful departure from the A standard, but the workaround is stable and the branch matrix format is foundational. This supports A- per rubric: "Strong overall but with one minor caveat."

---

### 3.3 Scalability

#### Strengths

- DCPF on MEDIUM (10k buses): 1.01s solve time, well within practical limits ([C-1](scalability/C-1_dcpf_scale_MEDIUM.md))
- ACPF on MEDIUM: 1.15s, 4 Newton iterations from flat start, no convergence difficulty ([C-2](scalability/C-2_acpf_scale_MEDIUM.md))
- DCOPF on MEDIUM: MIPS 9.7s (QP), GLPK 93s (LP with PWL costs); cross-solver consistency within 1.84e-6 relative ([C-3](scalability/C-3_dcopf_scale_MEDIUM.md))
- Solver swap is a single parameter change — no reformulation, no data restructuring ([C-7](scalability/C-7_solver_swap_MEDIUM.md))
- PTDF on MEDIUM: 28.7s, 1017 MB — feasible on reference workstation ([C-9](scalability/C-9_ptdf_scale_MEDIUM.md))

#### Weaknesses

- **C-4 (SCUC on SMALL): FAIL** — 200K+ variable MILP exceeds GLPK capacity; >10 min timeout ([C-4](scalability/C-4_scuc_scale_SMALL.md))
- **C-6 (Stochastic on SMALL): FAIL** — 1.3M+ variable QP exceeds MIPS capacity; >10 min timeout ([C-6](scalability/C-6_stochastic_scale_SMALL.md))
- **C-8 (SCOPF on MEDIUM): FAIL** — 6.4M+ constraints from 500 contingencies exceeds solver capacity; >10 min timeout. No iterative/cutting-plane SCOPF available ([C-8](scalability/C-8_scopf_scale_MEDIUM.md))
- LODF computation on MEDIUM bottlenecks at >10 min for the full 12,706 x 12,706 matrix ([C-5](scalability/C-5_contingency_sweep_scale_MEDIUM.md))
- Distributed slack OPF on MEDIUM requires ~90-120s total (PTDF computation + manual opt_model solve) ([C-10](scalability/C-10_distributed_slack_scale_MEDIUM.md))

#### Workarounds Required

- **C-5 (Contingency sweep):** LODF precomputation is the bottleneck; PTDF-based N-1 screening is feasible (~15s for PTDF). — **stable**
- **C-9 (PTDF):** `ext2int()` required before `makePTDF` on non-consecutively numbered networks. One extra line. — **stable**
- **C-10 (Distributed slack):** Same manual `opt_model` pattern as A-11, scaled to MEDIUM. ~155 LOC. — **stable**

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | Memory |
|------|---------|--------|------------|------|--------|
| C-1  | MEDIUM | pass | -- | 1.01s | ~5 MB |
| C-2  | MEDIUM | pass | -- | 1.15s | -- |
| C-3  | MEDIUM | pass | -- | 9.7s (MIPS) / 93s (GLPK) | -- |
| C-4  | SMALL  | fail | -- | >600s (timeout) | -- |
| C-5  | MEDIUM | qualified_pass | stable (LODF bottleneck) | >600s (LODF) | ~2.5 GB |
| C-6  | SMALL  | fail | -- | >600s (timeout) | -- |
| C-7  | MEDIUM | pass | -- | 11.9s | -- |
| C-8  | MEDIUM | fail | -- | >600s (timeout) | -- |
| C-9  | MEDIUM | pass | stable (ext2int) | 28.7s | 1017 MB |
| C-10 | MEDIUM | qualified_pass | stable (manual opt_model) | ~90-120s est. | ~1.2 GB |

#### Grade Rationale

Core PF and OPF scale well to MEDIUM (10k buses): DCPF ~1s, ACPF ~1s, DCOPF ~10s. Solver swap is trivial. PTDF extraction is feasible at 1 GB memory. However, three MOST-based analyses fail at SMALL or MEDIUM scale: SCUC (C-4), stochastic (C-6), and SCOPF (C-8). These failures stem from MOST's monolithic formulation that constructs a single massive LP/MILP/QP without decomposition, paired with MIPS/GLPK solver limitations on Octave. Per rubric: "B: Performs adequately at 10k buses but with caveats — contingency sweeps require careful batching, or specific solver needed for MILP problems." The three outright failures push below B toward B-. The rubric states: "B-: Functional but multiple workarounds needed, some fragile." The failures are not workaround-solvable (no decomposition available in MOST), but they affect only MOST-based multi-period/multi-scenario analyses, not core PF/OPF. Grade: **B-**.

---

### 3.4 Workforce Accessibility

#### Strengths

- Core API is clean and intuitive: `mpc = loadcase('case39'); results = rundcpf(mpc)` — two lines to first solve ([D-1](accessibility/D-1_install_to_first_solve.md))
- Core MATPOWER (PF, OPF, sensitivity) is excellently documented — 6/11 A-tests fully completable from official docs ([D-2](accessibility/D-2_documentation_audit.md))
- MOST examples are the most reliable shipped examples — 6/7 run unmodified ([D-3](accessibility/D-3_example_verification.md))
- Invalid bus type error is clear, specific, and actionable ("bus 1 has an invalid BUS_TYPE") ([D-4](accessibility/D-4_error_quality.md))
- Bundled PDF manuals ship with the release, matching the installed version ([F-9](supply_chain/F-9_getting_started_integrity.md))

#### Weaknesses

- No package manager support — manual zip download, 5+ `addpath` calls, interactive installer unusable in batch mode ([D-1](accessibility/D-1_install_to_first_solve.md))
- MOST documentation is comprehensive but difficult to navigate; result extraction requires reading source code ([D-2](accessibility/D-2_documentation_audit.md))
- 65% example pass rate (13/20) — 4 fail on headless graphics, 2 reference MATLAB-only functions, 1 solver convergence failure, 1 display bug ([D-3](accessibility/D-3_example_verification.md))
- Missing gencost rows produces cryptic array indexing error with no domain context (2/10 quality) ([D-4](accessibility/D-4_error_quality.md))
- MOST-based tests average 349 LOC vs 132 LOC for core PF/OPF — steep complexity cliff ([D-5](accessibility/D-5_code_volume_comparison.md))
- Absence of features (lossy DC OPF, distributed slack) is not documented — users discover only via GitHub issues or source reading ([D-2](accessibility/D-2_documentation_audit.md))
- Solver compatibility matrix is missing — GLPK/MIQP limitation undocumented ([D-2](accessibility/D-2_documentation_audit.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| D-1  | informational | ~10 min new user, ~2 min experienced; no pkg manager |
| D-2  | informational | 6/11 from docs, 3 partial, 2 not completable |
| D-3  | informational | 13/20 examples pass (65%) |
| D-4  | informational | Mixed: 9/10 (bus type), 6/10 (infeasible), 2/10 (gencost) |
| D-5  | informational | Mean 266 LOC; MOST avg 349 LOC; core avg 132 LOC |

#### Grade Rationale

Per rubric: "B: API is learnable but has rough edges. Documentation covers the basics but gaps exist for advanced use cases. Learning curve measured in weeks, not days. Error messages require solver familiarity to interpret." The core MATPOWER API is clean and well-documented (would merit B+ alone), but MOST introduces significant learning curve friction, the example pass rate is only 65%, error messages are inconsistent, and the installation process lacks package manager support. The combination of strong core accessibility and weak MOST accessibility averages to **B**.

---

### 3.5 Maturity & Sustainability

#### Strengths

- 28-year continuous development history (1996-present) with consistent commit activity (129 commits in 2025-2026) ([E-2](maturity/E-2_commit_activity.md))
- 462 test files with GitHub Actions CI across macOS, Ubuntu 22.04/24.04, and MATLAB ([E-6](maturity/E-6_ci_test_coverage.md))
- 2 stable releases in 24 months (v8.0 May 2024, v8.1 July 2025) with substantive feature additions ([E-1](maturity/E-1_release_cadence.md))
- 750+ citations/year — the most widely cited open-source power systems tool ([E-7](maturity/E-7_operational_adoption.md))
- BSD-3 license and clean codebase enable community forking if needed ([E-3](maturity/E-3_contributor_concentration.md))

#### Weaknesses

- **Bus factor: 1** — Ray Zimmerman accounts for 98.5% of all commits (2,556/2,595). No co-maintainer, no succession planning ([E-3](maturity/E-3_contributor_concentration.md))
- **No funding** — NSF grants ended, left Cornell mid-2024, no institutional backing, no donation mechanism, no commercial entity ([E-4](maturity/E-4_funding_model.md))
- **Zero confirmed production deployment** by any utility, ISO, or government operational system ([E-7](maturity/E-7_operational_adoption.md))
- No patch releases — bugs accumulate 12+ months until next minor/major release ([E-1](maturity/E-1_release_cadence.md))
- Issue tracker shows batch processing pattern (single-maintainer triage); feature requests remain open indefinitely (distributed slack #136 open since 2022) ([E-5](maturity/E-5_issue_tracker_health.md))
- No formal code coverage metrics ([E-6](maturity/E-6_ci_test_coverage.md))

#### Evidence Summary Table

| Test | Key Finding |
|------|-------------|
| E-1  | 2 releases in 24 months; 14-17 month cadence; no patch releases |
| E-2  | 129 commits (2025-2026); 93% from single developer |
| E-3  | Bus factor 1; 17 total contributors; top contributor 98.5% |
| E-4  | Unfunded volunteer work since mid-2024; no institutional backing |
| E-5  | Median close time 108 days; oldest open issue 2,160 days; batch triage pattern |
| E-6  | 462 test files; GitHub Actions CI; no coverage metric |
| E-7  | 750+ citations/year; zero production deployment; purely academic adoption |

#### Grade Rationale

Per rubric: "C: Development driven by one or two individuals with no institutional backing. No CI or test suite, or CI is broken. No recent versioned releases or only dependency maintenance. No evidence of operational deployment. Issue tracker inactive or backlogged." MATPOWER clearly exceeds the C standard (it has CI, a large test suite, and recent substantive releases), but the bus factor of 1, absence of funding, and zero operational deployment are serious. Per rubric: "B: Active but smaller contributor base. CI exists but coverage is partial. Funding tied to ongoing research programs likely to continue but not guaranteed." The contributor base is not "smaller" — it is one person. Funding is not "likely to continue" — it has ended entirely. The project exceeds C+ (CI is strong, releases are substantive, code quality is high) but does not reach B- (bus factor 1 + no funding + zero production use). Grade: **C+**, reflecting the rubric's note that C+ means "Significant gaps but not disqualifying — tool is usable with substantial effort." The gap here is sustainability risk, not current capability.

---

### 3.6 Supply Chain (Gate)

#### Strengths

- BSD 3-Clause license — maximally permissive, no copyleft, no government deployment restrictions ([F-1](supply_chain/F-1_core_license.md))
- Zero external dependencies — self-contained zip with all sub-packages bundled ([F-2](supply_chain/F-2_dependency_tree.md))
- All sub-packages BSD 3-Clause; GPL runtime components (Octave, GLPK) accessed via interpreter interface, no license contamination ([F-3](supply_chain/F-3_dependency_license_audit.md))
- Zero compiled extensions — 100% readable .m source code, no MEX files, no shared libraries ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- Complete execution path from API entry to solver convergence is inspectable .m source ([F-5](supply_chain/F-5_code_inspectability.md))
- Fully air-gap installable — zip of text files, no runtime network calls, no license server, no telemetry ([F-7](supply_chain/F-7_airgap_installability.md))
- All core functionality works on open-source solvers alone; no commercial solver required ([F-8](supply_chain/F-8_solver_dependency.md))
- Examples and documentation bundled in release zip, version-pinned, no mutable URLs ([F-9](supply_chain/F-9_getting_started_integrity.md))

#### Weaknesses

- No publisher-provided checksums or GPG signatures on releases — integrity relies on GitHub HTTPS delivery ([F-6](supply_chain/F-6_distribution_integrity.md))
- GitHub license detection reports `NOASSERTION` due to case file carve-out preamble (cosmetic; actual license is standard BSD-3) ([F-1](supply_chain/F-1_core_license.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| F-1  | pass | BSD 3-Clause; case file carve-out documented |
| F-2  | pass | Zero external deps; all sub-packages bundled |
| F-3  | pass | All BSD-3; GPL only in runtime (Octave/GLPK) |
| F-4  | pass | Zero compiled extensions in distribution |
| F-5  | pass | Full execution path is readable .m source |
| F-6  | informational | No checksums/signatures; versioned GitHub Releases |
| F-7  | pass | Fully air-gap compatible |
| F-8  | pass | All functionality on open-source solvers |
| F-9  | informational | Docs/examples bundled in release; web docs track latest |

#### Grade Rationale

Per rubric: "A: Permissive license (MIT or BSD-3). Full dependency tree is open-source, auditable, and version-pinned in release artifacts. Full execution path is readable source with no opaque binaries. Any compiled extensions have publicly available, buildable source. Functional on open-source solvers alone for all target use cases. Releases versioned, signed, and distributed through standard trustworthy channels. Getting-started examples pinned to a specific release. Dependency tree shallow enough for tractable audit. All components installable offline." MATPOWER meets every element of the A standard except "signed" releases (no GPG signatures or publisher checksums). This is a minor gap that does not materially affect the security authorization path — the distribution is a zip of text files that can be audited by `diff` against the Git repository. Grade: **A**.

---

## 4. Cross-Cutting Observations

### API Friction Patterns

MATPOWER exhibits a sharp two-tier friction profile. Core analyses (PF, OPF, sensitivity) follow a consistent three-step pattern — `loadcase`, `mpoption`, solver call — with results in a predictable struct layout. Column-index ergonomics via `define_constants` are the main friction point, requiring users to load named constants or memorize numeric indices. This is a MATLAB ecosystem pattern, not MATPOWER-specific.

MOST-based analyses (SCUC, SCED, stochastic, SCOPF) have materially higher friction: five interrelated data structures (mpc, xGenData, transmat, profiles, contab), a 3D profile values array with non-intuitive structure, and result extraction that requires reading source code. The profile system (`idx_ct` constants, `chgtype` field with PR_REP/PR_REL/PR_ADD modes) adds a dimension of complexity that the MOST manual documents but does not make accessible. The data prep effort dwarfs the actual solve call for every MOST test.

### Documentation Gaps

Core MATPOWER documentation is strong — function help text, User's Manual, column index defines. Three specific gaps are notable:

1. **Absence of features is not documented.** The lossy DC OPF limitation and distributed slack absence are discoverable only through GitHub issues or source code reading. The existence of `get_losses()` (which only works on AC PF results) creates false expectations.
2. **Solver compatibility matrix is missing.** The GLPK/MIQP incompatibility that affects SCUC is not documented anywhere.
3. **MOST result extraction is under-documented.** Fields like `mdo.results.ExpectedDispatch` are not in the manual; users must read MOST source.

### Solver Ecosystem

The available solver stack on Octave is limited: MIPS (built-in QP/NLP) and GLPK (LP/MILP). This pairing has specific blind spots:

- GLPK cannot solve QP (no quadratic costs with integers), requiring PWL conversion for SCUC.
- MIPS struggles with large QPs (stochastic MOST on SMALL failed with +/-10% load variation on TINY, and entirely on SMALL).
- HiGHS is supported in MATPOWER 8.1 but requires MEX compilation on Octave (not available in our environment).
- The solver swap mechanism itself is excellent — single parameter change, no reformulation.

### Architecture Quality

MATPOWER's architecture is a genuine strength. The unified `mpc` struct enables seamless workflow composition across all analysis types. The mutable struct pattern makes contingency loops, parameter sweeps, and scenario analysis trivially implementable without model rebuild overhead. The `opt_model` extraction as a standalone package (MP-Opt-Model) demonstrates real separation of concerns. The new MP-Core three-layer framework (data model, network model, mathematical model) adds principled extensibility through element composition. The `userfcn` callback system and its built-in toggles (`toggle_iflims`, `toggle_reserves`, `toggle_softlims`) serve as well-documented extension templates.

---

## 5. Items Requiring Human Spot-Check

- [ ] **A-5 (SCUC) workaround classification** — PWL conversion for GLPK is classified as "stable workaround." Verify this is correct given that the workaround would be unnecessary with HiGHS (which MATPOWER supports but was not available in the test environment). Does the solver limitation change the expressiveness assessment?
- [ ] **A-10 (Lossy DC OPF) qualified pass** — The loss component is computed post-hoc and is NOT part of the optimization formulation. Verify that "qualified pass" (vs "fail") is appropriate given that the rubric asks "Can LMPs be decomposed into energy, congestion, and loss components?" The energy + congestion decomposition is exact; only the loss component is approximate and external.
- [ ] **A-11 (Distributed slack OPF) qualified pass** — The workaround produces correct results but requires ~100 LOC of manual `opt_model` construction with undocumented sign conventions. Verify the "stable workaround" classification given the undocumented shadow price sign conventions.
- [ ] **B-8 (Reference bus config) qualified pass** — Parts (a) and (b) pass cleanly; only part (c) distributed slack requires workaround. Verify that "qualified pass" is appropriate vs "pass" given that 2/3 sub-parts are native.
- [ ] **C-5 (Contingency sweep) qualified pass** — LODF precomputation exceeds 10 min on MEDIUM but PTDF-based N-1 screening is feasible in ~15s. Verify whether the qualified pass is appropriate given the LODF bottleneck vs the PTDF alternative.
- [ ] **C-10 (Distributed slack scale) qualified pass** — Estimated timing (~90-120s) based on component measurements, not a single end-to-end run. Verify whether the estimated timing is acceptable or if a timed end-to-end run is needed.
- [ ] **Maturity grade C+ vs B-** — The bus factor of 1 and absence of funding are serious, but the project has 462 test files, CI, and 28 years of continuous development. The boundary between C+ and B- requires human judgment on how heavily to weight sustainability risk vs current engineering quality.
- [ ] **MATPOWER as reference benchmark** — The rubric notes "MATPOWER (reference benchmark only -- MATLAB runtime disqualifies for classified deployment)." Verify that the Octave runtime changes this assessment for the supply chain gate, given that all testing was conducted on Octave.

---

## 6. Methodology Notes

- **Scale cap applied:** MEDIUM (all gate tiers G-1/G-2/G-3 passed)
- **Tests skipped:** None — all 57 protocol tests executed
- **Solver versions:** MIPS 1.5.2 (bundled), GLPK (bundled with Octave 9.2)
- **Tool version:** MATPOWER 8.1 (12-Jul-2025), SHA256: `7f13b1441669a64e312d14a60e564cd91977ff1676ff77d25538e94ff313dd56`
- **Runtime:** GNU Octave 9.2 on Ubuntu 24.04 (devcontainer)
- **HiGHS availability:** Not available in test environment (requires MEX compilation on Octave). MATPOWER 8.1 supports HiGHS but it was not tested.
- **Scalability timeout:** 10 minutes per test (C-4, C-6, C-8 exceeded)
- **Reference networks:** IEEE 39-bus (TINY), ACTIVSg 2000 (SMALL), ACTIVSg 10000 (MEDIUM)
- **ACTIVSg 10k data note:** 19.4% of branches (2,462/12,706) have zero RATE_A; set to 9999 MW for OPF tests per standard MATPOWER convention

### Phase 2 Readiness Summary

| Finding | Status | Key Detail |
|---------|--------|------------|
| P2-1: PSS/E RAW parsing | Native, built-in | `psse2mpc()` supports Rev 23-33+; 143 unit tests; round-trip verified |
| P2-2: Piecewise-linear costs | Native, first-class | MODEL=1 gencost; CCV formulation; verified with 3-segment and 10-segment tests |
| P2-3: Commitment injection | Full pipeline demonstrated | SCUC -> DCOPF -> ACPF with low friction; consistent struct API throughout |
