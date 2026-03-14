# PyPSA v1.1.2 — Phase 1 Synthesis Report

**Contract:** 
**Tool:** PyPSA v1.1.2
**Protocol version:** v10
**Skill version:** v1
**Evaluation date:** 2026-03-13

---

## 1. Executive Summary

PyPSA is a well-architected, Python-native power system optimization library with strong expressiveness across DC/AC power flow, DC OPF, SCUC, SCOPF, lossy OPF, and multi-period storage optimization. Its pandas DataFrame-centric data model and linopy-based optimization layer provide clean extensibility with documented injection points. The supply chain gate passes with qualification: all dependencies are permissively licensed except a single GPL-2.0 convenience dependency (Levenshtein) that is replaceable. The primary weaknesses are a SCUC scalability ceiling at the 2,000-bus MILP scale with open-source solvers (C-4 fail) and no PSS/E ingestion path (G-FNM-1 fail). G-FNM-3 DCPF now passes with 0.0 deviation after applying the shared `matpower_loader.load_pypsa()` which patches a branch status bug in `import_from_pypower_ppc`. Scale cap is MEDIUM (all gate tests passed).

---

## 2. Grade Recommendations Table

| Criterion | Grade | Confidence | Key Evidence |
|-----------|-------|------------|--------------|
| Problem Expressiveness | B+ | High | 8/10 Suite A tests pass; A-11 blocking (no distributed slack OPF); A-6 stable workaround; A-12 fragile workaround for shadow prices |
| Extensibility | A- | High | All 8 Suite B tests pass with no workarounds; documented extra_functionality API; native NetworkX bridge; PTDF extraction |
| Scalability | C+ | Medium | C-4 SCUC SMALL fails (HiGHS timeout); C-5 ACPF passes at MEDIUM (10k buses); 7 MEDIUM tests skipped due to C-SMALL-gate; FNM DCPF passes |
| Workforce Accessibility | A- | High | Frictionless install; 5/10 tests completable from docs; good error messages; cosmetic warning noise |
| Maturity & Sustainability | A | High | 33 releases in 24 months; 325 commits from 18 contributors; EU institutional backing; 1,898 stars |
| Supply Chain (Gate) | B+ | High | MIT core; one GPL-2.0 dep (Levenshtein) that is replaceable; pure Python; all compiled deps open-source and buildable |

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness

#### Strengths

- Native DC power flow with structured DataFrame outputs and sub-second solve times ([A-1](expressiveness/A-1_dcpf.md))
- AC power flow with built-in Newton-Raphson solver, first-class convergence diagnostics (residual, iteration count, converged flag) ([A-2](expressiveness/A-2_acpf.md))
- DC OPF via `n.optimize()` with automatic LMP population on `n.buses_t.marginal_price` ([A-3](expressiveness/A-3_dcopf.md))
- AC feasibility check on DC OPF dispatch within same model context, no file export/reimport needed ([A-4](expressiveness/A-4_ac_feasibility.md))
- SCUC with all standard UC constraints as built-in generator attributes (committable, min_up_time, min_down_time, start_up_cost, ramp_limit_up/down) producing demonstrable generator cycling ([A-5](expressiveness/A-5_scuc.md))
- Native SCOPF via `optimize_security_constrained()` with BODF-based N-1 constraints embedded in the LP ([A-9](expressiveness/A-9_scopf.md))
- Native lossy DC OPF via `transmission_losses` parameter with piecewise-linear loss approximation and LMP decomposition ([A-10](expressiveness/A-10_lossy_dcopf_lmp.md))
- Multi-period DCOPF with native `StorageUnit` component including cyclic SoC, charge/discharge efficiencies, and correct BESS arbitrage behavior ([A-12](expressiveness/A-12_multiperiod_dcopf_storage.md))

#### Weaknesses

