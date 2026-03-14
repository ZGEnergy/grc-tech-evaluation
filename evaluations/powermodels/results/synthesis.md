# powermodels -- Phase 1 Evaluation Synthesis

## 1. Executive Summary

PowerModels.jl v0.21.5 is a mature, LANL-backed Julia library for steady-state power network
optimization built on JuMP/MathOptInterface. Its primary strength is a clean four-layer
extensible architecture with first-class DCPF, DC OPF, PTDF extraction, and multi-period
multi-network formulations that scale reliably to 10,000-bus MEDIUM networks. The supply
chain is permissive (BSD 3-Clause/MIT) with no binary blobs and air-gap installability
confirmed -- the gate criterion passes at A-. Three hard capability boundaries depress the
expressiveness grade: no native unit commitment (SCUC), no distributed slack OPF, and no
stochastic scenario formulation. ACPF fails at MEDIUM scale (both NLsolve and Ipopt diverge
on 10k-bus networks), though it converges reliably at SMALL (2,000-bus). FNM ingestion
required a MATPOWER fallback (PSS/E v31 parser crashes on the header), and the DCPF
verification against the FNM reference failed due to DCPPowerModel's simplified B-matrix
ignoring transformer taps. Scale cap is MEDIUM (all gate tests passed).

---

## 2. Grade Recommendations Table

| Criterion | Grade | Confidence | Key Evidence |
|-----------|-------|------------|--------------|
| Problem Expressiveness | B- | High | Strong DC OPF/SCOPF/storage/lossy OPF; SCUC, stochastic, distributed slack all blocking fails; ACPF fails at MEDIUM; FNM DCPF verification fails |
| Extensibility | A- | High | Two-level API clean constraint injection; PTDF first-class; 4-layer dispatch architecture; contingency sweep scales; graph access stable workaround; supplemental CSV 39% native |
| Scalability | B- | High | DCPF/DC OPF scale to MEDIUM; ACPF fails at MEDIUM; SCOPF 595s/1 iteration at MEDIUM; SCUC 15 min at SMALL with SCIP; C-2/C-5 MEDIUM/C-10 blocked |
| Workforce Accessibility | B- | Medium | Clean install; Julia JIT tax; branch flow post-processing gap pervasive; doc coverage partial; error quality mixed |
| Maturity & Sustainability | B | High | 5a: B+ (LANL/DOE backing, 94% coverage, 5 releases/24mo, PGLIB reference); 5b: C+ (82.9% single contributor, bus factor 1, 100% reviewer concentration) |
| Supply Chain (Gate) | A- | High | BSD 3-Clause; pure Julia; air-gap installable; SCIP ZIB Academic is optional; all core use cases on permissive-licensed solvers |

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness

#### Strengths

- Native DCPF via direct B-matrix solve: TINY 0.003s ([A-1](expressiveness/A-1_dcpf_TINY.md)), MEDIUM 10k-bus 1.67s including parse ([C-1](scalability/C-1_dcpf_scale_MEDIUM.md))
- DC OPF with LMP extraction via `lam_kcl_r` duals: clean pass at TINY ([A-3](expressiveness/A-3_dcopf_TINY.md), HiGHS 0.007s, $282/MWh LMP spread with 70% derating). MEDIUM 6.34s HiGHS ([C-3](scalability/C-3_dcopf_scale_MEDIUM.md))
- ACPF at TINY: converged with flat start, 100% non-flat PQ bus voltages ([A-2](expressiveness/A-2_acpf_TINY.md)). At SMALL: converges in 0.231s with DC warm-start ([C-5 SMALL](scalability/C-5_ac_feasibility_relaxation_SMALL.md))
- AC feasibility check (DC OPF then ACPF in same model context): pass, correctly identifies 4 thermal violations from reactive power flows ([A-4](expressiveness/A-4_ac_feasibility_check_TINY.md))
- SCOPF via iterative Benders cutting-plane using documented two-level API: qualified pass at TINY ([A-9](expressiveness/A-9_scopf_TINY.md)), mechanism fully demonstrated with PTDF/LODF computation and JuMP constraint injection
- Lossy DC OPF with LMP decomposition: qualified pass ([A-10](expressiveness/A-10_lossy_dcopf_lmp_decomposition_TINY.md)). DCPLLPowerModel with Ipopt produces energy/congestion/loss components; all 4 consistency checks pass (losses 0.7%, lossy objective exceeds lossless by $7,132/h)
- Multi-period DCOPF with BESS: pass ([A-12](expressiveness/A-12_multiperiod_dcopf_storage_TINY.md)). Cyclic SoC, BESS arbitrage confirmed (charge $45/MWh, discharge $75/MWh), 24/24 hours congested
- SCED (ED-only with ramp constraints): qualified pass ([A-6](expressiveness/A-6_sced_TINY.md)). 24-period multi-network LP via `replicate` + manual ramp constraints, 0 ramp violations
- SCUC user-assembled JuMP MILP: qualified pass with blocking workaround ([A-5](expressiveness/A-5_scuc_TINY.md)). ~250 LOC custom MILP achieves 3 generators cycling, MIP gap 0.004%. Demonstrates JuMP foundation viability but no native API

#### Weaknesses

