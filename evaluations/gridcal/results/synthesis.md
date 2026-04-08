# Synthesis Report: GridCal (VeraGridEngine 5.6.28)

**Protocol version:** v11
**Skill version:** v2
**Tool version:** VeraGridEngine 5.6.28 (PyPI: `veragridengine`)
**Evaluation date:** 2026-03-24

---

## 1. Executive Summary

GridCal (VeraGridEngine) is a pure-Python power systems tool with native MATPOWER ingestion, PTDF-based DC OPF, LODF-based SCOPF, and built-in Newton-Raphson AC power flow. It passes the supply chain gate (MPL-2.0 license, open-source solvers, fully inspectable Python source). The tool's primary strengths are its clean 3-line power flow API, first-class PTDF/LODF extraction, native contingency modeling, and parameter-only solver swapping via PuLP. Its primary weaknesses are two blocking formulation bugs (battery energy balance sign error in A-12, distributed slack hardcoded off in OPF in A-11), soft branch flow constraints that mask infeasibility in DC OPF, and poor OPF diagnostic quality. No scale cap was applied; the tool was tested at MEDIUM (10,000 buses) for scalability tests.

---

## 2. Test Results Summary

| Criterion | Tests Run | Pass | Partial/Constrained | Qualified Pass | Fail | Informational/Skip | Confidence | Key Evidence |
|-----------|----------|------|---------------------|---------------|------|-------------------|------------|--------------|
| Problem Expressiveness | 10 | 3 | 2 | 2 | 2 | 1 (A-9 pass) | High | 2 independent fails (A-11, A-12); soft constraints in DCOPF |
| Extensibility | 8 | 5 | 1 | 1 | 0 | 1 | High | Fragile monkey-patch for custom constraints (B-1) |
| Scalability | 11 | 6 | 0 | 3 | 1 | 1 (C-8 SMALL pass) | High | 1 cascaded fail (C-10 from A-11); MEDIUM scale achieved |
| Workforce Accessibility | 5 | 0 | 0 | 0 | 0 | 5 | Medium | 2/10 Suite A tests completable from docs alone |
| Maturity & Sustainability | 7 | 0 | 0 | 0 | 0 | 7 | Medium | Bus factor 1; zero code review; CI non-functional |
| Supply Chain (Gate) | 9 | 9 | 0 | 0 | 0 | 0 | High | MPL-2.0; pure Python; all open-source solvers |

**Pass rate computation** (excluding gate tests G-1/G-2/G-3, informational, and skipped):

- **Expressiveness (10 scored):** 3 pass + 1 partial_pass + 1 constrained_pass + 2 qualified_pass + 2 fail = 7/10 at qualified or better; 2 independent fails
- **Extensibility (7 scored):** 5 pass + 1 partial_pass + 1 qualified_pass = 7/7 at partial or better; 0 fails
- **Scalability (10 scored):** 6 pass + 3 qualified_pass + 1 fail (cascaded) = 9/10 at qualified or better; 0 independent fails, 1 cascaded fail

**Confidence levels:**
- **High** -- Clear, unambiguous evidence from multiple tests
- **Medium** -- Evidence supports conclusions but some judgment involved
- **Low** -- Limited or ambiguous evidence; needs human spot-check

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness

#### Strengths

- Native DC power flow with clean 3-line API and DataFrame export ([A-1](expressiveness/A-1_dcpf.md))
- Native Newton-Raphson ACPF with Tier 1 convergence diagnostics (residual + iterations as first-class attributes) ([A-2](expressiveness/A-2_acpf.md))
- DCOPF with differentiated costs, LMP extraction via `bus_shadow_prices`, and congestion signal ([A-3](expressiveness/A-3_dcopf.md))
- Same-model-context DCOPF-to-ACPF feasibility check with no export/reimport ([A-4](expressiveness/A-4_ac_feasibility.md))
- Native 24-hour SCUC with `OpfDispatchMode.UnitCommitment`, ramp rates, and min up/down ([A-5](expressiveness/A-5_scuc.md))
- LODF-based SCOPF via `consider_contingencies=True` with joint formulation (not Benders) ([A-9](expressiveness/A-9_scopf.md))
- Lossy DCOPF via `add_losses_approximation=True` flag (feature exists, though output quality limited) ([A-10](expressiveness/A-10_lossy_dcopf_lmp.md))

