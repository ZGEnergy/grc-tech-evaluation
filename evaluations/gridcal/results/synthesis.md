# Synthesis Report: GridCal (VeraGridEngine 5.6.28)

**Contract:** FA714626C0006
**Protocol version:** v10
**Tool version:** VeraGridEngine 5.6.28 (PyPI: `veragridengine`)
**Evaluation date:** 2026-03-13

---

## 1. Executive Summary

GridCal is a Python-based power system modeling tool backed by eRoots Analytics (Barcelona) under an open-core business model. It passes all gate criteria with a MEDIUM scale cap and demonstrates strong core capabilities in DCPF, DCOPF, SCOPF, PTDF extraction, and contingency analysis. Its most significant weaknesses are a blocking battery energy balance sign error (A-12), distributed slack hardcoded off in OPF (A-11), a monolithic OPF formulation with no public API for custom constraint injection (B-1), and a PSS/e parser limited to v35 format that cannot parse the FNM v31 RAW file. The tool has a bus factor of 1, zero CI test execution, and documentation lagging 6 minor versions behind the installed release. Supply chain findings (MPL-2.0, 2 LGPL transitive deps, pure Python core) are well within the gate threshold.

---

## 2. Grade Recommendations Table

| Criterion | Grade | Confidence | Key Evidence |
|-----------|-------|------------|--------------|
| Problem Expressiveness | B | High | 8/10 pass (2 blocking fails: A-11 distributed slack, A-12 storage sign error); native SCOPF and UC |
| Extensibility | B- | High | PTDF/graph/contingency sweep all native; custom constraints require fragile monkey-patching (B-1); monolithic OPF |
| Scalability | B | Medium | DCPF 1.0s, ACPF 3.1s, DCOPF 8.4s, SCOPF 29s on MEDIUM (10k bus); SCUC requires snapshot workaround; 1 cascaded fail |
| Workforce Accessibility | C+ | High | 2/10 Suite A tests completable from docs; 0/2 tutorials run; OPF reports converged on infeasible; median 183 NBNC LOC |
| Maturity & Sustainability | C | High | Bus factor 1, zero PR reviews, no tests in CI, 209 releases/24mo, broken tutorials, battery sign error shipped |
| Supply Chain (Gate) | B- | High | MPL-2.0, pure Python core, 62 deps with 2 LGPL; no signing, single-account PyPI publish, sdist-only |

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness

#### Strengths
- Native DC OPF with LMP extraction and 7 binding branches under congestion ([A-3](expressiveness/A-3_dcopf.md))
- Native SCOPF via `consider_contingencies=True` with LODF-based security constraints embedded in optimization ([A-9](expressiveness/A-9_scopf.md))
- Native 24-hour SCUC with min up/down, startup costs, ramp rates via `OpfDispatchMode.UnitCommitment` ([A-5](expressiveness/A-5_scuc.md))
- AC power flow convergence in 4 NR iterations with residual 3.32e-11 on TINY ([A-2](expressiveness/A-2_acpf.md))
- AC feasibility check via same-model-context workflow — no export/reimport needed ([A-4](expressiveness/A-4_ac_feasibility.md))

#### Weaknesses
- Distributed slack hardcoded off in OPF formulation (`linear_opf_ts.py` line 3022) despite working in power flow ([A-11](expressiveness/A-11_distributed_slack_opf.md))
- Battery energy balance sign error causes continuous discharge and energy gain — blocking formulation bug ([A-12](expressiveness/A-12_multiperiod_dcopf_storage.md))
- Loss approximation produces negligible 0.055 MW (0.0009% of load) due to formula using branch rating instead of actual flow ([A-10](expressiveness/A-10_lossy_dcopf_lmp.md))
- No LMP decomposition into energy + congestion + loss components ([A-10](expressiveness/A-10_lossy_dcopf_lmp.md))

