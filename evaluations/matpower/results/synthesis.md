# Synthesis Report -- MATPOWER 8.1

**Contract:** FA714626C0006
**Tool version:** MATPOWER 8.1 (released 2025-07-13)
**Protocol version:** v11
**Skill version:** v2
**Synthesis date:** 2026-03-24

---

## 1. Executive Summary

MATPOWER 8.1 is a mature, mathematically transparent power systems simulation tool with exceptional supply chain properties and strong core power flow / OPF capabilities, but limited by its Octave solver ecosystem for MILP and advanced formulations. All three gate tests pass cleanly. The tool excels at DCPF, ACPF, DC OPF, and AC feasibility checking, with native PTDF/LODF computation and a well-documented custom constraint API. Critical weaknesses include the absence of native SCOPF and lossy DC OPF formulations, a GLPK exit flag integration bug that blocks SCUC result extraction in the Octave environment, and a bus factor of 1 for project maintenance. The scale cap is SMALL: all MEDIUM-tier scalability tests were skipped because C-4 SCUC failed at SMALL (cascaded from the GLPK integration bug, not a scalability limitation).

---

## 2. Test Results Summary

| Criterion | Tests Run | Pass | Qualified/Constrained | Fail | Skip | Informational | Confidence | Key Evidence |
|-----------|-----------|------|----------------------|------|------|---------------|------------|--------------|
| Problem Expressiveness | 10 | 5 | 3 (2 QP, 1 CP) | 2 | 0 | 0 | High | SCOPF and lossy DC OPF fail; SCUC qualified via GLPK bug |
| Extensibility | 8 | 4 | 2 | 0 | 0 | 1 | High | Clean constraint API, native PTDF/LODF, strong architecture |
| Scalability | 14 | 3 | 1 | 1 | 9 | 0 | Low | SMALL passes; all MEDIUM skipped (cascaded C-4 failure) |
| Workforce Accessibility | 5 | 0 | 0 | 0 | 0 | 5 | Medium | Good docs for core API; MOST/MP-Core docs less mature |
| Maturity & Sustainability | 7 | 0 | 0 | 0 | 0 | 7 | High | Bus factor 1; funding in transition; strong CI |
| Supply Chain (Gate) | 9 | 9 | 0 | 0 | 0 | 0 | High | BSD 3-Clause, zero dependencies, 100% inspectable |
| FNM Ingestion | 5 | 1 | 0 | 1 | 1 | 2 | Medium | No CSV import; DCPF reference passes; ACPF non-convergent |
| P2 Readiness | 3 | 0 | 0 | 0 | 0 | 3 | High | Native PSS/E RAW, PWL costs, clean commitment injection |

**Gate tests (G-1, G-2, G-3): 3/3 pass.** Excluded from pass rate statistics per protocol.

**Pass rate (scored tests, excluding gate and informational):** 13 pass + 6 qualified/constrained + 3 fail + 10 skip = 32 scored results. Of non-skip scored tests: 13 pass + 6 qualified/constrained + 3 fail = 22 tests. Independent failures: 3 (A-9, A-10, G-FNM-1). Blocked failures: 1 (C-4 SMALL, blocked_by A-5). Blocked skips: 9 MEDIUM tests (blocked_by C-SMALL-gate) + 1 G-FNM-2 (blocked_by G-FNM-1).

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness (Suite A)

#### Strengths

- Native DCPF with single-call API and structured output ([A-1](expressiveness/A-1_dcpf.md))
- Robust ACPF via built-in Newton-Raphson; 4-iteration convergence from flat start on TINY ([A-2](expressiveness/A-2_acpf.md))
- DC OPF with differentiated costs, LMP extraction, and binding branch shadow prices ([A-3](expressiveness/A-3_dcopf.md))
- Seamless DC OPF to AC PF pipeline within a single mpc struct; no file I/O needed ([A-4](expressiveness/A-4_ac_feasibility.md))
- MOST provides built-in SCUC formulation with all constraint types (MinUp/MinDown, startup costs, ramp rates, reserves, storage) ([A-5](expressiveness/A-5_scuc.md))
- Clean two-stage UC/ED separability via GEN_STATUS toggling and per-period rundcopf ([A-6](expressiveness/A-6_sced.md))
- MOST native multi-period DCOPF with storage via addstorage() API; correct BESS arbitrage behavior ([A-12](expressiveness/A-12_multiperiod_dcopf_storage.md))