- **SCUC (A-5):** Blocking workaround. No binary commitment variables, no min up/down constraints, no startup costs in PowerModels. Entire ~250-line MILP assembled from scratch using JuMP ([A-5](expressiveness/A-5_scuc_TINY.md))
- **Distributed slack OPF (A-11):** Fail with blocking workaround. No native formulation; ~150 lines of custom PTDF-based JuMP OPF required. All three API paths attempted and confirmed absent ([A-11](expressiveness/A-11_distributed_slack_opf_TINY.md))
- **ACPF at MEDIUM (C-2):** Independent fail. Both NLsolve (v9: 581s, no convergence) and Ipopt (v10: MUMPS memory exhaustion at iteration 14, inf_du 7.58e+23) diverge on 10k-bus network ([C-2](scalability/C-2_acpf_scale_MEDIUM.md)). Convergence boundary lies between 2,000 and 10,000 buses
- **FNM DCPF verification (G-FNM-3):** Fail. DCPPowerModel's simplified B-matrix ignores transformer tap ratios. 97.6% of buses fail angle tolerance, mean deviation 5.1 degrees. Formulation difference, not data issue ([G-FNM-3](fnm_ingestion/G-FNM-3_dcpf_verification.md))
- **NR convergence diagnostics absent:** `compute_ac_pf` returns only Bool termination status; no iteration count, no residual exposed

#### Workarounds Required

- Branch flows from `compute_dc_pf`/`compute_ac_pf` require manual post-processing via DC formula or `calc_branch_flow_ac` -- **stable**
- DCPLLPowerModel requires Ipopt (not HiGHS) due to quadratic constraints -- **stable**
- SCIP required for multi-period storage OPF (MIQP with ZeroOne constraints) -- **stable**
- Cyclic SoC requires manual `@constraint(pm.model, se[T] == energy_initial)` -- **stable**
- Two-phase LMP extraction for MIQP (SCIP solves integer, HiGHS re-solves LP for duals) -- **stable**
- A-6 SCED bypasses UC stage (all units assumed committed) -- **stable** scope reduction

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| A-1 DCPF | TINY | qualified_pass | -- | stable (branch flows) | 0.003s | 250 |
| A-2 ACPF | TINY | qualified_pass | -- | stable (branch flows, no NR diag) | 0.005s | 346 |
| A-3 DC OPF | TINY | pass | -- | -- | 0.007s | 354 |
| A-4 AC feasibility | TINY | pass | -- | stable (branch flows) | 2.517s | 155 |
| A-5 SCUC | TINY | qualified_pass | -- | blocking | 1.466s | 250 |
| A-6 SCED | TINY | qualified_pass | -- | stable | 1.81s | 240 |
| A-9 SCOPF | TINY | qualified_pass | -- | stable | 3.882s | 420 |
| A-10 Lossy DCOPF | TINY | qualified_pass | -- | stable (Ipopt) | 3.28s | 260 |
| A-11 Dist. slack | TINY | **fail** | -- | blocking | 2.29s | 160 |
| A-12 Multi-period+BESS | TINY | pass | -- | stable (3 workarounds) | 5.81s | 310 |

**Independent fails:** A-11 (distributed slack -- blocking, no API path exists)
**Blocking workarounds producing qualified_pass:** A-5 (SCUC -- entire formulation user-assembled)
**Cascaded:** None in expressiveness suite

#### Grade Rationale

B- reflects a strong DC OPF capability profile (DCPF, DC OPF, SCOPF, lossy OPF, multi-period storage all pass or qualified-pass) offset by one independent blocking fail (distributed slack) and one blocking-workaround qualified pass (SCUC requires ~250 LOC user-assembled MILP). The rubric B- standard states "functional but multiple workarounds needed, some fragile." PowerModels' workarounds are stable rather than fragile, but the SCUC and distributed slack gaps are architectural boundaries -- not non-obvious uses of existing features. ACPF capping at ~2000 buses and the FNM DCPF formulation mismatch (G-FNM-3) provide additional negative evidence. The DC formulations are genuinely strong, placing this above C+, but the missing problem types and AC scale ceiling prevent B.

---

### 3.2 Extensibility

#### Strengths

