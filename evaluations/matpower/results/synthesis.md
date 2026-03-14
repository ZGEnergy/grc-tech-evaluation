# Synthesis Report — MATPOWER 8.1

**Contract:** 
**Protocol:** v10 | **Skill:** v1
**Tool Version:** MATPOWER 8.1 (GNU Octave 9.2.0)
**Generated:** 2026-03-14

---

## 1. Executive Summary

MATPOWER 8.1 is a mature, academically ubiquitous power systems simulation tool with exceptionally clean supply chain properties (100% pure .m source, BSD 3-Clause, zero compiled extensions, fully air-gap installable). Its core power flow and DC OPF capabilities are strong and fast, with native PTDF/LODF computation and a well-documented user constraint API. However, two blocking expressiveness failures (SCOPF and lossy DCOPF/LMP decomposition) and a pervasive solver ecosystem limitation on Octave -- where only MIPS (built-in) and GLPK are available, with no HiGHS or Ipopt -- constrain its effective capability envelope. The MATPOWER-GLPK exit flag integration bug cascades from A-5 through C-4, blocking all MEDIUM scalability tests and preventing SCUC evaluation at scale. The bus factor of 1 (97.6% of lifetime commits from a single maintainer) and the funding model transition from academic grants to an uncertain commercial path represent the most significant maturity risks. All gates passed (TINY/SMALL/MEDIUM ingestion); scale cap is MEDIUM.

---

## 2. Grade Recommendations Table

| Criterion | Grade | Confidence | Key Evidence |
|-----------|-------|------------|--------------|
| Problem Expressiveness | B- | High | 6 pass + 3 qualified_pass + 2 fail (A-9 SCOPF, A-10 lossy LMP); core PF/OPF strong but advanced formulations blocked by solver limitations |
| Extensibility | A- | High | 5 pass + 3 qualified_pass; native PTDF/LODF, clean user constraint API, excellent architecture; limited by MIPS solver with user constraints |
| Scalability | C+ | Medium | 4 pass + 1 qualified_pass + 1 fail at SMALL; all 8 MEDIUM tests skipped (cascaded from C-4/A-5); FNM DCPF in 0.168s is strong evidence |
| Workforce Accessibility | B | Medium | Strong docs for core API (247-page manual), MOST docs less mature; moderate install friction; mixed error quality |
| Maturity & Sustainability | C+ | High | Bus factor 1 (97.6% single contributor), funding in transition, no operational deployments; strong CI and 25+ year track record partially compensate |
| Supply Chain (Gate) | A | High | All 9 tests pass; BSD 3-Clause throughout, zero compiled extensions, fully air-gap installable, built-in solver |

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness

#### Strengths
- Native DC power flow with structured output and sub-second solve times ([A-1](expressiveness/A-1_dcpf.md))
- Robust AC power flow with Newton-Raphson converging from flat start in 4-5 iterations ([A-2](expressiveness/A-2_acpf.md))
- DC OPF with differentiated costs, LMP extraction, and binding branch identification ([A-3](expressiveness/A-3_dcopf.md))
- Seamless DC OPF to AC PF workflow within the same mpc struct -- no file I/O needed ([A-4](expressiveness/A-4_ac_feasibility.md))
- MOST provides built-in SCUC formulation with all standard constraint types (min up/down, startup costs, ramp rates, reserves) ([A-5](expressiveness/A-5_scuc.md))
- Clean two-stage UC/ED separation via GEN_STATUS and per-period rundcopf ([A-6](expressiveness/A-6_sced.md))
- Native multi-period DCOPF with storage via MOST addstorage() API -- cyclic SoC, charge/discharge efficiency, arbitrage behavior all correct ([A-12](expressiveness/A-12_multiperiod_dcopf_storage.md))

