# Synthesis Report: pandapower v3.4.0

**Contract:** FA714626C0006
**Tool version:** pandapower 3.4.0
**Protocol version:** v4
**Evaluation date:** 2026-03-06/07
**Scale cap:** MEDIUM (10,000 buses)

---

## 1. Executive Summary

pandapower is a mature, well-architected steady-state power flow and basic OPF tool with excellent supply chain properties and strong accessibility. It excels at DCPF, ACPF, contingency analysis, and graph-based topology operations, with a clean pandas-native data model that enables trivial interoperability. However, it has fundamental architectural limitations that prevent it from serving as a production cost model: 6 of 11 expressiveness tests FAIL with blocking limitations due to the absence of MILP optimization, temporal modeling, stochastic formulations, SCOPF, lossy DC OPF, and distributed slack OPF. The OPF solver is locked to PYPOWER's interior point method with no ability to swap solvers. Supply chain gate passes cleanly (BSD 3-Clause, all-permissive dependencies, fully airgap-installable, Sigstore attestations).

---

## 2. Grade Recommendations Table

| Criterion | Grade | Confidence | Key Evidence |
|-----------|-------|------------|--------------|
| Problem Expressiveness | C+ | High | 5/11 pass, 6/11 fail with blocking architectural gaps (no SCUC/SCED/SCOPF/stochastic/lossy/dist-slack OPF) |
| Extensibility | B | High | Strong graph access, in-place switching, DataFrame interop; custom constraints and PTDF require fragile internal access |
| Scalability | B- | High | PF/contingency scale well to 10k buses; OPF single-solver only, 2.1% stochastic convergence, 4 tests fail on dependencies |
| Workforce Accessibility | B+ | High | 5-LOC first solve, good PF docs, tutorials work; OPF docs have gaps, mixed error quality |
| Maturity & Sustainability | A- | High | 15 releases/24mo, dual institutional backing, strong CI, European DSO adoption; no ISO/RTO adoption |
| Supply Chain (Gate) | A | High | BSD 3-Clause, all-permissive deps, pure Python core, Sigstore attestations, airgap-installable |

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness

#### Strengths

- Native DCPF with clean DataFrame results, 0.80s on 10k buses ([A-1](expressiveness/A-1_dcpf.md))
- Native ACPF with multiple solver algorithms and DC warm start fallback ([A-2](expressiveness/A-2_acpf.md))
- DC OPF with LMP extraction via `net.res_bus["lam_p"]` ([A-3](expressiveness/A-3_dcopf.md))
- Seamless DC OPF to AC PF feasibility check in same model context ([A-4](expressiveness/A-4_ac_feasibility.md))
- N-M contingency sweep with graph-distance scoping and in-place branch switching ([A-7](expressiveness/A-7_contingency_sweep.md))

#### Weaknesses

- No SCUC: no MILP solver, no binary commitment variables, no temporal optimization ([A-5](expressiveness/A-5_scuc.md)) -- **blocking**
- No SCED: depends on A-5, no ramp rate constraints ([A-6](expressiveness/A-6_sced.md)) -- **blocking**
- No stochastic OPF: no scenario tree, no two-stage formulation ([A-8](expressiveness/A-8_stochastic_timeseries.md)) -- **blocking**
- No SCOPF: no contingency-constrained optimization ([A-9](expressiveness/A-9_scopf.md)) -- **blocking**
- No lossy DC OPF: lossless only, no LMP decomposition into energy/congestion/loss ([A-10](expressiveness/A-10_lossy_dcopf_lmp.md)) -- **blocking**
- No distributed slack OPF: distributed slack available for PF but not OPF ([A-11](expressiveness/A-11_distributed_slack_opf.md)) -- **blocking**

#### Workarounds Required