#### Weaknesses

- No native SCOPF function; requires manual LODF computation and user constraint injection [tool-specific]. The 70%-derated case39 network is also N-1 infeasible [network configuration] ([A-9](expressiveness/A-9_scopf.md))
- No internal loss model in DC OPF; B-matrix excludes resistance [tool-specific]. Iterative loss injection produces correct total losses but zero marginal loss LMP components ([A-10](expressiveness/A-10_lossy_dcopf_lmp.md))
- OPF uses single slack bus internally; distributed slack available only via post-processing [tool-specific] ([A-11](expressiveness/A-11_distributed_slack_opf.md))
- GLPK exit flag integration bug prevents SCUC result extraction for non-trivial problems [solver-specific: MATPOWER miqps_glpk.m wrapper] ([A-5](expressiveness/A-5_scuc.md))
- MIPS solver diverges on multi-period QP with storage, forcing linear costs [solver-specific: MIPS numerical conditioning] ([A-12](expressiveness/A-12_multiperiod_dcopf_storage.md))

#### Workarounds Required

- A-5 SCUC: GLPK MIP gap exit code mapped to failure; validated on bundled test case instead of case39 -- **stable** (MOST API is documented; issue is solver-specific)
- A-11 Distributed slack: Post-processing via `makePTDF(baseMVA, bus, branch, slack_weights)` -- **stable** (documented public API)
- A-12 Multi-period storage: Linear costs instead of quadratic due to MIPS/GLPK solver limitations -- **stable** (behavioral pass conditions met; limitation is solver-specific)
- A-9 SCOPF: Benders iteration with LODF constraint injection via mpc.A/l/u -- **blocking** (API works but problem is N-1 infeasible and MIPS has numerical issues)
- A-10 Lossy DC OPF: Iterative loss injection external to OPF -- **blocking** (cannot produce non-zero loss LMP components)

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| A-1 | TINY | pass | -- | -- | 0.07s | 28 |
| A-2 | TINY | pass | -- | -- | 0.09s | 32 |
| A-3 | TINY | pass | -- | -- | 0.10s | 55 |
| A-4 | TINY | pass | -- | -- | 0.48s | 247 |
| A-5 | TINY | qualified_pass | -- | stable | 0.68s | 283 |
| A-6 | TINY | pass | -- | -- | 1.06s | 554 |
| A-9 | TINY | fail | -- | blocking | N/A | 297 |
| A-10 | TINY | fail | -- | blocking | N/A | 375 |
| A-11 | TINY | qualified_pass | -- | stable | 0.28s | 300 |
| A-12 | TINY | constrained_pass | -- | -- | 0.73s | 501 |

**A-6 sced_mode: ed_only** -- per-period DC OPF without embedded security constraints.

#### Findings Summary

MATPOWER demonstrates strong expressiveness for core power flow and OPF formulations (A-1 through A-4 all pass cleanly). The MOST extension provides genuine SCUC and multi-period scheduling capability with all required constraint types built-in, though its practical use in the Octave environment is limited by the GLPK integration bug [solver-specific]. Two independent failures represent fundamental formulation gaps: no native SCOPF [tool-specific] and no internal loss model in DC OPF [tool-specific]. The distributed slack limitation is minor (clean documented workaround via makePTDF). 2 independent failures + 0 blocked failures.

---

### 3.2 Extensibility (Suite B)

#### Strengths