#### Workarounds Required
- "SCED via profile manipulation (`Pmax_prof`/`Pmin_prof` zeroing) rather than dedicated commitment-fixing API ([A-6](expressiveness/A-6_sced.md)) — **stable**"

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| A-1 DCPF | TINY | pass | — | — | 1.33s | 137 |
| A-2 ACPF | TINY | pass | — | — | 2.24s | 198 |
| A-3 DCOPF | TINY | pass | — | — | 1.37s | 200 |
| A-4 AC feasibility | TINY | pass | — | — | 2.78s | 225 |
| A-5 SCUC | TINY | pass | — | — | 1.65s | 278 |
| A-6 SCED | TINY | pass | — | stable (profile manipulation) | 2.19s | 291 |
| A-9 SCOPF | TINY | pass | — | — | 1.84s | 242 |
| A-10 Lossy DCOPF | TINY | qualified_pass | — | — | 1.81s | 265 |
| A-11 Distributed slack OPF | TINY | fail | — | blocking | 1.78s | 219 |
| A-12 Multi-period storage | TINY | fail | — | blocking | 1.57s | 434 |

**Independent fails: 2 (A-11, A-12). Cascaded: 0.**

#### Grade Rationale

GridCal passes 8 of 10 expressiveness tests including the challenging SCOPF and SCUC formulations. The two failures are both blocking: A-11 (distributed slack hardcoded off in OPF) and A-12 (battery energy balance sign error). A-10 is a qualified pass — the loss approximation feature exists but produces negligible results. The stable workaround for A-6 is clean. This profile meets the B standard: "Mostly strong with meaningful gaps." The two independent blocking failures prevent B+ (which requires only one meaningful gap with stable workaround).

---

### 3.2 Extensibility

#### Strengths
- Native NetworkX graph via `build_graph()` with standard BFS/subgraph algorithms ([B-2](extensibility/B-2_graph_access.md))
- N-M contingency sweep: 377 DCPF solves in 2.16s via simple `branch.active` toggle ([B-3](extensibility/B-3_contingency_sweep.md))
- PTDF extraction via one-line API call, machine-precision match to DCPF ([B-9](extensibility/B-9_ptdf_extraction.md))
- Trivial solver swap via single parameter change, no reformulation needed ([B-8](extensibility/B-8_reference_bus_config.md))
- DataFrame export in 4 LOC with `get_bus_df()` / `get_branch_df()` ([B-5](extensibility/B-5_interoperability.md))

#### Weaknesses
- No public API for custom constraint injection — monkey-patching internal PuLP model required ([B-1](extensibility/B-1_custom_constraints.md))
- Monolithic OPF formulation (3146 LOC, single function, no hook points) — architectural barrier to extensibility ([B-6](extensibility/B-6_code_architecture.md))
- TapPhaseControl enum bug prevents native time-series OPF on networks with transformers ([B-4](extensibility/B-4_stochastic_scenario.md))

#### Workarounds Required
- "Custom constraint injection via monkey-patching `PulpLpModel.solve` — depends on internal constraint naming ([B-1](extensibility/B-1_custom_constraints.md)) — **fragile**"
- "Stochastic scenario DCOPF via sequential snapshots due to TapPhaseControl enum bug ([B-4](extensibility/B-4_stochastic_scenario.md)) — **stable**"

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| B-1 Custom constraints | TINY | qualified_pass | — | fragile (monkey-patch) | 1.41s | 268 |
| B-2 Graph access | TINY | pass | — | — | 1.24s | 133 |
| B-3 Contingency sweep | TINY | pass | — | — | 3.49s | 202 |
| B-4 Stochastic scenario | TINY | qualified_pass | — | stable (sequential snapshots) | 11.73s | 321 |
| B-5 Interoperability | TINY | pass | — | — | 1.24s | 129 |
| B-6 Code architecture | N/A | informational | — | — | 0.12s | 332 |
| B-8 Reference bus config | TINY | pass | — | — | 1.36s | 225 |
| B-9 PTDF extraction | TINY | pass | — | — | 1.37s | 169 |

#### Grade Rationale

GridCal demonstrates strong native extensibility in graph access, PTDF extraction, contingency analysis, and interoperability. However, the fragile monkey-patching required for custom constraint injection (B-1) — the most important extensibility capability for market-facing use — is a significant gap. The monolithic OPF architecture means this is an architectural limitation, not a missing feature that could be easily added. This meets the B- standard: "Mostly capable with one fragile workaround on a key capability." The strong native capabilities in B-2, B-3, B-5, B-8, B-9 prevent a C+ grade.

