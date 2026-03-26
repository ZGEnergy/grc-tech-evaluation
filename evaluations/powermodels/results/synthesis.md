# PowerModels.jl v0.21.5 — Synthesis Report

**Contract:** 
**Protocol:** v11 | **Skill:** v2 | **Scale cap:** MEDIUM | **FNM_AVAILABLE:** true
**Date:** 2026-03-24

---

## 1. Executive Summary

PowerModels.jl is a research-grade steady-state power network optimization library built on the JuMP mathematical programming framework. It provides a clean, extensible four-layer architecture with strong separation between data model, problem formulation, and solver interface. Gate tests pass at all three scales (TINY/SMALL/MEDIUM). The supply chain is clean for commercial use when optional GPL/ZIB-licensed solvers (GLPK, SCIP v8.0) are excluded. The tool's primary strengths are its native DC OPF with LMP extraction, first-class PTDF computation, and the two-level API enabling custom constraint injection. Its primary weaknesses are the absence of native SCUC and distributed slack formulations, ACPF convergence failure at MEDIUM scale (10k buses), and extreme contributor concentration (bus factor = 1). Scale cap MEDIUM applies; DC OPF scales to 10k buses in 4s (HiGHS) but ACPF does not converge beyond ~2,000 buses.

---

## 2. Test Results Summary

**Note:** Gate tests (G-1, G-2, G-3) are excluded from pass rate statistics per protocol.

| Criterion | Tests | Passed | Failed | Qualified Pass | Constrained Pass | Skip | Informational | Confidence | Key Evidence |
|-----------|-------|--------|--------|----------------|------------------|------|---------------|------------|--------------|
| Problem Expressiveness (A) | 11 | 3 | 3 | 5 | 0 | 0 | 0 | High | Native DCOPF+LMP; no SCUC or distributed slack |
| Extensibility (B) | 8 | 5 | 0 | 3 | 0 | 0 | 0 | High | Two-level API clean constraint injection in 4 LOC |
| Scalability (C) | 10 | 2 | 3 | 3 | 1 | 0 | 2 | High | DCPF 10k in 0.23s; ACPF fails at 10k |
| Workforce Accessibility (D) | 5 | 0 | 0 | 4 | 0 | 0 | 1 | Medium | 8/10 examples work; JIT cold-start tax |
| Maturity & Sustainability (E) | 7 | 3 | 1 | 3 | 0 | 0 | 0 | High | 94% CI coverage; bus factor=1 |
| Supply Chain (Gate) (F) | 9 | 7 | 0 | 2 | 0 | 0 | 0 | High | BSD-3 core; GLPK GPL, SCIP ZIB flagged |
| FNM Ingestion (G-FNM) | 5 | 0 | 2 | 0 | 0 | 1 | 2 | High | No CSV ingestion; DCPPowerModel ignores taps |
| P2 Readiness (P2) | 3 | 0 | 0 | 0 | 0 | 0 | 3 | Medium | PWL native; commitment injection via gen_status |

**Overall (excluding gate G-1/2/3):** 56 scored/informational tests. 20 pass, 9 fail (5 independent + 4 blocked), 18 qualified_pass, 1 constrained_pass, 1 skip, 7 informational.

**Independent failures:** A-5 (SCUC unsupported), A-11 (distributed slack unsupported), C-2 (ACPF MEDIUM diverges), E-3 (bus factor=1), G-FNM-1 (no CSV ingestion).

**Blocked failures:** C-4 (by A-5), C-10 (by A-11), G-FNM-3 (independent -- DCPPowerModel formulation choice).

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness (Suite A)

#### Strengths

- Native DC OPF with LMP extraction via `lam_kcl_r` dual variable, clean one-call API ([A-3](expressiveness/A-3_dcopf_TINY.md))
- DC loss approximation via `DCPLLPowerModel` with three-component LMP decomposition (energy/congestion/loss) ([A-10](expressiveness/A-10_lossy_dcopf_lmp_decomposition_TINY.md))
- Multi-period OPF with storage via `replicate()` + `solve_mn_opf_strg`, including binary charge/discharge complementarity ([A-12](expressiveness/A-12_multiperiod_dcopf_storage_TINY.md))
- SCOPF mechanism demonstrated via PTDF/LODF + two-level API constraint injection ([A-9](expressiveness/A-9_scopf_TINY.md))
- SCED (ED-only mode) implemented via `replicate()` + ramp constraints on multi-period DCPPowerModel ([A-6](expressiveness/A-6_sced_TINY.md))