- Custom constraint injection via documented two-level API: pass ([B-1](extensibility/B-1_custom_constraints_TINY.md)). Pattern: `instantiate_model` -> `var(pm, :p)` -> `@constraint(pm.model, ...)` -> `optimize_model!`. Dual extraction via `JuMP.dual()`. Only 4 lines of constraint code beyond model instantiation
- PTDF extraction as first-class native API: pass ([B-9](extensibility/B-9_ptdf_extraction_TINY.md)). `calc_basic_ptdf_matrix` produces exact results (max error 1.33e-14 pu at TINY, 2.18e-11 at MEDIUM). Phase-shifter handling transparent via `make_basic_network`. Single-row variant `calc_basic_ptdf_row` validated
- Four-layer dispatch architecture with clean separation of concerns: pass ([B-6](extensibility/B-6_code_architecture.md)). Network data / problem formulation / solver interface / results all separated. Julia multiple dispatch is the extension mechanism -- idiomatic and powerful
- N-M contingency sweep: pass ([B-3](extensibility/B-3_contingency_sweep_TINY.md)). 595 contingencies (N-1 through N-3 with graph-distance pruning) in 1.098s using `deepcopy` + `br_status=0`. No model reconstruction per case. 88.7% pruning efficiency
- Stochastic wrapping: pass ([B-4](extensibility/B-4_stochastic_wrapping_TINY.md)). 20 scenarios via `deepcopy` + dict mutation + `solve_dc_opf`, 3.7ms/scenario average. All inputs injected programmatically
- Interoperability: pass ([B-5](extensibility/B-5_interoperability_TINY.md)). Results exported to DataFrames/CSV in 3 lines per component type. Plain `Dict{String,Any}` results enable trivial extraction
- Reference bus configuration: qualified pass ([B-8](extensibility/B-8_reference_bus_config_TINY.md)). Single-slack change is 2 lines of code; dispatch and LMPs invariant. Distributed slack requires ~150 LOC custom PTDF-based OPF
- FNM supplemental CSV representability: 39% native, 18% extension, 43% external ([G-FNM-5](fnm_ingestion/G-FNM-5_supplemental_csv_representability.md)). Strong on thermal ratings (3-tier native); weak on interfaces (0% native) and trading hubs (25% native)

#### Weaknesses

- No native Graphs.jl integration. Graph access requires ~12 lines manual adjacency construction from `data["branch"]` f_bus/t_bus fields ([B-2](extensibility/B-2_graph_access_TINY.md)). Alternative `pm.ref[:bus_arcs]` reduces to ~5 lines post-instantiation
- `build_opf` has empty docstring. Formulation-specific methods in `form/*.jl` have no docstrings. Extending with new formulations requires source code reading
- `make_basic_network` absorbs phase shifts silently, changing the basic network representation. Users must be aware this affects PTDF interpretation on phase-shifter-heavy networks
- Interface definitions (flowgates) are 100% tool-external -- no structural analog in PowerModels for aggregated branch flow monitoring with directional limits

#### Workarounds Required

- Graph adjacency construction: ~12 lines manual BFS from data dict fields ([B-2](extensibility/B-2_graph_access_TINY.md)) -- **stable**
- Distributed slack via custom PTDF-based OPF: ~150 LOC ([B-8](extensibility/B-8_reference_bus_config_TINY.md)) -- **stable**

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| B-1 Custom constraints | TINY | pass | -- | -- | 0.981s | 4 |
| B-2 Graph access | TINY | qualified_pass | -- | stable (~12 LOC) | 0.132s | 12 |
| B-3 Contingency sweep | TINY | pass | -- | -- | 1.098s | 320 |
| B-4 Stochastic wrapping | TINY | pass | -- | -- | 2.436s | 271 |
| B-5 Interoperability | TINY | pass | -- | stable (DataFrames add) | 1.316s | 3 |
| B-6 Architecture audit | N/A | pass | -- | -- | -- | -- |
| B-8 Reference bus config | TINY | qualified_pass | -- | stable (~150 LOC dist. slack) | 3.781s | 334 |
| B-9 PTDF extraction | TINY | pass | -- | -- | 2.373s | 211 |

**0 independent fails, 0 cascaded fails**

#### Grade Rationale

A- reflects an excellent extensibility profile. The two-level API provides clean, documented custom constraint injection with dual extraction. PTDF is a first-class native API with machine-epsilon accuracy. The four-layer dispatch architecture is well-separated and idiomatic Julia. The one minor caveat is the absence of Graphs.jl integration (stable ~12-line workaround) and thin internal docstrings on formulation methods. Meets the A- standard: "strong overall but with one minor caveat that doesn't affect core workflows." The supplemental CSV analysis (39% native) is moderate -- better than some tools on thermal ratings but weak on market-layer concepts. The distributed slack workaround (~150 LOC) is documented under B-8 but its effort level is moderate, not trivial. On balance, the overall extensibility architecture is strong enough for A- given that the core extension hooks (custom constraints, PTDF, contingency loops, stochastic wrapping) all pass cleanly.

---

### 3.3 Scalability

#### Strengths

- DCPF scales to MEDIUM: 10k-bus in 1.67s total (0.21s solve, 1.27s parse) ([C-1](scalability/C-1_dcpf_scale_MEDIUM.md)). 598 MB RSS
- DC OPF scales to MEDIUM with cost linearization: HiGHS LP in 6.34s (3.91s solver), GLPK in 63.2s ([C-3](scalability/C-3_dcopf_scale_MEDIUM.md)). Both produce identical objectives ($2,401,337/h)
- Solver swap requires zero reformulation: one-line optimizer change across HiGHS/GLPK/SCIP/Ipopt ([C-7](scalability/C-7_solver_swap_MEDIUM.md)). SCIP crashes on dual extraction (InfrastructureModels compatibility issue) but solves correctly
- PTDF matrix at MEDIUM: 12706x10000 dense matrix in 2.37s (warm JIT), 969 MB, max error 2.18e-11 pu ([C-9](scalability/C-9_ptdf_scale_MEDIUM.md))
- SCOPF at MEDIUM: iterative Benders, 1 iteration in 595s budget. Base DC OPF 87.6s, 50 contingencies screened, 17 binding, 8 blocks added. ~1 GB RSS ([C-8](scalability/C-8_scopf_scale_MEDIUM.md))
- ACPF converges at SMALL (2,000-bus) in 0.231s with DC warm-start, 0% thermal relaxation needed ([C-5 SMALL](scalability/C-5_ac_feasibility_relaxation_SMALL.md))
- SCUC at SMALL: user-assembled MILP (100K variables, 340K constraints) solved by SCIP in 15 min with 0.20% gap. HiGHS failed to find feasible solution in 30 min ([C-4](scalability/C-4_scuc_scale_SMALL.md))