- Documented custom constraint API (`mpc.A/l/u`) with dual value extraction at `results.lin.mu.u.usr` ([B-1](extensibility/B-1_custom_constraints.md))
- Direct graph access via branch F_BUS/T_BUS with native `find_islands()` for connected-component analysis ([B-2](extensibility/B-2_graph_access.md))
- Native `makePTDF()`/`makeLODF()` enable efficient LODF-based contingency screening; 126 contingencies in 12.1s ([B-3](extensibility/B-3_contingency_sweep.md))
- Per-period rundcopf loop handles 240 scenario-hour solves (20 scenarios x 12 hours) at 0.148s/solve ([B-4](extensibility/B-4_stochastic_scenario.md))
- Single-call PTDF computation via `makePTDF()` with machine-precision flow accuracy (max error 1.5e-12 MW) ([B-9](extensibility/B-9_ptdf_extraction.md))
- Reference bus reconfiguration is a single matrix element assignment; LMPs invariant to slack choice ([B-8](extensibility/B-8_reference_bus_config.md))
- Dual-framework architecture (legacy procedural + MP-Core OO) with formal Extension API for adding custom elements ([B-6](extensibility/B-6_code_architecture.md))

#### Weaknesses

- MIPS solver fails with user constraints on QP problems [solver-specific: numerical singularity with augmented KKT system] ([B-1](extensibility/B-1_custom_constraints.md))
- No DataFrame abstraction; CSV export requires manual fopen/fprintf/fclose pattern for column headers [tool-specific: Octave platform limitation] ([B-5](extensibility/B-5_interoperability.md))

#### Workarounds Required

- B-1 Custom constraints: GLPK (LP) with PWL-linearized costs instead of MIPS (QP) -- **stable** (mpc.A/l/u is documented public API; solver limitation only)
- B-5 CSV export: Manual header writing via fopen/fprintf/fclose + dlmwrite -- **stable** (standard Octave I/O)

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| B-1 | TINY | qualified_pass | -- | stable | 0.70s | 210 |
| B-2 | TINY | pass | -- | -- | 0.17s | 166 |
| B-3 | TINY | pass | -- | -- | 12.13s | 382 |
| B-4 | TINY | pass | -- | -- | 36.04s | 281 |
| B-5 | TINY | qualified_pass | -- | stable | 0.25s | 153 |
| B-6 | N/A | informational | -- | -- | -- | -- |
| B-8 | TINY | pass | -- | -- | 1.81s | 242 |
| B-9 | TINY | pass | -- | -- | 0.29s | 169 |

#### Findings Summary

MATPOWER's extensibility is strong. The combination of native PTDF/LODF computation, documented custom constraint injection (mpc.A/l/u with dual extraction), and the flat mpc struct data model provides a capable foundation for custom analysis workflows. The in-place branch status toggling enables efficient contingency sweeps without model reconstruction. The B-6 architecture audit confirms clean solver interface separation with 12+ solver backends accessible via a single mpoption parameter. The only limitations are solver-specific (MIPS fails with user constraints on QP) and platform-specific (Octave lacks DataFrame abstractions). 0 independent failures + 0 blocked failures.

---

### 3.3 Scalability (Suite C)

#### Strengths

- DCPF on SMALL (2000-bus) in 0.103s ([C-1 SMALL](scalability/C-1_dcpf_scale_SMALL.md))
- ACPF on SMALL converges from flat start in 5 NR iterations, 0.165s ([C-2 SMALL](scalability/C-2_acpf_scale_SMALL.md))
- DC OPF on SMALL via MIPS in 0.507s with all LMPs resolved ([C-3 SMALL](scalability/C-3_dcopf_scale_SMALL.md))
- AC feasibility with progressive relaxation: SMALL converges at all levels with no violations ([C-5 SMALL](scalability/C-5_ac_feasibility_relaxation_SMALL.md))
- DCPF on FNM (~28,000-bus LARGE) in 0.217s via G-FNM-3 ([G-FNM-3](fnm_ingestion/G-FNM-3_fnm_dcpf_verification.md))

#### Weaknesses

- SCUC on SMALL fails due to GLPK exit flag integration bug (cascaded from A-5) [solver-specific: miqps_glpk.m wrapper] ([C-4 SMALL](scalability/C-4_scuc_scale_SMALL.md))
- All MEDIUM-tier tests skipped due to C-4 SMALL failure triggering the Suite C SMALL gate [cascaded]
- GLPK fails with singular basis on SMALL DC OPF even with linear costs [solver-specific] ([C-3 SMALL](scalability/C-3_dcopf_scale_SMALL.md))

#### Workarounds Required