#### Weaknesses

- No native SCUC -- UC binary variables, min up/down times, startup costs entirely absent [tool-specific] ([A-5](expressiveness/A-5_scuc_TINY.md))
- No distributed slack formulation -- all 18 built-in formulations use single reference bus [tool-specific] ([A-11](expressiveness/A-11_distributed_slack_opf_TINY.md))
- `compute_ac_pf` does not expose NR iteration count or convergence residual -- only Bool `termination_status` [tool-specific] ([A-2](expressiveness/A-2_acpf_TINY.md))
- `compute_dc_pf` and `compute_ac_pf` do not populate branch flows in result dict [tool-specific] ([A-1](expressiveness/A-1_dcpf_TINY.md), [A-2](expressiveness/A-2_acpf_TINY.md))

#### Workarounds Required

- Branch flow post-processing via `calc_branch_flow_ac` / manual DC formula (~10 LOC) -- **stable** ([A-1](expressiveness/A-1_dcpf_TINY.md), [A-2](expressiveness/A-2_acpf_TINY.md))
- Cyclic SoC constraint via manual JuMP injection `se[T] == energy_initial` -- **stable** ([A-12](expressiveness/A-12_multiperiod_dcopf_storage_TINY.md))
- SCIP required for storage OPF (HiGHS/Ipopt reject MIQP ZeroOne constraints) -- **stable** ([A-12](expressiveness/A-12_multiperiod_dcopf_storage_TINY.md))
- DCPLLPowerModel requires Ipopt (HiGHS rejects quadratic constraints) -- **stable** ([A-10](expressiveness/A-10_lossy_dcopf_lmp_decomposition_TINY.md))
- SCOPF requires manual LODF computation + iterative Benders cutting plane -- **stable** ([A-9](expressiveness/A-9_scopf_TINY.md))
- Distributed slack requires ~150 LOC custom PTDF-based JuMP OPF -- **blocking** ([A-11](expressiveness/A-11_distributed_slack_opf_TINY.md))

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| A-1 | TINY | qualified_pass | -- | stable (branch flows) | 0.003s | 250 |
| A-2 | TINY | qualified_pass | -- | stable (branch flows, diagnostics) | 0.006s | 395 |
| A-3 | TINY | pass | -- | -- | 0.007s | 375 |
| A-4 | TINY | pass | -- | stable (branch flows) | 2.362s | 155 |
| A-5 | TINY | fail | -- | -- (unsupported) | -- | -- |
| A-6 | TINY | qualified_pass | A-5 | stable (ed_only, ramp injection) | 2.00s | 310 |
| A-9 | TINY | qualified_pass | -- | stable (manual SCOPF) | 3.821s | 420 |
| A-10 | TINY | qualified_pass | -- | stable (Ipopt for DCPLL) | 3.29s | 260 |
| A-11 | TINY | fail | -- | blocking (no distributed slack) | 2.30s | 160 |
| A-12 | TINY | pass | -- | stable (SCIP, cyclic SoC, 2-phase LMP) | 5.85s | 310 |

**A-6 SCED mode: ed_only** (UC stage bypassed, all generators assumed committed, due to A-5 failure).

**Independent fails: 2** (A-5 SCUC, A-11 distributed slack). **Blocked: 0** in expressiveness (A-6 has `blocked_by: A-5` but still achieved qualified_pass as ed_only).

#### Findings Summary

PowerModels provides strong native coverage for steady-state OPF problems including DC, AC, and lossy DC formulations with LMP extraction. The two-level API enables SCOPF and multi-period storage OPF through documented extension mechanisms. Two blocking gaps exist: no native SCUC (unit commitment is entirely outside scope) and no distributed slack formulation. These are fundamental scope boundaries of a steady-state OPF library, not fixable via workarounds. The `compute_*` functions (non-JuMP path) consistently lack branch flow population and convergence diagnostics, requiring stable but repetitive workarounds.