#### Weaknesses
- No native SCOPF function; user constraint injection via mpc.A/l/u fails with MIPS solver due to numerical singularity ([A-9](expressiveness/A-9_scopf.md))
- No internal loss model in DC OPF -- iterative loss injection produces correct totals but zero-valued loss LMP components, blocking LMP decomposition ([A-10](expressiveness/A-10_lossy_dcopf_lmp.md))
- Distributed slack not supported in OPF solver itself (open issue #136) -- requires post-processing via makePTDF ([A-11](expressiveness/A-11_distributed_slack_opf.md))

#### Workarounds Required
- A-5 (SCUC): GLPK MIP gap termination code mapped to failure exit flag by miqps_glpk.m; validated on bundled test case instead -- **stable**
- A-6 (SCED): Per-period rundcopf with manual Pmin/Pmax ramp tightening instead of MOST CommitKey mechanism -- **stable**
- A-11 (distributed slack): Post-processing LMPs via makePTDF with slack weight vector instead of native OPF support -- **stable**
- A-12 (multi-period storage): Linear costs with GLPK instead of quadratic costs due to MIPS numerical issues -- **stable**
- A-9 (SCOPF): No viable workaround within available solver ecosystem -- **blocking**
- A-10 (lossy LMP): No viable workaround without modifying source code power balance equations -- **blocking**

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| A-1 | TINY | pass | -- | -- | 0.074s | 28 |
| A-2 | TINY | pass | -- | -- | 0.088s | 32 |
| A-3 | TINY | pass | -- | -- | 0.104s | 55 |
| A-4 | TINY | pass | -- | -- | 0.183s | 242 |
| A-5 | TINY | qualified_pass | -- | stable | 0.68s | 283 |
| A-6 | TINY | pass | -- | stable | 0.95s | 207 |
| A-9 | TINY | fail | -- | blocking | -- | 288 |
| A-10 | TINY | fail | -- | blocking | -- | 350 |
| A-11 | TINY | qualified_pass | -- | stable | 0.10s | 287 |
| A-12 | TINY | qualified_pass | -- | stable | 0.71s | 279 |

**Independent failures: 2 (A-9, A-10). Qualified passes: 3 (A-5, A-11, A-12).**

#### Grade Rationale

Grade: **B-**. MATPOWER demonstrates strong core expressiveness for PF, OPF, SCUC (formulation), SCED, and multi-period storage -- covering 8 of 10 tests with pass or qualified_pass. However, SCOPF (A-9) and lossy DCOPF with LMP decomposition (A-10) are blocking failures with no viable workaround. These are not merely solver-environment issues: A-10 reflects a fundamental formulation gap (no internal loss model in DC OPF), and A-9's MIPS singularity with user constraints is a practical limitation even though the API mechanism exists. The B- grade reflects "core capabilities strong, but two meaningful gaps without workarounds." This falls short of B ("mostly strong, one meaningful gap with stable workaround") because there are two independent blocking failures.

---

### 3.2 Extensibility

#### Strengths
- Documented user constraint API (mpc.A/l/u) with dual value extraction at results.lin.mu -- works with GLPK for LP problems ([B-1](extensibility/B-1_custom_constraints.md))
- Direct graph access via sparse adjacency matrix from branch F_BUS/T_BUS columns; native find_islands() for connected components ([B-2](extensibility/B-2_graph_access.md))
- Native makePTDF() and makeLODF() enable LODF-based contingency screening without re-solving; branch status toggling via BR_STATUS avoids model reconstruction ([B-3](extensibility/B-3_contingency_sweep.md))
- Programmatic scenario loop with per-period mpc modification is frictionless -- 240 solves in 7.7s ([B-4](extensibility/B-4_stochastic_scenario.md))
- Reference bus reconfiguration is a 2-line matrix write (BUS_TYPE column) -- no model reconstruction needed ([B-8](extensibility/B-8_reference_bus_config.md))
- Native makePTDF() with machine-precision flow accuracy (error < 1e-12 MW) and support for custom slack distribution vectors ([B-9](extensibility/B-9_ptdf_extraction.md))
- Dual-framework architecture (legacy + MP-Core) with formal Extension API for custom elements and formulations ([B-6](extensibility/B-6_code_architecture.md))

#### Weaknesses
- MIPS solver fails with user constraints (mpc.A) for QP problems -- limits custom constraint injection to LP formulations in Octave ([B-1](extensibility/B-1_custom_constraints.md))
- No DataFrame abstraction -- CSV export with headers requires verbose fopen/fprintf/dlmwrite pattern ([B-5](extensibility/B-5_interoperability.md))

#### Workarounds Required
- B-1 (custom constraints): Used GLPK with linear costs instead of MIPS with quadratic costs; removed branch derating -- **stable**
- B-4 (stochastic scenario): Per-period rundcopf loop instead of MOST multi-period framework; GLPK with linear costs -- **stable**
- B-5 (interoperability): Manual fopen/fprintf/dlmwrite for CSV headers; minimal export (no headers) is 3 lines -- **stable**

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| B-1 | TINY | qualified_pass | -- | stable | 0.203s | 283 |
| B-2 | TINY | pass | -- | -- | 0.035s | 190 |
| B-3 | TINY | pass | -- | -- | 3.526s | 368 |
| B-4 | TINY | pass | -- | stable | 7.73s | 280 |
| B-5 | TINY | qualified_pass | -- | stable | 0.118s | 176 |
| B-6 | N/A | pass | -- | -- | -- | -- |
| B-8 | TINY | pass | -- | -- | 0.20s | 195 |
| B-9 | TINY | pass | -- | -- | 0.116s | 212 |

**Independent failures: 0. Qualified passes: 2 (B-1, B-5).**

#### Grade Rationale

Grade: **A-**. MATPOWER's extensibility is strong across all 8 tests (5 pass, 3 qualified_pass, 0 fail). The flat data model with named column constants enables frictionless network modification, and native PTDF/LODF/island detection provide essential building blocks for advanced analysis. The formal Extension API in MP-Core is a significant architectural asset. The two qualified passes (B-1 solver limitation, B-5 no DataFrame) are minor gaps with stable workarounds. This meets the A- standard: "strong across the board with minor gaps that have clean workarounds."

---

### 3.3 Scalability

#### Strengths
- DCPF on SMALL (2000 buses) in 0.103s with 1.9 MB peak memory ([C-1](scalability/C-1_dcpf_scale_SMALL.md))
- ACPF on SMALL converges from flat start in 5 NR iterations, 0.165s ([C-2](scalability/C-2_acpf_scale_SMALL.md))
- DC OPF on SMALL with MIPS in 0.507s -- all uniform LMPs confirm uncongested network ([C-3](scalability/C-3_dcopf_scale_SMALL.md))
- AC feasibility on SMALL at 0%/10%/20% relaxation -- all converge from flat start identically ([C-5](scalability/C-5_ac_feasibility_relaxation_SMALL.md))
- FNM DCPF (27,862 buses) in 0.168s demonstrates sub-second performance at LARGE scale ([G-FNM-3](fnm_ingestion/G-FNM-3_fnm_dcpf_verification.md))

#### Weaknesses
- C-4 (SCUC on SMALL) fails due to cascaded GLPK exit flag bug from A-5 -- all 8 MEDIUM scalability tests skipped ([C-4](scalability/C-4_scuc_scale_SMALL.md))
- GLPK fails with singular basis on SMALL DC OPF even with linear costs ([C-3](scalability/C-3_dcopf_scale_SMALL.md))
- Only MIPS available for QP/NLP problems on Octave; no HiGHS, no Ipopt binding

#### Workarounds Required
- C-3 (DC OPF): Used MIPS instead of HiGHS/GLPK -- no workaround needed for MIPS path
- C-4 (SCUC): No viable workaround -- GLPK exit flag mapping bug blocks solution extraction -- **blocking (cascaded from A-5)**

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| C-1 | SMALL | pass | -- | -- | 0.103s | 96 |
| C-2 | SMALL | pass | -- | -- | 0.165s | 168 |
| C-3 | SMALL | qualified_pass | -- | -- | 0.507s | 187 |
| C-4 | SMALL | fail | A-5 | -- | 1.112s | 220 |
| C-5 | SMALL | pass | -- | -- | 0.168s | 196 |
| C-1 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-2 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-3 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-5 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-7 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-8 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-9 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-10 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |

**Independent failures: 0. Cascaded failures: 1 (C-4, blocked by A-5). Skipped: 8 (MEDIUM tier).**

#### Grade Rationale

Grade: **C+**. The SMALL-tier results are strong (4 pass, 1 qualified_pass), and FNM DCPF at LARGE scale (0.168s for 28k buses) provides compelling evidence of efficient sparse linear algebra. However, the C-4 cascaded failure from A-5 triggers the Suite C SMALL gate, blocking all 8 MEDIUM-tier tests. This severely limits scalability evidence. The C-4 failure is a solver integration bug (GLPK exit flag mapping), not a fundamental scalability limitation -- GLPK solved the 162K-variable SCUC problem in 1.1s, but MOST cannot extract the results. The C+ grade reflects "limited evidence due to cascaded gate failure; available evidence is positive but incomplete." A higher grade cannot be justified without MEDIUM-tier evidence.

---

### 3.4 Workforce Accessibility

#### Strengths
- Core API (runpf, rundcopf, loadcase) is minimal and well-documented in the 247-page User's Manual ([D-2](accessibility/D-2_documentation_audit.md))
- 6 of 7 tested examples run without modification; inline manual examples are reliable ([D-3](accessibility/D-3_example_verification.md))
- Error validation for data quality issues (invalid bus types, missing fields) is excellent -- pinpoints exact bus and field ([D-4](accessibility/D-4_error_quality.md))
- First solve requires only 3 lines of code after path setup ([D-1](accessibility/D-1_install_to_first_solve.md))
- 5 of 10 Suite A tests completable from docs alone ([D-2](accessibility/D-2_documentation_audit.md))

#### Weaknesses
- Interactive installer (install_matpower.m) unusable in CI/Docker/batch mode -- blocks on stdin input() ([D-1](accessibility/D-1_install_to_first_solve.md))
- Hidden path dependencies (mips/lib, mp-opt-model/lib) not documented outside interactive installer ([D-1](accessibility/D-1_install_to_first_solve.md))
- RATE_A = 0 silently means "unconstrained" rather than "zero capacity" -- produces wrong results with no warning ([D-4](accessibility/D-4_error_quality.md))
- MIPS solver diagnostics poor -- "matrix singular to machine precision" with no root cause indication ([D-4](accessibility/D-4_error_quality.md))
- GLPK exitflag=-9 gives no indication that a feasible solution was found ([D-4](accessibility/D-4_error_quality.md))
- MOST table format (xgd_table, sd_table) underdocumented -- requires source code reading ([D-2](accessibility/D-2_documentation_audit.md))
- Higher code volume than Python tools due to manual CSV parsing, no DataFrame abstraction, path setup boilerplate ([D-5](accessibility/D-5_code_volume.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| D-1 | informational | 2-3 min install with friction; interactive installer unusable in CI |
| D-2 | informational | 5/10 Suite A from docs alone; MOST docs need source reading |
| D-3 | informational | 6/7 examples work; 1 fails on path issue |
| D-4 | informational | Mixed: excellent data validation, poor solver diagnostics |
| D-5 | informational | Median 265 LOC per Suite A test; core solve is 1-5 lines |

#### Grade Rationale

Grade: **B**. The core API is compact and the User's Manual is among the most comprehensive in the evaluation. Getting-started examples are reliable, and data validation errors are well-diagnosed. However, installation friction (interactive installer, hidden path dependencies), poor solver-level diagnostics (MIPS singularity, GLPK exit flag), the RATE_A=0 semantic trap, and MOST documentation gaps lower the grade. Higher code volume due to Octave's lack of DataFrame abstractions is a platform limitation. This meets the B standard: "good overall with identifiable friction points that are manageable but not negligible."

---

### 3.5 Maturity & Sustainability

#### Strengths
- 25+ year development history with stable core algorithms since the 1990s ([E-1](maturity/E-1_release_cadence.md))
- 2 releases in 24 months (8.0 and 8.1), with 8.0 being a major architectural rewrite ([E-1](maturity/E-1_release_cadence.md))
- Comprehensive CI pipeline: 4 OS/platform combinations, multi-solver testing, consistently passing ([E-6](maturity/E-6_ci_test_coverage.md))
- Most widely cited open-source power systems tool; 800K+ downloads; MATPOWER case format is a de facto industry standard ([E-7](maturity/E-7_operational_adoption.md))
- 121 commits in last 12 months with ongoing feature development, not just maintenance ([E-2](maturity/E-2_commit_activity.md))

#### Weaknesses
- Bus factor of 1: rdzman (Ray Zimmerman) accounts for 97.6% of lifetime commits and 100% of review authority ([E-3](maturity/E-3_contributor_concentration.md))
- Funding model in transition: NSF grants ended, Cornell affiliation ended, current funding limited to MathWorks sponsorship; commercial venture exploratory ([E-4](maturity/E-4_funding_model.md))
- No confirmed operational deployments at utilities or ISOs -- exclusively academic/research adoption ([E-7](maturity/E-7_operational_adoption.md))
- Batched issue response pattern: median 37 days to close, with many issues batch-closed months later without explanation ([E-5](maturity/E-5_issue_tracker_health.md))
- No quantitative code coverage metrics published ([E-6](maturity/E-6_ci_test_coverage.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| E-1 | informational | 2 releases in 24 months; annual cadence improving |
| E-2 | informational | 121 commits/12mo; 87.6% from single maintainer |
| E-3 | informational | Bus factor 1; top contributor 97.6% lifetime |
| E-4 | informational | Grant funding ended; MathWorks sponsorship + exploratory commercial |
| E-5 | informational | Median 37d to close; batched triage pattern |
| E-6 | informational | CI on 4 platforms, consistently passing; no coverage metrics |
| E-7 | informational | 800K downloads, no operational deployments |

#### Grade Rationale

Grade: **C+**. MATPOWER's 25-year track record, comprehensive CI, and academic ubiquity are significant maturity strengths. However, the bus factor of 1 is the most severe contributor concentration in the evaluation -- 97.6% from a single maintainer who has retired from his academic position and whose continued availability depends on employer goodwill at a private company. The funding transition from government grants to an uncertain model with no established replacement compounds this risk. The absence of operational deployments means no production-grade reliability validation exists. The C+ grade reflects "meaningful maturity risks that offset a strong track record." The bus factor alone prevents a B- or higher grade.

---

### 3.6 Supply Chain (Gate)

#### Strengths
- BSD 3-Clause license throughout all bundled code -- no copyleft exposure in core distribution ([F-1](supply_chain/F-1_core_license.md), [F-3](supply_chain/F-3_dependency_license_audit.md))
- Zero external runtime dependencies; 4 sub-packages all bundled in distribution zip ([F-2](supply_chain/F-2_dependency_tree.md))
- 100% pure .m source code -- zero compiled extensions (.mex, .so, .dll, .oct) in entire distribution ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- Full execution path traceable through human-readable source files; zero opaque steps ([F-5](supply_chain/F-5_code_inspectability.md))
- Fully air-gap installable: download zip, extract, addpath -- no network access at runtime ([F-7](supply_chain/F-7_airgap_installability.md))
- Built-in MIPS solver handles all core PF/OPF formulations without any external solver dependency ([F-8](supply_chain/F-8_solver_dependency.md))
- Version-pinned GitHub releases with SHA-256 checksums and Zenodo DOIs for archival persistence ([F-6](supply_chain/F-6_distribution_integrity.md), [F-9](supply_chain/F-9_getting_started_integrity.md))

#### Weaknesses
- None identified in the core distribution. GLPK (GPL-3.0) is optional and avoidable.

#### Evidence Summary Table

| Test | Network | Status | Key Finding |
|------|---------|--------|-------------|
| F-1 | N/A | pass | BSD 3-Clause, no copyleft |
| F-2 | N/A | pass | 4 bundled deps, tree depth 1, zero external |
| F-3 | N/A | pass | All bundled deps BSD 3-Clause |
| F-4 | N/A | pass | Zero compiled extensions |
| F-5 | N/A | pass | Zero opaque steps in execution path |
| F-6 | N/A | pass | Versioned releases with SHA-256 |
| F-7 | N/A | pass | Fully air-gap installable |
| F-8 | N/A | pass | Built-in MIPS solver, no commercial requirement |
| F-9 | N/A | pass | Version-pinned, immutable release artifacts |

#### Grade Rationale

Grade: **A**. MATPOWER achieves the highest possible supply chain score. Every test passes without qualification. The combination of BSD 3-Clause licensing, zero compiled extensions, zero external runtime dependencies, built-in solver, full code inspectability, air-gap installability, and version-pinned distribution with checksums represents the cleanest supply chain in the evaluation. This meets the A standard: "no supply chain concerns identified."

---

### 3b. FNM Ingestion Findings (Suite G)

Suite G executed (FNM_PATH set). G-FNM-1 failed; G-FNM-2 skipped; G-FNM-3/4/5 used MATPOWER fallback path.

#### Data Model Fidelity

G-FNM-1 **failed**: MATPOWER has no CSV import capability. Its data ingestion is limited to `.m`/`.mat` via `loadcase()` and PSS/E RAW via `psse2mpc()`. Building a CSV-to-MPC importer would require hundreds of lines of custom code equivalent to psse2mpc() itself. G-FNM-2 was **skipped** (blocked by G-FNM-1). DCPF-critical field coverage could not be assessed via the CSV path. When using MATPOWER's native format, all DCPF-critical fields are preserved by design.

**Expressiveness impact:** The CSV import failure is a data ingestion limitation, not an expressiveness gap. MATPOWER's native psse2mpc() provides direct PSS/E RAW import for production use. The inability to handle intermediate CSV tables is relevant to workflow integration but does not affect formulation capability.

#### Power Flow Verification

G-FNM-3 (DCPF) **passed** with zero deviation against the reference solution (self-consistent, as reference was also generated by MATPOWER). The 27,862-bus network solved in 0.168s -- the fastest DCPF solve observed across all evaluated tools on this network.

G-FNM-4 (ACPF) is **informational**: Newton-Raphson failed to converge at all three relaxation levels (0%, 10%, 20%) due to singular Jacobian (rcond ~ 1.9e-17). The DCPF warm-start angles reach 537 degrees, placing the initial point far from any physical AC solution. The ACPF reference data shows non-physical voltage magnitudes (up to 379,646 pu), confirming this is a network-level convergence challenge rather than a MATPOWER-specific limitation.

**Scalability impact:** DCPF performance at FNM scale is excellent. ACPF non-convergence is attributable to network characteristics, not tool limitations.

#### Supplemental Data Representability

G-FNM-5 is **informational**: MATPOWER achieves 45% native field coverage (20 of 44 fields), ranking second among all six tools. Key differentiators: native 3-tier thermal ratings (RATE_A/B/C) and native interface support (mpc.if/mpc.iflim). Key gaps: no contingency object, no trading hub model, no outage scheduling, no generator name field.

**Extensibility impact:** MATPOWER's interface flow limit support (`mpc.if`/`mpc.iflim`) is a unique capability shared only with PowerSimulations.jl. The lack of contingency definitions is manageable via scripted BR_STATUS toggling (demonstrated in B-3). Market-layer concepts (hubs, distribution factors, outages) require external data structures, consistent with all evaluated tools.

---

## 4. Cross-Cutting Observations

### API Friction Patterns

Two high-severity API friction observations were recorded:

1. **No CSV import capability** (G-FNM-1): MATPOWER's data model is tightly coupled to its own case format. Any non-MATPOWER data source requires pre-conversion to .m/.mat format or building custom import code. This increases integration effort for operational workflows where data arrives in tabular formats.

2. **No DataFrame or structured export** (B-5): Results are bare numeric matrices with no column name metadata. Production-quality CSV export requires verbose manual formatting. This contrasts with Python tools where `DataFrame.to_csv()` is a single call.

### Documentation Gaps

The User's Manual is comprehensive for core PF/OPF operations. Documentation gaps concentrate in:
- **MOST table formats:** The xgd_table, sd_table, and profile struct formats require reading source code and examples to construct. Column name strings must match exactly but are not listed in a single reference.
- **Internal/external indexing:** ext2int() and int2ext() transformations are critical for custom constraint injection but explained only in the Developer Manual, not the User's Manual.
- **MP-Core framework:** The Developer Manual (introduced in 8.0) is less mature than the 247-page legacy User's Manual, creating confusion about which API to target.

### Solver Ecosystem

The solver ecosystem on Octave is the most significant cross-cutting limitation, affecting expressiveness, extensibility, and scalability simultaneously:

| Issue | Severity | Tests Affected |
|-------|----------|---------------|
| HiGHS unavailable (no Octave binding) | High | A-3, A-5, A-12, B-1, B-4, C-3, C-7 |
| Ipopt unavailable (no MEX interface) | Medium | A-2 (used built-in NR), C-2 |
| MIPS numerical singularity with user constraints + QP | High | A-9, B-1 |
| MIPS numerical singularity on multi-period QP | Medium | A-12 |
| GLPK exit flag mapping bug (GLP_EMIPGAP -> failure) | High | A-5, C-4 (cascaded) |
| GLPK singular basis on SMALL network | Medium | C-3 |
| GLPK cannot handle QP | Medium | A-3, A-12, B-1, C-3 |

The effective solver stack on Octave is: MIPS (QP/NLP, built-in) + GLPK (LP/MILP only, with exit flag bug for MIP gap termination). On MATLAB with commercial solvers (CPLEX, Gurobi, MOSEK), many of these limitations would not apply. This platform asymmetry means MATPOWER's theoretical capability exceeds its demonstrated capability in this evaluation.

### Architecture Quality

MATPOWER's dual-framework architecture (legacy procedural + MP-Core OOP) provides:
- **Legacy:** Lean, transparent, 25+ years of stability. The core DCPF solver (dcpf.m) is 46 lines.
- **MP-Core:** Clean 4-layer separation (data/network/mathematical/task models) with formal Extension API for custom elements and formulations.

The flat matrix data model enables low-friction contingency analysis (BR_STATUS toggling without model reconstruction) but sacrifices type safety and column-name validation -- typos in column indices produce silent wrong results.

### FNM Data Model

MATPOWER's native interface support (mpc.if/mpc.iflim) is a differentiating capability for market-layer modeling. However, market-layer concepts (trading hubs, generator distribution factors, outage schedules, contingency definitions) have no native representation and require external data structures. This is consistent across most evaluated tools -- only GridCal and PowerSimulations.jl offer limited native contingency support.

---

## 5. Items Requiring Human Spot-Check

- [ ] **A-5 (SCUC) qualified_pass** -- Validated on MOST bundled test case (ex_case3b), not on case39 due to GLPK exit flag bug. Verify that the SCUC formulation on case39 is correct by examining the solution vector in mdo.QP.x if accessible.
- [ ] **A-9 (SCOPF) fail classification** -- MIPS fails with user constraints, but MOST has a contingency framework (Approach 3 was not fully pursued). Verify whether MOST's contingency table approach would have produced a working SCOPF.
- [ ] **A-11 (distributed slack) qualified_pass** -- Post-processing approach produces identical dispatch to single-slack. Verify whether the uniform LMP shift is the expected mathematical behavior for DC OPF (it is for lossless DC, but the distinction matters for grading).
- [ ] **A-12 (multi-period storage) qualified_pass** -- Linear costs used instead of quadratic. Verify whether LP degeneracy affected the BESS arbitrage timing or LMP values.
- [ ] **B-1 (custom constraints) qualified_pass** -- MIPS fails but GLPK works for LP. Verify that the MIPS failure is a solver-specific issue and not an API misuse (incorrect variable ordering in mpc.A matrix).
- [ ] **B-5 (interoperability) qualified_pass** -- Minimal export (3 lines, no headers) vs production export (12 lines, with headers). Verify whether the "<5 lines" criterion applies to the minimal or production-quality version.
- [ ] **C-4 cascaded failure** -- Blocked by A-5 GLPK bug, not by scalability. Verify that this cascaded failure is appropriately distinguished from an independent scalability limitation in grading.
- [ ] **Scalability grade (C+)** -- Based on SMALL-tier evidence only due to cascaded gate failure. The FNM DCPF evidence (G-FNM-3, 0.168s for 28k buses) suggests strong DCPF scalability but is from Suite G, not Suite C. Verify whether FNM evidence should influence the scalability grade.
- [ ] **Maturity grade (C+)** -- Bus factor of 1 is the primary driver. The December 2024 blog post mentions plans to diversify, but as of March 2026, contributor data shows no diversification. Verify whether any non-public information about maintainer succession planning exists.

---

## 6. Methodology Notes

- **Scale cap:** MEDIUM (all gates G-1/G-2/G-3 passed). Suite C SMALL gate failed (C-4 cascaded from A-5), blocking MEDIUM scalability tests.
- **FNM status:** Suite G executed (FNM_PATH set). G-FNM-1 failed (no CSV import); G-FNM-2 skipped (blocked by G-FNM-1); G-FNM-3/4/5 used MATPOWER fallback path (.mat file).
- **Tests skipped:** 9 total -- 8 MEDIUM scalability tests (C-1/2/3/5/7/8/9/10 MEDIUM, blocked by C-SMALL-gate) + G-FNM-2 (blocked by G-FNM-1).
- **Solver versions:** MIPS 1.5.2 (built-in), GLPK (Octave built-in binding, version not separately tracked). HiGHS and Ipopt NOT available in Octave devcontainer.
- **Tool version:** MATPOWER 8.1 (released 2025-07-13), with MOST 1.3.1, MP-Opt-Model 5.0, MP-Test 8.1.
- **Protocol version:** v10 for all tests.
- **Platform:** GNU Octave 9.2.0 on Ubuntu 24.04 (devcontainer).
- **Key limitation:** The Octave solver ecosystem is narrower than the MATLAB solver ecosystem. Several tests that failed or required workarounds (A-5, A-9, A-12, B-1, C-3, C-4) would likely produce better results on MATLAB with commercial MILP/QP solvers. The evaluation reflects MATPOWER's capabilities in the open-source Octave deployment context specified by the contract.
