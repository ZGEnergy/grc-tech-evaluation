# Synthesis Report -- PowerModels.jl v0.21.5

**Contract:** FA714626C0006
**Tool:** PowerModels.jl v0.21.5 (LANL, Julia)
**Protocol:** v4
**Evaluation date:** 2026-03-07
**Result files:** 76 (0 gaps)

---

## 1. Executive Summary

PowerModels.jl is a research-grade steady-state power network optimization framework from Los Alamos National Laboratory, built on Julia's JuMP mathematical programming ecosystem. It excels at its core use case -- formulation-flexible OPF -- with native DCPF, ACPF, and DCOPF, clean JuMP model access for custom constraints, and a strong PTDF pipeline. The tool passes all gate tests (G-1/G-2/G-3) and the supply chain gate (BSD-3-Clause core, fully functional on permissive-licensed open-source solvers). However, PowerModels has no native SCUC, SCED, stochastic OPF, SCOPF, or distributed slack support -- these require 140-400 lines of user-assembled JuMP code. ACPF fails at 10k-bus scale. The bus factor is effectively 1 (ccoffrin 82.4% of commits, with an informal transition to odow underway), and there is no evidence of operational/production deployment. Scale cap: MEDIUM.

---

## 2. Grade Recommendations Table

| Criterion | Grade | Confidence | Key Evidence |
|-----------|-------|------------|--------------|
| Problem Expressiveness | B- | High | Core PF/OPF native and strong; SCUC/SCED/SCOPF require 140-400 LOC user-assembled JuMP; stochastic OPF blocking fail (A-8); ACPF fails at 10k-bus |
| Extensibility | A- | High | Two-level API enables clean constraint injection (B-1); JuMP interop excellent; PTDF native; no native graph library (B-2 qualified) |
| Scalability | B- | High | DCPF/DCOPF scale to 10k-bus; ACPF fails at 10k; SCUC times out at 2k; SCOPF/contingency sweep infeasible at MEDIUM; solver swap works but some solvers struggle |
| Workforce Accessibility | B- | Medium | Core PF/OPF well-documented; 4/11 Suite A tests from docs alone; Julia startup overhead; poor error messages for data errors |
| Maturity & Sustainability | C+ | High | Bus factor = 1; no operational adoption; but strong CI (94% coverage), DOE funding, quarterly releases, JuMP ecosystem integration |
| Supply Chain (Gate) | A | High | BSD-3-Clause core; pure Julia; HiGHS (MIT) + Ipopt (EPL-2.0) cover all formulations; airgap-installable; GLPK/SCIP optional and removable |

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness

#### Strengths

- Native DCPF via direct linear solve, no optimizer needed -- 0.0006s on TINY, 0.234s on MEDIUM ([A-1](expressiveness/A-1_dcpf_TINY.md), [A-1 MEDIUM](expressiveness/A-1_dcpf_MEDIUM.md))
- Native ACPF via NLsolve Newton-Raphson, converges on flat start for TINY and SMALL ([A-2](expressiveness/A-2_acpf_TINY.md))
- Native DCOPF with LMP extraction via single function call, scales to 10k-bus in 3.1s with Ipopt ([A-3](expressiveness/A-3_dcopf_TINY.md), [A-3 MEDIUM](expressiveness/A-3_dcopf_MEDIUM.md))
- AC feasibility check is a clean 3-line workflow on in-memory data -- no file export/reimport ([A-4](expressiveness/A-4_ac_feasibility_TINY.md))
- Built-in lossy DC OPF formulation (DCPLLPowerModel) produces loss-inclusive LMPs with non-zero loss components ([A-10](expressiveness/A-10_lossy_dcopf_lmp_TINY.md))
- Multi-network framework supports temporal (multi-period) optimization via `replicate()` + `solve_mn_opf()` ([A-8](expressiveness/A-8_stochastic_timeseries_TINY.md))
- SCOPF achievable at SMALL scale via manual JuMP assembly with 4.74% security premium ([A-9 SMALL](expressiveness/A-9_scopf_SMALL.md))
- Distributed slack OPF achievable via PTDF algebra with settable weight vectors ([A-11](expressiveness/A-11_distributed_slack_opf_TINY.md))

#### Weaknesses