---

### 3.2 Extensibility (Suite B)

#### Strengths

- Two-level API provides clean custom constraint injection in 4 LOC with dual extraction ([B-1](extensibility/B-1_custom_constraints_TINY.md))
- Four-layer dispatch architecture (public API / model lifecycle / formulation build / solver) with clean separation of concerns ([B-6](extensibility/B-6_code_architecture.md))
- First-class PTDF API: `calc_basic_ptdf_matrix` returns dense matrix with machine-epsilon accuracy ([B-9](extensibility/B-9_ptdf_extraction_TINY.md))
- N-M contingency sweep via `deepcopy` + `br_status=0` pattern at 1.25ms/case ([B-3](extensibility/B-3_contingency_sweep_TINY.md))
- Stochastic wrapping via `deepcopy` + dict mutation at 4ms/scenario ([B-4](extensibility/B-4_stochastic_wrapping_TINY.md))
- Interoperability: 3 LOC per component type to export to DataFrame/CSV ([B-5](extensibility/B-5_interoperability_TINY.md))

#### Weaknesses

- No Graphs.jl integration -- adjacency must be built manually from `data["branch"]` (~12 LOC) [tool-specific] ([B-2](extensibility/B-2_graph_access_TINY.md))
- No native distributed slack in reference bus configuration -- requires ~150 LOC custom JuMP OPF [tool-specific] ([B-8](extensibility/B-8_reference_bus_config_TINY.md))
- Formulation-specific methods in `form/*.jl` lack docstrings [tool-specific] ([B-6](extensibility/B-6_code_architecture.md))

#### Workarounds Required

- Graph adjacency construction from `data["branch"]` (~12 LOC) -- **stable** ([B-2](extensibility/B-2_graph_access_TINY.md))
- Single-slack reference bus change via 2-line dict mutation -- **stable** ([B-8](extensibility/B-8_reference_bus_config_TINY.md))
- Distributed slack via ~150 LOC PTDF-based JuMP OPF -- **stable** (but high effort) ([B-8](extensibility/B-8_reference_bus_config_TINY.md))

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| B-1 | TINY | pass | -- | -- | 1.119s | 4 |
| B-2 | TINY | qualified_pass | -- | stable (manual adjacency) | 0.495s | 12 |
| B-3 | TINY | pass | -- | -- | 1.176s | 348 |
| B-4 | TINY | pass | -- | -- | 2.491s | 296 |
| B-5 | TINY | pass | -- | stable (DataFrames.jl add) | 1.427s | 3 |
| B-6 | N/A | pass | -- | -- | -- | -- |
| B-8 | TINY | qualified_pass | -- | stable (distributed slack ~150 LOC) | 4.034s | 354 |
| B-9 | TINY | pass | -- | -- | 2.389s | 213 |

**Independent fails: 0. Blocked: 0.**

#### Findings Summary

Extensibility is a clear strength. The four-layer architecture with Julia multiple dispatch provides a clean extension mechanism. The two-level API (`instantiate_model` + `@constraint` + `optimize_model!`) is well-documented and enables ad-hoc constraint injection without source patching. PTDF computation is first-class. The primary gap is the absence of distributed slack, which requires bypassing PowerModels' problem specification entirely (~150 LOC custom JuMP). Documentation gaps in formulation-specific methods are minor but affect developers extending the codebase.

---

### 3.3 Scalability (Suite C)

#### Strengths

- DCPF on 10k buses in 0.23s (linear algebra solve) + 0.04s branch flow post-processing ([C-1](scalability/C-1_dcpf_scale_MEDIUM.md))
- DC OPF on 10k buses OPTIMAL in 4.0s (HiGHS) with objective consistency across 4 solvers ([C-3](scalability/C-3_dcopf_scale_MEDIUM.md), [C-7](scalability/C-7_solver_swap_MEDIUM.md))
- PTDF matrix computation (12,706 x 10,000) in 2.77s with 2.18e-11 max error ([C-9](scalability/C-9_ptdf_scale_MEDIUM.md))
- Solver swap is parameter-only (no reformulation) -- verified with HiGHS, GLPK, SCIP, Ipopt ([C-7](scalability/C-7_solver_swap_MEDIUM.md))
- ACPF converges at SMALL (2,000 buses) in 0.279s with 0% relaxation ([C-5 SMALL](scalability/C-5_ac_feasibility_relaxation_SMALL.md))