---

### 3.3 Scalability

#### Strengths
- DCPF on MEDIUM (10k bus) in 1.05s, 82 MB — excellent linear scaling ([C-1](scalability/C-1_dcpf_scale_MEDIUM.md))
- ACPF on MEDIUM in 3.1s, 5 NR iterations, flat start — no DC warm start needed ([C-2](scalability/C-2_acpf_scale_MEDIUM.md))
- SCOPF on MEDIUM (50 contingencies) in 29.3s — time scales roughly linearly with bus count ([C-8](scalability/C-8_scopf_scale_MEDIUM.md))
- PTDF on MEDIUM in 6.7s (7.6 GB) — sub-linear scaling from TINY ([C-9](scalability/C-9_ptdf_scale_MEDIUM.md))
- Dual-solver comparison (HiGHS/SCIP) confirms identical results and easy swap mechanism ([C-3](scalability/C-3_dcopf_scale_MEDIUM.md), [C-7](scalability/C-7_solver_swap_MEDIUM.md))

#### Weaknesses
- SCUC at SMALL requires sequential snapshot workaround — monolithic MILP intractable (>25 min), TapPhaseControl bug ([C-4](scalability/C-4_scuc_scale_SMALL.md))
- Distributed slack OPF on MEDIUM fails — cascaded from A-11 ([C-10](scalability/C-10_distributed_slack_scale_MEDIUM.md))
- SCOPF memory: 5.9 GB on MEDIUM — super-linear scaling due to LODF matrix ([C-8](scalability/C-8_scopf_scale_MEDIUM.md))
- ACPF infeasible on FNM (27,862 bus) under all solver/relaxation combinations ([G-FNM-4](fnm_ingestion/G-FNM-4_fnm_acpf_convergence.md))

#### Workarounds Required
- "SCUC on SMALL via sequential hourly snapshots, losing inter-temporal coupling ([C-4](scalability/C-4_scuc_scale_SMALL.md)) — **stable**"
- "GLPK unavailable; SCIP used as second open-source solver ([C-3](scalability/C-3_dcopf_scale_MEDIUM.md), [C-7](scalability/C-7_solver_swap_MEDIUM.md)) — **stable**"

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| C-1 DCPF | MEDIUM | pass | — | — | 1.05s | 130 |
| C-2 ACPF | MEDIUM | pass | — | — | 3.10s | 281 |
| C-3 DCOPF | MEDIUM | pass | — | stable (SCIP for GLPK) | 8.45s | 171 |
| C-4 SCUC | SMALL | qualified_pass | — | stable (sequential snapshots) | 286s | 246 |
| C-5 AC feasibility | SMALL | pass | — | — | 54.1s | 409 |
| C-5 AC feasibility | MEDIUM | pass | — | — | 2.87s | 394 |
| C-7 Solver swap | MEDIUM | pass | — | stable (SCIP for GLPK) | 12.6s | 244 |
| C-8 SCOPF | SMALL | pass | — | — | 9.73s | 248 |
| C-8 SCOPF | MEDIUM | pass | — | — | 29.3s | 257 |
| C-9 PTDF | MEDIUM | pass | — | — | 6.67s | 207 |
| C-10 Dist. slack | MEDIUM | fail | A-11 | blocking | 0.0s | 66 |

**Independent fails: 0. Cascaded: 1 (C-10 from A-11).**

#### Grade Rationale

GridCal demonstrates solid scalability for DCPF, ACPF, DCOPF, SCOPF, and PTDF at MEDIUM scale (10k bus), with competitive solve times and manageable memory. The SCUC scalability gap (monolithic MILP intractable, snapshot workaround loses inter-temporal coupling) and the cascaded C-10 failure are notable but do not dominate the profile. The stable workarounds for SCUC and solver substitution are clean. This meets the B standard: "Scales adequately to MEDIUM with stable workarounds for gaps." The single cascaded failure (not independent) prevents downgrade below B.

---

### 3.4 Workforce Accessibility