#### Weaknesses

- Distributed slack hardcoded off in OPF formulation (`distributed_slack=False` at `linear_opf_ts.py` line 3022); silently ignored when set to True [tool-specific] ([A-11](expressiveness/A-11_distributed_slack_opf.md))
- Battery energy balance sign error in multi-period OPF: energy increases during discharge, producing physically impossible results and no arbitrage behavior [tool-specific] ([A-12](expressiveness/A-12_multiperiod_dcopf_storage.md))
- Soft branch flow constraints in DCOPF allow overloading (112% observed on TINY); no hard-constraint mode available [tool-specific] ([A-3](expressiveness/A-3_dcopf.md))
- Loss approximation underestimates by >500x (8.74e-04% vs expected 0.5-3%); formula uses static thermal rating instead of actual flow [tool-specific] ([A-10](expressiveness/A-10_lossy_dcopf_lmp.md))
- No LMP decomposition into energy, congestion, and loss components [tool-specific] ([A-10](expressiveness/A-10_lossy_dcopf_lmp.md))
- No direct access to binary UC variables; commitment inferred from `generator_power > threshold` [tool-specific] ([A-5](expressiveness/A-5_scuc.md))
- Ramp constraint enforcement partially fails with very tight limits in `OpfDispatchMode.Normal` [tool-specific] ([A-6](expressiveness/A-6_sced.md))
- No native SCED abstraction; UC-ED separation requires manual Pmax/Pmin profile manipulation [tool-specific] ([A-6](expressiveness/A-6_sced.md))

#### Workarounds Required

- SCED via Pmax_prof/Pmin_prof profile zeroing for decommitted generators ([A-6](expressiveness/A-6_sced.md)) -- **stable**
- No workaround available for distributed slack in OPF ([A-11](expressiveness/A-11_distributed_slack_opf.md)) -- **blocking**
- No workaround available for battery sign error ([A-12](expressiveness/A-12_multiperiod_dcopf_storage.md)) -- **blocking**

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| A-1 | TINY | pass | -- | -- | 1.37s | 137 |
| A-2 | TINY | pass | -- | -- | 2.20s | 215 |
| A-3 | TINY | partial_pass | -- | -- | 1.27s | 229 |
| A-4 | TINY | pass | -- | -- | 2.25s | 226 |
| A-5 | TINY | qualified_pass | -- | -- | 1.88s | 361 |
| A-6 | TINY | qualified_pass | -- | stable | 1.97s | 418 |
| A-9 | TINY | pass | -- | -- | 1.42s | 234 |
| A-10 | TINY | constrained_pass | -- | -- | 1.37s | 265 |
| A-11 | TINY | fail | -- | blocking | 1.41s | 219 |
| A-12 | TINY | fail | -- | blocking | 1.28s | 418 |

**Independent fails: 2** (A-11 distributed slack, A-12 multi-period storage). Both are tool-specific formulation issues, not solver-specific.

#### Findings Summary

GridCal covers the core expressiveness spectrum (DCPF, ACPF, DCOPF, SCUC, SCED, SCOPF) with clean native APIs. Two blocking formulation bugs -- the battery energy balance sign error (A-12) and the hardcoded `distributed_slack=False` in the OPF (A-11) -- are both tool-specific and cannot be worked around via the public API. The soft-constraint DCOPF formulation (A-3) and the severely underestimating loss approximation (A-10) are architectural choices that limit formulation fidelity. The SCOPF implementation (A-9) via LODF-based joint formulation is a notable strength.

---

### 3.2 Extensibility

#### Strengths