#### Weaknesses

- ACPF fails at MEDIUM (10k buses) -- both Ipopt and NLsolve diverge with MUMPS memory exhaustion [solver-specific + tool-specific] ([C-2](scalability/C-2_acpf_scale_MEDIUM.md))
- SCUC blocked at all scales -- cascaded from A-5 [tool-specific] ([C-4](scalability/C-4_scuc_scale_SMALL.md))
- Distributed slack blocked at MEDIUM -- cascaded from A-11 [tool-specific] ([C-10](scalability/C-10_distributed_slack_scale_MEDIUM.md))
- SCOPF at MEDIUM: Benders algorithm did not converge within time budget (1 iteration in 2837s, CPU-contended) ([C-8](scalability/C-8_scopf_scale_MEDIUM.md))

#### Workarounds Required

- Quadratic cost linearization required for MEDIUM DC OPF (1,130 generators, 45.5%) -- **stable** ([C-3](scalability/C-3_dcopf_scale_MEDIUM.md))
- SCIP dual extraction crash handled via two-level API fallback -- **stable** ([C-7](scalability/C-7_solver_swap_MEDIUM.md))
- Branch flows from `compute_dc_pf` require manual post-processing at scale -- **stable** ([C-1](scalability/C-1_dcpf_scale_MEDIUM.md))

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| C-1 | MEDIUM | qualified_pass | -- | stable (branch flows) | 2.09s | 167 |
| C-2 | MEDIUM | fail | -- | blocking (ACPF diverges) | -- | 247 |
| C-3 | MEDIUM | qualified_pass | -- | stable (cost linearization) | 77.20s | 213 |
| C-4 | SMALL | fail | A-5 | -- (SCUC unsupported) | -- | -- |
| C-5 SMALL | SMALL | informational | -- | stable (diagnostics) | 1.504s | 170 |
| C-5 MEDIUM | MEDIUM | informational | -- | blocking (ACPF diverges) | -- | 275 |
| C-7 | MEDIUM | qualified_pass | -- | stable (cost linearization, SCIP fallback) | 134.68s | 319 |
| C-8 | MEDIUM | constrained_pass | -- | stable (manual SCOPF) | 2836.88s | 485 |
| C-9 | MEDIUM | pass | -- | -- | 8.33s | 310 |
| C-10 | MEDIUM | fail | A-11 | blocking (no distributed slack) | -- | -- |

**Independent fails: 1** (C-2 ACPF MEDIUM). **Blocked: 2** (C-4 by A-5, C-10 by A-11).

#### Findings Summary

DC formulations (DCPF, DCOPF, PTDF) scale cleanly to MEDIUM (10k buses). Solver swap is parameter-only with consistent results across 4 solvers. ACPF convergence fails at MEDIUM scale due to Ipopt/MUMPS divergence on the pure-feasibility NLP formulation (0 inequality constraints); the convergence boundary lies between 2,000 and 10,000 buses. Two scalability tests are blocked by upstream expressiveness failures (SCUC, distributed slack). The SCOPF Benders algorithm works correctly at MEDIUM scale but is slow (not converged within time budget).

---

### 3.4 Workforce Accessibility (Suite D)

#### Strengths

- Install-to-first-solve in 3.6s with warm precompile cache; zero system dependencies beyond Julia ([D-1](accessibility/D-1_install_to_first_solve.md))
- 8/10 quickstart examples work on v0.21.5; core MATPOWER and two-level API examples reliable ([D-3](accessibility/D-3_example_verification.md))
- Infeasible OPF produces clear `INFEASIBLE` / `INFEASIBLE_POINT` status codes ([D-4](accessibility/D-4_error_quality.md))
- Minimum working code 40-80 LOC for natively supported operations (DCPF, ACPF, DCOPF) ([D-5](accessibility/D-5_code_volume.md))

#### Weaknesses