#### Weaknesses

- **ACPF fails at MEDIUM (C-2):** Both NLsolve and Ipopt diverge on 10k-bus. Ipopt: MUMPS memory exhaustion at iteration 14, dual infeasibility 7.58e+23. `solve_ac_pf` formulation has 0 inequality constraints, making it challenging for interior-point methods ([C-2](scalability/C-2_acpf_scale_MEDIUM.md))
- **AC feasibility fails at MEDIUM (C-5 MEDIUM):** Cascaded from C-2. Same Ipopt divergence pattern. Progressive thermal relaxation has no effect because `solve_ac_pf` has 0 inequality constraints ([C-5 MEDIUM](scalability/C-5_ac_feasibility_relaxation_MEDIUM.md))
- **Distributed slack scale untestable (C-10):** Cascaded from A-11 blocking fail ([C-10](scalability/C-10_distributed_slack_scale_MEDIUM.md))
- SCOPF bottleneck: post-contingency DCPF screening at 8.3s/case inside the Benders loop. Full convergence would exceed memory at MEDIUM scale
- SCUC at SMALL requires ~300 LOC user-assembled MILP; HiGHS cannot find feasible solutions within 30 min on this problem

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time |
|------|---------|--------|------------|------------|------|
| C-1 DCPF | MEDIUM | qualified_pass | -- | stable (branch flows) | 1.67s |
| C-2 ACPF | MEDIUM | **fail** | -- | blocking | killed ~5 min |
| C-3 DC OPF | MEDIUM | qualified_pass | -- | stable (cost linearize) | 72.45s |
| C-4 SCUC | SMALL | qualified_pass | -- | blocking (user MILP) | 2712.72s |
| C-5 AC feasibility | SMALL | pass | -- | stable | 1.442s |
| C-5 AC feasibility | MEDIUM | **fail** | C-2 | blocking | killed ~8 min |
| C-7 Solver swap | MEDIUM | qualified_pass | -- | stable (cost linearize) | 5.88s |
| C-8 SCOPF | MEDIUM | pass | -- | stable | 595.18s |
| C-9 PTDF | MEDIUM | pass | -- | -- | 7.55s |
| C-10 Dist. slack | MEDIUM | **fail** | A-11 | blocking (cascaded) | -- |

**Independent fails:** C-2 (ACPF MEDIUM)
**Cascaded fails:** C-5 MEDIUM (from C-2), C-10 (from A-11)

#### Grade Rationale

B- reflects DC workflows scaling reliably to MEDIUM (DCPF 1.67s, DC OPF 6.34s HiGHS, PTDF 2.37s) while ACPF is hard-capped between 2,000 and 10,000 buses. The ACPF failure at MEDIUM is a significant scalability limitation -- both NLsolve and Ipopt paths diverge. SCUC scales to SMALL (2,000-bus) in 15 min with SCIP but requires user-assembled MILP. SCOPF at MEDIUM demonstrates the scale mechanism but did not converge within the time budget. Meets the B- standard: "functional but multiple workarounds needed" -- DC scale is strong, AC scale is a hard wall, and two tests are blocked by upstream expressiveness fails.

---

### 3.4 Workforce Accessibility

#### Strengths

- Clean install: Julia Pkg workflow, no system libraries beyond Julia artifacts ([D-1](accessibility/D-1_install_to_first_solve.md)). First solve in 2.96s wall-clock (cache warm). Zero-friction for Julia users
- Core OPF fully documented: A-3 (DC OPF + LMPs) is the only test rated "fully documented" ([D-2](accessibility/D-2_documentation_audit.md)). Two-level API well-covered in quickguide
- 7 of 10 getting-started examples run correctly on v0.21.5 ([D-3](accessibility/D-3_example_verification.md)). Two failures share same root cause (PSS/E header edge case)
- Error handling for infeasible OPF: clean `INFEASIBLE`/`INFEASIBLE_POINT` status from JuMP/HiGHS ([D-4](accessibility/D-4_error_quality.md))
- All source is pure readable Julia -- source code reading fills documentation gaps effectively

#### Weaknesses