- No native SCUC -- requires ~140 LOC of user-assembled JuMP; at SMALL scale, HiGHS times out on the MILP ([A-5](expressiveness/A-5_scuc_TINY.md), [A-5 SMALL](expressiveness/A-5_scuc_SMALL.md))
- No native SCED -- requires ~200 LOC of manual two-stage decomposition; blocked at SMALL by SCUC failure ([A-6](expressiveness/A-6_sced_TINY.md), [A-6 SMALL](expressiveness/A-6_sced_SMALL.md))
- No native stochastic OPF -- **blocking fail**. Multi-network framework is one-dimensional (time periods only, no scenario indexing, no probability weighting, no recourse structure) ([A-8](expressiveness/A-8_stochastic_timeseries_TINY.md))
- ACPF fails at 10k-bus scale -- NLsolve does not converge with flat start or DC warm start ([A-2 MEDIUM](expressiveness/A-2_acpf_MEDIUM.md))
- No native SCOPF -- requires ~180-285 LOC of manual JuMP assembly ([A-9](expressiveness/A-9_scopf_TINY.md))
- No native distributed slack -- requires ~150-350 LOC of manual PTDF-based OPF ([A-11](expressiveness/A-11_distributed_slack_opf_TINY.md))
- No native contingency sweep -- manual BFS + combinatorial enumeration required; infeasible at MEDIUM scale due to combinatorial explosion ([A-7](expressiveness/A-7_contingency_sweep_TINY.md), [A-7 MEDIUM](expressiveness/A-7_contingency_sweep_MEDIUM.md))

#### Workarounds Required

- SCUC via manual JuMP MILP assembly (~140 LOC) -- **stable**([A-5](expressiveness/A-5_scuc_TINY.md))
- SCED via manual two-stage UC+ED decomposition (~200 LOC) -- **stable**([A-6](expressiveness/A-6_sced_TINY.md))
- SCOPF via manual JuMP LP with per-contingency networks (~180 LOC) -- **stable**([A-9](expressiveness/A-9_scopf_TINY.md))
- Lossy DCOPF requires Ipopt (HiGHS cannot solve QCQP) -- **stable**([A-10](expressiveness/A-10_lossy_dcopf_lmp_TINY.md))
- LMP decomposition computed manually from bus duals -- **stable**([A-10](expressiveness/A-10_lossy_dcopf_lmp_TINY.md))
- Distributed slack OPF via manual PTDF-based formulation (~150 LOC) -- **stable**([A-11](expressiveness/A-11_distributed_slack_opf_TINY.md))
- Contingency sweep via manual BFS + deepcopy loop -- **stable**([A-7](expressiveness/A-7_contingency_sweep_TINY.md))
- Stochastic OPF -- **blocking**, no viable workaround within test scope ([A-8](expressiveness/A-8_stochastic_timeseries_TINY.md))
- Cost linearization required for HiGHS + binary variables (MIQP unsupported) -- **stable**([A-5](expressiveness/A-5_scuc_TINY.md))

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | LOC |
|------|---------|--------|------------|------|-----|
| A-1 | TINY | pass | -- | 0.27s | 131 |
| A-1 | MEDIUM | pass | -- | 1.85s | 103 |
| A-2 | TINY | pass | -- | 0.31s | 144 |
| A-2 | MEDIUM | fail | -- | 67.0s | 127 |
| A-3 | TINY | pass | -- | 1.67s | 124 |
| A-3 | MEDIUM | pass | stable (data fix) | 3.13s | 149 |
| A-4 | TINY | pass | -- | 0.43s | 226 |
| A-4 | MEDIUM | qualified_pass | stable | -- | 226 |
| A-5 | TINY | qualified_pass | stable | 4.91s | 295 |
| A-5 | SMALL | fail | stable | 494.5s | 240 |
| A-6 | TINY | qualified_pass | stable | 4.91s | 406 |
| A-6 | SMALL | fail | stable (blocked) | -- | 407 |
| A-7 | TINY | qualified_pass | stable | 2.25s | 333 |
| A-7 | MEDIUM | fail | stable | -- | 333 |
| A-8 | TINY | fail | blocking | 2.52s | 132 |
| A-8 | SMALL | fail | blocking | -- | 132 |
| A-9 | TINY | qualified_pass | stable | 3.59s | 331 |
| A-9 | SMALL | qualified_pass | stable | 118.9s | 285 |
| A-10 | TINY | qualified_pass | stable | 5.07s | 367 |
| A-10 | SMALL | qualified_pass | stable | 22.87s | 210 |
| A-11 | TINY | qualified_pass | stable | 8.01s | 396 |
| A-11 | SMALL | qualified_pass | stable | 153.7s | 350 |

