# Synthesis Report: PyPSA v1.1.2

**Contract:** FA714626C0006
**Tool:** PyPSA (Python for Power System Analysis)
**Version:** 1.1.2 (released 2026-02-23)
**Evaluation date:** 2026-03-24
**Protocol version:** v11
**Skill version:** v2

---

## 1. Executive Summary

PyPSA v1.1.2 is a mature, well-architected Python power system analysis tool with strong expressiveness across DCPF, ACPF, DC OPF, SCUC, SCOPF, lossy OPF, and multi-period storage optimization. All three gate tests passed (TINY/SMALL/MEDIUM ingestion), establishing a MEDIUM scale cap. The tool's primary strengths are its pandas DataFrame-native data model enabling zero-friction interoperability, a clean `extra_functionality` callback for custom constraint injection, and a robust open-source supply chain anchored by the bundled HiGHS solver (MIT). Key limitations include the architectural absence of distributed slack in DC OPF [tool-specific], linopy model-building overhead dominating MEDIUM-scale wall-clock times [tool-specific], HiGHS single-threaded MILP performance limiting SCUC at SMALL scale [solver-specific], and no PSS/E format ingestion capability. The supply chain gate passes with one GPL-2.0 dependency (Levenshtein) flagged for review.

---

## 2. Test Results Summary

| Criterion | Tests Run | Pass | Qualified Pass | Partial/Constrained | Fail | Skip | Informational | Confidence | Key Evidence |
|-----------|----------|------|----------------|---------------------|------|------|---------------|------------|--------------|
| Problem Expressiveness | 11 | 8 | 2 (A-6, A-12) | 1 (A-11) | 0 | 0 | 0 | High | Native DCPF/ACPF/DCOPF/SCUC/SCOPF/lossy OPF/storage; distributed slack OPF blocked |
| Extensibility | 8 | 8 | 0 | 0 | 0 | 0 | 0 | High | extra_functionality callback, NetworkX graph, PTDF, scenario loops |
| Scalability | 10 | 8 | 0 | 1 (C-4 constrained), 1 (C-10 partial) | 0 | 0 | 0 | High | MEDIUM DCPF/ACPF/DCOPF/SCOPF/PTDF pass; SCUC constrained at SMALL; dist. slack blocked |
| Workforce Accessibility | 5 | 3 | 0 | 0 | 0 | 0 | 2 (D-2, D-5) | High | Sub-7s install-to-solve, examples work, meaningful errors |
| Maturity & Sustainability | 7 | 7 | 0 | 0 | 0 | 0 | 0 | High | 32 releases/24mo, 84% coverage, 99 contributors, TSO/regulator adoption |
| Supply Chain (gate) | 9 | 8 | 1 (F-3) | 0 | 0 | 0 | 1 (F-2) | High | MIT core, 1 GPL dep (Levenshtein), fully air-gap installable |
| FNM Ingestion | 5 | 1 (G-FNM-3) | 0 | 0 | 1 (G-FNM-1) | 1 (G-FNM-2) | 2 (G-FNM-4, G-FNM-5) | High | No PSS/E parsing; DCPF 100% match via MATPOWER fallback |
| P2 Readiness | 3 | 0 | 0 | 0 | 0 | 0 | 3 | Medium | No PSS/E RAW parsing; tranche workaround for piecewise costs; commitment injection capable |

**Note:** Gate tests (G-1, G-2, G-3) are excluded from pass rate statistics. All three passed.

**Overall non-gate, non-informational test outcomes:** 38 pass, 3 qualified_pass, 2 partial_pass, 1 constrained_pass, 1 fail, 1 skip. No cascaded failures beyond C-10 (blocked by A-11).

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness (Suite A)

#### Strengths