- **Julia JIT overhead:** 5-15 minute first-install compile time; 5-15s load tax per fresh process. Mitigated by REPL persistence but creates friction in CI/scripted contexts
- **Branch flows not in result dict:** `compute_dc_pf` and `compute_ac_pf` omit `result["solution"]["branch"]`. Manual post-processing required. This is the most pervasive friction pattern across the evaluation
- **API signature discovery issue:** Some online examples show deprecated 3-argument form. Error message mentions `InitializeInfrastructureModel` without pointing at the API mismatch
- **NR convergence diagnostics absent:** `compute_ac_pf` returns only Bool; no iteration count, no residual
- **Silent failure on invalid bus_type:** Setting `bus_type=99` on all buses produces `OTHER_ERROR` with no indication of root cause ([D-4](accessibility/D-4_error_quality.md))
- **Missing cost key produces cryptic KeyError:** `key "model" not found` with deep stack trace; not domain-user-friendly
- **Advanced capabilities undocumented:** SCUC, stochastic OPF, distributed slack, SCOPF LODF patterns all require source code reading or are entirely absent from docs

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| D-1 Install to first solve | qualified_pass | JIT overhead + API sig discovery issue |
| D-2 Documentation audit | qualified_pass | Core OPF documented; branch flow gap; advanced types undocumented |
| D-3 Example verification | qualified_pass | 7/10 pass; 2 fail (PSS/E header); 1 skip |
| D-4 Error quality | qualified_pass | INFEASIBLE OK; missing cost cryptic; invalid bus_type silent |
| D-5 Code volume | informational | Mean 379 NBNCL; 40-80 LOC minimum for native tests; 100-250 for user-assembled |

#### Grade Rationale

B- reflects a clean install and mostly usable documentation qualified by recurring API friction -- especially the branch flow post-processing gap and Julia startup overhead -- that meaningfully increase time-to-productivity. The documentation is well-structured for formulation concepts but weak on solver compatibility matrices, result dict key documentation for `compute_*` variants, and advanced problem types. Meets the B- standard: "functional but with friction that would slow a new user materially."

---

### 3.5 Maturity and Sustainability

#### 5a -- Demonstrated Maturity: B+

**Strengths:**
- LANL/DOE institutional backing via Advanced Network Science Initiative ([E-4](maturity/E-4_funding_model.md)). Not grant-dependent
- 5 releases in 24 months, all semver-compliant with maintained changelog ([E-1](maturity/E-1_release_cadence.md)). Latest v0.21.5 (2025-08-12)
- 93.93% code coverage via Codecov, CI on 3 OS x 2 Julia versions, weekly scheduled runs ([E-6](maturity/E-6_ci_test_coverage.md))
- PGLIB-OPF reference platform role; 500+ academic citations; NREL Sienna ecosystem integration ([E-7](maturity/E-7_operational_adoption.md))
- Issue tracker shows substantive technical engagement: 80% of open issues have maintainer response ([E-5](maturity/E-5_issue_tracker_health.md))

**Weaknesses:**
- 24 commits in last 12 months from 3 human authors -- low volume, maintenance/stabilization mode ([E-2](maturity/E-2_commit_activity.md))
- Median time-to-close ~71.5 days on sampled closed issues; open issue queue has items 500-900 days old with no ETA ([E-5](maturity/E-5_issue_tracker_health.md))
- No commercial ISO/utility deployment evidence -- adoption is national-lab and academic ([E-7](maturity/E-7_operational_adoption.md))

#### 5b -- Sustainability Risk: C+

**Findings:**
- Extreme lifetime commit concentration: 82.9% from @ccoffrin (LANL). Bus factor for core domain knowledge is 1 ([E-3](maturity/E-3_contributor_concentration.md))
- @ccoffrin has 0 direct commits in last 12 months; @odow (JuMP ecosystem) now drives 17 of 24 commits -- maintenance partially transferred but domain expertise is not
- Reviewer concentration: 100% of formal approvals from @odow in 50-PR sample. Informal review model means code oversight is not externally auditable
- DOE/LANL institutional backing provides funding stability (strong positive), but contributor concentration remains high-risk

#### Composite Grade: B

Using the 5a/5b composite matrix: 5a=B+ (high B range) with 5b=C+ (high C range) maps to the B range / C range cell which yields B / B-. Given 5a is solidly in the B+ range and 5b is at the top of C range (strong institutional funding partially offsets contributor concentration), the composite grade is B.

#### Grade Rationale

B reflects strong institutional backing and demonstrated engineering discipline (94% coverage, maintained releases, PGLIB reference role) offset by a bus-factor-of-1 sustainability risk. The 5a maturity signals are genuine and well-evidenced. The 5b contributor concentration (82.9% single author, 100% reviewer concentration) is the primary risk factor. Using the composite matrix, B+ (5a) x C+ (5b) = B.

---

### 3.6 Supply Chain (Gate Criterion)

#### Strengths

- Core license: BSD 3-Clause equivalent (LANL government origin) -- permissive, no copyleft ([F-1](supply_chain/F-1_core_license.md))
- Full dependency tree enumerable: 114 packages, all pinned in Manifest.toml with git-tree-sha1 hashes ([F-2](supply_chain/F-2_dependency_tree.md))
- Pure Julia with no binary blobs or C extensions beyond JLL solver artifacts. Full execution path traceable ([F-5](supply_chain/F-5_code_inspectability.md))
- All compiled components (35 JLL packages) have publicly available source and reproducible Yggdrasil build recipes ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- Distribution integrity via Julia General Registry with content-hash verification ([F-6](supply_chain/F-6_distribution_integrity.md))
- Air-gap installable via Julia depot caching + `Pkg.offline(true)` ([F-7](supply_chain/F-7_air_gap_installability.md))
- HiGHS (MIT) + Ipopt (EPL 2.0) cover all core use cases without commercial solvers ([F-8](supply_chain/F-8_solver_dependency_assessment.md))
- Getting-started docs use `/stable/` URL paths; no mutable download URLs in functional examples ([F-9](supply_chain/F-9_getting_started_artifact_integrity.md))