- DC OPF solver locked to PYPOWER interior point; no HiGHS/GLPK ([A-3](expressiveness/A-3_dcopf.md)) -- **stable** (converges correctly but cannot swap)

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | LOC |
|------|---------|--------|------------|------|-----|
| A-1 (DCPF) | MEDIUM | pass | -- | 3.31s | 88 |
| A-2 (ACPF) | MEDIUM | pass | -- | 0.27s (DC warm start) | 139 |
| A-3 (DC OPF) | MEDIUM | qualified_pass | stable (PYPOWER only) | 20.66s | 123 |
| A-4 (AC feasibility) | MEDIUM | pass | -- | 12.27s | 165 |
| A-5 (SCUC) | N/A | fail | blocking | N/A | N/A |
| A-6 (SCED) | N/A | fail | blocking | N/A | N/A |
| A-7 (Contingency) | MEDIUM | pass | -- | 391.85s | 178 |
| A-8 (Stochastic OPF) | N/A | fail | blocking | N/A | N/A |
| A-9 (SCOPF) | N/A | fail | blocking | N/A | N/A |
| A-10 (Lossy DC OPF) | N/A | fail | blocking | N/A | N/A |
| A-11 (Dist. slack OPF) | N/A | fail | blocking | N/A | N/A |

#### Grade Rationale

**C+**: pandapower passes 5 of 11 expressiveness tests but fails 6 with blocking architectural limitations. The failures are not bugs or missing features that could be added -- they reflect a fundamental design scope limited to single-period steady-state analysis. The tool excels within its scope (PF, basic OPF, contingency) but cannot express SCUC, SCED, SCOPF, stochastic OPF, lossy DC OPF, or distributed slack OPF. Per rubric, C+ is "significant gaps, but NOT disqualifying for gate" -- the tool has genuine strengths in its domain but over half the expressiveness suite is inaccessible. The single qualified pass (A-3, solver lock-in) is a stable limitation that does not further degrade the grade.

---

### 3.2 Extensibility

#### Strengths

- Clean NetworkX integration via `create_nxgraph()` with `respect_switches` parameter ([B-2](extensibility/B-2_graph_access.md))
- Efficient in-place branch switching for contingency loops, 0.040s per case at 10k buses ([B-3](extensibility/B-3_contingency_loop.md))
- Trivial DataFrame export to CSV/JSON/Parquet via native pandas methods ([B-5](extensibility/B-5_interoperability.md))
- Clean 4-layer architecture: API, orchestration, data conversion, solver ([B-6](extensibility/B-6_code_architecture.md))
- AC feasibility check requires no workaround -- natural same-model workflow ([B-7](extensibility/B-7_ac_feasibility_extension.md))

#### Weaknesses

- Custom constraint dual values require access to private `net._ppc` internals ([B-1](extensibility/B-1_custom_constraints.md)) -- **fragile**
- PTDF extraction requires PYPOWER internals; flow prediction diverges on MEDIUM networks ([B-9](extensibility/B-9_ptdf_extraction.md)) -- **fragile**
- Distributed slack silently ignored in OPF; `**kwargs` swallows unknown parameters ([B-8](extensibility/B-8_reference_bus_config.md))

#### Workarounds Required

- Dual value extraction via `net._ppc["branch"][:, 17:18]` PYPOWER internals ([B-1](extensibility/B-1_custom_constraints.md)) -- **fragile**
- Stochastic multi-period DCOPF via manual loop with in-place DataFrame modification ([B-4](extensibility/B-4_stochastic_wrapping.md)) -- **stable**
- PTDF via `pandapower.pypower.makePTDF` after running DCPF to populate `_ppc` ([B-9](extensibility/B-9_ptdf_extraction.md)) -- **fragile**
- Slack bus reconfiguration via manual ext_grid/gen creation/deletion ([B-8](extensibility/B-8_reference_bus_config.md)) -- **stable**

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | LOC |
|------|---------|--------|------------|------|-----|
| B-1 (Custom constraints) | MEDIUM | qualified_pass | fragile (_ppc duals) | 46.22s | 194 |
| B-2 (Graph access) | MEDIUM | pass | -- | 2.01s | 112 |
| B-3 (Contingency loop) | MEDIUM | pass | -- | 3.71s | 164 |
| B-4 (Stochastic wrapping) | SMALL | qualified_pass | stable (manual loop) | 330.35s | 190 |
| B-5 (Interoperability) | MEDIUM | pass | -- | 1.74s | 93 |
| B-6 (Code architecture) | N/A | pass | -- | N/A | N/A |
| B-7 (AC feasibility ext.) | N/A | pass | -- | N/A | N/A |
| B-8 (Reference bus config) | SMALL | qualified_pass | stable (manual element mgmt) | 4.48s | 172 |
| B-9 (PTDF extraction) | MEDIUM | qualified_pass | fragile (_ppc internals) | 31.16s | 187 |

#### Grade Rationale