- Native DCPF via direct sparse linear solve with no external optimizer needed ([A-1](expressiveness/A-1_dcpf.md))
- Newton-Raphson ACPF with first-class convergence diagnostics (converged, n_iter, residual) ([A-2](expressiveness/A-2_acpf.md))
- DC OPF with LMP extraction, hard branch constraint enforcement, and shadow prices via linopy duals ([A-3](expressiveness/A-3_dcopf.md))
- DC OPF to AC PF feasibility check within the same model context, no file export/reimport ([A-4](expressiveness/A-4_ac_feasibility.md))
- Built-in SCUC with committable generators, min up/down times, startup costs, ramp limits -- all as native attributes ([A-5](expressiveness/A-5_scuc.md))
- Built-in SCOPF via BODF-based N-1 contingency constraints in the LP formulation ([A-9](expressiveness/A-9_scopf.md))
- Native lossy DC OPF with piecewise-linear loss approximation (`transmission_losses` parameter) ([A-10](expressiveness/A-10_lossy_dcopf_lmp.md))
- Multi-period DCOPF with native StorageUnit (cyclic SoC, charge/discharge efficiencies) ([A-12](expressiveness/A-12_multiperiod_dcopf_storage.md))

#### Weaknesses

- Distributed slack DC OPF is architecturally impossible -- linopy model has no Bus-v_ang variables [tool-specific] ([A-11](expressiveness/A-11_distributed_slack_opf.md))
- Branch shadow prices (`mu_upper`/`mu_lower`) not populated after `n.optimize()` in v1.1.2 [tool-specific] ([A-3](expressiveness/A-3_dcopf.md), [A-12](expressiveness/A-12_multiperiod_dcopf_storage.md))
- No `fix_commitment()` API for two-stage UC/ED workflow [tool-specific] ([A-6](expressiveness/A-6_sced.md))
- SCOPF API excludes transformer contingencies (Lines only in `branch_outages`) [tool-specific] ([A-9](expressiveness/A-9_scopf.md))
- `import_from_pypower_ppc` does not import gencost or honor branch status [tool-specific] (all gate tests, addressed by shared loader)

#### Workarounds Required

- A-6 SCED: Manual `p_min_pu`/`p_max_pu` bound construction to fix commitment schedule -- **stable** (documented public API) ([A-6](expressiveness/A-6_sced.md))
- A-12 shadow prices: Extract from `n.model.constraints['Line-fix-s-upper'].dual` instead of `n.lines_t.mu_upper` -- **fragile** (depends on linopy internal constraint naming) ([A-12](expressiveness/A-12_multiperiod_dcopf_storage.md))
- A-11 distributed slack: Available in AC PF context (`n.pf(distribute_slack=True)`) but blocked in OPF context -- **blocking** ([A-11](expressiveness/A-11_distributed_slack_opf.md))

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| A-1 | TINY | pass | -- | -- | 1.94s | 143 |
| A-2 | TINY | pass | -- | -- | 2.11s | 245 |
| A-3 | TINY | pass | -- | -- | 3.30s | 271 |
| A-4 | TINY | pass | -- | -- | 2.11s | 346 |
| A-5 | TINY | pass | -- | -- | 6.77s | 467 |
| A-6 | TINY | qualified_pass | -- | stable | 3.88s | 558 |
| A-9 | TINY | pass | -- | -- | 2.63s | 335 |
| A-10 | TINY | pass | -- | -- | 2.21s | 332 |
| A-11 | TINY | partial_pass | -- | blocking | 1.90s | 326 |
| A-12 | TINY | qualified_pass | -- | fragile | 7.32s | 433 |

#### Findings Summary

PyPSA demonstrates broad expressiveness across standard power system formulations. Nine of eleven tests pass or qualify. The distributed slack OPF limitation (A-11) is the only blocking architectural gap -- PyPSA's flow-based OPF formulation lacks angle variables, making distributed slack fundamentally unachievable [tool-specific]. The shadow price assignment gap and missing `fix_commitment()` method are usability issues, not capability gaps. SCOPF's transformer exclusion is a notable API restriction but does not prevent N-1 analysis on line contingencies.

---

### 3.2 Extensibility (Suite B)

#### Strengths