#### Weaknesses

- **GLPK.jl wrapper is GPL v3 (copyleft):** Optional solver, can be excluded ([F-3](supply_chain/F-3_dependency_license_audit.md))
- **SCIP_jll v0.2.1 wraps SCIP 8.0.0 under ZIB Academic License:** F-8 notes SCIP 8.0 is Apache 2.0, but F-3 classifies the JLL artifact as ZIB Academic. SCIP is optional -- core DC and AC OPF do not require it. Only multi-period storage OPF (A-12) requires SCIP for MIQP
- **JuMP (MPL-2.0) and Ipopt (EPL 2.0)** are weak/file-scoped copyleft -- acceptable for commercial use as libraries
- No GPG signing of packages (not standard Julia practice); integrity assured by content-hash verification

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| F-1 Core license | pass | BSD 3-Clause (LANL) |
| F-2 Dependency tree | pass | 114 packages, all pinned |
| F-3 License audit | qualified_pass | GLPK GPL v3, SCIP ZIB Academic -- both optional |
| F-4 Compiled extensions | pass | All 35 JLL components have public source |
| F-5 Code inspectability | pass | Full call chain traceable, pure Julia to ccall boundary |
| F-6 Distribution integrity | pass | Registry SHA verification |
| F-7 Air-gap installability | pass | Julia depot + offline mode |
| F-8 Solver sufficiency | pass | HiGHS + Ipopt cover all core use cases |
| F-9 Getting-started integrity | qualified_pass | /stable/ links OK; no version pin guidance in examples |

#### Grade Rationale

A- reflects an excellent supply chain posture. The core stack (PowerModels BSD-3 + JuMP MPL-2.0 + Ipopt EPL-2.0 + HiGHS MIT) is clean for commercial deployment. The sole qualification is the SCIP/GLPK licensing flags, both of which attach to optional solver dependencies that can be excluded without losing core functionality. Meets the A- standard: "strong overall but with one minor caveat that doesn't affect core workflows."

---

## 3b. FNM Ingestion Findings (Suite G)

Suite G executed (FNM_PATH set). FNM ingestion used the MATPOWER `.m` fallback because PowerModels' PSS/E v31 RAW parser crashes on the Case Identification header, and no CSV parser exists.

### Data Model Fidelity (G-FNM-1, G-FNM-2)

**G-FNM-1: Qualified pass via MATPOWER fallback** ([G-FNM-1](fnm_ingestion/G-FNM-1_intermediate_ingestion.md)). The MATPOWER fallback file (`fnm_main_island.m`) loaded in 2.97s with correct baseMVA (100), slack bus (29421), and tap ratio handling. Record counts show deficits vs. manifest (bus -8.1%, load -42.7%, gen -0.5%, branch -3.6%) because the fallback is a pre-cleaned main-island subset, not a PowerModels ingestion error. The PSS/E v31 parse failure is documented in P2-1 and estimated at 1-2 days to fix.

**G-FNM-2: Pass** ([G-FNM-2](fnm_ingestion/G-FNM-2_field_coverage_audit.md)). **100% DCPF-critical field coverage** achieved (19/19 fields present). ACPF-critical coverage is 8.0% (19/237) and Informational is 12.6% (11/87). The low ACPF/Informational rates are structural consequences of the MATPOWER PPC format, which flattens transformer data and does not carry record types beyond core five (bus, load, gen, branch, shunt). Key ACPF-critical gaps: ZIP load components, generator IREG, 42 of 44 transformer detailed fields, and entire record types (HVDC, FACTS, switched shunt discrete steps, area interchange).

### Power Flow Verification (G-FNM-3, G-FNM-4)

**G-FNM-3: Fail** ([G-FNM-3](fnm_ingestion/G-FNM-3_dcpf_verification.md)). Bus angle pass rate 2.43% (need >=95%), branch flow pass rate 78.88% (need >=90%). All three hard-fail conditions triggered. Root cause: `DCPPowerModel` uses a simplified B-matrix (`b = -1/x`) that ignores transformer tap ratios. The FNM has 12,501 transformer-connected buses. The MATPOWER reference uses the full B-matrix via `makeBdc()`. This is a formulation difference, not a data issue. `DCMPPowerModel` (full B-matrix) could potentially match the reference but is not accessible through `solve_dc_pf`.

**G-FNM-4: Informational** ([G-FNM-4](fnm_ingestion/G-FNM-4_acpf_convergence.md)). ACPF does not converge on the 27,862-bus FNM at any relaxation level. Ipopt diverges: inf_pr grows to 4.17e6 by iteration 14, MUMPS requires 7 GB memory. The ACPF reference data itself shows divergent values (bus VM up to 379,646 pu), confirming the case is inherently challenging. No gate consequence.

### Supplemental Data Representability (G-FNM-5)