**B**: pandapower is extensible for its core domain (PF, contingency, topology) with clean APIs and efficient in-place modification. However, OPF-related extension points (custom constraints, dual values, PTDF) require fragile access to PYPOWER internals. Per rubric, B is "supported with caveats, moderate friction" -- the tool is extensible for power flow workflows but OPF extension requires knowledge of undocumented internals. The two fragile workarounds (B-1 duals, B-9 PTDF) and two stable workarounds (B-4 loop, B-8 slack config) place this solidly at B.

---

### 3.3 Scalability

#### Strengths

- DCPF scales well: 0.80s on 10k buses, 322 MB peak memory ([C-1](scalability/C-1_dcpf_scale.md))
- ACPF with DC warm start: 2.52s total (0.105s solve-only) on 10k buses ([C-2](scalability/C-2_acpf_scale.md))
- Contingency sweep: 10,000 cases at 0.054s/case, 357 MB memory ([C-5](scalability/C-5_contingency_sweep_scale.md))
- PTDF matrix: 12,706x10,000 matrix in 14s, correct dimensions and properties ([C-9](scalability/C-9_ptdf_scale.md))

#### Weaknesses

- DC OPF: 8.49s on 10k buses but single solver only, no comparison possible ([C-3](scalability/C-3_dcopf_scale.md))
- Stochastic DCOPF: only 2.1% convergence rate on SMALL network (5/240 solves) ([C-6](scalability/C-6_stochastic_scale.md))
- Solver swap: impossible -- no solver selection API ([C-7](scalability/C-7_solver_swap.md)) -- **fail**
- SCUC scale: blocked by A-5 failure ([C-4](scalability/C-4_scuc_scale.md)) -- **fail**
- SCOPF scale: blocked by A-9 failure ([C-8](scalability/C-8_scopf_scale.md)) -- **fail**
- Distributed slack scale: blocked by A-11 failure ([C-10](scalability/C-10_distributed_slack_scale.md)) -- **fail**

#### Workarounds Required

- Stochastic DCOPF via sequential `rundcopp()` loop ([C-6](scalability/C-6_stochastic_scale.md)) -- **stable** (but 97.9% solver failure rate)

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | Memory |
|------|---------|--------|------------|------|--------|
| C-1 (DCPF scale) | MEDIUM | pass | -- | 0.80s | 323 MB |
| C-2 (ACPF scale) | MEDIUM | pass | -- | 2.52s | 347 MB |
| C-3 (DC OPF scale) | MEDIUM | qualified_pass | -- (single solver) | 8.49s | 1,531 MB |
| C-4 (SCUC scale) | N/A | fail | blocked (A-5) | N/A | N/A |
| C-5 (Contingency scale) | MEDIUM | pass | -- | 541.62s | 357 MB |
| C-6 (Stochastic scale) | SMALL | qualified_pass | stable (2.1% convergence) | 314.37s | 406 MB |
| C-7 (Solver swap) | N/A | fail | -- | N/A | N/A |
| C-8 (SCOPF scale) | N/A | fail | blocked (A-9) | N/A | N/A |
| C-9 (PTDF scale) | MEDIUM | pass | -- | 14.99s | 4,916 MB |
| C-10 (Dist. slack scale) | N/A | fail | blocked (A-11) | N/A | N/A |

#### Grade Rationale

**B-**: Power flow and contingency analysis scale well to 10k buses with competitive times and modest memory. However, 4 of 10 scalability tests fail due to dependency on absent expressiveness features, the solver swap test fails due to architectural lock-in, and the stochastic scale test shows a 2.1% convergence rate that severely limits practical utility. Per rubric, B- is "multiple workarounds, some fragile" -- the PF scalability is strong but OPF scalability is undermined by solver limitations and cascading feature gaps.

---

### 3.4 Workforce Accessibility

#### Strengths

- 5 lines of code from install to first DCPF solve, under 0.5s ([D-1](accessibility/D-1_install_to_first_solve.md))
- Pure Python install via `pip`/`uv sync` with no compiled extension builds required ([D-1](accessibility/D-1_install_to_first_solve.md))
- All 8 tested tutorials run without modification on v3.4.0 ([D-3](accessibility/D-3_example_verification.md))
- Pandas-native data model makes results immediately accessible to any Python data scientist ([B-5](extensibility/B-5_interoperability.md))
- Power flow documentation is comprehensive with examples ([D-2](accessibility/D-2_documentation_audit.md))