- NetworkX graph via `build_graph()` enables BFS, shortest-path, and subgraph extraction natively ([B-2](extensibility/B-2_graph_access.md))
- Branch toggle via `branch.active` for contingency sweeps with no model reconstruction ([B-3](extensibility/B-3_contingency_sweep.md))
- 4-line DataFrame export to CSV via `get_bus_df()` / `get_branch_df()` + `to_csv()` ([B-5](extensibility/B-5_interoperability.md))
- PTDF and LODF matrices as dense NumPy arrays via one-line `vge.linear_power_flow()` ([B-9](extensibility/B-9_ptdf_extraction.md))
- Slack bus reconfiguration via `bus.is_slack` boolean toggle; LMPs invariant to slack choice (PTDF-based) ([B-8](extensibility/B-8_reference_bus_config.md))
- Solver swap is a single parameter change (`mip_solver=MIPSolvers.X`); no reformulation needed ([B-4](extensibility/B-4_stochastic_scenario.md))

#### Weaknesses

- No public API for custom constraint injection into OPF [tool-specific] ([B-1](extensibility/B-1_custom_constraints.md))
- Monkey-patch required to add flowgate constraints; relies on internal naming convention `br_flow_upper_lim_0_<idx>` [tool-specific] ([B-1](extensibility/B-1_custom_constraints.md))
- TapPhaseControl enum bug crashes time-series OPF on networks with transformers (v5.6.28) [tool-specific] ([B-4](extensibility/B-4_stochastic_scenario.md))
- Monolithic OPF formulation (3,146 LOC single file) with no hook points or plugin architecture [tool-specific] ([B-6](extensibility/B-6_code_architecture.md))

#### Workarounds Required

- Custom constraint injection via PulpLpModel.solve monkey-patch ([B-1](extensibility/B-1_custom_constraints.md)) -- **fragile**
- Sequential snapshot OPF instead of time-series driver to avoid TapPhaseControl bug ([B-4](extensibility/B-4_stochastic_scenario.md)) -- **stable** (loses inter-temporal coupling)

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| B-1 | TINY | partial_pass | -- | fragile | 1.43s | 268 |
| B-2 | TINY | pass | -- | -- | 1.20s | 133 |
| B-3 | TINY | pass | -- | -- | 3.13s | 204 |
| B-4 | TINY | qualified_pass | -- | stable | 11.33s | 321 |
| B-5 | TINY | pass | -- | -- | 1.16s | 129 |
| B-6 | N/A | informational | -- | -- | 1.13s | 332 |
| B-8 | TINY | pass | -- | -- | 1.24s | 221 |
| B-9 | TINY | pass | -- | -- | 1.25s | 169 |

**Independent fails: 0.** All tests pass at partial or better.

#### Findings Summary

GridCal provides strong graph access, interoperability, and PTDF/LODF extraction through clean public APIs. The principal gap is the absence of a custom constraint injection API -- the only path requires fragile monkey-patching of internal PuLP model objects (B-1). The monolithic OPF formulation architecture (B-6) is the root cause: there are no extension points designed for user-defined constraints. The TapPhaseControl enum bug (B-4) is a v5.6.28-specific defect that blocks the time-series OPF driver on networks with transformers.

---

### 3.3 Scalability

#### Strengths

- DCPF on MEDIUM (10k buses) in 1.1s, 82.6 MB ([C-1](scalability/C-1_dcpf_scale_MEDIUM.md))
- ACPF on MEDIUM in 3.4s, 5 NR iterations, residual 2.7e-07 ([C-2](scalability/C-2_acpf_scale_MEDIUM.md))
- DCOPF on MEDIUM in 8.9s with HiGHS; identical results with SCIP ([C-3](scalability/C-3_dcopf_scale_MEDIUM.md))
- SCOPF with 50 N-1 contingencies on MEDIUM in 32.1s; 956 MW aggregate redispatch confirms active security constraints ([C-8](scalability/C-8_scopf_scale_MEDIUM.md))
- PTDF on MEDIUM (12,706 x 10,000 matrix) in 15.7s; sub-linear scaling from TINY ([C-9](scalability/C-9_ptdf_scale_MEDIUM.md))
- AC feasibility at both SMALL and MEDIUM scales ([C-5](scalability/C-5_ac_feasibility_progressive_SMALL.md), [C-5](scalability/C-5_ac_feasibility_progressive_MEDIUM.md))

#### Weaknesses