None applicable -- the SCUC failure is a solver integration bug, not addressable by workaround in the current Octave environment.

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| C-1 | SMALL | pass | -- | -- | 0.10s | 96 |
| C-1 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-2 | SMALL | pass | -- | -- | 0.17s | 168 |
| C-2 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-3 | SMALL | qualified_pass | -- | -- | 0.51s | 187 |
| C-3 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-4 | SMALL | fail | A-5 | -- | 1.11s | 220 |
| C-4 | MEDIUM | skip | C-4 | -- | -- | -- |
| C-5 | SMALL | pass | -- | -- | 0.17s | 196 |
| C-5 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-7 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-8 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-9 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-10 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |

#### Findings Summary

MATPOWER demonstrates strong scalability for power flow and DC OPF at SMALL scale (2000-bus): DCPF in 0.1s, ACPF in 0.17s, DC OPF in 0.5s. The FNM DCPF result (~28,000-bus in 0.217s) provides additional evidence of scalability for linear solves. However, the Suite C SMALL gate failed because C-4 SCUC failed -- this is a cascaded failure from the A-5 GLPK integration bug (blocked_by: A-5), not a scalability limitation. MOST assembled and GLPK solved the 162K-variable SCUC problem in 1.1s, but the solution could not be extracted. All 9 MEDIUM-tier tests are skipped as a consequence. 1 independent failure (C-4 SMALL, but blocked_by A-5 -- effectively 0 independent scalability failures) + 9 blocked skips.

**Scale cap: SMALL** -- applied due to C-4 SCUC failure triggering the Suite C SMALL gate. Evidence from G-FNM-3 (DCPF on 28k-bus FNM) suggests DCPF/ACPF would scale to MEDIUM/LARGE, but this cannot be verified within the gated protocol.

---

### 3.4 Workforce Accessibility (Suite D)

All Suite D tests produce informational results (no pass/fail scoring).

#### Strengths

- Core API (`runpf`, `rundcopf`, `loadcase`) is minimal and well-documented; first solve requires 3 lines of code ([D-1](accessibility/D-1_install_to_first_solve.md))
- User's Manual (247 pages) is comprehensive for legacy API; 5 of 10 Suite A tests completable from docs alone ([D-2](accessibility/D-2_documentation_audit.md))
- 6 of 7 tested examples run without modification in Octave ([D-3](accessibility/D-3_example_verification.md))
- Strong data validation errors: bus type and missing field errors are clear and actionable ([D-4](accessibility/D-4_error_quality.md))

#### Weaknesses

- Interactive installer (`install_matpower.m`) blocks on stdin; unusable in CI/Docker/batch [tool-specific] ([D-1](accessibility/D-1_install_to_first_solve.md))
- Hidden path dependencies (`mips/lib`, `mp-opt-model/lib`) not documented outside interactive installer [tool-specific] ([D-1](accessibility/D-1_install_to_first_solve.md))
- RATE_A=0 treated as "no limit" (silent success with different problem than intended) [tool-specific] ([D-4](accessibility/D-4_error_quality.md))
- GLPK exitflag=-9 error message gives no indication that a feasible solution exists [solver-specific] ([D-4](accessibility/D-4_error_quality.md))
- MOST table format (xgd_table, sd_table, profile structs) underdocumented; requires reading source code [tool-specific] ([D-2](accessibility/D-2_documentation_audit.md))
- No DataFrame abstraction; Octave's manual CSV parsing adds 10-20 lines per file compared to Python/Julia [tool-specific: platform] ([D-5](accessibility/D-5_code_volume.md))
- Median test LOC is 265 lines; MOST setup adds 30-60 lines of boilerplate per test ([D-5](accessibility/D-5_code_volume.md))

#### Findings Summary

MATPOWER's accessibility is strong for core power flow and OPF operations -- the runpf/rundcopf API is among the most compact in the evaluation. However, advanced features (MOST scheduling, custom constraints) require source code reading, and the Octave platform imposes code volume overhead due to missing DataFrame abstractions. The install experience has moderate friction from the interactive installer and hidden path dependencies. Error diagnostics are mixed: excellent for data validation, poor for solver-level issues.

---

### 3.5 Maturity & Sustainability (Suite E)