#### Grade Rationale

**B-: "Multiple workarounds, some fragile."** PowerModels' core PF/OPF is strong (A-1 through A-4 pass at grade network). However, 6 of 11 Suite A tests required user-assembled JuMP formulations averaging 269 code LOC. The stochastic OPF (A-8) is a blocking fail with no workaround -- the multi-network framework architecturally lacks scenario indexing. SCUC/SCED fail at their grade network (SMALL) due to solver timeouts. ACPF fails at 10k-bus. The tool provides substantial value for steady-state OPF but imposes significant development overhead for market-operations problems (UC, ED, SCOPF). The blocking A-8 fail and the SCUC/SCED grade-network failures pull below B.

---

### 3.2 Extensibility

#### Strengths

- Two-level API (`instantiate_model` / `optimize_model!`) exposes JuMP model for arbitrary constraint injection -- no source patching needed ([B-1](extensibility/B-1_custom_constraints_TINY.md), [arch-quality observation](observations/arch-quality-extensibility-B-1_custom_constraints.md))
- Custom flow gate constraint with dual extraction works cleanly at TINY and MEDIUM scale ([B-1 MEDIUM](extensibility/B-1_custom_constraints_MEDIUM.md))
- Dict-based data model enables efficient contingency loops via `deepcopy` + `br_status=0` -- 46 N-1 in 0.22s on TINY, 50 N-1 in 3.43s on MEDIUM ([B-3](extensibility/B-3_contingency_loop_TINY.md), [B-3 MEDIUM](extensibility/B-3_contingency_loop_MEDIUM.md))
- Native PTDF via `calc_basic_ptdf_matrix` with flow prediction error < 1e-11 at 10k-bus ([B-9](extensibility/B-9_ptdf_extraction_TINY.md), [B-9 MEDIUM](extensibility/B-9_ptdf_extraction_MEDIUM.md))
- Scenario wrapping loop runs 20 scenarios x 12 periods on SMALL in 281.6s with consistent timing ([B-4](extensibility/B-4_stochastic_wrapping_TINY.md), [B-4 SMALL](extensibility/B-4_stochastic_wrapping_SMALL.md))
- Interoperability to DataFrames.jl + CSV in < 5 lines at both TINY and MEDIUM ([B-5](extensibility/B-5_interoperability_TINY.md), [B-5 MEDIUM](extensibility/B-5_interoperability_MEDIUM.md))
- Clean 4-layer code architecture: IO / Data Model / Formulation / Solver with type-parameterized formulations ([B-6](extensibility/B-6_code_architecture.md))
- Reference bus reconfigurable via data dict modification; distributed slack via PTDF algebra ([B-8](extensibility/B-8_reference_bus_config_TINY.md))

#### Weaknesses

- No native graph library -- BFS/adjacency must be built manually from branch `f_bus`/`t_bus` pairs (~15-20 LOC) ([B-2](extensibility/B-2_graph_access_TINY.md), [api-friction observation](observations/api-friction-extensibility-B-2_graph_access.md))

#### Workarounds Required

- Manual adjacency graph construction for BFS/topology analysis (~15 LOC) -- **stable**([B-2](extensibility/B-2_graph_access_TINY.md))
- Reference bus change requires model re-solve (no hot-swap) -- **stable**([B-8](extensibility/B-8_reference_bus_config_TINY.md))

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | LOC |
|------|---------|--------|------------|------|-----|
| B-1 | TINY | pass | -- | 1.85s | 210 |
| B-1 | MEDIUM | pass | -- | 54.4s | 210 |
| B-2 | TINY | qualified_pass | stable | -- | -- |
| B-2 | MEDIUM | qualified_pass | stable | -- | -- |
| B-3 | TINY | pass | -- | 0.22s | -- |
| B-3 | MEDIUM | pass | -- | 3.43s | -- |
| B-4 | TINY | pass | -- | 1.37s | -- |
| B-4 | SMALL | pass | -- | 281.6s | -- |
| B-5 | TINY | pass | -- | -- | -- |
| B-5 | MEDIUM | pass | -- | -- | -- |
| B-6 | N/A | pass | -- | -- | -- |
| B-7 | TINY | pass | -- | -- | -- |
| B-7 | MEDIUM | pass | -- | -- | -- |
| B-8 | TINY | pass | stable | -- | -- |
| B-8 | SMALL | pass | stable | -- | -- |
| B-9 | TINY | pass | -- | -- | -- |
| B-9 | MEDIUM | pass | -- | 274.4s | 187 |