- SCUC at SMALL (2000 buses) requires sequential snapshot workaround; TapPhaseControl bug + monolithic MILP intractability block native time-series UC [mixed: tool-specific bug + solver-specific MILP scaling] ([C-4](scalability/C-4_scuc_scale_SMALL.md))
- PuLP interface does not expose solver thread configuration; all solves are single-threaded despite 32 CPU threads available [tool-specific] ([C-4](scalability/C-4_scuc_scale_SMALL.md))
- PTDF on MEDIUM consumes 7.6 GB peak memory due to dense matrix storage [tool-specific: no sparse PTDF option] ([C-9](scalability/C-9_ptdf_scale_MEDIUM.md))
- SCOPF on MEDIUM consumes 5.9 GB peak memory due to LODF matrix + contingency constraint storage ([C-8](scalability/C-8_scopf_scale_MEDIUM.md))
- GLPK not available in MIPSolvers enum; CBC and PDLP enum values crash at runtime [tool-specific] ([C-7](scalability/C-7_solver_swap_MEDIUM.md))

#### Workarounds Required

- Sequential snapshot OPF for SCUC at SMALL scale ([C-4](scalability/C-4_scuc_scale_SMALL.md)) -- **stable** (loses inter-temporal coupling)
- SCIP substituted for GLPK in dual-solver comparison ([C-3](scalability/C-3_dcopf_scale_MEDIUM.md), [C-7](scalability/C-7_solver_swap_MEDIUM.md)) -- **stable**

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| C-1 | MEDIUM | pass | -- | -- | 1.1s | 133 |
| C-2 | MEDIUM | pass | -- | -- | 3.4s | 271 |
| C-3 | MEDIUM | qualified_pass | -- | stable | 8.9s | 179 |
| C-4 | SMALL | qualified_pass | -- | stable | 301.0s | 268 |
| C-5 | SMALL | pass | -- | -- | 58.5s | 409 |
| C-5 | MEDIUM | pass | -- | -- | 3.2s | 389 |
| C-7 | MEDIUM | qualified_pass | -- | stable | 8.9s | 251 |
| C-8 | SMALL | pass | -- | -- | 9.7s | 248 |
| C-8 | MEDIUM | pass | -- | -- | 32.1s | 300 |
| C-9 | MEDIUM | pass | -- | -- | 15.7s | 214 |
| C-10 | MEDIUM | fail | A-11 | blocking | 0.0s | 72 |

**Independent fails: 0.** C-10 is cascaded from A-11 (distributed slack not supported in OPF). All other tests pass at qualified or better.

#### Findings Summary

GridCal scales well for power flow and single-period OPF up to MEDIUM (10k buses). DCPF and ACPF timings are competitive, and SCOPF handles 50 contingencies at MEDIUM scale. The key scalability gap is multi-period SCUC, which is blocked by the TapPhaseControl enum bug and the monolithic MILP formulation's intractability at SMALL scale (544 generators x 24 hours). Memory usage for PTDF and SCOPF at MEDIUM scale is high (5.9-7.6 GB) due to dense matrix storage. The inability to expose solver threading through PuLP limits optimization solve times to single-threaded performance.

---

### 3.4 FNM Ingestion Findings (Suite G)

Suite G was executed (FNM_PATH set). The MATPOWER fallback path was used because GridCal cannot parse the intermediate CSV tables.

- **Data Model Fidelity:** G-FNM-1 failed -- GridCal has no CSV network import capability [tool-specific]. G-FNM-2 was skipped (blocked by G-FNM-1). The MATPOWER `.m` fallback successfully loaded ~28,000 buses, ~5,800 generators, ~23,000 lines, and ~9,500 transformers. All bus load values match the reference exactly (0 mismatches in the power balance cross-reference). 100% DCPF-critical field coverage was not achieved via CSV path; MATPOWER format loses PSS/E-specific fields (tap control modes, switched shunt steps, area interchange).

- **Power Flow Verification:** G-FNM-3 achieved qualified_pass -- bus angles match the MATPOWER reference within machine precision (100% passing, max deviation 7.7e-09 deg). Branch flows pass the aggregate threshold (99.0% within 10% tolerance), but 326 branches show extreme deviations (up to 5.6e+05%) concentrated near transformer-connected buses (88.65% transformer-adjacent). This is classified as a formulation difference [tool-specific: simplified B-matrix in DCPF]. G-FNM-4 was informational -- ACPF failed to converge at all relaxation levels with all solver algorithms (NR, LM, HELM). Best residual was 15.83 (LM, 200 iterations). Contributing factors include MATPOWER format data loss for ACPF-critical fields and network conditioning.