- Only 1/12 Suite A tests fully documented; 6 partially documented; 2 require source code reading [tool-specific] ([D-2](accessibility/D-2_documentation_audit.md))
- Invalid `bus_type` (=99) produces silent failure (`OTHER_ERROR`, NaN objective) -- no input validation [tool-specific] ([D-4](accessibility/D-4_error_quality.md))
- Missing generator cost data produces cryptic `KeyError("model")` without generator ID [tool-specific] ([D-4](accessibility/D-4_error_quality.md))
- JIT cold-start 5-15 minutes for first `Pkg.instantiate()` [solver-specific: Julia language characteristic] ([D-1](accessibility/D-1_install_to_first_solve.md))

#### Evidence Summary Table

| Test | Status | Key Evidence |
|------|--------|--------------|
| D-1 | qualified_pass | 3.6s warm; 5-15 min cold JIT |
| D-2 | qualified_pass | 1/12 fully documented; no source patching needed for any test |
| D-3 | qualified_pass | 8/10 examples pass; PSS/E edge case on non-standard file |
| D-4 | qualified_pass | 1 clear, 1 cryptic, 1 silent failure |
| D-5 | informational | Mean 397 NBNCL; range 176-663 |

#### Findings Summary

The tool is accessible for Julia-experienced developers but imposes meaningful friction for newcomers. Documentation covers core OPF well but lacks worked examples for data manipulation patterns, solver compatibility matrices, and advanced capabilities (SCOPF, lossy DCOPF). Error quality is mixed -- solver-detectable problems get clean diagnostics but data validation is minimal. The JIT cold-start is a one-time cost inherent to Julia, not a tool design issue.

---

### 3.5 Maturity & Sustainability (Suite E)

#### Strengths

- 4 releases in 24 months with maintained CHANGELOG and semver compliance ([E-1](maturity/E-1_release_cadence.md))
- 93.93% CI test coverage with 6-job matrix (2 Julia versions x 3 OS); weekly scheduled CI ([E-6](maturity/E-6_ci_test_coverage.md))
- DOE/LANL institutional backing under contract DE-AC52-06NA25396; 5 LANL staff contributors ([E-4](maturity/E-4_funding_model.md))
- IEEE PES PGLIB-OPF benchmark reference implementation; NREL Sienna ecosystem connection ([E-7](maturity/E-7_operational_adoption.md))
- 80% closed-issue maintainer response rate with substantive technical answers ([E-5](maturity/E-5_issue_tracker_health.md))

#### Weaknesses

- Bus factor = 1: @ccoffrin holds 82.9% of lifetime commits; zero direct commits in last 12 months [tool-specific] ([E-3](maturity/E-3_contributor_concentration.md))
- Zero formal code reviews: 100% of last 50 merged PRs were self-merged by 2 people [tool-specific] ([E-3](maturity/E-3_contributor_concentration.md))
- 24 commits in 12 months from 3 human authors -- low absolute volume indicating maintenance mode ([E-2](maturity/E-2_commit_activity.md))
- 7/10 open issues older than 1 year; PSS/E parser issues accumulate as technical debt ([E-5](maturity/E-5_issue_tracker_health.md))

#### Evidence Summary Table

| Test | Status | Key Evidence |
|------|--------|--------------|
| E-1 | pass | 4 releases in 24 months; ~6-month cadence |
| E-2 | qualified_pass | 24 commits/12mo; 2.4:1 substantive-to-maintenance ratio |
| E-3 | fail | 82.9% commits from one person; 0 formal reviews |
| E-4 | pass | LANL/DOE institutional backing |
| E-5 | qualified_pass | 28-day median close; 7/10 open issues >1 year |
| E-6 | pass | 93.93% coverage; multi-OS CI; weekly scheduled |
| E-7 | qualified_pass | DOE/PGLIB-OPF adoption; no commercial ISO deployment |

**Independent fails: 1** (E-3 contributor concentration).

#### Findings Summary

The project has strong institutional backing (DOE/LANL) and excellent CI infrastructure (94% coverage, multi-platform). Release cadence is consistent at ~6 months. The critical risk is contributor concentration: the primary author holds 83% of commits but was inactive in the last 12 months. Maintenance has transferred to @odow (JuMP ecosystem) who provides high-quality engineering but not domain expertise. The absence of formal code review is a process-maturity gap. The project is in stable maintenance mode, not active feature development.