All Suite E tests produce informational results (no pass/fail scoring).

#### Strengths

- 2 stable releases in 24 months (8.0 May 2024, 8.1 July 2025) ([E-1](maturity/E-1_release_cadence.md))
- 121 commits in last 12 months; active development continuing ([E-2](maturity/E-2_commit_activity.md))
- Comprehensive CI pipeline: 4 OS/platform combinations, multi-solver testing, dual legacy/MP-Core test suites ([E-6](maturity/E-6_ci_test_coverage.md))
- 800,000+ downloads; most widely cited open-source power systems tool; MATPOWER case format is a de facto industry standard ([E-7](maturity/E-7_operational_adoption.md))

#### Weaknesses

- **Bus factor 1:** rdzman (Ray Zimmerman) accounts for 97.6% of lifetime commits and 100% of review authority [tool-specific] ([E-3](maturity/E-3_contributor_concentration.md))
- **Funding in transition:** Historical government/academic grants have ended; current funding limited to MathWorks sponsorship; commercial venture exploratory [tool-specific] ([E-4](maturity/E-4_funding_model.md))
- **No operational deployment:** Overwhelmingly academic/research tool; no confirmed production use at utilities or ISOs ([E-7](maturity/E-7_operational_adoption.md))
- Batched issue response pattern: median time-to-close 37 days with bimodal distribution ([E-5](maturity/E-5_issue_tracker_health.md))
- No quantitative code coverage metric published ([E-6](maturity/E-6_ci_test_coverage.md))

#### Findings Summary

MATPOWER is a mature, actively maintained project with a 25+ year history and strong academic adoption. The bus factor of 1 and funding transition are the most significant sustainability risks. The maintainer's retirement from Cornell and move to private employment introduces uncertainty about long-term open-source investment. Despite plans to expand the maintainer team announced in December 2024, contributor data as of March 2026 shows no material diversification. CI quality is strong. No operational deployment evidence exists, consistent with the tool's stated purpose as a research and education platform.

---

### 3.6 Supply Chain (Suite F -- Gate)

#### Strengths

- BSD 3-Clause license with no copyleft or proprietary restrictions ([F-1](supply_chain/F-1_core_license.md))
- Zero external dependencies; all 4 sub-packages bundled in the distribution ([F-2](supply_chain/F-2_dependency_tree.md))
- All bundled packages BSD 3-Clause; no copyleft in core distribution ([F-3](supply_chain/F-3_dependency_license_audit.md))
- 100% pure MATLAB/Octave code; zero compiled extensions in distribution ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- Full execution path traceable through human-readable .m files; zero opaque steps ([F-5](supply_chain/F-5_code_inspectability.md))
- Version-pinned GitHub releases with SHA-256 checksums; Zenodo DOIs for archival persistence ([F-6](supply_chain/F-6_distribution_integrity.md))
- Fully air-gap installable: single zip extract, no runtime network calls ([F-7](supply_chain/F-7_airgap_installability.md))
- Built-in MIPS solver eliminates hard dependency on external solvers ([F-8](supply_chain/F-8_solver_dependency.md))
- Version-pinned, checksummed, immutable download artifacts ([F-9](supply_chain/F-9_getting_started_integrity.md))

#### Weaknesses