- Clean `extra_functionality` callback for custom constraint injection with linopy model access ([B-1](extensibility/B-1_custom_constraints.md))
- Native NetworkX graph export via `n.graph()` -- zero-friction BFS/DFS/shortest-path ([B-2](extensibility/B-2_graph_access.md))
- N-M contingency sweep via `n.copy()` + `n.lpf()` with no file re-reads (3,276 cases in 213s) ([B-3](extensibility/B-3_contingency_sweep.md))
- Programmatic timeseries injection via DataFrame assignment for stochastic scenarios ([B-4](extensibility/B-4_stochastic_scenario.md))
- DataFrame-native results -- zero-friction export to CSV/Parquet/HDF5 ([B-5](extensibility/B-5_interoperability.md))
- Well-separated 4-layer architecture with 5 documented injection points ([B-6](extensibility/B-6_code_architecture.md))
- Slack bus reconfigurable via 2-line DataFrame assignment, no model reconstruction ([B-8](extensibility/B-8_reference_bus_config.md))
- Native PTDF extraction with machine-precision flow predictions (max error 1.9e-14 pu) ([B-9](extensibility/B-9_ptdf_extraction.md))

#### Weaknesses

- `n.lpf_contingency()` broken on Python 3.12+ [tool-specific] (observation from B-3)
- DCPF solver (scipy.sparse) hardcoded -- not swappable via parameter [tool-specific] ([B-6](extensibility/B-6_code_architecture.md))
- SubNetwork-level methods (calculate_B_H, calculate_PTDF, calculate_Y) undocumented in user guide [tool-specific] ([B-6](extensibility/B-6_code_architecture.md))

#### Workarounds Required

None across all extensibility tests. All functionality achieved through documented public APIs.

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| B-1 | TINY | pass | -- | -- | 3.93s | 309 |
| B-2 | TINY | pass | -- | -- | 1.84s | 122 |
| B-3 | TINY | pass | -- | -- | 213.0s | 256 |
| B-4 | TINY | pass | -- | -- | 7.46s | 279 |
| B-5 | TINY | pass | -- | -- | 1.36s | 136 |
| B-6 | N/A | pass | -- | -- | 1.09s | 349 |
| B-8 | TINY | pass | -- | -- | 2.36s | 247 |
| B-9 | TINY | pass | -- | -- | 1.32s | 221 |

#### Findings Summary

PyPSA achieves a clean sweep across all extensibility tests. The `extra_functionality` callback, NetworkX graph bridge, DataFrame-native data model, and PTDF extraction provide a comprehensive extensibility surface. No workarounds were required for any test. The broken `lpf_contingency()` on Python 3.12+ is a maintenance gap but does not block N-M contingency analysis (BODF or copy+lpf patterns work).

---

### 3.3 Scalability (Suite C)

#### Strengths

- DCPF on MEDIUM (10k buses) in 22s with 2.1 GB memory ([C-1](scalability/C-1_dcpf_medium.md))
- ACPF on MEDIUM converges in 5 NR iterations, residual 1.86e-9 ([C-2](scalability/C-2_acpf_medium.md))
- DC OPF on MEDIUM: HiGHS solves in 6.2s (solver-only); cross-solver match with GLPK ([C-3](scalability/C-3_dcopf_medium.md))
- SCOPF with 50 contingencies on MEDIUM: 1.3M-row LP solved in 29.5s (solver-only) ([C-8](scalability/C-8_scopf_medium.md))
- PTDF computed on MEDIUM (12,706 x 10,000) in 7.9s ([C-9](scalability/C-9_ptdf_medium.md))
- AC feasibility at SMALL and MEDIUM: converges at 0% relaxation (no relaxation needed) ([C-5](scalability/C-5_ac_feasibility_progressive_SMALL.md), [C-5](scalability/C-5_ac_feasibility_progressive_MEDIUM.md))
- Solver swap via single parameter change, no reformulation ([C-7](scalability/C-7_solver_swap_medium.md))

#### Weaknesses