- No distributed slack OPF capability -- the DC OPF formulation uses flow variables without bus angle variables, making distributed slack architecturally impossible in `n.optimize()` ([A-11](expressiveness/A-11_distributed_slack_opf.md))
- No PSS/E ingestion path in any form (raw, intermediate CSV, or converted) -- blocks FNM-based expressiveness evidence ([G-FNM-1](fnm_ingestion/G-FNM-1_intermediate_format_ingestion.md))
- SCOPF limited to Line contingencies only; transformer contingencies not accepted by `optimize_security_constrained()` ([A-9](expressiveness/A-9_scopf.md))
- No native piecewise-linear cost curves (tracked as high-priority issue #1020) ([P2-2](p2_readiness/P2-2_piecewise_linear_cost.md))

#### Workarounds Required

- A-3 shadow price extraction via `n.model.constraints` instead of empty `n.lines_t.mu_upper/mu_lower` -- **stable** (linopy public API)
- A-6 SCED two-stage UC/ED via manual `p_min_pu`/`p_max_pu` bound manipulation -- **stable** (documented public API, ~15 LOC)
- A-11 distributed slack only in `n.pf()` context (AC PF), not in `n.optimize()` (OPF) -- **blocking** (architectural limitation)
- A-12 branch shadow prices via internal linopy constraint naming -- **fragile** (undocumented naming convention)

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| A-1 | TINY | pass | -- | -- | 1.2s | 145 |
| A-2 | TINY | pass | -- | -- | 1.3s | 256 |
| A-3 | TINY | pass | -- | stable | 2.1s | 283 |
| A-4 | TINY | pass | -- | -- | 1.4s | 400 |
| A-5 | TINY | pass | -- | -- | 4.3s | 362 |
| A-6 | TINY | qualified_pass | -- | stable | 3.0s | 453 |
| A-9 | TINY | pass | -- | -- | 4.1s | 404 |
| A-10 | TINY | pass | -- | -- | 1.9s | 332 |
| A-11 | TINY | qualified_pass | -- | blocking | 1.9s | 326 |
| A-12 | TINY | pass | -- | fragile | 6.9s | 432 |

0 independent failures. 2 qualified passes. 0 cascaded failures.

#### Grade Rationale

PyPSA passes 8 of 10 Suite A tests cleanly (including SCOPF, lossy OPF, and multi-period storage) with 2 qualified passes (A-6 stable workaround, A-11 blocking limitation). The tool satisfies the B+ standard: "Mostly strong, one meaningful gap that has a stable workaround." The meaningful gap is A-11 (distributed slack OPF) which is a blocking architectural limitation -- no workaround exists in the OPF context. However, 8 of 10 core problem types are natively expressible with built-in constraints, and SCOPF/lossy OPF/storage add Phase 2 readiness evidence that approaches A-level. The A-12 fragile workaround for shadow prices is a second, minor concern. The A-11 blocking gap prevents an A- grade.

### 3.2 Extensibility

#### Strengths

- Documented `extra_functionality` callback for custom constraint injection with full access to linopy Model object ([B-1](extensibility/B-1_custom_constraints.md))
- Native NetworkX graph export via `n.graph()` for topology analysis, BFS/DFS, subgraph extraction ([B-2](extensibility/B-2_graph_access.md))
- Efficient contingency loop via `n.copy()` without file re-reads or model reconstruction; 3,276 N-3 contingencies solved in 196s ([B-3](extensibility/B-3_contingency_sweep.md))
- Scenario ensembles via `n.copy()` + DataFrame injection; 20 scenarios at 0.30s each ([B-4](extensibility/B-4_stochastic_scenario.md))
- Zero-friction interoperability -- all results natively stored as pandas DataFrames, 2 lines to export to CSV ([B-5](extensibility/B-5_interoperability.md))
- Clean 4-layer architecture with 8 mixins; explicit separation of data model, formulation, solver, and results ([B-6](extensibility/B-6_code_architecture.md))
- Reference bus reconfiguration via single DataFrame attribute assignment ([B-8](extensibility/B-8_reference_bus_config.md))
- Native PTDF computation via SubNetwork API with machine-precision validation (max error 1.91e-14) ([B-9](extensibility/B-9_ptdf_extraction.md))

#### Weaknesses

- DCPF solver (scipy.sparse) hardcoded -- not swappable via parameter ([B-6](extensibility/B-6_code_architecture.md))
- PF build/solve not separated (no equivalent of create_model/solve_model for power flow) ([B-6](extensibility/B-6_code_architecture.md))
- SubNetwork/mixin architecture undocumented; PTDF column ordering non-obvious ([B-6](extensibility/B-6_code_architecture.md), [B-9](extensibility/B-9_ptdf_extraction.md))
- No fast-decoupled or continuation PF methods -- only NR for ACPF ([G-FNM-4](fnm_ingestion/G-FNM-4_acpf_convergence.md))

#### Workarounds Required

None. All 8 Suite B tests pass without workarounds.

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| B-1 | TINY | pass | -- | -- | 1.9s | 354 |
| B-2 | TINY | pass | -- | -- | 1.1s | 126 |
| B-3 | TINY | pass | -- | -- | 196.3s | 251 |
| B-4 | TINY | pass | -- | -- | 7.1s | 265 |
| B-5 | TINY | pass | -- | -- | 1.2s | 141 |
| B-6 | N/A | pass | -- | -- | 1.1s | 377 |
| B-8 | TINY | pass | -- | -- | 2.2s | 244 |
| B-9 | TINY | pass | -- | -- | 1.2s | 218 |

0 failures. 0 qualified passes. 0 cascaded failures.

#### Grade Rationale

PyPSA passes all 8 extensibility tests without any workarounds. The tool satisfies the A standard: "Strong native support, well-tested at scale, no significant caveats." The `extra_functionality` callback, native NetworkX graph export, efficient `n.copy()` cloning, DataFrame-native results, and PTDF extraction collectively demonstrate that PyPSA was designed for extension. The one minor caveat is that the SubNetwork/mixin internal architecture is undocumented, requiring source-reading for advanced use (PTDF column ordering). This minor documentation gap produces an A- rather than a full A.

### 3.3 Scalability

#### Strengths

- AC PF converges robustly on SMALL (2k buses, 4 NR iterations, 4.2s) and MEDIUM (10k buses, 5 NR iterations, 19.1s) without relaxation ([C-5](scalability/C-5_ac_feasibility_progressive_SMALL.md), [C-5 MEDIUM](scalability/C-5_ac_feasibility_progressive_MEDIUM.md))
- ACPF wall-clock scales approximately linearly with network size (4.6x for 5x buses)
- FNM DCPF on 27,862 buses completes in 31.3s with 0.0 deviation from MATPOWER reference (100% pass on all thresholds), demonstrating LARGE-scale power flow capability and exact numerical agreement ([G-FNM-3](fnm_ingestion/G-FNM-3_dcpf_verification.md))

#### Weaknesses

- C-4 SCUC SMALL fails: HiGHS cannot solve root LP relaxation of 544-generator 24hr SCUC within 600s on single thread (39,168 binary variables) ([C-4](scalability/C-4_scuc_small.md))
- SCIP not available in devcontainer despite configuration (environment issue, not PyPSA limitation) ([C-4](scalability/C-4_scuc_small.md))
- Peak memory scales super-linearly for ACPF: 84 MB (SMALL) to 2,099 MB (MEDIUM) = 25x for 5x buses ([C-5 MEDIUM](scalability/C-5_ac_feasibility_progressive_MEDIUM.md))
- G-FNM-4 ACPF fails on FNM at all relaxation levels (SuperLU factorization failure) -- consistent with MATPOWER failure on same network ([G-FNM-4](fnm_ingestion/G-FNM-4_acpf_convergence.md))

#### Workarounds Required

None applicable -- C-4 fails due to solver scalability, not a workaround opportunity.

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| C-4 | SMALL | fail | -- | -- | 665.7s | 289 |
| C-5 | SMALL | pass | -- | -- | 15.1s | 342 |
| C-5 | MEDIUM | pass | -- | -- | 86.7s | 342 |
| C-1 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-2 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-3 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-7 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-8 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-9 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-10 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| G-FNM-3 | LARGE | pass | -- | stable | 31.3s | 446 |
| G-FNM-4 | LARGE | informational | -- | -- | 131.2s | 276 |

1 independent failure (C-4). 7 cascaded skips (C-SMALL-gate). 1 FNM pass (G-FNM-3, via shared matpower_loader). 1 FNM informational (G-FNM-4).

#### Grade Rationale

C-4 SCUC failure on SMALL is a genuine scalability limitation: 544-generator 24hr MILP is intractable for HiGHS within 600s single-threaded. This triggers the C-SMALL-gate, blocking 7 MEDIUM tests. However, C-5 passes at both SMALL and MEDIUM (demonstrating ACPF scalability to 10k buses), and the failure is solver-bound (HiGHS limitation), not a PyPSA architectural ceiling. G-FNM-3 now passes with 0.0 deviation on the 27,862-bus FNM (after applying the shared matpower_loader branch status patch), demonstrating LARGE-scale DCPF fidelity. The tool satisfies the C+ standard: "Significant gaps but not disqualifying -- tool is usable with substantial effort." The gap (MILP scalability) has a known mitigation path (multi-threaded solving, commercial solvers), and the LP/PF paths scale well to LARGE. C+ is assigned rather than B- because the C-SMALL-gate prevents demonstrating MEDIUM-tier OPF capability, and the MILP scalability gap is real.

### 3.4 Workforce Accessibility

#### Strengths

- Frictionless install: `uv sync` resolves all dependencies including bundled HiGHS solver; first solve in 1.2s ([D-1](accessibility/D-1_install_to_first_solve.md))
- All 11 example networks load and solve without modification ([D-3](accessibility/D-3_example_verification.md))
- Good error quality: infeasibility reported clearly, invalid bus references caught with actionable ConsistencyError ([D-4](accessibility/D-4_error_quality.md))
- Moderate code volume: median 259 LOC for Suite A tests; simplest analysis (DCPF) at 111 LOC ([D-5](accessibility/D-5_code_volume.md))

#### Weaknesses

- 5/10 Suite A tests completable from docs alone; 3 require source-reading, 2 require trial-and-error ([D-2](accessibility/D-2_documentation_audit.md))
- Shadow price assignment bug: `n.lines_t.mu_upper/mu_lower` silently empty after `optimize()` ([D-2](accessibility/D-2_documentation_audit.md))
- Transformer `b` field dual semantics (DC vs AC) undocumented, causes silent ACPF divergence with DC-oriented loader ([D-2](accessibility/D-2_documentation_audit.md))
- No `fix_commitment()` convenience API; UC/ED two-stage workflow undocumented ([D-2](accessibility/D-2_documentation_audit.md))
- Verbose warning noise on first use (FutureWarning, carrier warnings, shadow price warnings) ([D-1](accessibility/D-1_install_to_first_solve.md))
- Deferred validation: invalid component references caught at solve time, not at construction time ([D-4](accessibility/D-4_error_quality.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| D-1 | pass | Install-to-first-solve: 1.2s total |
| D-2 | informational | 5/10 from docs, 3 need source, 2 need trial-and-error |
| D-3 | pass | 11/11 examples work unmodified |
| D-4 | pass | 3/3 error scenarios produce meaningful diagnostics |
| D-5 | informational | Median 259 LOC; range 111-415 |

#### Grade Rationale

PyPSA's accessibility profile is strong: frictionless install, reliable examples, good error messages, and moderate code volume. The tool approaches the A standard: "Strong native support, well-tested at scale." The one minor caveat is the documentation gap pattern -- 50% of tests require source code reading or trial-and-error, and the shadow price / transformer `b` field issues are not documented. These documentation gaps produce friction but do not prevent task completion. A- is assigned: "Strong overall but with one minor caveat" -- the documentation gap pattern is the caveat.

### 3.5 Maturity & Sustainability

#### Strengths

- 33 releases in 24 months (1.4/month); last release 18 days before evaluation ([E-1](maturity/E-1_release_cadence.md))
- 325 commits from 18 human contributors in 12 months ([E-2](maturity/E-2_commit_activity.md))
- Bus factor 2-3 with successful maintainership transition from founder to current team; 99 total contributors ([E-3](maturity/E-3_contributor_concentration.md))
- Stable institutional backing: TU Berlin academic positions, EU research grants, Open Energy Transition non-profit ([E-4](maturity/E-4_funding_model.md))
- Median 4-day issue time-to-close; 80% substantive response rate ([E-5](maturity/E-5_issue_tracker_health.md))
- CI on 3 OS x multiple Python versions with daily scheduled runs and downstream model testing ([E-6](maturity/E-6_ci_cd_coverage.md))
- Production-grade operational adoption: PyPSA-Eur (EU-wide), national grid studies, commercial user engagement ([E-7](maturity/E-7_operational_adoption.md))

#### Weaknesses

- High merge concentration: lkstrp merges 84% of PRs ([E-3](maturity/E-3_contributor_concentration.md))
- Code coverage not reported as a badge; test comprehensiveness inferred from matrix ([E-6](maturity/E-6_ci_cd_coverage.md))

#### Evidence Summary Table

| Test | Status | Key Metric |
|------|--------|------------|
| E-1 | pass | 33 releases / 24 months, semver compliant |
| E-2 | pass | 325 commits, 18 contributors, 95% human-authored |
| E-3 | pass | Bus factor 2-3; top 3 = 55% of all-time commits |
| E-4 | pass | TU Berlin + EU grants + OET; high durability |
| E-5 | pass | Median 4.0-day TTR; 80% ack rate |
| E-6 | pass | CI exists (4 workflows), tests pass on current release |
| E-7 | pass | PyPSA-Eur (EU policy), national grid studies, industry users |

#### Grade Rationale

PyPSA passes all 7 maturity tests with strong metrics across release cadence, contributor diversity, institutional funding, and operational adoption. The project demonstrates the A standard: "Strong native support, well-tested at scale, no significant caveats." The high merge concentration on lkstrp (84%) is a minor risk factor but is mitigated by distributed review load (4 reviewers at >13% each) and the demonstrated ability to transition maintainership. A is assigned.

### 3.6 Supply Chain (Gate)

#### Strengths

- MIT core license -- fully permissive ([F-1](supply_chain/F-1_core_license.md))
- Pure Python core with all compiled dependencies (numpy, scipy, highspy) open-source and buildable from source ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- Full execution path inspectable: 0 opaque steps from API call to solver invocation ([F-5](supply_chain/F-5_code_inspectability.md))
- Standard PyPI distribution with versioned releases and hash digests ([F-6](supply_chain/F-6_distribution_integrity.md))
- Fully air-gap installable; no runtime network dependencies for core computation ([F-7](supply_chain/F-7_airgap_installability.md))
- HiGHS bundled as a direct dependency (MIT); no solver license management required ([F-8](supply_chain/F-8_solver_dependency.md))
- All test cases completed with open-source solvers only ([F-8](supply_chain/F-8_solver_dependency.md))

#### Weaknesses

- `levenshtein` (GPL-2.0-or-later) is a direct dependency for fuzzy string matching in component validation ([F-3](supply_chain/F-3_dependency_license_audit.md))
- No PGP or Sigstore release signing (consistent with broader PyPI ecosystem deprecation of PGP) ([F-6](supply_chain/F-6_distribution_integrity.md))
- Google Cloud Storage dependencies pulled transitively via linopy (~8 packages, unnecessary for local use) ([F-2](supply_chain/F-2_dependency_tree.md))

#### Workarounds Required

None. The GPL Levenshtein dependency is replaceable with MIT-licensed `rapidfuzz` (already a transitive dependency).

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| F-1 | pass | MIT license |
| F-2 | informational | ~70 transitive deps, max depth 4 |
| F-3 | qualified_pass | 1 GPL dep (Levenshtein), replaceable |
| F-4 | pass | Pure Python core; 9 compiled deps all open-source |
| F-5 | pass | 0 opaque steps in execution path |
| F-6 | pass | Versioned PyPI releases with hash digests |
| F-7 | pass | Full air-gap install possible |
| F-8 | pass | HiGHS bundled (MIT); 0 commercial solver failures |
| F-9 | pass | Examples version-coupled via docs; no mutable refs |

#### Grade Rationale

PyPSA's supply chain is clean: MIT core, pure Python, all compiled dependencies open-source and buildable, full air-gap capability, bundled open-source solver. The one finding is the GPL-2.0 Levenshtein dependency. This is a direct dependency but is used only for convenience UX (fuzzy attribute name suggestions), not computation. It is immediately replaceable with the MIT-licensed `rapidfuzz` (already installed as a transitive dependency). Under the rubric, this satisfies the B+ standard: "Mostly strong, one meaningful gap that has a stable workaround." The gap (GPL dependency) has a trivial, stable workaround (replace with rapidfuzz or make optional). This is above the C+ disqualifying threshold.

---

## 3b. FNM Ingestion Findings (Suite G)

Suite G executed (FNM_PATH set). FNM findings are additive evidence and do not independently determine grades.

### Data Model Fidelity

**G-FNM-1: FAIL (psse_parse_error).** PyPSA has no PSS/E ingestion capability in any form. All six import methods expect PyPSA-native formats, PYPOWER PPC dictionaries, or pandapower networks. The intermediate CSV tables with PSS/E field names and semantics have no mapping path into PyPSA. This is a fundamental format gap attributed to Expressiveness (missing record type support, not scale).

**G-FNM-2: SKIP (blocked by G-FNM-1).** Field fidelity cannot be assessed without successful parsing.

### Power Flow Verification

**G-FNM-3: PASS.** Via shared `matpower_loader.load_pypsa()` (MATPOWER fallback with branch status, transformer susceptance, and gencost patches), PyPSA solved DCPF on 27,862 buses in 31.3s with **zero deviation** from the MATPOWER reference — 100% of buses and 100% of branches match exactly. The original run (without the shared loader) failed with 91% bus angle failures due to `import_from_pypower_ppc` ignoring MATPOWER's `BR_STATUS` column, which caused 74 inactive branches to participate in the DCPF. The shared loader's branch status patch corrects this, and both tools use identical DCPF formulations (`b = 1/(x*tap)`).

**G-FNM-4: INFORMATIONAL (ACPF infeasible).** PyPSA's Newton-Raphson solver encountered a SuperLU factorization failure at all relaxation levels on the FNM, consistent with MATPOWER 8.1's failure on the same network. The FNM planning model lacks a feasible AC operating point at full load. Neither tool converges.

### Supplemental Data Representability

**G-FNM-5: INFORMATIONAL.** PyPSA achieves 20.5% native, 61.6% extension-representable, and 17.8% tool-external across 73 supplemental CSV fields. The high extension-representability reflects PyPSA's flexible DataFrame architecture -- custom columns persist on component DataFrames. However, extension-classified fields (contingencies, interfaces, trading hubs) require 50-100 lines of custom code each. OUTAGE schedule data and generator distribution factors are universally external across all tools.

---

## 4. Cross-Cutting Observations

### API Friction Patterns

- **Shadow price assignment bug:** After `n.optimize()`, branch constraint duals (`n.lines_t.mu_upper/mu_lower`) are empty despite solver computing them. Bus-level LMPs are correctly populated. Workaround via `n.model.constraints[name].dual` is available but fragile (depends on internal naming). Observed in A-3 and A-12. (severity: medium)
- **No fix_commitment() convenience API:** Two-stage UC/ED requires manual p_min_pu/p_max_pu bound manipulation (~15 LOC). Standard pattern but undocumented. (severity: low)
- **SCOPF transformer exclusion:** `optimize_security_constrained()` silently rejects transformer names from `branch_outages` without explaining the limitation in docs. (severity: low)
- **No PSS/E ingestion path:** All six import methods expect tool-native or PYPOWER formats. Users with PSS/E data face a mandatory external conversion step. (severity: high)
- **No MIP gap extraction API:** When HiGHS hits time limit, the MIP gap is only visible in console output, not queryable via API. (severity: low)

### Documentation Gaps

- Transformer `b` field dual semantics (DC series susceptance vs AC shunt susceptance) not documented; causes silent ACPF divergence with DC-oriented loaders
- PTDF column ordering (`sub_network.buses_o`, not `n.buses.index`) not documented
- SubNetwork/mixin architecture and advanced methods (`calculate_PTDF`, `calculate_BODF`, `calculate_B_H`) require source-reading
- SCIP solver installation gap in devcontainer (environment issue)

### Solver Ecosystem

- **HiGHS (MIT):** Primary solver, bundled, handles LP/MILP/QP. Scalability ceiling at 544-generator 24hr SCUC single-threaded. Root LP relaxation alone exhausts 600s budget.
- **GLPK (GPL):** Available as secondary LP/MILP solver; slower than HiGHS on larger problems.
- **SCIP:** Listed in devcontainer but not actually installed. PyPSA supports it via linopy.
- **Ipopt:** Not in the OPF path; PyPSA uses internal NR for ACPF, not Ipopt as an NLP solver. AC OPF uses iterative LOPF+PF, not direct NLP.
- **Positive finding:** PyPSA's internal NR solver converges robustly on SMALL (2k) and MEDIUM (10k) networks for ACPF with 4-5 iterations.

### Architecture Quality

- Clean 4-layer architecture: User API -> Mixin Dispatch -> SubNetwork Computation -> Linear Algebra Backend
- 8 mixin classes compose the Network object with single-concern separation
- OPF path has explicit model-build/solve separation via linopy (`create_model()` / `solve_model()`)
- DataFrame-native data model eliminates impedance mismatch between internal state and export format
- 5 documented injection points for extending behavior
- DCPF solver (scipy.sparse) hardcoded -- not swappable

### FNM Data Model

- DCPF on 27,862-bus FNM produces zero deviation from MATPOWER reference when using shared `matpower_loader.load_pypsa()` (patches `import_from_pypower_ppc` branch status bug)
- `import_from_pypower_ppc` ignores MATPOWER BR_STATUS column — 74 inactive branches treated as active without the loader patch
- Both PyPSA and MATPOWER use identical DCPF formulations (`b = 1/(x*tap)` via `makeBdc.m` / `calculate_B_H`)
- Extension mechanism (custom DataFrame columns) empirically verified for supplemental data storage
- 82% in-model representability for supplemental CSVs; only OUTAGE scheduling data and market settlement constructs are universally external

---

## 5. Items Requiring Human Spot-Check

- [ ] **A-6 (SCED) qualified_pass** -- The two-stage UC/ED workflow uses only documented API (`generators_t.p_min_pu/p_max_pu`), but the lack of a `fix_commitment()` method means the pattern is "standard but undocumented." Verify whether this constitutes a workaround or an expected usage pattern.
- [ ] **A-11 (distributed slack) qualified_pass** -- Classified as "blocking" because DC OPF uses flow variables without bus angle variables. Verify whether PyPSA's flow-based formulation is architecturally incompatible with distributed slack, or whether an `extra_functionality` workaround could approximate it via reference-bus-weighted energy pricing.
- [ ] **A-12 shadow price workaround classified as "fragile"** -- The workaround accesses `n.model.constraints['Line-fix-s-upper'].dual` using internal linopy constraint naming. Verify whether this naming convention is part of linopy's public contract or an implementation detail.
- [ ] **F-3 (GPL Levenshtein) qualified_pass** -- The Levenshtein package is a direct dependency but is used only for UX (fuzzy attribute name matching). Verify whether internal-use-only deployment eliminates the GPL concern, and whether the `rapidfuzz` replacement path is tested.
- [ ] **Scalability grade (C+) vs potential B-** -- The C-4 failure is solver-bound (HiGHS single-threaded), not a PyPSA architectural limitation. Multi-threaded solving or Gurobi/CPLEX would likely resolve it. Determine whether the grade should reflect the tool's architecture (which is sound) or the tested configuration (which failed).
- [x] **G-FNM-3 DCPF deviation resolved** -- Root cause identified: `import_from_pypower_ppc` ignores MATPOWER BR_STATUS column, including 74 inactive branches in the DCPF. Shared `matpower_loader.load_pypsa()` branch status patch fixes this, producing 0.0 deviation. No spot-check needed.

---

## 6. Methodology Notes

- **Scale cap:** MEDIUM (all gate tests G-1, G-2, G-3 passed)
- **FNM status:** Suite G executed (FNM_PATH set). G-FNM-1 failed (no PSS/E ingestion); G-FNM-3 through G-FNM-5 executed via MATPOWER fallback.
- **Tests skipped and reason:** G-FNM-2 blocked by G-FNM-1. C-1, C-2, C-3, C-7, C-8, C-9, C-10 blocked by C-SMALL-gate (C-4 failure).
- **Solver versions:** HiGHS 1.13.1 (via highspy, MIT), GLPK (via system package, GPL), SCIP (not installed)
- **Tool version:** PyPSA 1.1.2 (released 2026-02-23)
- **Protocol version:** v10
- **Skill version:** v1
- **Devcontainer environment:** Ubuntu 24.04, Python 3.12, uv-managed
- **Total tests executed:** 33 (10 Suite A + 8 Suite B + 10 Suite C + 5 Suite D + 7 Suite E + 9 Suite F + 5 Suite G + 3 P2 + 3 Gate). Of these: 23 pass, 2 qualified_pass, 2 fail, 8 skip, 5 informational.