- GLPK (GPL-3.0) is the primary available MILP solver in Octave, introducing optional copyleft exposure [solver-specific] ([F-3](supply_chain/F-3_dependency_license_audit.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| F-1 | pass | BSD 3-Clause, no copyleft |
| F-2 | pass | 4 bundled deps, zero external, tree depth 1 |
| F-3 | pass | All bundled deps BSD 3-Clause |
| F-4 | pass | 0 compiled binaries in distribution |
| F-5 | pass | 0 opaque execution steps |
| F-6 | pass | SHA-256 checksums, Zenodo DOIs |
| F-7 | pass | Full air-gap install capability |
| F-8 | pass | Built-in MIPS solver, no hard external dep |
| F-9 | pass | Version-pinned immutable artifacts |

#### Findings Summary

MATPOWER achieves a perfect 9/9 on supply chain tests. The self-contained distribution model (single zip, all deps bundled, zero runtime network calls) is the strongest supply chain profile in this evaluation. 100% code inspectability (no compiled extensions) enables full audit of the execution path from API call to solver invocation. The only copyleft exposure is the optional GLPK solver (GPL-3.0), which can be avoided by using the built-in MIPS solver (BSD 3-Clause).

---

## 3b. FNM Ingestion Findings (Suite G)

### Data Model Fidelity

**G-FNM-1: FAIL** -- MATPOWER cannot parse the intermediate CSV tables. Its data ingestion API is limited to MATPOWER case files (`.m`/`.mat` via `loadcase()`) and PSS/E RAW files (via `psse2mpc()`). No CSV import function exists in the MATPOWER 8.1 source tree. Building a CSV-to-MPC importer would require hundreds of lines of custom code, equivalent in scope to `psse2mpc()` [tool-specific: no tabular/CSV import API] ([G-FNM-1](fnm_ingestion/G-FNM-1_fnm_ingestion_gate.md)).

**G-FNM-2: SKIP** -- Blocked by G-FNM-1 failure. Field coverage against the criticality matrix cannot be evaluated without CSV ingestion. When MATPOWER ingests data via its native format or `psse2mpc()`, all DCPF-critical fields are preserved by design ([G-FNM-2](fnm_ingestion/G-FNM-2_fnm_field_coverage.md)).

### Power Flow Verification

**G-FNM-3: PASS** -- DCPF on the ~28,000-bus FNM main island (via MATPOWER fallback `.mat` path) in 0.217s. All deviations at float64 machine noise (max VA deviation 5.0e-9 deg, max branch flow deviation 5.0e-7%). Bus injection power balance confirmed to machine precision (max mismatch 6.2e-9 MW). MATPOWER is the reference DCPF implementation for this network ([G-FNM-3](fnm_ingestion/G-FNM-3_fnm_dcpf_verification.md)).

**G-FNM-4: INFORMATIONAL** -- ACPF fails to converge at all relaxation levels (0%, 10%, 20%) with singular Jacobian (rcond ~1.9e-17). DCPF angles reach 537 degrees absolute maximum, indicating structurally ill-conditioned network. The ACPF reference data contains non-physical values (VM up to 379,646 pu), confirming this is a network characteristic rather than a tool limitation [solver-specific: Newton-Raphson on structurally ill-conditioned network] ([G-FNM-4](fnm_ingestion/G-FNM-4_fnm_acpf_convergence.md)).

### Supplemental Data Representability

**G-FNM-5: INFORMATIONAL** -- MATPOWER achieves 45% native (N), 27% extension (E), 28% external (X) field coverage across 7 supplemental CSVs (44 fields). Key differentiator: native interface support via `mpc.if`/`mpc.iflim` with `toggle_iflims` for OPF enforcement. Three-tier thermal ratings (RATE_A/B/C) also native. Gaps: no contingency definitions, no trading hub model, no temporal/outage scheduling concepts ([G-FNM-5](fnm_ingestion/G-FNM-5_fnm_supplemental_csv.md)).

**Expressiveness additive evidence:** G-FNM-3 confirms DCPF scales to LARGE (28k buses) in sub-second time, strengthening the scalability assessment beyond Suite C SMALL results. G-FNM-5 native interface support strengthens extensibility for flowgate-based congestion analysis.

**Extensibility additive evidence:** G-FNM-5 shows MATPOWER's `mpc` struct extension mechanism provides a clean path for carrying 27% of supplemental fields alongside the network model. The 28% external fields (hubs, outage schedules) are fundamentally outside MATPOWER's domain model.

---

## 4. Cross-Cutting Observations

### API Friction Patterns

- **No CSV/tabular import:** MATPOWER's data model is tightly coupled to its own case format (position-indexed numeric matrices). Workflows requiring data from non-MATPOWER sources must pre-convert to `.m`/`.mat` format or build custom import code. This is the single largest API friction point for operational integration ([api-friction: G-FNM-1](observations/api-friction-fnm_ingestion-G-FNM-1_fnm_ingestion_gate.md)).
- **No DataFrame abstraction:** Results are bare numeric matrices with no column name metadata. CSV export with headers requires 4 lines per table instead of 1 ([api-friction: B-5](observations/api-friction-extensibility-B-5_interoperability.md)).

### Documentation Gaps

- MOST table formats (xgd_table, sd_table, profile structs) underdocumented; column names must be discovered from source code or examples ([D-2](accessibility/D-2_documentation_audit.md))
- Internal/external indexing (`ext2int`/`int2ext`) critical for custom constraint injection but explained only in Developer Manual ([D-2](accessibility/D-2_documentation_audit.md))
- MP-Core (new framework) Developer Manual less mature than the legacy User's Manual ([D-2](accessibility/D-2_documentation_audit.md))
- Lossy DC OPF and LMP decomposition not documented because the capability does not exist ([D-2](accessibility/D-2_documentation_audit.md))

### Solver Ecosystem

- **HiGHS unavailable in Octave devcontainer** [solver-specific]: `have_feature('highs')` returns 0. MATPOWER documents HiGHS support but it requires separate MEX/Octave binding installation ([solver-issues: A-3](observations/solver-issues-expressiveness-A-3_dcopf.md))
- **GLPK exit flag integration bug** [solver-specific: MATPOWER miqps_glpk.m wrapper]: GLPK's GLP_EMIPGAP (errnum=9) mapped to exitflag=-9, blocking MOST post-processing. Affects all non-trivial MILP problems where GLPK terminates at MIP gap tolerance ([solver-issues: A-5](observations/solver-issues-expressiveness-A-5_scuc.md))
- **MIPS numerical instability with user constraints** [solver-specific: MIPS]: Fails on QP problems with augmented constraint matrices (A-9 SCOPF, B-1 custom constraints). Also diverges on multi-period QP with storage ([solver-issues: B-1](observations/solver-issues-extensibility-B-1_custom_constraints.md), [solver-issues: A-12](observations/solver-issues-expressiveness-A-12_multiperiod_dcopf_storage.md))
- **GLPK singular basis at SMALL scale** [solver-specific: GLPK]: Fails with singular basis on 2000-bus DC OPF even with linear costs ([solver-issues: C-3](observations/solver-issues-scalability-C-3_dcopf_scale.md))
- **MIPS/GLPK fail with LODF constraints at MEDIUM** [mixed: tool lacks native SCOPF + solvers cannot handle manual constraint injection at scale] ([solver-issues: C-8](observations/solver-issues-scalability-C-8_scopf_scale.md))

**Summary:** MATPOWER's Octave solver ecosystem is significantly more constrained than its MATLAB counterpart. MIPS handles core PF/OPF well but struggles with augmented constraint matrices and large multi-period QPs. GLPK is unreliable beyond TINY-scale for MILP and singular on SMALL-scale LP. HiGHS would likely resolve many of these issues but is not available. Commercial solvers (CPLEX, Gurobi) are the primary design targets for MOST.

### Architecture Quality

- **Flat data model enables low-friction contingency analysis:** In-place branch status toggling (`BR_STATUS=0`) without model reconstruction. Combined with native `makePTDF()`/`makeLODF()` and `find_islands()`, provides all building blocks for N-M sweeps ([arch-quality: B-3](observations/arch-quality-extensibility-B-3_contingency_sweep.md)).
- **Dual-framework architecture (legacy + MP-Core):** Legacy procedural framework (stable since 1997) coexists with new OO MP-Core (introduced 8.0). MP-Core provides clean 4-layer separation and formal Extension API. Core DCPF solver (`dcpf.m`) is 46 lines -- one of the most transparent implementations in this evaluation ([arch-quality: B-6](observations/arch-quality-extensibility-B-6_code_architecture.md)).

### FNM Data Model

- MATPOWER achieves 45% native supplemental field coverage (second among evaluated tools). Native interface support (`mpc.if`/`mpc.iflim`) is a differentiator shared only with PowerSimulations.jl. Gaps in contingency definitions and market-layer data are consistent with MATPOWER's domain as a power system simulation tool rather than a market operations platform ([fnm-data-model: G-FNM-5](observations/fnm-data-model-fnm_ingestion-G-FNM-5_fnm_supplemental_csv.md)).

---

## 5. Items Requiring Human Spot-Check

- [ ] A-5 (SCUC qualified_pass) -- SCUC formulation validated on bundled ex_case3b test case, not on case39. The GLPK exit flag bug prevents result extraction on case39 but the API and formulation are correct. Spot-check whether the ex_case3b validation is sufficient evidence of SCUC expressiveness.
- [ ] A-9 (SCOPF fail) -- Failure has two contributing factors: (1) 70%-derated case39 is N-1 infeasible [network configuration], (2) no native SCOPF function [tool-specific]. Spot-check whether network infeasibility should partially mitigate the fail grade, given that the Benders iteration completed 2 iterations and the API building blocks (makePTDF, makeLODF, mpc.A/l/u) work correctly.
- [ ] A-11 (distributed slack qualified_pass) -- Post-processing via `makePTDF` with documented slack distribution vector. Spot-check whether this should be pass vs qualified_pass, given that the API is documented and results are mathematically correct for lossless DC OPF.
- [ ] A-12 (constrained_pass) -- All three behavioral pass conditions met with linear costs. Quadratic costs failed due to MIPS/GLPK solver limitations [solver-specific]. Spot-check whether constrained_pass is appropriate vs qualified_pass.
- [ ] B-1 (qualified_pass) -- Custom constraint API works correctly but requires GLPK (LP) instead of MIPS (QP). Solver limitation is clearly solver-specific. Spot-check whether the MIPS failure should affect the extensibility grade.
- [ ] C-3 SMALL (qualified_pass) -- MIPS pass, GLPK fail. Spot-check whether single-solver success is sufficient for pass vs qualified_pass.
- [ ] C-4 SMALL (fail, blocked_by A-5) -- MOST assembles the SCUC correctly and GLPK solves in 1.1s, but exit flag mapping prevents extraction. Spot-check whether this should be classified as a tool failure or solver integration bug, and its impact on the SMALL gate.
- [ ] E-3 (bus factor 1) -- Single-maintainer risk with funding in transition. Spot-check current contributor activity (may have changed since March 2026 data collection).
- [ ] G-FNM-1 (fail) -- MATPOWER cannot parse intermediate CSV tables but can parse PSS/E RAW directly via `psse2mpc()`. Spot-check whether RAW parsing capability should partially mitigate the CSV ingestion failure.
- [ ] Solver-vs-tool attribution -- Multiple test limitations stem from the Octave solver ecosystem (MIPS, GLPK) rather than MATPOWER's architecture. Spot-check whether the evaluation adequately separates platform limitations from tool limitations for tiering purposes.

---

## 6. Methodology Notes

- **Scale cap applied:** SMALL -- C-4 SCUC failure at SMALL triggered the Suite C SMALL gate, skipping all MEDIUM tests. The C-4 failure is cascaded from the GLPK integration bug (blocked_by: A-5), not a genuine scalability limitation. G-FNM-3 provides supplementary evidence that DCPF scales to LARGE (28k buses).
- **FNM status:** Suite G partially executed. G-FNM-1 failed (no CSV import capability). G-FNM-3, G-FNM-4, G-FNM-5 executed via MATPOWER fallback path (`.mat` file). G-FNM-2 skipped (blocked by G-FNM-1).
- **Tests skipped and reason:** 10 tests skipped total: 9 MEDIUM scalability tests (C-1, C-2, C-3, C-4, C-5, C-7, C-8, C-9, C-10 MEDIUM) due to C-SMALL-gate; 1 FNM test (G-FNM-2) due to G-FNM-1 failure.
- **Solver versions used:** MIPS 1.5.2 (built-in), GLPK (via Octave 9.2.0 built-in binding), Newton-Raphson (MATPOWER built-in). HiGHS and IPOPT not available in devcontainer.
- **Tool version evaluated:** MATPOWER 8.1 (released 2025-07-13), with bundled MOST 1.3.1, MP-Opt-Model 5.0, MIPS 1.5.2, MP-Test 8.1.
- **Runtime environment:** GNU Octave 9.2.0 on Ubuntu 24.04 (devcontainer), single-threaded.
- **A-6 sced_mode:** ed_only -- per-period DC OPF without embedded security constraints.