---

### 3.6 Supply Chain (Suite F -- Gate)

#### Strengths

- BSD-3 core license (LANL); permissive and commercial-use compatible ([F-1](supply_chain/F-1_core_license.md))
- 114 packages fully resolved and pinned in Manifest.toml with git-tree-sha1 hashes ([F-2](supply_chain/F-2_dependency_tree.md))
- All 35 compiled components have public source and are reproducibly built via Yggdrasil ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- Complete execution path traceable through open-source Julia code; no opaque binaries ([F-5](supply_chain/F-5_code_inspectability.md))
- Air-gap installable via Julia depot caching; no runtime network access ([F-7](supply_chain/F-7_air_gap_installability.md))
- Open-source solvers sufficient for all use cases: Ipopt (EPL 2.0) + HiGHS (MIT) cover AC+DC ([F-8](supply_chain/F-8_solver_dependency_assessment.md))

#### Weaknesses

- GLPK.jl wrapper is GPL v3 (copyleft) -- must be excluded from commercial deployments ([F-3](supply_chain/F-3_dependency_license_audit.md))
- SCIP_jll v0.2.1 uses ZIB Academic License for SCIP 8.0.0 -- non-commercial only at pinned version ([F-3](supply_chain/F-3_dependency_license_audit.md))
- Getting-started examples lack explicit version pins; rely on implicit Manifest.toml semantics ([F-9](supply_chain/F-9_getting_started_artifact_integrity.md))

#### Evidence Summary Table

| Test | Status | Key Evidence |
|------|--------|--------------|
| F-1 | pass | BSD-3 (LANL) |
| F-2 | pass | 114 packages; 6 direct, 108 transitive |
| F-3 | qualified_pass | GLPK GPL v3, SCIP ZIB Academic flagged; both optional |
| F-4 | pass | 35 JLL packages; all source-available |
| F-5 | pass | Full call chain traceable; no opaque steps |
| F-6 | pass | Julia General Registry; git-tree-sha1 verified |
| F-7 | pass | Depot caching; no runtime network access |
| F-8 | pass | Ipopt + HiGHS cover all standard formulations |
| F-9 | qualified_pass | /stable/ docs links; mutable badge refs |

#### Findings Summary

The supply chain is clean for commercial deployment. The core PowerModels + JuMP + Ipopt + HiGHS stack uses permissive licenses (BSD-3, MIT, EPL 2.0, MPL 2.0). The two flagged dependencies (GLPK GPL, SCIP ZIB Academic) are optional solvers that can be excluded without loss of capability. Distribution integrity is strong via Julia's content-addressable registry. All compiled binaries are reproducibly built from public source.

---

## 3b. FNM Ingestion Findings (Suite G)

Suite G executed (FNM_PATH set). FNM ingestion used the MATPOWER fallback path because PowerModels cannot parse intermediate CSV format or PSS/E RAW v31.

### Data Model Fidelity

**G-FNM-1 (fail):** PowerModels has no CSV parser. The PSS/E RAW parser fails on v31 headers. MATPOWER fallback loaded 27,862 buses / 32,606 branches / 5,741 generators / 8,624 loads (vs manifest: 30,307 / 33,840 / 5,768 / 15,062). Count deltas are attributable to the pre-cleaned main-island subset, not ingestion errors. [tool-specific: no CSV ingestion path] ([G-FNM-1](fnm_ingestion/G-FNM-1_intermediate_ingestion.md))

**G-FNM-2 (skip):** Field coverage audit skipped because G-FNM-1 failed (no CSV ingestion). Cannot assess field-level coverage against the intermediate schema. ([G-FNM-2](fnm_ingestion/G-FNM-2_field_coverage_audit.md))

### Power Flow Verification

**G-FNM-3 (fail):** DCPF verification fails with 2.43% bus angle pass rate (need >=95%) and 78.88% branch flow pass rate (need >=90%). All three hard-fail conditions triggered. Root cause: `DCPPowerModel` uses simplified B-matrix (`b = -1/x`) that ignores transformer tap ratios. The effect is global (not localized to transformer-adjacent buses) because the simplified admittance changes network impedance structure throughout. The MATPOWER reference uses `makeBdc()` with full tap handling. [tool-specific: DCPPowerModel formulation choice] ([G-FNM-3](fnm_ingestion/G-FNM-3_dcpf_verification.md))