#### Strengths
- Fast install via `uv sync` with no compilation steps (0.59s resolution) ([D-1](accessibility/D-1_install_to_first_solve.md))
- Clean first-solve pattern: `vge.open_file()` / `vge.power_flow()` in 26 lines ([D-1](accessibility/D-1_install_to_first_solve.md))
- Excellent PF convergence diagnostics (iteration count, residual, converged flag) on results object ([D-4](accessibility/D-4_error_quality.md))

#### Weaknesses
- Only 2 of 10 Suite A tests completable from documentation alone ([D-2](accessibility/D-2_documentation_audit.md))
- ReadTheDocs covers v5.0.2; installed version is v5.6.28 — 6 minor versions of undocumented API changes ([D-2](accessibility/D-2_documentation_audit.md))
- 0 of 2 official tutorials run unmodified — all use deprecated `GridCal.Engine` imports ([D-3](accessibility/D-3_example_verification.md))
- OPF reports `converged=True` on infeasible problems (rate=0); no warning or infeasibility detection ([D-4](accessibility/D-4_error_quality.md))
- Distributed slack option silently ignored by OPF — no warning that the flag has no effect ([D-4](accessibility/D-4_error_quality.md))
- Naming inconsistency: `PowerFlowOptions.solver_type=` vs `OptimalPowerFlowOptions.solver=` ([D-2](accessibility/D-2_documentation_audit.md))
- Median 183 NBNC lines per Suite A test — moderate verbosity ([D-5](accessibility/D-5_code_volume.md))

#### Grade Rationale

The documentation and tutorial gaps are severe: a new user cannot complete 80% of Suite A tests without reading source code, and all official tutorials are broken. The OPF error reporting (converged=True on infeasible, silently ignored options) is a significant usability concern. The fast install and clean PF diagnostics are positive but do not overcome the documentation deficit. This meets the C+ standard: "Functional but requires substantial source code reading; documentation is inadequate for self-service adoption."

---

### 3.5 Maturity & Sustainability

#### Strengths
- 209 releases in 24 months demonstrates active development ([E-1](maturity/E-1_release_cadence.md))
- ~2,357 commits with 8 named contributors in last 12 months ([E-2](maturity/E-2_commit_activity.md))
- eRoots Analytics commercial backing provides institutional continuity ([E-4](maturity/E-4_funding_model.md))
- Claims Redeia (Spanish TSO), Schneider Electric, GE Vernova as clients ([E-7](maturity/E-7_operational_adoption.md))
- 125 test files exist in repository ([E-6](maturity/E-6_ci_test_coverage.md))

#### Weaknesses
- Bus factor of 1: SanPen (Santiago Penate Vera) has 70% of all-time commits, is sole PyPI publisher, sole repo owner ([E-3](maturity/E-3_contributor_concentration.md))
- Zero code review on any merged PR — 0 of 30 sampled PRs had assigned reviewers ([E-3](maturity/E-3_contributor_concentration.md))
- No tests run in CI — pylint-only workflow targeting Python 3.8-3.10 (project requires 3.12) ([E-6](maturity/E-6_ci_test_coverage.md))
- Battery energy balance sign error shipped in released version — indicates insufficient unit testing ([A-12](expressiveness/A-12_multiperiod_dcopf_storage.md))
- Median 115 days to close issues; batch-closing pattern rather than continuous triage ([E-5](maturity/E-5_issue_tracker_health.md))
- Only 28 of 209 PyPI releases have corresponding GitHub tags ([E-1](maturity/E-1_release_cadence.md))

#### Grade Rationale

The project shows active development but critical maturity gaps. The bus factor of 1, complete absence of code review, and zero test execution in CI are serious concerns for operational reliance. A formulation bug (battery sign error) shipping in a released version confirms the lack of automated quality gates. The dual-repo model (private eRoots + public GitHub) with only 28 of 209 releases tagged makes change tracking opaque. This meets the C standard: "Active development but significant quality assurance and governance gaps that create operational risk."

---

### 3.6 Supply Chain (Gate)