#### Weaknesses

- OPF convergence check uses `net["OPF_converged"]` vs PF's `net["converged"]` -- underdocumented asymmetry ([D-2](accessibility/D-2_documentation_audit.md))
- Missing cost curves cause silent fallback to minimize-generation objective via stderr warning, not exception ([D-4](accessibility/D-4_error_quality.md))
- Invalid bus types accepted without validation; invalid bus references produce raw numpy IndexError ([D-4](accessibility/D-4_error_quality.md))
- Distributed slack parameter silently swallowed by OPF functions ([B-8 observation](observations/api-friction-extensibility-B-8_reference_bus_config.md))

#### Workarounds Required

- Source code inspection needed for OPF convergence flags and `res_cost` access pattern ([D-2](accessibility/D-2_documentation_audit.md)) -- **stable**

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| D-1 (Install to first solve) | pass | 5 LOC, 0.488s, 38 packages |
| D-2 (Documentation audit) | qualified_pass | 4/6 passing tests from docs alone; OPF gaps |
| D-3 (Example verification) | pass | 8/8 tutorials work on v3.4.0 |
| D-4 (Error quality) | qualified_pass | OPF infeasibility clear; missing costs silent; invalid bus types ignored |
| D-5 (Code volume) | informational | Mean 92 code lines for passing tests |

#### Grade Rationale

**B+**: pandapower has a low barrier to entry and strong documentation for power flow. Per rubric, B+ is "mostly strong, one meaningful gap with stable workaround." The meaningful gap is OPF documentation and error quality: convergence flags, objective access patterns, and missing-cost-curve behavior require source reading or trial-and-error. For PF users the experience is A-level; for OPF users it drops to B.

---

### 3.5 Maturity & Sustainability

#### Strengths

- 15 releases in 24 months with semantic versioning and active v3.x development ([E-1](maturity/E-1_release_cadence.md))
- 891 commits from 21 committers in 12 months; substantive feature/fix ratio ~3:1 ([E-2](maturity/E-2_commit_activity.md))
- Dual institutional backing: University of Kassel + Fraunhofer IEE with commercial spin-off (Retoflow) ([E-4](maturity/E-4_funding_model.md))
- 1.9-day median issue close time, 85% closed within 7 days ([E-5](maturity/E-5_issue_tracker_health.md))
- CI across 5 Python versions (3.10-3.14) with pytest-split parallelism and Codecov ([E-6](maturity/E-6_ci_test_coverage.md))
- European DSO adoption (10+ DSOs via pandapowerpro), LBNL regulatory prototype ([E-7](maturity/E-7_operational_adoption.md))

#### Weaknesses