#### Grade Rationale

**A-: "Strong overall, one minor caveat."** All 17 extensibility tests pass or qualified-pass. The JuMP interop model is one of the cleanest extension patterns among evaluated tools -- users can inject arbitrary constraints, extract duals, and swap solvers with minimal code. The PTDF pipeline is native and accurate. The sole caveat is the missing native graph API (B-2 qualified pass), which requires ~15 lines of manual adjacency construction. This is a minor gap that does not impede any critical workflow.

---

### 3.3 Scalability

#### Strengths

- DCPF scales cleanly to 10k-bus: 0.234s solve, 121 MB memory ([C-1](scalability/C-1_dcpf_scale_MEDIUM.md))
- DCOPF scales to 10k-bus with Ipopt: 3.1s total, 25 iterations ([C-3](scalability/C-3_dcopf_scale_MEDIUM.md))
- PTDF computation scales to 10k-bus (127M elements) in 3.73s, 1 GB matrix ([C-9](scalability/C-9_ptdf_scale_MEDIUM.md))
- Distributed slack scales to 10k-bus: 12.2s total wall-clock ([C-10](scalability/C-10_distributed_slack_scale_MEDIUM.md))
- Stochastic wrapping (20 scenarios x 12 periods) scales to SMALL in 281.6s with consistent per-scenario timing ([C-6](scalability/C-6_stochastic_scale_SMALL.md))
- Solver swap is a one-line API change; 4 solvers tested at MEDIUM ([C-7](scalability/C-7_solver_swap_MEDIUM.md))

#### Weaknesses

- ACPF fails at 10k-bus -- NLsolve Newton-Raphson does not converge ([C-2](scalability/C-2_acpf_scale_MEDIUM.md))
- SCUC times out at SMALL (2k-bus, 24hr) -- HiGHS MIP cannot solve LP relaxation in 300s ([C-4](scalability/C-4_scuc_scale_SMALL.md))
- N-M contingency sweep infeasible at MEDIUM -- combinatorial explosion ([C-5](scalability/C-5_contingency_sweep_scale_MEDIUM.md))
- SCOPF infeasible at MEDIUM with 500 contingencies -- problem size exceeds solver capacity ([C-8](scalability/C-8_scopf_scale_MEDIUM.md))
- HiGHS QP struggles at 10k-bus scale (300s timeout); GLPK requires cost linearization ([C-3](scalability/C-3_dcopf_scale_MEDIUM.md), [C-7](scalability/C-7_solver_swap_MEDIUM.md))

#### Workarounds Required

- Ipopt required for DCOPF at 10k-bus with quadratic costs (HiGHS QP too slow) -- **stable**([C-3](scalability/C-3_dcopf_scale_MEDIUM.md))
- Cost linearization for LP-only solvers (GLPK, SCIP) -- **stable**([C-7](scalability/C-7_solver_swap_MEDIUM.md))
- Distributed slack requires ~350 LOC of manual JuMP at any scale -- **stable**([C-10](scalability/C-10_distributed_slack_scale_MEDIUM.md))

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | Memory |
|------|---------|--------|------------|------|--------|
| C-1 | MEDIUM | pass | -- | 1.85s | 121 MB |
| C-2 | MEDIUM | fail | -- | 67.0s | -- |
| C-3 | MEDIUM | pass | stable | 3.13s | 184 MB |
| C-4 | SMALL | fail | stable | 494.5s | -- |
| C-5 | MEDIUM | fail | stable | -- | -- |
| C-6 | SMALL | pass | -- | 281.6s | -- |
| C-7 | MEDIUM | qualified_pass | stable | varies | -- |
| C-8 | MEDIUM | fail | stable | -- | -- |
| C-9 | MEDIUM | pass | -- | 6.65s | 2,452 MB |
| C-10 | MEDIUM | qualified_pass | stable | 12.2s | 1,017 MB |

#### Grade Rationale