**G-FNM-4 (informational):** ACPF does not converge at any relaxation level. Ipopt diverges (inf_du = 4.28e17 at iteration 14, MUMPS memory exhaustion at ~7GB). The ACPF reference data itself shows divergent values (VM up to 379,646 p.u.), confirming the FNM case is inherently difficult for ACPF. No gate consequence. ([G-FNM-4](fnm_ingestion/G-FNM-4_acpf_convergence.md))

### Supplemental Data Representability

**G-FNM-5 (informational):** 39% native field coverage across 44 supplemental CSV fields (17 N, 8 E, 19 X). Strengths: 3 thermal rating tiers native (RATE_A/B/C), standard bus/branch identifiers. Gaps: interface definitions (100% external), trading hub data (75% external), outage scheduling (50% external). PowerModels' dict-based data model provides simple extension for custom fields but has no semantic support for market-layer concepts (hubs, interfaces, contingency definitions). ([G-FNM-5](fnm_ingestion/G-FNM-5_supplemental_csv_representability.md))

**FNM findings weaken the Expressiveness assessment:** The `DCPPowerModel` formulation's omission of tap ratios in the B-matrix is a structural limitation that produces systematically incorrect DCPF results on networks with off-nominal transformers (the FNM has 2,358 transformers with off-nominal taps). The `DCMPPowerModel` alternative exists but is not accessible through `solve_dc_pf`.

---

## 4. Cross-Cutting Observations

### API Friction Patterns

- **Branch flow gap:** `compute_dc_pf` and `compute_ac_pf` consistently omit branch flows from result dict. Requires manual post-processing or `calc_branch_flow_ac/dc`. Affects A-1, A-2, A-4, B-3, B-5, C-1 and all scale variants. Stable workaround (~10 LOC).
- **Solver compatibility:** Multiple formulation/solver mismatches require user knowledge: DCPLLPowerModel needs Ipopt (not HiGHS); storage OPF needs SCIP (not HiGHS/Ipopt); quadratic costs with security constraints cause HiGHS QP numerical errors. No solver compatibility matrix in documentation.
- **baseMVA type inconsistency:** Parsed as `Int64` from case39.m, causing type mismatch when multiplied with Float64 results. Minor but recurring friction.
- **`make_basic_network` absorbs phase shifts:** Phase-shifter handling is automatic but undocumented. PTDF computation uses simplified admittance after absorption, producing correct results but making the transformation opaque.

### Documentation Gaps

- SCOPF LODF formula not documented; `var(pm, :p)` tuple key structure discoverable only via source code.
- Formulation-specific methods in `form/*.jl` lack docstrings; developers must read source to understand template-method split.
- No solver compatibility matrix for formulation types.
- No worked examples for data manipulation patterns (load injection, cost modification, commitment injection).

### Solver Ecosystem

- **Ipopt + MUMPS divergence at scale** [solver-specific]: Interior-point method diverges on ACPF feasibility NLP at 10k+ buses. The pure-feasibility formulation (0 inequality constraints) is numerically challenging. MUMPS workspace grows to >5GB before exhaustion.
- **HiGHS QP sensitivity** [solver-specific]: Reports `OTHER_ERROR` on quadratic costs with security constraints at TINY scale and on MIQP at any scale.
- **SCIP dual extraction incompatibility** [solver-specific]: SCIP.jl v0.11.6 does not support `ConstraintDual`; InfrastructureModels crashes during solution building. Workaround via two-level API.
- **Julia JIT compilation tax** [solver-specific: language characteristic]: First invocation 5-15x slower than subsequent calls. `Pkg.instantiate()` takes 5-15 minutes. Multi-network code path JIT >15 minutes from cold start.

### Architecture Quality

- Four-layer dispatch architecture (public API / model lifecycle / formulation build / solver) is cleanly separated with Julia multiple dispatch as the extension mechanism.
- `ref_add_core!` provides comprehensive preprocessed reference data (bus, gen, branch, arcs).
- `instantiate_model` / `optimize_model!` two-level API is the primary extensibility strength.
- PTDF API (`calc_basic_ptdf_matrix`) is first-class with machine-epsilon accuracy.