- Linopy model building dominates MEDIUM DC OPF wall-clock: 302s overhead vs 6s solve [tool-specific] ([C-3](scalability/C-3_dcopf_medium.md))
- HiGHS single-threaded MILP cannot solve root LP of SMALL SCUC within 600s [solver-specific] ([C-4](scalability/C-4_scuc_small.md))
- HiGHS 32-thread SCUC achieves only 1.63% MIP gap (target: 1%) in 1800s budget [solver-specific] ([C-4](scalability/C-4_scuc_small.md))
- Distributed slack DC OPF blocked at MEDIUM (cascaded from A-11) [tool-specific] ([C-10](scalability/C-10_distributed_slack_medium.md))
- HiGHS simplex does not parallelize -- 32-thread SCOPF shows 0.92x speedup [solver-specific] ([C-8](scalability/C-8_scopf_medium.md))
- SCIP not installed in devcontainer -- dual-solver MILP comparison not possible (environment issue) ([C-4](scalability/C-4_scuc_small.md))
- Memory scales super-linearly: 84 MB (SMALL) to 2,099 MB (MEDIUM) for ACPF (25x for 5x buses) [tool-specific] ([C-5](scalability/C-5_ac_feasibility_progressive_MEDIUM.md))

#### Workarounds Required

- C-3, C-8: Generator marginal costs assigned from gencost via shared loader -- **stable** ([C-3](scalability/C-3_dcopf_medium.md))
- C-3, C-8: `overwrite_zero_s_nom=99999.0` for MATPOWER zero-rated branches -- **stable** ([C-3](scalability/C-3_dcopf_medium.md))

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| C-1 | MEDIUM | pass | -- | -- | 22.2s | 144 |
| C-2 | MEDIUM | pass | -- | -- | 21.7s | 196 |
| C-3 | MEDIUM | pass | -- | stable | 604.1s | 224 |
| C-4 | SMALL | constrained_pass | -- | -- | 1836.5s | 353 |
| C-5 (SMALL) | SMALL | pass | -- | -- | 14.9s | 337 |
| C-5 (MEDIUM) | MEDIUM | pass | -- | -- | 193.1s | 243 |
| C-7 | MEDIUM | pass | -- | -- | 1313.7s | 185 |
| C-8 | MEDIUM | pass | -- | stable | 315.1s | 376 |
| C-9 | MEDIUM | pass | -- | -- | 20.1s | 192 |
| C-10 | MEDIUM | partial_pass | A-11 | blocking | 698.2s | 221 |

**Failure breakdown:** 0 independent fails, 1 cascaded partial_pass (C-10 from A-11), 1 constrained_pass (C-4 solver-limited).

#### Findings Summary

PyPSA scales well to MEDIUM for DCPF, ACPF, DC OPF, SCOPF, and PTDF. The dominant scalability bottleneck for optimization is linopy model construction overhead [tool-specific], not solver time -- HiGHS solves the MEDIUM DC OPF LP in 6.2s but the full `n.optimize()` call takes 308s. SCUC at SMALL scale is constrained by HiGHS MILP performance [solver-specific]; a commercial solver would likely close the MIP gap faster. The distributed slack OPF limitation (C-10) is a cascaded architectural finding from A-11, not a scale-dependent failure.

---

### 3.4 Workforce Accessibility (Suite D)

#### Strengths

- Sub-7s install-to-first-solve with `uv sync` + `import pypsa` + `n.lpf()` ([D-1](accessibility/D-1_install_to_first_solve.md))
- All 6 built-in examples load and 3/3 tested solve unmodified ([D-3](accessibility/D-3_example_verification.md))
- Meaningful error diagnostics for all 3 deliberate error scenarios -- no silent failures ([D-4](accessibility/D-4_error_quality.md))
- DataFrame-native results enable immediate use of pandas ecosystem tools ([B-5](extensibility/B-5_interoperability.md))

#### Weaknesses