#### Strengths
- MPL-2.0 core license — file-level copyleft, compatible with proprietary integration ([F-1](supply_chain/F-1_core_license.md))
- Pure Python core with zero compiled extensions — fully inspectable ([F-4](supply_chain/F-4_compiled_extension_audit.md), [F-5](supply_chain/F-5_code_inspectability.md))
- DCPF execution path traceable through 4 layers of readable Python to `scipy.sparse.linalg.spsolve` ([F-5](supply_chain/F-5_code_inspectability.md))
- Open-source solvers sufficient — HiGHS bundled, no commercial solver required ([F-8](supply_chain/F-8_solver_dependency.md))

#### Weaknesses
- 2 LGPL dependencies: chardet (LGPL-2.1+, pure Python) and moocore (LGPL-2.1, 1 .so) — low risk ([F-3](supply_chain/F-3_dependency_license_audit.md))
- 62 packages with 360 compiled .so files in dependency tree ([F-2](supply_chain/F-2_dependency_tree.md))
- No release signing (PGP, Sigstore), no Trusted Publisher workflow, single-account PyPI publish ([F-6](supply_chain/F-6_distribution_integrity.md))
- Air-gap install requires ~500-700 MB bundle with platform-specific wheels; sdist-only distribution ([F-7](supply_chain/F-7_airgap_installability.md))
- Only 28 of 66 `veragridengine` releases have corresponding GitHub tags — poor version traceability ([F-6](supply_chain/F-6_distribution_integrity.md))
- Unpinned dependency versions in eval project; no lock file ([F-9](supply_chain/F-9_getting_started_integrity.md))
- Several unnecessary dependencies for power flow use (opencv-python, windpowerlib, pymoo) ([F-2](supply_chain/F-2_dependency_tree.md))

#### Grade Rationale

The supply chain profile passes the gate threshold comfortably. MPL-2.0 is enterprise-friendly, the core is fully inspectable pure Python, and no commercial solver is required. The 2 LGPL transitive dependencies are low-risk (one is pure Python, one is in an optional multi-objective optimization path). The distribution integrity gaps (no signing, single publisher, poor GitHub-PyPI alignment) and heavy dependency tree are concerns but do not approach the gate threshold. This meets the B- standard: "Passes gate criteria with some distribution integrity and dependency hygiene concerns."

---

## 3b. FNM Ingestion Findings (Suite G)

Suite G executed (FNM_PATH set).

### Data Model Fidelity

**G-FNM-1: FAIL.** GridCal cannot ingest the intermediate CSV tables (no CSV network import) and cannot parse the source PSS/e v31 RAW file (parser hardcoded for v35 format). The MATPOWER fallback path successfully loads the main-island subset (27,862 of 30,307 buses) with expected count differences due to type-4 bus filtering. **100% DCPF-critical field coverage was not assessed** (G-FNM-2 skipped, blocked by G-FNM-1). This weakens Expressiveness evidence for FNM-scale data ingestion but does not change the Expressiveness grade, which is already set by Suite A findings.

### Power Flow Verification

**G-FNM-3: QUALIFIED PASS.** Bus voltage angles match the MATPOWER reference exactly (0.0 deg max deviation, 100% pass rate). Branch flows pass the aggregate threshold (99.0% within 10% tolerance, above the 90% requirement). However, 326 branches (1.0%) show extreme deviations (up to 562,955%), with 88.7% being transformer-adjacent. This is classified as a formulation difference in B-matrix construction for transformer tap ratios, not a data ingestion error. Attributed to Expressiveness (DCPF formulation sophistication).

**G-FNM-4: INFORMATIONAL.** ACPF fails to converge on the 27,862-bus FNM under all 12 solver/relaxation combinations tested (4 solvers x 3 relaxation levels). Best residual: 15.83 (LM, 200 iterations). Contributing factors include MATPOWER format data loss (transformer control modes, switched shunt steps) and network complexity. Attributed to Scalability (ACPF ceiling between MEDIUM and LARGE).

### Supplemental Data Representability

**G-FNM-5: INFORMATIONAL.** 39% native, 23% extension, 38% external across 44 fields in 7 supplemental CSVs. Standout: 83% native contingency coverage (best among Python tools). Principal gaps: no interface/flowgate model (100% external), no trading hub model (75% external), no outage schedule model (50% external). Single thermal rating tier (vs 3-4 in ISO data). All classifications match the analytical reference exactly. Attributed to Extensibility (data model completeness for market-facing use).