**G-FNM-5: Informational** ([G-FNM-5](fnm_ingestion/G-FNM-5_supplemental_csv_representability.md)). 39% native (17/44 fields), 18% extension (8/44), 43% external (19/44). Strong on thermal ratings (LINE_AND_TRANSFORMER: 60% native with 3-tier rate_a/b/c). Weak on interfaces (0% native -- no flowgate concept), trading hubs (25% native -- market-layer absent), and outages (38% native -- no temporal scheduling).

### FNM Impact on Grades

- **Expressiveness:** G-FNM-3 failure (DCPF formulation mismatch) is additive negative evidence. The simplified B-matrix in DCPPowerModel produces systematically incorrect results on transformer-heavy production networks. This reinforces B-.
- **Extensibility:** G-FNM-5 supplemental CSV analysis (39% native) is moderate. Market-layer concepts (interfaces, hubs) are entirely external. The dict-based extension mechanism provides a simple path for extension-representable fields. No grade change.
- **Scalability:** G-FNM-4 ACPF divergence on 27,862-bus network is consistent with the C-2 MEDIUM finding. No additional information beyond the known ACPF scale ceiling.

---

## 4. Cross-Cutting Observations

### API Friction Patterns

1. **Branch flows absent from compute_* result dicts.** Both `compute_dc_pf` and `compute_ac_pf` omit `result["solution"]["branch"]`. This forces manual post-processing (DC formula or `calc_branch_flow_ac`) in every test involving branch flows. Most pervasive friction point across A-1, A-2, A-4, B-3, C-1. The `solve_*` OPF variants do populate branch flows.

2. **Quadratic costs silently trigger QP at scale.** `solve_dc_opf` with polynomial cost model 2 produces QP without warning. HiGHS handles QP but at higher cost; GLPK rejects QP entirely. Users must diagnose and linearize costs manually. Observed in C-3, C-7.

3. **DCPLLPowerModel requires Ipopt, not HiGHS.** Quadratic constraints in the loss approximation model are rejected by HiGHS with `UnsupportedConstraint`. No guidance in docs on which formulations require which solvers. Observed in A-10.

4. **`baseMVA` returns `Int` not `Float64`.** MATPOWER parser reads `100` as integer. Functions with `::Float64` type annotations fail. Fixed by using `::Real`. Observed in A-6.

5. **SCIP dual extraction crash.** SCIP.jl v0.11.6 does not support `ConstraintDual`. InfrastructureModels unconditionally attempts dual extraction, crashing after SCIP solves correctly. Observed in C-7.

### Documentation Gaps

1. **SCUC, stochastic OPF, and distributed slack absence not called out in docs.** Users must exhaust the problem type list to discover these capabilities are missing. No guidance on implementing them.

2. **`build_opf` empty docstring.** Formulation-specific methods in `form/*.jl` have no docstrings. Extension developers must read source code.

3. **LODF computation for SCOPF undocumented.** The formula deriving LODF from PTDF is not in official docs.

4. **Solver compatibility matrix absent.** No documentation of which formulations (DCPLLPowerModel, build_mn_opf_strg) require which solvers (Ipopt, SCIP).

5. **NR convergence diagnostics gap.** `compute_ac_pf` exposes only Bool status; no iteration count or mismatch residual.

### Solver Ecosystem

1. **HiGHS is the primary solver.** MIT license, reliable at MEDIUM LP scale, correct dual extraction.

2. **Ipopt is the primary NLP solver.** EPL 2.0, handles AC OPF and DCPLLPowerModel. Diverges on MEDIUM ACPF but converges at TINY/SMALL AC OPF.

3. **SCIP required for MIQP (multi-period storage).** ZIB Academic License concern (F-3) vs. Apache 2.0 finding (F-8) -- license version discrepancy between JLL artifact and upstream project. SCIP outperforms HiGHS on MILP (C-4: SCIP finds feasible in 15 min, HiGHS fails in 30 min).

4. **GLPK limited.** Cannot handle quadratic costs (no QP). GPL v3 copyleft. Viable only for pure LP on small-medium networks. Converged on MEDIUM LP in 61.86s (improved from v9 timeout).

### Architecture Quality

1. **Four-layer dispatch architecture** (public API -> model lifecycle -> formulation build -> solver) is clean and consistent. Extension via Julia multiple dispatch is idiomatic.

2. **`deepcopy` vs. in-place patterns.** For contingency loops, `deepcopy(base_data)` is expensive at MEDIUM scale. In-place `br_status` toggle with restore is the performance pattern.

3. **Multi-network `replicate` is first-class** for multi-period analysis. Creates coupled time-step networks; storage SoC constraints cross periods. Not a scenario tree -- no non-anticipativity.

### FNM Data Model

1. **DCPPowerModel simplified B-matrix** ignores transformer tap ratios. On the FNM (12,501 transformer-connected buses), this produces 5.1-degree mean angle deviation from the reference. `DCMPPowerModel` exists but is not accessible through `solve_dc_pf`.

2. **MATPOWER PPC format limitations.** Flattens transformer data, drops switched shunt discrete steps, HVDC, FACTS, area interchange, impedance correction tables. 8.0% ACPF-critical field coverage reflects format limitations, not PowerModels limitations per se.