- 5 of 10 Suite A tests implementable from docs alone; 2 require trial-and-error [tool-specific] ([D-2](accessibility/D-2_documentation_audit.md))
- Transformer `b` field has dual semantics (shunt vs series susceptance) -- undocumented [tool-specific] ([D-2](accessibility/D-2_documentation_audit.md))
- Shadow price extraction, PTDF bus ordering, mixin architecture undocumented [tool-specific] ([D-2](accessibility/D-2_documentation_audit.md))
- Deferred validation: invalid bus reference accepted at `n.add()`, caught only at `optimize()` [tool-specific] ([D-4](accessibility/D-4_error_quality.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| D-1 | pass | 0.4s install, 6.4s first solve (post-bytecode cache) |
| D-2 | informational | 50% docs-only implementability for Suite A |
| D-3 | pass | 6/6 examples load, 3/3 solve |
| D-4 | pass | 3/3 error scenarios produce meaningful diagnostics |
| D-5 | informational | Mean 275 LOC across TINY test scripts |

#### Findings Summary

PyPSA has excellent onboarding (sub-7s install, working examples, no compiler needed) and good error quality. Documentation is strong for standard workflows but has gaps for intermediate use cases (shadow prices, DC/AC transformer semantics, PTDF ordering). The DataFrame-native data model is a significant accessibility advantage.

---

### 3.5 Maturity & Sustainability (Suite E)

#### Strengths

- 32 releases in 24 months, averaging 1.3/month; semver compliant since v1.0.0 ([E-1](maturity/E-1_release_cadence.md))
- 321 commits from 22 human contributors in 12 months; 95% substantive ([E-2](maturity/E-2_commit_activity.md))
- Bus factor 2-3 with successful founder-to-maintainer transition ([E-3](maturity/E-3_contributor_concentration.md))
- Multi-channel institutional funding: TU Berlin, OET/Sequoia, EU grants, commercial support ([E-4](maturity/E-4_funding_model.md))
- Median issue time-to-close: 0.9 days; 75% acknowledged ([E-5](maturity/E-5_issue_tracker_health.md))
- 84.4% code coverage via Codecov; multi-OS/multi-Python CI matrix with daily runs ([E-6](maturity/E-6_ci_cd_coverage.md))
- Planning-grade production adoption by 6+ TSOs, IEA, ACER, Shell, Saudi Aramco ([E-7](maturity/E-7_operational_adoption.md))

#### Weaknesses

- Merge concentration on single maintainer (lkstrp, 82% of merges) ([E-3](maturity/E-3_contributor_concentration.md))
- `n.lpf_contingency()` broken on Python 3.12+ across multiple releases (maintenance gap) (observation from B-3)
- Branch shadow price assignment bug persists in v1.1.2 [tool-specific] (observation from A-3)

#### Evidence Summary Table

| Test | Status | Key Metric |
|------|--------|------------|
| E-1 | pass | 32 releases / 24 months |
| E-2 | pass | 321 commits, 22 human contributors |
| E-3 | pass | Bus factor 2-3; top reviewer 58.1% |
| E-4 | pass | 5+ independent funding channels |
| E-5 | pass | 0.9-day median time-to-close |
| E-6 | pass | 84.4% coverage, daily CI, downstream testing |
| E-7 | pass | TSOs, regulators, oil majors, 1,905 GitHub stars |

#### Findings Summary

PyPSA has among the strongest maturity signals in the open-source power systems ecosystem. The combination of frequent releases, broad contributor base, institutional funding durability, and production adoption by TSOs and regulators represents a mature project. The merge concentration on a single maintainer is the primary risk factor but is mitigated by a broader review pool.

---

### 3.6 Supply Chain (Suite F) -- Gate

#### Strengths

- MIT-licensed core package with SPDX headers ([F-1](supply_chain/F-1_core_license.md))
- Pure Python with zero compiled extensions; all dependency binaries have open source ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- Full execution path inspectable from API to solver ([F-5](supply_chain/F-5_code_inspectability.md))
- PyPI distribution with SHA-256 hashes and automated CI/CD release ([F-6](supply_chain/F-6_distribution_integrity.md))
- Fully air-gap installable; no runtime network dependencies for computation ([F-7](supply_chain/F-7_airgap_installability.md))
- HiGHS (MIT) bundled as default solver; covers LP/MILP/QP ([F-8](supply_chain/F-8_solver_dependency.md))
- Self-contained examples with no mutable URLs ([F-9](supply_chain/F-9_getting_started_integrity.md))

#### Weaknesses

- 1 GPL-2.0-or-later direct dependency: `Levenshtein` (fuzzy string matching for UX) [tool-specific] ([F-3](supply_chain/F-3_dependency_license_audit.md))
- No Sigstore attestations (ecosystem-wide gap) ([F-6](supply_chain/F-6_distribution_integrity.md))
- Mandatory visualization/cloud dependencies (matplotlib, plotly, google-cloud-storage) inflate install footprint [tool-specific] ([F-2](supply_chain/F-2_dependency_tree.md))

#### Workarounds Required

- F-3 GPL dependency: replaceable with `rapidfuzz` (MIT, already a transitive dep) -- **stable** ([F-3](supply_chain/F-3_dependency_license_audit.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| F-1 | pass | MIT license, SPDX headers |
| F-2 | informational | 17 direct deps, ~70 transitive, max depth 4 |
| F-3 | qualified_pass | 1 GPL dep (Levenshtein), 85 permissive |
| F-4 | pass | Pure Python core; 249 .so files in deps, all with source |
| F-5 | pass | Full path inspectable; zero opaque steps |
| F-6 | pass | PyPI with hashes; no Sigstore (ecosystem gap) |
| F-7 | pass | Fully air-gap installable |
| F-8 | pass | HiGHS (MIT) bundled; GLPK, Ipopt available |
| F-9 | pass | Self-contained examples, no mutable URLs |

#### Findings Summary

The supply chain gate passes. The single GPL-2.0 dependency (Levenshtein) is a convenience feature (fuzzy attribute name matching) replaceable with the MIT-licensed `rapidfuzz`. For internal-use deployments, GPL imposes no additional obligations. The bundled HiGHS solver under MIT license eliminates the common commercial-solver dependency concern.

---

## 4. FNM Ingestion Findings (Suite G)

### Data Model Fidelity

**G-FNM-1 (Intermediate Format Ingestion): FAIL** -- PyPSA v1.1.2 has no import method that accepts PSS/E v31 record types. The six available import methods (`import_from_csv_folder`, `import_from_pypower_ppc`, `import_from_pandapower_net`, `import_from_hdf5`, `import_from_netcdf`, `import_from_excel`) all expect tool-native formats. No PSS/E field translator or import adapter exists. ([G-FNM-1](fnm_ingestion/G-FNM-1_intermediate_format_ingestion.md))

**G-FNM-2 (Field Fidelity): SKIP** -- Blocked by G-FNM-1. Field-level fidelity assessment requires successful PSS/E CSV parsing. The MATPOWER fallback path inherently loses PSS/E-specific fields (83-column transformer records, switched shunts, FACTS, multi-terminal DC). ([G-FNM-2](fnm_ingestion/G-FNM-2_field_fidelity.md))

### Power Flow Verification

**G-FNM-3 (DCPF Verification): PASS** -- 100% of buses (~28,000) and 100% of branches (~33,000) pass all tolerance thresholds via MATPOWER fallback path. Max bus angle deviation: 1.07e-08 degrees. Max branch flow deviation: 5.76e-07%. Bus injection power balance verified on all buses (max mismatch: 1.32e-07 MW). The shared `matpower_loader.load_pypsa()` addresses the `import_from_pypower_ppc` branch status bug that caused the original v10 G-FNM-3 failure. Solve time: 40.1s, peak memory: 16,289 MB. ([G-FNM-3](fnm_ingestion/G-FNM-3_dcpf_verification.md))

**G-FNM-4 (ACPF Convergence): INFORMATIONAL** -- PyPSA's Newton-Raphson ACPF did not converge at any relaxation level (0%, 10%, 20%) on the ~28,000-bus FNM. SuperLU factorization failure at all levels. Consistent with MATPOWER 8.1's failure on the same network. The FNM planning model lacks a feasible AC operating point at full load. PyPSA's ACPF solver offers fewer recovery options than MATPOWER (no continuation PF, no fast-decoupled variants). [solver-specific: SuperLU factorization on ill-conditioned admittance matrix] ([G-FNM-4](fnm_ingestion/G-FNM-4_acpf_convergence.md))

### Supplemental Data Representability

**G-FNM-5: 34% Native / 23% Extension / 43% External** across the standardized 44-field set. PyPSA achieves 57% in-model representability (N+E). Extension mechanism empirically verified: custom columns on component DataFrames persist correctly. The highest extension potential is in CONTINGENCY (50% E via extra_functionality + BODF) and INTERFACE (100% E via PTDF constraints). Market-layer concepts (hub types, outage schedules, participation factors) are external to all power flow tools. ([G-FNM-5](fnm_ingestion/G-FNM-5_supplemental_csv_representability.md))

### FNM Evidence Integration

- **Expressiveness:** The G-FNM-1 failure (no PSS/E parsing) is a format gap, not an expressiveness limitation. G-FNM-3's machine-precision DCPF match confirms PyPSA's formulation correctness on large networks (~28,000 buses). G-FNM-4's ACPF non-convergence is consistent with MATPOWER and reflects network characteristics, not a tool deficiency.
- **Extensibility:** G-FNM-5's 23% extension-representable rate demonstrates that PyPSA's DataFrame-centric architecture enables supplemental data storage, though semantic interpretation requires custom code.
- **Scalability:** G-FNM-3 demonstrates DCPF scaling to LARGE (~28,000 buses) in 40s with 16 GB memory. Memory overhead is notable (16 GB for a sparse linear solve on ~28k buses).

---

## 5. Cross-Cutting Observations

### API Friction Patterns

- **Shadow price assignment gap (medium):** `n.lines_t.mu_upper`/`mu_lower` empty after `optimize()` in v1.1.2. Must extract from linopy constraint duals. Affects A-3, A-12. (observations: api-friction A-3, A-12)
- **Transformer `b` field dual semantics (medium):** Series susceptance for DCPF vs shunt susceptance for ACPF. Undocumented. Causes silent ACPF divergence when using DC-oriented loader. (observations: api-friction A-2, convergence-quality A-11)
- **No `fix_commitment()` method (medium):** Two-stage UC/ED requires manual bound manipulation (~20 LOC boilerplate). (observation: api-friction A-6)
- **SCOPF transformer exclusion (medium):** `branch_outages` accepts Lines only. (observation: api-friction A-9)
- **Linopy model building overhead (medium):** 98% of MEDIUM DC OPF wall-clock is model construction, not solving. (observation: api-friction C-3)
- **No MIP gap API access (low):** Termination gap only available in solver console log. (observation: api-friction C-4)
- **PSS/E format gap (high):** No ingestion path for PSS/E data in any form. (observation: api-friction G-FNM-1)
- **Positive: Storage API (low friction):** StorageUnit with cyclic SoC is well-designed and intuitive. (observation: api-friction A-12, positive)
- **Positive: DataFrame export (zero friction):** Results are pandas DataFrames natively. (observation: api-friction B-5, positive)

### Documentation Gaps

- Transformer `b` field semantics (DC vs AC) not documented
- Branch shadow price extraction via linopy not shown in examples
- PTDF column ordering (`sn.buses_o` not `n.buses.index`) requires source reading
- Mixin architecture and SubNetwork-level methods undocumented in user guide
- SCOPF transformer restriction not mentioned in API docs
- Two-stage UC/ED workflow not covered in any example

### Solver Ecosystem

- **HiGHS LP performance:** Solves MEDIUM DC OPF in 6.2s. Strong LP performance. [solver-specific]
- **HiGHS MILP scalability wall:** Root LP of SMALL SCUC takes >600s single-threaded, ~1,230s with 32 threads. 1.63% MIP gap at timeout. [solver-specific]
- **HiGHS simplex non-parallel:** Dual simplex does not benefit from multi-threading (0.92x on SCOPF). IPM would parallelize but is not the default. [solver-specific]
- **GLPK 14x slower than HiGHS:** On MEDIUM DC OPF, GLPK LP solve takes 117s vs HiGHS 6.2s. Identical solutions. [solver-specific]
- **SCIP not installed:** Environment configuration issue, not a PyPSA limitation. [environment issue]
- **Solver swap is seamless:** Single `solver_name` parameter change, no reformulation needed. [tool-specific, positive]

### Architecture Quality

- Clean 4-layer architecture with explicit model-build/solve separation for OPF
- 8-mixin class composition with 5 documented injection points
- DataFrame-native data model provides zero-impedance interoperability
- NetworkX graph bridge enables immediate access to graph algorithm library
- OPF formulation via linopy provides solver abstraction layer
- DCPF solver (scipy.sparse) is hardcoded -- no parameter to swap

### FNM Data Model

- `import_from_pypower_ppc` ignores MATPOWER branch status -- shared loader patches this deterministically
- No formulation difference from MATPOWER for DCPF when branch status is correctly handled
- PyPSA DCPF matches MATPOWER at float64 machine precision on the ~28,000-bus FNM
- 57% in-model supplemental CSV representability (34% N + 23% E) via DataFrame custom columns

---

## 6. Items Requiring Human Spot-Check

- [ ] **A-6 qualified_pass** -- The `fix_commitment()` workaround uses documented public API but involves non-obvious manual bound manipulation. Verify the "stable" classification is appropriate.
- [ ] **A-12 qualified_pass** -- Shadow price extraction via `n.model.constraints['Line-fix-s-upper'].dual` depends on linopy internal constraint naming. Verify "fragile" classification.
- [ ] **A-11 distributed slack OPF** -- Partial pass based on PF-context availability but OPF-context impossibility. Verify this correctly reflects the protocol's pass conditions.
- [ ] **C-4 constrained_pass** -- SCUC achieved 1.63% MIP gap (target: 1%) with 78 cycling generators. Verify that the 1.63% gap and 32-thread requirement justify constrained rather than fail.
- [ ] **C-10 cascaded from A-11** -- Confirm that the C-10 partial_pass is correctly attributed as cascaded (not independent).
- [ ] **F-3 GPL dependency** -- Levenshtein (GPL-2.0-or-later) is a direct dependency used for UX fuzzy matching. Verify the "qualified_pass" classification given the internal-use mitigation and `rapidfuzz` (MIT) replacement path.
- [ ] **G-FNM-3 MATPOWER fallback path** -- DCPF 100% match achieved via shared loader patches (branch status, transformer susceptance). Verify that the loader workaround (stable) is appropriately credited rather than treated as a native capability.
- [ ] **Solver-vs-tool attribution for linopy overhead** -- The 302s linopy model-building overhead on MEDIUM DC OPF is classified as [tool-specific]. Verify this is correct (linopy is integral to PyPSA, not an external solver).
- [ ] **HiGHS MILP single-threaded limitation** -- Classified as [solver-specific]. Verify this attribution given that PyPSA bundles HiGHS as its default/only solver and does not offer parallel MILP alternatives.

---

## 7. Methodology Notes

- **Scale cap applied:** MEDIUM -- All three gate tests (G-1, G-2, G-3) passed. TINY (39 buses), SMALL (2,000 buses), and MEDIUM (10,000 buses) networks all ingested successfully.
- **FNM status:** Suite G partially executed. G-FNM-1 failed (no PSS/E parsing). G-FNM-2 skipped (blocked by G-FNM-1). G-FNM-3 through G-FNM-5 executed via MATPOWER fallback path.
- **Tests skipped:** G-FNM-2 (blocked by G-FNM-1). SCIP solver comparison in C-4 and C-7 (SCIP not installed in devcontainer).
- **Solver versions:** HiGHS 1.13.1, GLPK 5.0, Ipopt (via Pyomo, available but not primary). SCIP not installed.
- **Tool version:** PyPSA 1.1.2 with linopy 0.6.4
- **Python version:** 3.12
- **Devcontainer environment:** Ubuntu 24.04 + Python 3.12 + Julia 1.10 + Octave + uv