- **Supplemental Data Representability:** G-FNM-5 shows 39% native, 23% extension, 38% external across 44 fields. GridCal's standout is contingency coverage (83% native via `ContingencyGroup`/`Contingency`). Principal gaps are interfaces/flowgates (100% external) and trading hubs (75% external). Single thermal rating tier (vs. 4 in the FNM data) limits LINE_AND_TRANSFORMER coverage.

FNM findings strengthen the expressiveness evidence: the formulation difference in branch flows (G-FNM-3) is consistent with the simplified B-matrix formulation observed in DCOPF on synthetic networks. The ACPF convergence failure (G-FNM-4) is consistent with the tool's limited solver portfolio (no Ipopt) but cannot be definitively attributed to tool vs. network conditioning.

---

### 3.5 Workforce Accessibility

All 5 tests are informational (evidence collection).

#### Strengths

- Clean install via `uv sync` with no compilation; first solve in 1.485s including import ([D-1](accessibility/D-1_install_to_first_solve.md))
- Intuitive core API: `open_file()` / `power_flow()` / `linear_opf()` pattern ([D-1](accessibility/D-1_install_to_first_solve.md))
- 49 example scripts in the main VeraGrid repo using current imports ([D-3](accessibility/D-3_example_verification.md))
- Built-in DataFrame export with physically meaningful column names ([D-5](accessibility/D-5_code_volume.md))

#### Weaknesses

- Only 2 of 10 Suite A tests completable from documentation alone (A-1, A-2) [tool-specific] ([D-2](accessibility/D-2_documentation_audit.md))
- OPF diagnostics are poor: infeasible problems report `converged=True`; silently ignored options produce no warnings [tool-specific] ([D-4](accessibility/D-4_error_quality.md))
- Rebrand confusion: PyPI package `veragridengine`, import `VeraGridEngine`, legacy docs reference `GridCal` [tool-specific] ([D-1](accessibility/D-1_install_to_first_solve.md))
- API naming inconsistency: `PowerFlowOptions.solver_type=` vs `OptimalPowerFlowOptions.solver=` [tool-specific] ([D-2](accessibility/D-2_documentation_audit.md))
- GridCalTutorials repo completely broken (deprecated imports) ([D-3](accessibility/D-3_example_verification.md))
- Median 203 NBNC lines per Suite A test; temporal profile boilerplate adds 30-50 lines vs tools with datetime-based profiles ([D-5](accessibility/D-5_code_volume.md))

#### Findings Summary

GridCal's power flow API is clean and discoverable, but OPF workflows require source code reading. The PF/OPF diagnostic asymmetry is the central accessibility finding: power flow provides excellent convergence feedback (residual, iterations, converged as first-class attributes), while OPF provides none -- infeasible problems "succeed," and silently ignored options produce no warnings. Documentation has improved with the auto-generated API index and 49 examples in the main repo, but advanced workflows (SCUC, SCED, SCOPF, multi-period storage) remain underdocumented.

---

### 3.6 Maturity & Sustainability

All 7 tests are informational (evidence collection).

#### Key Evidence