3. **PSS/E v31 parser bug** is localized to the Case Identification header parsing function. Estimated 1-2 day fix.

---

## 5. Items Requiring Human Spot-Check

- [ ] **A-5 SCUC (qualified_pass, blocking workaround)** -- Entire 250-line MILP is user-assembled. The qualified_pass reflects that the JuMP MILP works correctly (3 generators cycle, 0.004% MIP gap), but PowerModels provides only data parsing. Verify whether "qualified_pass with blocking workaround" is the correct classification vs. "fail" for the expressiveness sub-question
- [ ] **A-9 SCOPF (qualified_pass, stable workaround)** -- Network is N-1 infeasible with Modified Tiny profile. Iterative mechanism demonstrated on individual contingencies. Verify that N-1 infeasibility is acceptable for mechanism verification
- [ ] **A-12 (pass with 3 stable workarounds)** -- SCIP solver switch, cyclic SoC manual constraint, two-phase LMP extraction. Verify whether three simultaneous workarounds should remain "pass" or be reclassified as "qualified_pass"
- [ ] **C-8 SCOPF MEDIUM (pass, 1 iteration, not converged)** -- Only 1 Benders iteration completed within 595s budget. Verify whether a non-converged result qualifies as "pass" vs. "qualified_pass"
- [ ] **B- Expressiveness grade boundary** -- Three architectural gaps (SCUC blocking, stochastic absent, distributed slack fail) vs. strong DC formulation performance. A C+ grade is defensible if those gaps are critical blocking criteria. Confirm weighting
- [ ] **A- vs. B+ Extensibility grade** -- 6 of 8 extensibility tests pass cleanly; B-2 (graph) and B-8 (ref bus) are qualified_pass with stable workarounds. The supplemental CSV analysis shows 43% tool-external fields. Verify whether A- is justified given the interface/hub gaps
- [ ] **F-3 vs. F-8 SCIP license discrepancy** -- F-3 classifies SCIP_jll as ZIB Academic; F-8 reports SCIP 8.0.0 as Apache 2.0. Both reference the same JLL version. Needs definitive resolution
- [ ] **G-FNM-3 DCPF formulation difference** -- DCPPowerModel vs. DCMPPowerModel. Verify whether using `solve_pf(data, DCMPPowerModel, optimizer)` would pass the DCPF verification; this was not tested because the task spec requires `solve_dc_pf`
- [ ] **Maturity 5b: C+ vs. C** -- 82.9% single-contributor concentration, 100% reviewer approval concentration. Strong DOE/LANL funding partially offsets. Verify C+ placement given the extreme concentration metrics

---

## 6. Methodology Notes

- **Scale cap:** MEDIUM. All three gate tests passed (G-1 TINY, G-2 SMALL, G-3 MEDIUM). No scale restriction applied.
- **FNM status:** Suite G executed (FNM_PATH set). G-FNM-1 used MATPOWER fallback (PSS/E v31 parse failure). G-FNM-2 pass (100% DCPF-critical). G-FNM-3 fail (formulation mismatch). G-FNM-4 informational (ACPF diverges). G-FNM-5 informational (39% native supplemental CSV).
- **Tests skipped:** None. All 60 result files produced. A-11 (distributed slack) failed at TINY; C-10 cascaded. No tests were skipped due to environment or configuration issues.
- **Solver versions:** HiGHS 1.21.1 (MIT), Ipopt 1.14.1 (EPL 2.0), GLPK 1.2.1 (GPL v3), SCIP 0.11.6 / SCIP 8.0.0 binary (license disputed between ZIB Academic and Apache 2.0).
- **Tool version evaluated:** PowerModels.jl v0.21.5 (git-tree-sha1: `b8e410e1d827b621e82e7e670967f0efc5845c30`).
- **Protocol version:** v10 for all tests.
- **Skill version:** v1.
- **Devcontainer:** Ubuntu 24.04, Julia 1.10, Python 3.12; container provides solver binaries as Julia JLL artifacts.
- **Timing methodology:** All wall-clock times measured from Julia process after JIT warm-up on case39 (unless noted as "includes JIT"). First-invocation JIT times are reported separately where relevant.
- **MEDIUM preprocessing:** 2,462/12,706 branches (19.4%) had rate_a = Inf/0 in raw ACTIVSg10k; set to 9999 MVA. No zero-reactance branches required correction. 70% branch derating applied on TINY where congestion is required (A-3, A-4, A-10, A-12).
- **Phase 2 readiness findings (informational):** P2-1 ([PSS/E RAW parsing](p2_readiness/P2-1_psse_raw_parsing.md)): partial capability, v33 only, FNM v31 parse fails on line 1 (LOW fix effort). P2-2 ([Piecewise-linear costs](p2_readiness/P2-2_piecewise_linear_costs.md)): native support via `model=1` with lambda-variable LP formulation; convex PWL only, no SOS2. P2-3 ([Commitment injection workflow](p2_readiness/P2-3_commitment_injection_workflow.md)): functional via `gen_status=0` field + `replicate` + `solve_mn_opf`; ~40 LOC basic workflow; ramp/reserve constraints require manual JuMP extension.