**B-: "Multiple workarounds, some fragile."** DCPF and DCOPF scale well to MEDIUM (10k-bus). PTDF and distributed slack also scale. However, 4 of 10 scalability tests fail outright: ACPF (convergence), SCUC (solver timeout), contingency sweep (combinatorial), SCOPF (problem size). These are not merely workaround-needing -- they are non-functional at scale. The ACPF failure is a tool limitation (NLsolve configuration not exposed). The SCUC/SCOPF/contingency failures involve both tool limitations (no built-in formulations requiring manual assembly) and open-source solver limitations at scale. The 4 passes and 2 qualified passes on core capabilities keep this above C+, but the breadth of scale failures warrants B-.

---

### 3.4 Workforce Accessibility

#### Strengths

- Install-to-first-solve in ~5.2s after precompilation; clear 3-line install docs ([D-1](accessibility/D-1_install_to_first_solve.md))
- Core PF/OPF functions (A-1, A-2, A-3) completable from official documentation alone ([D-2](accessibility/D-2_documentation_audit.md))
- All getting-started examples use current, valid API -- 7-year-old tutorial still works ([D-3](accessibility/D-3_example_verification.md))
- Built-in problem types require ~100 LOC; clean, minimal API ([D-5](accessibility/D-5_code_volume.md))
- Infeasible OPF returns structured solver status with clear `INFEASIBLE` message ([D-4](accessibility/D-4_error_quality.md))

#### Weaknesses