### FNM Data Model

- No CSV ingestion path; PSS/E v31 parser fails on header format.
- MATPOWER fallback works but requires external conversion step.
- `DCPPowerModel` B-matrix formulation ignores tap ratios, producing systematic DCPF errors on real networks with transformers.
- 39% native field coverage for supplemental market data; no interface, hub, or contingency definition concepts.

---

## 5. Items Requiring Human Spot-Check

- [ ] A-1, A-2, A-4 (qualified_pass) -- branch flow workaround classified as "stable"; verify ~10 LOC post-processing does not constitute fragile workaround for production use
- [ ] A-6 (qualified_pass) -- ed_only SCED mode due to A-5 SCUC failure; verify whether ed_only is acceptable for expressiveness assessment
- [ ] A-9 (qualified_pass) -- SCOPF via manual Benders cutting plane; verify whether manual LODF/PTDF implementation constitutes "native" or "wrapper" SCOPF capability
- [ ] A-10 (qualified_pass) -- solver switch (HiGHS to Ipopt) for DCPLLPowerModel; verify attribution as solver-specific vs tool-specific
- [ ] A-12 (pass) -- three workarounds (SCIP solver, cyclic SoC injection, two-phase LMP); verify pass vs qualified_pass given workaround count
- [ ] B-2 (qualified_pass) -- ~12 LOC adjacency construction classified as "stable"; verify this is not over-generous given no Graphs.jl integration
- [ ] B-8 (qualified_pass) -- distributed slack ~150 LOC custom JuMP classified as "stable" workaround; should this be "blocking" (as in A-11)?
- [ ] C-2 (fail) -- ACPF MEDIUM failure attributed as "solver-specific + tool-specific"; the `solve_ac_pf` formulation (0 inequality constraints) is tool-specific but the MUMPS divergence is solver-specific
- [ ] C-8 (constrained_pass) -- SCOPF MEDIUM timing inflated ~5x by CPU contention; verify acceptability of constrained_pass vs fail given non-convergence
- [ ] E-3 (fail) -- contributor concentration near-borderline given @odow's active maintenance; verify bus factor assessment considering JuMP ecosystem continuity
- [ ] F-3 (qualified_pass) -- SCIP ZIB Academic License flagged; F-8 states SCIP 8.0 is Apache 2.0; resolve license version discrepancy between F-3 and F-8
- [ ] G-FNM-3 (fail) -- DCPPowerModel tap-ratio omission; verify whether DCMPPowerModel via custom solve call should be attempted as workaround
- [ ] D-2, D-3, D-4 (all qualified_pass) -- three accessibility tests at qualified_pass; verify whether the pattern suggests Medium or Low confidence

---

## 6. Methodology Notes

- **Scale cap applied:** MEDIUM (ACTIVSg 10k-bus). Scalability tests C-1 through C-10 used MEDIUM as the target scale.
- **FNM status:** Suite G executed (FNM_PATH set). MATPOWER fallback ingestion path used. G-FNM-1 failed (no CSV parser, PSS/E v31 incompatible). G-FNM-2 skipped (blocked by G-FNM-1). G-FNM-3 failed (DCPPowerModel B-matrix ignores taps). G-FNM-4 and G-FNM-5 informational.
- **Tests skipped:** G-FNM-2 (blocked by G-FNM-1 CSV ingestion failure). 1 total skip.
- **Solver versions used:** HiGHS 1.13.1 (via HiGHS_jll), Ipopt 3.14.19 (via Ipopt_jll), SCIP 8.0.0 (via SCIP_jll v0.2.1), GLPK 5.0.1 (via GLPK_jll), NLsolve 4.5.1 (Julia package), MUMPS 5.8.2 (via MUMPS_seq_jll).
- **Tool version evaluated:** PowerModels.jl v0.21.5 (git-tree-sha1: b8e410e1d827b621e82e7e670967f0efc5845c30).
- **Julia version:** 1.10.7.
- **Devcontainer environment:** Ubuntu 24.04 + Julia 1.10 + Python 3.12 + Octave + uv.