- Bus factor ~2-3; top 2 contributors hold 43.3% of commits, both at same institution ([E-3](maturity/E-3_contributor_concentration.md))
- No ISO/RTO or transmission-level operational adoption found ([E-7](maturity/E-7_operational_adoption.md))
- OPF tests excluded from main CI pipeline ([E-6](maturity/E-6_ci_test_coverage.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| E-1 (Release cadence) | pass | 15 releases/24mo, latest 25 days before eval |
| E-2 (Commit activity) | pass | 891 commits, 21 committers in 12 months |
| E-3 (Contributor concentration) | pass | Bus factor ~2-3, institutionally backed |
| E-4 (Funding model) | pass | Dual institution + commercial spin-off |
| E-5 (Issue tracker) | pass | 1.9 day median close |
| E-6 (CI/coverage) | pass | 5 Python versions, pytest-split, Codecov |
| E-7 (Operational adoption) | pass | European DSOs, LBNL; no ISO/RTO |

#### Grade Rationale

**A-**: All 7 maturity tests pass. The project demonstrates strong institutional backing, active development, responsive maintenance, and real-world operational adoption at the distribution level. Per rubric, A- is "strong overall, one minor caveat." The minor caveat is the absence of ISO/RTO adoption and the concentration of key contributors at a single institution. The Fraunhofer/university model provides structural stability but creates geographic and institutional concentration risk.

---

### 3.6 Supply Chain (Gate)

#### Strengths

- BSD 3-Clause license with no copyleft or proprietary restrictions ([F-1](supply_chain/F-1_core_license.md))
- 38 total packages, max dependency depth 2, all compatible-release pinned ([F-2](supply_chain/F-2_dependency_tree.md))
- All dependencies permissive; weakest is MPL-2.0 (file-level copyleft) on optional performance extras ([F-3](supply_chain/F-3_dependency_license_audit.md))
- Pure Python core with no compiled extensions; all dependency .so files have public source ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- Full call chain traceable through Python source to scipy spsolve ([F-5](supply_chain/F-5_code_inspectability_trace.md))
- Sigstore attestations via GitHub Actions Trusted Publishing ([F-6](supply_chain/F-6_distribution_integrity.md))
- Fully airgap-installable with no runtime network access ([F-7](supply_chain/F-7_airgap_installability.md))
- No commercial solver required; all solvers bundled and BSD-licensed ([F-8](supply_chain/F-8_solver_dependency.md))

#### Weaknesses

- Getting-started page uses unversioned `pip install` commands and mutable branch URLs for tutorials ([F-9](supply_chain/F-9_getting_started_integrity.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| F-1 (Core license) | pass | BSD 3-Clause |
| F-2 (Dependency tree) | pass | 38 packages, depth 2 |
| F-3 (Dependency licenses) | pass | All permissive |
| F-4 (Compiled extensions) | pass | Pure Python core |
| F-5 (Code inspectability) | pass | Full Python trace to spsolve |
| F-6 (Distribution integrity) | pass | Sigstore attestations |
| F-7 (Airgap install) | pass | Full offline install |
| F-8 (Solver dependency) | pass | No commercial solvers |
| F-9 (Getting started integrity) | qualified_pass | Unversioned install commands |

#### Grade Rationale

**A**: All 9 supply chain tests pass (1 qualified). pandapower achieves the strongest possible supply chain profile: permissive license throughout, pure Python core, full inspectability, cryptographic distribution integrity, airgap-installable, and no commercial solver dependency. Per rubric, A is "strong native support, well-tested at scale." The single qualified pass (F-9, unversioned install commands) is a minor hygiene issue that does not affect the operational supply chain posture.

---

## 4. Cross-Cutting Observations

### API Friction Patterns

- **OPF convergence flag asymmetry:** `net["converged"]` (PF) vs `net["OPF_converged"]` (OPF) -- underdocumented difference ([A-3 observation](observations/api-friction-expressiveness-A-3_dcopf.md))
- **Distributed slack silently ignored in OPF:** `rundcopp(distributed_slack=True)` accepts the parameter via `**kwargs` but has no effect, with no warning ([B-8 observation](observations/api-friction-extensibility-B-8_reference_bus_config.md))
- **No native scenario/timeseries OPF API:** `run_timeseries()` supports PF but not OPF; multi-period OPF requires manual loop ([B-4 observation](observations/api-friction-extensibility-B-4_stochastic_wrapping.md))
- **PWL cost format diverges from MATPOWER convention:** `[[p_start, p_end, marginal_cost]]` vs MATPOWER's `[[p, c]]` pairs ([P2-2 observation](observations/doc-gaps-p2_readiness-P2-2_piecewise_linear_costs.md))

### Documentation Gaps

- **OPF constraint dual values undocumented:** Shadow prices only accessible via private `net._ppc["branch"]` at PYPOWER column indices 17-18 ([B-1 observation](observations/doc-gaps-extensibility-B-1_custom_constraints.md))
- **`res_cost` access pattern:** OPF objective is an attribute (`net.res_cost`), not a DataFrame like other `res_*` attributes -- not documented alongside OPF tutorials ([D-2](accessibility/D-2_documentation_audit.md))
- **Distributed slack parameter scope:** Documentation does not state which functions accept `distributed_slack` ([D-2](accessibility/D-2_documentation_audit.md))

### Solver Ecosystem

- **Single native OPF solver:** PYPOWER interior point (PIPS) is the only solver for `rundcopp()`/`runopp()`. No API to swap in HiGHS, GLPK, or any other solver ([A-3 solver observation](observations/solver-issues-expressiveness-A-3_dcopf.md))
- **Solver fragility:** PYPOWER IP diverges when generators are decommitted via `in_service=False`; produces lambda values ~1e25 ([P2-3 observation](observations/workaround-needed-p2_readiness-P2-3_commitment_injection.md))
- **Low stochastic convergence:** Only 2.1% of 240 DC OPF solves converged on the SMALL network under load/generation perturbations ([C-6](scalability/C-6_stochastic_scale.md))
- **PowerModels.jl bridge available but untested:** Requires Julia installation and is outside native Python API ([C-7](scalability/C-7_solver_swap.md))

### Architecture Quality

- **Clean 4-layer separation:** API -> orchestration -> data conversion -> solver, with solver fully isolated from data model ([B-6](extensibility/B-6_code_architecture.md))
- **Pandas-native data model:** All inputs and outputs are DataFrames, enabling trivial interoperability with the Python data science ecosystem ([B-5 observation](observations/arch-quality-extensibility-B-5_interoperability.md))
- **NetworkX graph bridge:** Well-designed topology integration with `respect_switches` parameter ([B-2 observation](observations/arch-quality-extensibility-B-2_graph_access.md))
- **Efficient in-place modification:** Branch switching for contingency analysis requires no model reconstruction ([B-3 observation](observations/arch-quality-extensibility-B-3_contingency_loop.md))
- **Informal layer boundaries:** No abstract base classes or formal interface contracts between layers; extensions must work with undocumented internals ([B-6 observation](observations/arch-quality-extensibility-B-6_code_architecture.md))

---

## 5. Items Requiring Human Spot-Check

- [ ] **A-3 (DC OPF) qualified pass** -- Solver lock-in to PYPOWER: confirm that the inability to use HiGHS/GLPK is correctly classified as "stable" workaround rather than "blocking" given it only affects solver choice, not correctness
- [ ] **B-1 (Custom constraints) fragile classification** -- Dual value extraction via `net._ppc` internals: verify that the `_ppc` structure is stable across pandapower minor versions or whether it has broken in the v2->v3 transition
- [ ] **B-4 (Stochastic wrapping) qualified pass** -- "Stable" workaround with 2.1% convergence rate on SMALL: assess whether solver failure rate should escalate the workaround classification from "stable" to "fragile"
- [ ] **B-8 (Reference bus config) qualified pass** -- Distributed slack produces identical results to single slack in OPF: confirm whether this represents silent parameter ignoring (API defect) or genuinely reduces to single slack in the PYPOWER formulation
- [ ] **B-9 (PTDF extraction) fragile classification** -- PTDF flow prediction diverges on MEDIUM (max diff 7.43 pu): determine whether this is a PTDF computation error or expected behavior from transformer tap ratios/shunts not captured by the basic PTDF formulation
- [ ] **C-6 (Stochastic scale) qualified pass** -- 2.1% convergence rate: subjective judgment whether this constitutes a "pass" for the loop-based approach or whether solver quality makes the approach practically unusable
- [ ] **D-4 (Error quality) qualified pass** -- Missing cost curve silent fallback: assess severity of silently changing the objective function from cost minimization to generation minimization
- [ ] **F-9 (Getting started integrity) qualified pass** -- Unversioned install commands: assess whether this is significant enough to note in the supply chain gate assessment or purely informational
- [ ] **Expressiveness grade C+ vs C boundary** -- 5/11 pass with 6 blocking failures: verify that C+ (lowest passing for gate) is appropriate given that the failures are architectural, not bugs

---

## 6. Methodology Notes

- **Scale cap:** MEDIUM (10,000 buses) -- ACTIVSg10k synthetic WECC network. Applied because pandapower does not support LARGE (70k+) networks in the test protocol.
- **Tests skipped:** A-5/A-6/A-8/A-9/A-10/A-11 skipped on MEDIUM after failing on TINY (architectural limitations, not scale-dependent). C-4/C-8/C-10 skipped due to dependency failures.
- **Solver versions:** PYPOWER interior point (PIPS, bundled in pandapower 3.4.0). Newton-Raphson for AC PF (pandapower internal). scipy 1.16.3 (spsolve via SuperLU).
- **Tool version:** pandapower 3.4.0 (released 2026-02-09), installed via `uv sync` with `[performance]` extras (LightSim2Grid 0.12.2, numba 0.64.0, ortools 9.15.6755).
- **Devcontainer:** Ubuntu 24.04 + Python 3.12, executed via `.devcontainer/dc-exec`.
- **Networks used:** case39.m (TINY, 39 buses), case_ACTIVSg2000.m (SMALL, 2000 buses), case_ACTIVSg10k.m (MEDIUM, 10000 buses).
- **Contingency sweep scope reduction:** A-7 and C-5 limited BFS computation to 200 of 10,701 seed branches due to time budget constraints. Full enumeration exceeds practical limits.