- 4/11 Suite A tests (36%) have no documentation support -- require source code reading and JuMP expertise ([D-2](accessibility/D-2_documentation_audit.md))
- Julia startup overhead (2-5s per invocation) and multi-minute first-time precompilation ([D-1](accessibility/D-1_install_to_first_solve.md))
- Data-level errors produce raw Julia exceptions (KeyError, AssertionError) with no domain-specific messages ([D-4](accessibility/D-4_error_quality.md))
- 6/11 Suite A tests require user-assembled JuMP formulations averaging 269 LOC -- 2.7x more than built-in tests ([D-5](accessibility/D-5_code_volume.md))
- Multi-network documentation is sparse and explicitly points readers to source code ([D-2](accessibility/D-2_documentation_audit.md))
- API inconsistency: `compute_dc_pf` returns Boolean status vs `solve_dc_pf` returns MOI enum ([observation](observations/expressiveness_api-friction.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| D-1 | qualified_pass | 5.2s load-to-first-solve; Julia startup overhead |
| D-2 | qualified_pass | 4/11 from docs alone, 4/11 no docs |
| D-3 | qualified_pass | All examples work; tutorial 7 years old, data paths only fix needed |
| D-4 | qualified_pass | 1/3 good, 2/3 poor error messages |
| D-5 | informational | Built-in ~100 LOC, manual ~269 LOC mean |

#### Grade Rationale

**B-: "Multiple workarounds, some fragile."** The core PF/OPF documentation is adequate and examples are API-stable. However, the sharp accessibility cliff beyond built-in problems (requiring JuMP expertise, source code reading, and 2.7x more code) significantly limits workforce accessibility. The Julia language barrier further narrows the available developer pool compared to Python-based tools. Poor data-level error messages add friction for programmatic workflows. The API inconsistency between native and JuMP-based PF interfaces is a minor but real usability issue. All D-tests are qualified_pass, indicating consistent moderate friction across the accessibility surface.

---

### 3.5 Maturity & Sustainability

#### Strengths

- Healthy release cadence: 5-7 releases in 24 months, approximately quarterly ([E-1](maturity/E-1_release_cadence.md))
- Strong CI: 94% code coverage, cross-platform matrix (Linux/macOS/Windows), weekly cron runs, 25 test files ([E-6](maturity/E-6_ci_test_coverage.md))
- DOE/LANL institutional backing under contract DE-AC52-06NA25396 ([E-4](maturity/E-4_funding_model.md))
- Issue tracker functional with 81-day median time-to-close and maintainer responses on most issues ([E-5](maturity/E-5_issue_tracker_health.md))
- JuMP ecosystem provides secondary sustainability path via Oscar Dowson (odow) as active maintainer ([E-2](maturity/E-2_commit_activity.md))

#### Weaknesses

- Bus factor = 1: ccoffrin (LANL) has 82.4% of all commits; top 3 contributors = 90.2% ([E-3](maturity/E-3_contributor_concentration.md))
- No operational/production deployment evidence -- confined to academic research and DOE benchmarking ([E-7](maturity/E-7_operational_adoption.md))
- Low commit activity: 24 commits in 12 months from 3 human committers ([E-2](maturity/E-2_commit_activity.md))
- Pre-1.0 after 9+ years (v0.21.x) ([E-1](maturity/E-1_release_cadence.md))
- Grant-cycle funding dependency -- no commercial entity funds or depends on PowerModels ([E-4](maturity/E-4_funding_model.md))
- Batch issue closure pattern suggests limited maintainer bandwidth ([E-5](maturity/E-5_issue_tracker_health.md))
- Informal maintainer transition from ccoffrin to odow -- not formalized ([E-3](maturity/E-3_contributor_concentration.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| E-1 | pass | 5-7 releases in 24 months, quarterly cadence |
| E-2 | qualified_pass | 24 commits/yr, 3 human committers, 75% substantive |
| E-3 | fail | Bus factor = 1, top contributor 82.4% |
| E-4 | informational | DOE/LANL funding, no commercial backing |
| E-5 | qualified_pass | 81-day median close, batch triage pattern |
| E-6 | pass | 94% coverage, cross-platform CI |
| E-7 | fail | No operational deployment evidence |

#### Grade Rationale

**C+: "Significant gaps, but NOT disqualifying."** The CI/test infrastructure (E-6) and release cadence (E-1) are strong, demonstrating engineering discipline. However, two tests fail outright: contributor concentration (E-3, bus factor = 1) and operational adoption (E-7, zero production deployments). The combination of extreme single-contributor dependency and no production track record represents material continuity risk. The DOE funding and JuMP ecosystem integration provide mitigants that prevent a C grade, and the informal maintainer transition to odow suggests the project is not at immediate risk of abandonment. However, the lack of formalized governance and any commercial adoption keeps this at the floor of passing.

---

### 3.6 Supply Chain (Gate)

#### Strengths

- BSD-3-Clause core license -- fully permissive, no copyleft ([F-1](supply_chain/F-1_core_license.md))
- Pure Julia source -- 42 .jl files, no compiled extensions in PowerModels itself ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- Full execution path traceable through pure Julia to solver binary boundary ([F-5](supply_chain/F-5_code_inspectability_trace.md))
- HiGHS (MIT) + Ipopt (EPL-2.0) cover all formulation types without proprietary solvers ([F-8](supply_chain/F-8_solver_dependency_assessment.md))
- Airgap-installable via Julia depot cloning mechanism ([F-7](supply_chain/F-7_airgap_installability.md))
- Content-addressed artifact hashes (git-tree-sha1) in Manifest.toml lockfile ([F-6](supply_chain/F-6_distribution_integrity.md))
- Getting-started examples use local bundled data, no mutable external URLs ([F-9](supply_chain/F-9_getting_started_integrity.md))

#### Weaknesses

- JuMP/MutableArithmetics are MPL-2.0 (weak copyleft, file-level) -- compatible with commercial use but requires awareness ([F-3](supply_chain/F-3_dependency_license_audit.md))
- GLPK (GPL-3.0) and SCIP (ZIB Academic, non-commercial) are in the evaluation environment but are optional and removable ([F-3](supply_chain/F-3_dependency_license_audit.md))
- No cryptographic package signing (Julia ecosystem limitation, shared with pip/npm) ([F-6](supply_chain/F-6_distribution_integrity.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| F-1 | pass | BSD-3-Clause |
| F-2 | informational | 114 packages (79 third-party + 35 JLL) |
| F-3 | qualified_pass | GPL-3.0 (GLPK) and ZIB (SCIP) optional/removable |
| F-4 | pass | Pure Julia core; solver JLLs have source available |
| F-5 | pass | Full path inspectable to solver binary boundary |
| F-6 | pass | Content-addressed hashes, lockfile |
| F-7 | pass | Airgap via depot cloning |
| F-8 | pass | HiGHS + Ipopt cover all formulations |
| F-9 | pass | No mutable URLs, local data |

#### Grade Rationale

**A: "Strong native support, well-tested at scale."** The supply chain is clean. The core package is BSD-3-Clause. All solver dependencies are open-source with permissive or weak-copyleft licenses. The only copyleft concerns (GLPK GPL-3.0, SCIP ZIB Academic) are optional solver packages that can be excluded without losing any formulation capability. The JuMP MPL-2.0 dependency is weak copyleft at the file level and explicitly permits "Larger Works." The F-3 qualified pass reflects that the evaluation environment includes these optional copyleft packages, but a production deployment can trivially exclude them.

---

### 3.7 Phase 2 Readiness (Informational, not graded)

| Finding | Status | Summary |
|---------|--------|---------|
| P2-1: PSS/E RAW parsing | HIGH for v33 | Built-in v33 parser (2,700 LOC); v34+ unsupported, significant effort to add |
| P2-2: Piecewise-linear costs | HIGH | Native PWL support (model=1), lambda formulation, no integer variables, LP-compatible |
| P2-3: Commitment injection | MODERATE | Steps 2-4 trivial; Step 1 (SCUC) requires ~140 LOC manual JuMP; `compute_ac_pf` bug with gen_status=0 |

---

## 4. Cross-Cutting Observations

### API Friction Patterns

- **Status type inconsistency:** `compute_dc_pf` returns Boolean `true`/`false` while `solve_dc_pf` returns MOI enum `OPTIMAL`. Code written for one API cannot be reused for the other without branching ([expressiveness api-friction](observations/expressiveness_api-friction.md))
- **Dual sign convention flip:** PowerModels reports negative LMPs (`lam_kcl_r`) while user-assembled JuMP formulations produce positive duals. Absolute values match but sign requires awareness ([A-11 api-friction](observations/api-friction-expressiveness-A-11_distributed_slack_opf.md))
- **No lightweight contingency toggle:** Each contingency requires `deepcopy(data)` + `br_status=0`. No branch status stack or undo mechanism exists ([A-7 api-friction](observations/api-friction-expressiveness-A-7_contingency_sweep.md))
- **SingularException on islanding:** `compute_dc_pf` throws unhandled `LinearAlgebra.SingularException` when contingencies create islands. Must pre-check with `calc_connected_components()` ([A-7 api-friction](observations/api-friction-expressiveness-A-7_contingency_sweep.md))
- **No native graph API:** Adjacency must be built manually from branch data; `ref` dict arcs only available after model instantiation ([B-2 api-friction](observations/api-friction-extensibility-B-2_graph_access.md))

### Documentation Gaps

- Multi-network framework documentation is explicitly marked "for advanced users" with pointer to source code (GitHub issue #169, open since 2017) ([D-2](accessibility/D-2_documentation_audit.md))
- No documentation on stochastic OPF limitations; discoverable only via GitHub issue #112 (2017) ([A-8 doc-gaps](observations/doc-gaps-expressiveness-A-8_stochastic_timeseries.md))
- No documentation on SCUC, SCED, SCOPF, distributed slack, LMP decomposition, or formulation selection guidance ([D-2](accessibility/D-2_documentation_audit.md))
- Solver requirements per formulation type (e.g., DCPLLPowerModel requires NLP solver) undocumented ([A-10 solver-issues](observations/solver-issues-expressiveness-A-10_lossy_dcopf_lmp.md))

### Solver Ecosystem

- **Ipopt is the most reliable solver** for PowerModels at 10k-bus scale -- handles QP/NLP natively ([C-3](scalability/C-3_dcopf_scale_MEDIUM.md))
- **HiGHS QP struggles at scale:** Times out on 10k-bus DCOPF (300s); cannot solve MIQP at all; QP fails with numerical issues on ACTIVSg2000 ([C-3](scalability/C-3_dcopf_scale_MEDIUM.md), [A-5](expressiveness/A-5_scuc_TINY.md))
- **GLPK/SCIP require cost linearization** -- LP-only solvers need manual removal of quadratic cost terms ([C-7](scalability/C-7_solver_swap_MEDIUM.md))
- **DCPLLPowerModel generates QCQP** despite the "linear loss" name -- incompatible with LP/QP solvers ([A-10 solver-issues](observations/solver-issues-expressiveness-A-10_lossy_dcopf_lmp.md))

### Architecture Quality

- **Two-level API is exemplary:** `instantiate_model` / `optimize_model!` cleanly separates model construction from solving, enabling arbitrary JuMP constraint injection without source patching ([B-1 arch-quality](observations/arch-quality-extensibility-B-1_custom_constraints.md))
- **Dict-based data model is simple and effective:** Plain Julia Dict enables in-memory modification, `deepcopy` cloning, and direct field access. No ORM or schema overhead ([B-3 arch-quality](observations/arch-quality-extensibility-B-3_contingency_loop.md))
- **Type-parameterized formulations:** `DCPPowerModel`, `ACPPowerModel`, `SOCWRPowerModel` etc. use Julia's type system for compile-time formulation dispatch -- elegant and extensible ([B-6](extensibility/B-6_code_architecture.md))
- **4-layer architecture:** IO (parsers) / Data Model (dict + ref) / Formulation (type-dispatched constraints) / Solver (JuMP/MOI). Clean separation of concerns ([B-6](extensibility/B-6_code_architecture.md))

---

## 5. Items Requiring Human Spot-Check

- [ ] **A-5/A-6 SMALL fail classification** -- Failures are solver timeouts (HiGHS MIP), not PowerModels API limitations. Consider whether a commercial solver (Gurobi) would change the SCUC/SCED grade.
- [ ] **A-8 blocking fail vs B-4 pass** -- Stochastic OPF is a blocking fail (no native scenario indexing), but the scenario wrapping loop (B-4) passes cleanly. The distinction rests on whether "the tool's optimization formulation is aware of multiple scenarios simultaneously" -- confirm this interpretation holds.
- [ ] **A-7/C-5 MEDIUM fail classification** -- Contingency sweep failures at MEDIUM are due to combinatorial explosion, not tool API gaps. The TINY test demonstrates full expressiveness. Confirm that scale-dependent combinatorial infeasibility is correctly scored as a fail.
- [ ] **A-9 SMALL qualified pass** -- Manual SCOPF assembly used only 20 of 3,206 possible contingencies. Confirm this satisfies the protocol requirement for SMALL (50 monitored branches).
- [ ] **A-10 solver swap** -- DCPLLPowerModel requires Ipopt (NLP) instead of protocol-specified HiGHS. Confirm the Ipopt fallback is acceptable for a qualified_pass.
- [ ] **A-11 LMP identity** -- Distributed slack LMPs are identical to single-slack on ACTIVSg2000 because no congestion exists. This is physically correct but means the mechanism is not differentially validated at SMALL scale.
- [ ] **C-2 ACPF fail** -- NLsolve convergence failure at 10k-bus. PowerModels does not expose NLsolve configuration. Confirm this is a tool limitation (not a test case issue -- ACTIVSg10k should have a solvable AC power flow).
- [ ] **C-7 qualified pass** -- Solver swap is trivially one-line, but HiGHS QP times out and GLPK/SCIP require cost linearization. Is the qualification appropriate or should this be a full pass (since the swap mechanism itself works)?
- [ ] **E-3 bus factor** -- ccoffrin (82.4%) is the lifetime top contributor, but odow has 17 of 20 recent human commits. Should the informal maintainer transition mitigate the fail classification?
- [ ] **F-3 GLPK/SCIP removability** -- Confirm that removing GLPK (GPL-3.0) and SCIP (ZIB Academic) from Project.toml does not break any PowerModels functionality.
- [ ] **Maturity C+ grade** -- This is the lowest passing grade for gate criteria. Confirm the tension between strong CI/releases (E-1, E-6 pass) and bus factor / no operational adoption (E-3, E-7 fail) warrants C+ rather than B- or C.
- [ ] **All 21 qualified_pass results** -- Each qualified pass involves judgment on whether the qualification is substantial enough to affect the criterion grade. Spot-check the qualifications listed in the evidence tables above.

---

## 6. Methodology Notes

- **Scale cap:** MEDIUM (ACTIVSg 10,000-bus). Applied because PowerModels' NLsolve-based ACPF does not converge at 10k-bus and SCUC/SCOPF are infeasible at SMALL/MEDIUM with open-source solvers.
- **Tests skipped:** C-5 (contingency sweep MEDIUM) and C-8 (SCOPF MEDIUM) were not executed due to expected combinatorial/size infeasibility; documented as expected-timeout fails. A-6 SMALL was blocked by A-5 SMALL failure. A-8 SMALL was not re-run (same architectural limitation as TINY).
- **Solver versions:** HiGHS v1.13.1 (via HiGHS.jl v1.12.2), Ipopt (via Ipopt.jl v1.14.1, Ipopt_jll v300.1400.1901), GLPK v1.2.1, SCIP v0.11.6, NLsolve v4.5.1
- **Tool version:** PowerModels.jl v0.21.5 (released 2025-08-12)
- **Julia version:** 1.10.10
- **Devcontainer environment:** Ubuntu 24.04, custom Dockerfile with pre-populated Julia depot at `/opt/julia-depot/`
- **Protocol:** v4 with 57 test IDs producing 76 result files across all tiers