---

## 4. Cross-Cutting Observations

### API Friction Patterns

GridCal's API is clean for basic power flow (`vge.open_file()` / `vge.power_flow()`) but becomes friction-heavy for OPF and temporal workflows:
- **Parameter naming inconsistency:** `PowerFlowOptions.solver_type=` vs `OptimalPowerFlowOptions.solver=` causes TypeErrors on first attempt ([A-3](observations/doc-gaps-expressiveness-A-3_dcopf.md))
- **Time profile API:** Requires numpy int64 unix timestamps, not datetime objects ([A-5](observations/api-friction-expressiveness-A-5_scuc.md))
- **Silently ignored options:** `distributed_slack=True` has zero effect on OPF with no warning ([A-11](observations/api-friction-expressiveness-A-11_distributed_slack_opf.md))
- **No custom constraint injection:** Monolithic OPF formulation has no hook points ([B-1](observations/api-friction-extensibility-B-1_custom_constraints.md))
- **No CSV network import:** PSS/e v31 unsupported, only v35 ([G-FNM-1](observations/api-friction-fnm_ingestion-G-FNM-1_fnm_ingestion_gate.md))

### Documentation Gaps

- ReadTheDocs frozen at v5.0.2; installed version is v5.6.28 — 6 minor versions undocumented ([D-2](accessibility/D-2_documentation_audit.md))
- All official tutorials use deprecated `GridCal.Engine` imports ([D-3](accessibility/D-3_example_verification.md))
- OPF options (`add_losses_approximation`, `consider_contingencies`, `OpfDispatchMode`) not documented ([D-2](accessibility/D-2_documentation_audit.md))
- No SCED workflow documentation ([A-6](observations/doc-gaps-expressiveness-A-6_sced.md))
- `build_graph()` node type (Bus objects, not integers) not documented ([B-2](observations/doc-gaps-extensibility-B-2_graph_access.md))
- `overloads` result attribute semantics undocumented ([A-3](observations/doc-gaps-expressiveness-A-3_dcopf.md))

### Solver Ecosystem

- **No Ipopt integration** for ACPF or AC OPF — native NR and custom IPS only ([A-2](observations/solver-issues-expressiveness-A-2_acpf.md))
- **GLPK absent** from `MIPSolvers` enum; CBC and PDLP crash at runtime despite being valid enum values ([C-7](scalability/C-7_solver_swap_MEDIUM.md))
- **TapPhaseControl enum bug** prevents native time-series OPF on networks with transformers ([B-4](observations/solver-issues-extensibility-B-4_stochastic_scenario.md))
- **Loss approximation formula** uses branch rating instead of actual flow — produces negligible losses ([A-10](observations/solver-issues-expressiveness-A-10_lossy_dcopf_lmp.md))
- **Battery energy balance sign error** — discharge adds energy, causing physically incorrect optimization ([A-12](observations/solver-issues-expressiveness-A-12_multiperiod_dcopf_storage.md))
- **Monolithic SCUC MILP** intractable at SMALL scale (544 gens x 24 hrs > 25 min timeout) ([C-4](observations/solver-issues-scalability-C-4_scuc_scale.md))

### Architecture Quality

- **5-layer architecture** with good macro-level separation (model/simulation/results) ([B-6](observations/arch-quality-extensibility-B-6_code_architecture.md))
- **Monolithic OPF:** 3146 LOC single function with no extension points ([B-6](observations/arch-quality-extensibility-B-6_code_architecture.md))
- **Clean branch toggling:** `branch.active` boolean enables efficient ad-hoc contingency analysis ([B-3](observations/arch-quality-extensibility-B-3_contingency_sweep.md))
- **PTDF as first-class API:** One-line extraction, dense NumPy arrays, machine-precision match to DCPF ([B-9](observations/arch-quality-extensibility-B-9_ptdf_extraction.md))
- **Slack-invariant LMPs:** PTDF-based formulation produces identical LMPs regardless of reference bus ([B-8](observations/arch-quality-extensibility-B-8_reference_bus_config.md))
- **Pure Python core** with numba JIT for performance-critical paths — auditable source throughout ([F-5](supply_chain/F-5_code_inspectability.md))