- **Release cadence:** ~128 releases in last 24 months; exceptionally high (~2+ per week). No changelogs for most releases. ([E-1](maturity/E-1_release_cadence.md))
- **Commit activity:** 2,217 commits in 12 months across 11 human committers. SanPen contributes 56.9%. ([E-2](maturity/E-2_commit_activity.md))
- **Bus factor: 1.** SanPen has 73.2% of all-time commits (9,523), is sole PyPI publisher, sole repo owner. No merged PRs have code review (0% review rate across 29 sampled PRs). ([E-3](maturity/E-3_contributor_concentration.md))
- **Funding model:** Small commercial entity (eRoots Analytics, Barcelona, est. 2022). Open-core model with proprietary compute backends. LF Energy incubation application withdrawn Jan 2025. ([E-4](maturity/E-4_funding_model.md))
- **Issue tracker:** 135-day median time-to-close; batch-closing pattern; 31% zero-comment closures. Open OPF constraint correctness issue (#397) at 293 days. ([E-5](maturity/E-5_issue_tracker_health.md))
- **CI/testing:** Only CodeQL runs in CI. Pylint workflow disabled. 102 test files exist but are not executed in any automated pipeline. No coverage measurement. No branch protection. ([E-6](maturity/E-6_ci_test_coverage.md))
- **Adoption:** 18+ client organizations listed on eRoots website including Redeia (Spanish TSO) and Schneider Electric. 519 GitHub stars. Niche operational adoption concentrated in eRoots consulting ecosystem. ([E-7](maturity/E-7_operational_adoption.md))

#### Findings Summary

The project has high development velocity from a small team centered on a single individual. The bus factor of 1, zero code review, and non-functional CI represent material project risks. The eRoots commercial backing provides some institutional continuity but the company is young (est. 2022). The issue tracker shows a disconnect between rapid release cadence and slow user-facing issue resolution (135-day median close). An organization adopting this tool would need to establish its own test, validation, and regression detection infrastructure.

---

### 3.7 Supply Chain (Gate)

All 9 tests pass.

#### Key Evidence

- **License:** MPL-2.0 (weak copyleft, file-level). Changed from LGPL Nov 2024. Compatible with enterprise adoption. ([F-1](supply_chain/F-1_core_license.md))
- **Dependencies:** 62 packages, 28 direct. 2 LGPL packages (chardet, moocore) -- both low-risk. No GPL, AGPL, or proprietary licenses. ([F-2](supply_chain/F-2_dependency_tree.md), [F-3](supply_chain/F-3_dependency_license_audit.md))
- **Compiled extensions:** VeraGridEngine is 100% pure Python (`py3-none-any`). 25 dependencies have compiled extensions, all with public source. Numba JIT in 38 files for performance. ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- **Inspectability:** Full DCPF path traceable through 4 layers of Python in ~200 lines. Custom IPS for AC OPF (no Ipopt dependency). ([F-5](supply_chain/F-5_code_inspectability.md))
- **Distribution:** sdist-only on PyPI. No release signing. Single-maintainer publishing. SHA-256 hashes available. ([F-6](supply_chain/F-6_distribution_integrity.md))
- **Air-gap:** Feasible; all compiled deps have platform wheels on PyPI. ~500-700 MB bundle. No runtime network access for core functionality. ([F-7](supply_chain/F-7_airgap_installability.md))
- **Solvers:** HiGHS (MIT, bundled), CBC (bundled with PuLP), GLPK (system). Custom IPS for AC OPF. No proprietary solver required. ([F-8](supply_chain/F-8_solver_dependency.md))
- **Getting started:** `verify_install.py` works correctly. `uv.lock` ensures reproducible installs. ([F-9](supply_chain/F-9_getting_started_integrity.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| F-1 | pass | MPL-2.0 (weak copyleft) |
| F-2 | pass | 62 packages, max depth 4 |
| F-3 | pass | 2 LGPL (chardet, moocore); no GPL/AGPL |
| F-4 | pass | Pure Python core; 25 deps with compiled extensions |
| F-5 | pass | 4-layer traceable path; all Python |
| F-6 | pass | sdist-only; no signing; SHA-256 hashes |
| F-7 | pass | Air-gap feasible; no runtime network access |
| F-8 | pass | HiGHS bundled; custom IPS for AC OPF |
| F-9 | pass | uv.lock ensures reproducibility |

#### Findings Summary

The supply chain profile is strong. MPL-2.0 is enterprise-compatible. The pure-Python codebase with open-source solvers provides excellent inspectability and no commercial dependencies. The main supply chain concern is the single-maintainer publishing model (no Trusted Publisher, no signing), which concentrates supply chain risk on one PyPI account.

---

## 4. Cross-Cutting Observations

### API Friction Patterns

- **Distributed slack silently ignored in OPF:** `PowerFlowOptions.distributed_slack=True` has zero effect on `linear_opf` results. No warning or error. ([A-11](expressiveness/A-11_distributed_slack_opf.md))
- **OPF parameter naming inconsistency:** `PowerFlowOptions` uses `solver_type=` while `OptimalPowerFlowOptions` uses `solver=`. Causes TypeErrors discoverable only through trial and error. ([D-2](accessibility/D-2_documentation_audit.md))
- **Time profile API requires unix timestamps:** `set_time_profile()` accepts numpy int64 unix timestamps, not datetime objects. Undocumented. ([A-5](expressiveness/A-5_scuc.md))
- **No public API for custom OPF constraints:** The monolithic `run_linear_opf_ts` builds, solves, and returns in one call with no hook points. ([B-1](extensibility/B-1_custom_constraints.md))
- **PuLP thread configuration not exposed:** Solver multi-threading (available in HiGHS) cannot be activated through GridCal's API. ([C-4](scalability/C-4_scuc_scale_SMALL.md))
- **Silent None return for unsupported formats:** `open_file()` returns `None` for `.mat` binary format instead of raising an error. ([G-FNM-1](fnm_ingestion/G-FNM-1_fnm_ingestion_gate.md))

### Documentation Gaps

- Only 2 of 10 Suite A tests (A-1, A-2) completable from official documentation alone. ([D-2](accessibility/D-2_documentation_audit.md))
- OPF options (`add_losses_approximation`, `consider_contingencies`, `OpfDispatchMode` variants) undocumented with usage examples. ([D-2](accessibility/D-2_documentation_audit.md))
- `build_graph()` return type (NetworkX MultiDiGraph) undocumented. ([B-2](extensibility/B-2_graph_access.md))
- Soft constraint behavior in DCOPF undocumented. ([A-3](expressiveness/A-3_dcopf.md))
- GridCalTutorials repo uses deprecated imports; 49 functional examples in main repo are less discoverable. ([D-3](accessibility/D-3_example_verification.md))

### Solver Ecosystem

- **HiGHS (MIT):** Primary solver. Works for LP, MILP, QP. Single-threaded in GridCal's PuLP binding. [solver-specific: single-threaded HiGHS MILP limits SCUC scaling]
- **SCIP:** Secondary open-source solver. Works correctly. Produces identical results to HiGHS. [solver-specific: SCIP available as GLPK substitute]
- **CBC/PDLP:** In `MIPSolvers` enum but crash at runtime (`Exception: PuLP Unsupported MIP solver`). [tool-specific: broken enum values]
- **GLPK:** Not in `MIPSolvers` enum despite being available as PuLP backend. [tool-specific: enum omission]
- **No Ipopt integration:** ACPF uses native NR; AC OPF uses custom IPS. All AC solver quality depends on GridCal's own implementation. [tool-specific: no external NLP solver]
- **Soft constraints in DCOPF:** The PTDF-based LP uses slack variables with penalty costs rather than hard inequality constraints. This is a tool formulation choice, not solver-dependent. [tool-specific]

### Architecture Quality

- **5-layer architecture** with clear macro-level separation (API / Driver / Worker / Results / Data Model). ([B-6](extensibility/B-6_code_architecture.md))
- **Monolithic OPF:** `linear_opf_ts.py` (3,146 LOC) contains the entire LP formulation as a single procedural function with if/else dispatch for all modes. No extension points. [tool-specific] ([B-6](extensibility/B-6_code_architecture.md))
- **Clean branch toggling:** `branch.active` boolean for contingency sweeps requires no model reconstruction. Efficient (4.92 ms/contingency on TINY). ([B-3](extensibility/B-3_contingency_sweep.md))
- **PTDF-invariant LMPs:** Reference bus selection has zero effect on LMPs due to pseudo-inverse PTDF computation. Positive architectural property. ([B-8](extensibility/B-8_reference_bus_config.md))
- **Compilation bottleneck:** Every solve recompiles MultiCircuit to NumericalCircuit with no caching. ([B-6](extensibility/B-6_code_architecture.md))

### FNM Data Model

- **No CSV network import:** GridCal cannot ingest intermediate CSV tables; MATPOWER `.m` is the only viable fallback path. ([G-FNM-1](fnm_ingestion/G-FNM-1_fnm_ingestion_gate.md))
- **Simplified B-matrix formulation:** 326 of ~33,000 branch flows deviate from reference on the ~28,000-bus FNM, concentrated near transformers (88.65% transformer-adjacent). [tool-specific] ([G-FNM-3](fnm_ingestion/G-FNM-3_fnm_dcpf_verification.md))
- **ACPF convergence failure on FNM:** All solver algorithms fail to converge (best residual 15.83). Contributing factors: MATPOWER format data loss + network conditioning + no Ipopt. ([G-FNM-4](fnm_ingestion/G-FNM-4_fnm_acpf_convergence.md))
- **Strong contingency model, weak interface model:** 83% native coverage on CONTINGENCY.csv, 100% external on INTERFACE.csv. No flowgate concept. ([G-FNM-5](fnm_ingestion/G-FNM-5_fnm_supplemental_csv.md))

---

## 5. Items Requiring Human Spot-Check

- [ ] **A-3 (partial_pass):** Soft-constraint DCOPF -- verify that the distinction between soft and hard constraints is correctly classified as partial_pass vs. fail. The formulation is intentional (not a bug) but produces overloaded branches.
- [ ] **A-5 (qualified_pass):** SCUC min up/down binding verification was inconclusive (constraints not binding due to test data characteristics). Verify whether the qualified_pass classification is appropriate given the test accepted the parameters without error.
- [ ] **A-6 (qualified_pass):** Ramp constraint violation detected with tightened limits (1 of 208 checks failed). Verify whether the ramp enforcement partial failure warrants qualified_pass or a lower classification.
- [ ] **A-10 (constrained_pass):** Loss approximation produces 500x underestimate. Verify whether constrained_pass is appropriate vs. fail given the feature exists but output quality is poor.
- [ ] **A-12 (fail):** Battery energy balance sign error -- verify the source code analysis identifying the sign error in `linear_opf_ts.py` line ~1776. This is a high-impact finding that should be confirmed against the actual source.
- [ ] **B-1 (partial_pass, fragile):** Monkey-patch for custom constraints relies on internal naming convention. Verify the fragile classification is correct and that no more stable injection path exists in v5.6.28.
- [ ] **B-4 (qualified_pass):** TapPhaseControl enum bug -- verify this is indeed a bug and not a configuration error. The workaround (sequential snapshot OPF) loses inter-temporal coupling.
- [ ] **C-4 (qualified_pass):** SCUC at SMALL required sequential snapshots. Verify whether the loss of inter-temporal coupling (ramps, min up/down) should reduce the classification below qualified_pass.
- [ ] **G-FNM-3 (qualified_pass):** 326 extreme branch flow deviations attributed to formulation difference. Verify the transformer-adjacency classification (88.65%) and confirm this is not a data ingestion issue.
- [ ] **G-FNM-4 (informational):** ACPF infeasible on ~28,000-bus FNM. Verify whether this should be attributed to the tool (no Ipopt, simplified data model) or the network (inherently difficult case).
- [ ] **Solver-vs-tool attribution:** The soft-constraint DCOPF (A-3) and the broken CBC/PDLP enum values (C-7) could arguably be classified either way. The current report tags both as tool-specific.
- [ ] **E-3 maturity:** Bus factor 1 with zero code review. This is a factual finding from API data but should be confirmed for any weighting implications.

---

## 6. Methodology Notes

- **Scale cap:** None applied. Tests ran at MEDIUM (10,000 buses) for scalability, LARGE (~28,000 buses) for FNM ingestion.
- **FNM status:** Suite G executed (FNM_PATH set). MATPOWER `.m` fallback used because GridCal cannot parse intermediate CSV tables.
- **Tests skipped:** G-FNM-2 (blocked by G-FNM-1 failure). C-10 not executed (cascaded from A-11).
- **Solver versions:** HiGHS (bundled via highspy >= 1.8.0), SCIP (via PuLP SCIP_CMD), PuLP 3.3.0.
- **Tool version:** VeraGridEngine 5.6.28 (installed from PyPI; latest at evaluation time was 5.6.38).
- **Devcontainer environment:** Ubuntu 24.04, Python 3.12, uv-managed virtualenv.
- **Gate tests excluded from pass rates:** G-1, G-2, G-3 (all pass).
- **Informational tests excluded from pass rates:** D-1 through D-5, E-1 through E-7, B-6.