### FNM Data Model

- **Transformer B-matrix formulation difference:** 326 branches (1.0%) show extreme flow deviations due to simplified susceptance calculation omitting tap ratio corrections ([G-FNM-3](observations/formulation-difference-fnm_ingestion-G-FNM-3_fnm_dcpf_verification.md))
- **DCPF scales to 27,862 buses** (2.4s solve, 1.9 GB memory) — LARGE tier feasible for DC analysis ([G-FNM-3](observations/fnm-scale-fnm_ingestion-G-FNM-3_fnm_dcpf_verification.md))
- **ACPF infeasible on FNM** — possible MATPOWER format data loss contributing factor ([G-FNM-4](observations/fnm-data-model-fnm_ingestion-G-FNM-4_fnm_acpf_convergence.md))
- **Native contingency model** (83% field coverage) but no interface/flowgate model (0% native) ([G-FNM-5](observations/fnm-data-model-fnm_ingestion-G-FNM-5_fnm_supplemental_csv.md))

---

## 5. Items Requiring Human Spot-Check

- [ ] **A-10 (Lossy DCOPF)** — Classified as qualified_pass because loss approximation exists but produces negligible results. Verify whether the feature intent is "screening-level approximation" or "quantitative loss modeling."
- [ ] **A-12 (Battery sign error)** — Verify whether this bug is fixed in v5.6.34 (latest release). If fixed, the fail may be version-specific. Check `linear_opf_ts.py` line ~1776 in the latest source.
- [ ] **B-1 (Custom constraints)** — Fragile workaround classification. The monkey-patch approach works but depends on 3 internal naming conventions. Verify whether this level of fragility meets "fragile" vs "blocking" threshold.
- [ ] **B-4 (Stochastic scenario)** — Stable workaround classification. Sequential snapshots lose inter-temporal coupling. Verify whether the TapPhaseControl enum bug is fixed in v5.6.34.
- [ ] **C-4 (SCUC SMALL)** — Qualified pass via sequential snapshots. True multi-period SCUC is intractable (>25 min). Verify whether this is a solver configuration issue (e.g., MIP gap tolerance) or a fundamental formulation scalability limit.
- [ ] **G-FNM-3 (DCPF verification)** — Qualified pass with formulation difference classification. The 326 transformer-adjacent branch flow deviations are systematic but extreme (up to 562,955%). Verify whether this is a known GridCal B-matrix simplification or a potential data ingestion issue.
- [ ] **E-7 (Operational adoption)** — Claims of Redeia, Schneider Electric, GE Vernova usage are unverified from public sources. The Navitasoft code contributions (52 commits) are the only independently verifiable external adoption signal.
- [ ] **Maturity grade (C vs C+)** — The bus factor of 1, zero code review, and no CI tests are severe. However, eRoots commercial backing and 209 releases/24mo show active investment. Verify whether institutional backing offsets governance gaps.
- [ ] **Supply chain LGPL deps** — chardet (LGPL-2.1+) and moocore (LGPL-2.1). Both are low-risk for library consumption, but verify organizational LGPL policy.

---

## 6. Methodology Notes

- **Scale cap:** MEDIUM (10,000-bus ACTIVSg). Gate tests passed at TINY, SMALL, and MEDIUM.
- **FNM status:** Suite G executed (FNM_PATH set). MATPOWER fallback path used for G-FNM-3/4/5 because G-FNM-1 (CSV ingestion gate) failed.
- **Tests skipped:** G-FNM-2 (field coverage audit) — blocked by G-FNM-1 failure.
- **Solver versions:** HiGHS (bundled via highspy>=1.8.0), SCIP (via pyscipopt/SCIP_CMD). Ipopt and GLPK not available in GridCal.
- **Tool version:** VeraGridEngine 5.6.28 (PyPI: `veragridengine`, installed 2026-02-25). Latest at evaluation time: 5.6.34.
- **Protocol version:** v10 for all suites.
- **Devcontainer:** Ubuntu 24.04 + Python 3.12 + uv.
