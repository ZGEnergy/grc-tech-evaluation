# Synthesis Report — PowerSimulations.jl

**Tool version:** v0.30.2 (ecosystem: PowerSystems.jl v4.6.2, PowerFlows.jl v0.9.0, PowerNetworkMatrices.jl v0.12.1)
**Protocol version:** v10
**Evaluation date:** 2026-03-14
**Scale cap:** MEDIUM

---

## 1. Executive Summary

PowerSimulations.jl is a simulation-oriented optimization framework built on JuMP/MathOptInterface with a cleanly layered multi-package architecture (PowerSystems for data, PowerFlows for power flow, PowerNetworkMatrices for PTDF/LODF, PowerSimulations for OPF/UC/ED). Its core strengths are built-in unit commitment formulations, solver-agnostic design via JuMP, excellent PTDF/LODF matrix computation, and strong institutional backing from NREL/DOE. The supply chain gate passes cleanly (BSD-3-Clause core, removable GLPK GPL-3.0 flag). The most notable weaknesses are two independent expressiveness failures (lossy DCOPF blocked by solver-formulation mismatch, distributed slack absent), fragile workarounds required for SCUC/SCED workflows due to initialization bugs and internal API access, no built-in SCOPF or storage formulations in v0.30.2, significant documentation gaps for LMP extraction and time series semantics, and a bus factor of 1 (jd-lara 70.5% commits, 78% review approvals). Scale cap is MEDIUM; the tool handles 10K-bus DCPF/ACPF cleanly but DCOPF at that scale requires 5 stacked workarounds.

---

## 2. Grade Recommendations

| Criterion | Grade | Confidence | Key Evidence |
|-----------|-------|------------|--------------|
| Problem Expressiveness | B- | High | 6/10 pass/qpass, 2 independent fails (A-10 blocking, A-11 blocking), 4 fragile workarounds |
| Extensibility | A- | High | 8/8 pass/qpass, JuMP model access, machine-precision PTDF, 5-layer architecture |
| Scalability | B- | High | DCPF/ACPF/PTDF scale cleanly to MEDIUM; DCOPF needs 5 workarounds; SCOPF crashes on MEDIUM; C-10 cascaded fail |
| Workforce Accessibility | C+ | Medium | 19s first-solve, 3/10 from docs, 0/10 examples unmodified, median 332 LOC |
| Maturity & Sustainability | B | High | 21 releases/24mo, 1019 commits/12mo, bus factor=1, NREL/DOE backing, no production deployment |
| Supply Chain (Gate) | B+ | High | BSD-3-Clause core, GLPK GPL-3.0 removable, 184 packages, air-gap feasible, all solvers open-source |

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness (Suite A)

#### Strengths

- Native DC and AC power flow via PowerFlows.jl with sub-millisecond solve times after JIT warm-up ([A-1](expressiveness/A-1_dcpf.md), [A-2](expressiveness/A-2_acpf.md))
- Built-in `ThermalStandardUnitCommitment` formulation with binary commitment, ramp, and min up/down constraints ([A-5](expressiveness/A-5_scuc.md))
- DCOPF with differentiated costs produces correct LMPs and binding branch identification ([A-3](expressiveness/A-3_dcopf.md))
- Seamless DCOPF-to-ACPF feasibility workflow via shared System data model ([A-4](expressiveness/A-4_ac_feasibility.md))
- SCOPF achievable via LODF-based manual constraint assembly with 17.7% cost increase over unconstrained OPF ([A-9](expressiveness/A-9_scopf.md))

#### Weaknesses

- Lossy DCOPF (A-10): DCPLLPowerModel exists in PowerModels.jl but uses quadratic constraints unsupported by HiGHS/GLPK/SCIP -- **blocking, no open-source LP solver workaround** ([A-10](expressiveness/A-10_lossy_dcopf_lmp.md))
- Distributed slack (A-11): No formulation exists in PSI or PowerModels -- **blocking, no workaround** ([A-11](expressiveness/A-11_distributed_slack_opf.md))
- No built-in storage formulations in PSI v0.30.2 -- `EnergyReservoirStorage` exists as a data type but PSI has no `construct_device!` method for it ([A-12](expressiveness/A-12_multiperiod_dcopf_storage.md))
- No built-in UC-to-ED handoff -- commitment transfer requires manual JuMP variable fixing ([A-6](expressiveness/A-6_sced.md))
- NR convergence diagnostics (iteration count, residual) not exposed by PowerFlows.jl ([A-2](expressiveness/A-2_acpf.md))

#### Workarounds Required

- `initialize_model=false` + `JuMP.optimize!()` for SCUC/SCED/multi-period solves ([A-5](expressiveness/A-5_scuc.md), [A-6](expressiveness/A-6_sced.md), [A-12](expressiveness/A-12_multiperiod_dcopf_storage.md)) -- **fragile** (internal API access)
- Manual JuMP BESS variables/constraints for storage ([A-12](expressiveness/A-12_multiperiod_dcopf_storage.md)) -- **fragile** (depends on PSI internal constraint naming)
- Manual LODF + JuMP constraint injection for SCOPF ([A-9](expressiveness/A-9_scopf.md)) -- **stable** (public LODF API + standard JuMP)
- Time series boilerplate required for every single-snapshot OPF ([A-3](expressiveness/A-3_dcopf.md)) -- **stable** (architectural design)
- No NR diagnostics from PowerFlows.jl ([A-2](expressiveness/A-2_acpf.md)) -- **stable** (return type design)

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| A-1 | TINY | pass | -- | -- | 0.0006s | 165 |
| A-2 | TINY | qualified_pass | -- | stable (no NR diagnostics) | 0.0007s | 213 |
| A-3 | TINY | pass | -- | stable (time series boilerplate) | 0.077s | 271 |
| A-4 | TINY | pass | -- | -- | 1.493s | 326 |
| A-5 | TINY | qualified_pass | -- | fragile (init bypass + internal API) | 0.797s | 374 |
| A-6 | TINY | qualified_pass | -- | fragile (no UC-ED handoff) | 1.064s | 529 |
| A-9 | TINY | qualified_pass | -- | stable (manual LODF+JuMP SCOPF) | 0.193s | 364 |
| A-10 | TINY | fail | -- | blocking (needs SOCP solver) | -- | 339 |
| A-11 | TINY | fail | -- | blocking (no formulation) | -- | 156 |
| A-12 | TINY | qualified_pass | -- | fragile (manual JuMP storage) | 0.108s | 646 |

**Independent failures: 2 (A-10, A-11). Cascaded failures: 0.**

#### Grade Rationale

Grade: **B-**. The tool passes 8 of 10 expressiveness tests (6 pass, 4 qualified_pass) but has 2 independent blocking failures and 4 tests requiring fragile workarounds that access PSI internal APIs. The B- reflects "multiple workarounds, some fragile" per the grading standard. The independent failures in lossy DCOPF and distributed slack are meaningful capability gaps for a production OPF tool. The fragile SCUC/SCED workarounds (initialization bypass, internal variable extraction) could break on version upgrades without notice.

---

### 3.2 Extensibility (Suite B)

#### Strengths

- Full JuMP model access via `PSI.get_jump_model()` enables arbitrary constraint addition and dual extraction ([B-1](extensibility/B-1_custom_constraints.md))
- Machine-precision PTDF verification (max error 1.15e-14 p.u.) with single-call API ([B-9](extensibility/B-9_ptdf_extraction.md))
- Clean 5-layer package architecture with DAG dependency structure, no circular dependencies ([B-6](extensibility/B-6_code_architecture.md))
- DataFrame-native results enable 2-LOC CSV export with no serialization code ([B-5](extensibility/B-5_interoperability.md))
- Reference bus configurable via `set_bustype!()` API with LMP invariance confirmed to machine precision ([B-8](extensibility/B-8_reference_bus_config.md))
- 20-scenario stochastic wrapping completes in 2.1s total, 0.1s mean per scenario ([B-4](extensibility/B-4_stochastic_timeseries.md))

#### Weaknesses

- No Graphs.jl integration -- BFS/DFS requires manual implementation over adjacency matrix ([B-2](extensibility/B-2_graph_access.md))
- LODF superposition is approximate for M>1 contingencies -- no Woodbury correction available ([B-3](extensibility/B-3_contingency_sweep.md))
- Time series immutability forces full System reconstruction per scenario ([B-4](extensibility/B-4_stochastic_timeseries.md))

#### Workarounds Required

- Manual BFS over `AdjacencyMatrix` for graph traversal ([B-2](extensibility/B-2_graph_access.md)) -- **stable**
- LODF screening pipeline assembled from 3 separate packages for N-M contingency sweep ([B-3](extensibility/B-3_contingency_sweep.md)) -- **stable**
- Full System reconstruction per scenario due to time series immutability ([B-4](extensibility/B-4_stochastic_timeseries.md)) -- **stable**

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| B-1 | TINY | pass | -- | -- | 0.23s | 360 |
| B-2 | TINY | qualified_pass | -- | stable (manual BFS) | 0.14s | 200 |
| B-3 | TINY | qualified_pass | -- | stable (LODF screening) | 0.41s | 369 |
| B-4 | TINY | pass | -- | stable (System reconstruction) | 2.13s | 297 |
| B-5 | TINY | pass | -- | -- | 0.20s | 126 |
| B-6 | N/A | pass | -- | -- | -- | 100 |
| B-8 | TINY | pass | -- | stable (3 single-slack configs) | 0.63s | 226 |
| B-9 | TINY | pass | -- | -- | 0.001s | 220 |

**Independent failures: 0. Cascaded failures: 0.**

#### Grade Rationale

Grade: **A-**. All 8 extensibility tests pass (5 pass, 3 qualified_pass with stable workarounds). JuMP model access is a genuine architectural strength, PTDF computation achieves machine precision, and the 5-layer package architecture is the cleanest among evaluated tools. The A- rather than A reflects the graph traversal gap and time series immutability friction. All workarounds are classified as stable.

---

### 3.3 Scalability (Suite C)

#### Strengths

- DCPF scales to 10K buses in 0.275s with no workarounds ([C-1](scalability/C-1_dcpf_scale.md))
- ACPF converges at 10K buses in 0.638s with DCPF warm-start ([C-2](scalability/C-2_acpf_scale.md))
- AC feasibility passes at 0% relaxation on both SMALL and MEDIUM ([C-5 SMALL](scalability/C-5_ac_feasibility_progressive_SMALL.md), [C-5 MEDIUM](scalability/C-5_ac_feasibility_progressive_MEDIUM.md))
- PTDF matrix computed in 1.6s for 10Kx12.7K matrix ([C-9](scalability/C-9_ptdf_scale.md))
- Solver swap is 1-LOC parameter change across 4 solvers with consistent objectives ([C-7](scalability/C-7_solver_swap.md))

#### Weaknesses

- DCOPF on MEDIUM requires 5 stacked workarounds: init bypass, linear costs, all-generators-available, unbounded branches, no hydro ([C-3](scalability/C-3_dcopf_scale.md))
- SCUC on SMALL: HiGHS solves in 404s but SCIP times out at 600s; requires same init bypass workaround ([C-4](scalability/C-4_scuc_scale.md))
- SCOPF on MEDIUM: HiGHS crashes with OTHER_ERROR on 474K-constraint LP; TIME_LIMIT on SMALL ([C-8](scalability/C-8_scopf_scale.md))
- Distributed slack: cascaded failure from A-11 -- capability does not exist ([C-10](scalability/C-10_distributed_slack_scale.md))

#### Workarounds Required

- 5 stacked workarounds for DCOPF at MEDIUM scale ([C-3](scalability/C-3_dcopf_scale.md)) -- **fragile**
- `initialize_model=false` + `JuMP.optimize!()` for SCUC at SMALL scale ([C-4](scalability/C-4_scuc_scale.md)) -- **fragile**
- Top-50 contingency selection + LODF constraint injection for SCOPF scaling ([C-8](scalability/C-8_scopf_scale.md)) -- **fragile** (solver crash on MEDIUM)
- Same 5 C-3 workarounds inherited by C-7 solver swap ([C-7](scalability/C-7_solver_swap.md)) -- **fragile**

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| C-1 | MEDIUM | pass | -- | -- | 0.275s | 188 |
| C-2 | MEDIUM | pass | -- | -- | 0.638s | 222 |
| C-3 | MEDIUM | qualified_pass | -- | fragile (5 stacked) | 11.3s HiGHS / 50.7s GLPK | 398 |
| C-4 | SMALL | qualified_pass | -- | fragile (init bypass) | 404s HiGHS / 607s SCIP | 401 |
| C-5 | SMALL | pass | -- | -- | 0.74s | 257 |
| C-5 | MEDIUM | pass | -- | -- | 1.57s | 266 |
| C-7 | MEDIUM | pass | -- | fragile (inherited C-3) | 9.7-50.7s | 370 |
| C-8 | SMALL/MEDIUM | qualified_pass | -- | fragile (solver crash on MEDIUM) | 602s SMALL / 449s MEDIUM | 412 |
| C-9 | MEDIUM | pass | -- | -- | 1.618s | 228 |
| C-10 | MEDIUM | fail | A-11 | blocking | -- | 44 |

**Independent failures: 0. Cascaded failures: 1 (C-10 from A-11).**

#### Grade Rationale

Grade: **B-**. Power flow and PTDF scale cleanly to MEDIUM with no workarounds. However, optimization at scale (DCOPF, SCUC, SCOPF) requires multiple fragile workarounds or hits solver limits. The 5-workaround stack for C-3 DCOPF and the solver crash on C-8 MEDIUM are significant scalability concerns. The B- reflects "multiple workarounds, some fragile" with one cascaded failure.

---

### 3.4 Workforce Accessibility (Suite D)

#### Strengths

- Infeasibility reporting is best-in-class: automatic model serialization to JSON for debugging ([D-4](accessibility/D-4_error_quality.md))
- Julia's type system catches structurally invalid states early (wrong cost type, isolated bus with connected branch) ([D-4](accessibility/D-4_error_quality.md))
- DCPF power flow (A-1 equivalent) is achievable in ~30 lines minimum ([D-5](accessibility/D-5_code_volume.md))

#### Weaknesses

- 19s time-to-first-solve from warm depot due to Julia JIT compilation ([D-1](accessibility/D-1_install_to_first_solve.md))
- Only 3/10 Suite A tests achievable from official documentation alone; critical gaps in dual unit conversion, time series multiplier semantics, and `initialize_model=false` workaround ([D-2](accessibility/D-2_documentation_audit.md))
- 0/10 official examples run unmodified -- all require `PowerSystemCaseBuilder` external package ([D-3](accessibility/D-3_example_verification.md))
- Median 332 LOC per Suite A test -- ~6x more than equivalent PyPSA/pandapower ([D-5](accessibility/D-5_code_volume.md))
- Zero-cost generators silently produce OPTIMAL with meaningless results ([D-4](accessibility/D-4_error_quality.md))

#### Grade Rationale

Grade: **C+**. The 0/10 example pass rate, 3/10 doc-achievable tests, high code volume, and JIT startup penalty create a steep learning curve. The Julia ecosystem imposes inherent accessibility costs (compilation, REPL-oriented workflow). Documentation gaps around LMP units and initialization workarounds could cause silent correctness errors. The C+ reflects "significant gaps" -- the lowest reasonable passing grade for this criterion.

---

### 3.5 Maturity & Sustainability (Suite E)

#### Strengths

- 21 releases in 24 months with most recent 18 days ago -- strong release cadence ([E-1](maturity/E-1_release_cadence.md))
- 1,019 commits in 12 months from 12 human contributors -- actively developed ([E-2](maturity/E-2_commit_activity.md))
- NREL/DOE institutional backing with federal appropriations -- strongest funding model among evaluated tools ([E-4](maturity/E-4_funding_model.md))
- Median 19.8-day time-to-close on issues with same-day fixes for critical bugs ([E-5](maturity/E-5_issue_tracker_health.md))
- 78% test coverage, 8 CI workflows including cross-package testing and performance regression ([E-6](maturity/E-6_ci_test_coverage.md))

#### Weaknesses

- Bus factor = 1: jd-lara accounts for 70.5% of all-time commits and 78% of review approvals ([E-3](maturity/E-3_contributor_concentration.md))
- No confirmed utility, ISO, or commercial production deployment ([E-7](maturity/E-7_operational_adoption.md))
- Pre-1.0 (v0.x) with no API stability guarantees; 4 patch releases for v0.32 in 10 days suggests instability at minor version boundaries ([E-1](maturity/E-1_release_cadence.md))

#### Grade Rationale

Grade: **B**. Strong development activity, institutional backing, and CI infrastructure earn B+ territory, but the bus factor of 1 and absence of production deployments outside NREL pull the grade down. The project is clearly institutionally supported but has not demonstrated the operational maturity that would justify B+. Meets the B standard: "good development health with notable risk factors."

---

### 3.6 Supply Chain — Gate (Suite F)

#### Strengths

- BSD-3-Clause license on all 5 core Sienna packages -- fully permissive ([F-1](supply_chain/F-1_core_license.md))
- All 4 solver binaries built from source via Yggdrasil with pinned commits and SHA-256 hashes ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- Full execution path from API call to solver invocation is inspectable Julia source except solver engines ([F-5](supply_chain/F-5_code_inspectability.md))
- Air-gap installation feasible via depot copy + `JULIA_PKG_OFFLINE=true` ([F-7](supply_chain/F-7_airgap_installability.md))
- All core use cases work on open-source solvers; no commercial solver required ([F-8](supply_chain/F-8_solver_dependency_assessment.md))

#### Weaknesses

- GLPK GPL-3.0 present in dependency tree -- **removable** by switching to HiGHS ([F-3](supply_chain/F-3_dependency_license_audit.md))
- 184 total packages in dependency tree (169 transitive) -- large surface area ([F-2](supply_chain/F-2_dependency_tree.md))
- No GPG/Sigstore signatures on packages; relies on git-tree-sha1 and SHA-256 artifact hashes ([F-6](supply_chain/F-6_distribution_integrity.md))
- Getting-started tutorials use mutable URLs, unversioned imports, and external data downloads ([F-9](supply_chain/F-9_getting_started_integrity.md))

#### Grade Rationale

Grade: **B+**. The core license is clean, all compiled components are source-available and reproducibly built, and air-gap deployment is feasible. The GLPK GPL-3.0 flag is a known removable risk, not a blocker. The 184-package dependency tree is large but standard for Julia projects with solver bindings. The B+ rather than A reflects the dependency count, lack of cryptographic signatures, and tutorial integrity gaps.

---

## 3b. FNM Ingestion Findings (Suite G)

### Data Model Fidelity

G-FNM-1 **failed**: PowerSystems.jl v4.6.2 cannot parse PSS/E RAW v31 files -- the PTI parser lacks fixed-width column support for pre-v33 formats. The parser fails at line 1 of the CASE IDENTIFICATION section. G-FNM-2 is **blocked** by G-FNM-1 (skip). The MATPOWER fallback path loaded the ~28,000-bus main island successfully with correct component type differentiation (Line vs Transformer2W vs TapTransformer). 100% DCPF-critical coverage was **not assessed** via the native PSS/E path.

**Impact on Expressiveness:** The PSS/E v31 parse failure is additive negative evidence. It weakens the tool's data ingestion capability but does not change the Expressiveness grade boundary (the A-10/A-11 failures are more determinative).

### Power Flow Verification

G-FNM-3 **failed**: Bus angle gate fails (13.2% passing vs 95% required). Branch flow gate passes (96.5% passing vs 90% required). The failure is attributable to a formulation difference: PowerFlows.jl uses a simplified B-matrix (`b = -1/x`) that ignores transformer tap ratios, while the MATPOWER reference uses the full B-matrix. With 2,340 off-nominal tap transformers in the network, this produces systematic angle deviations (mean 2.66 deg). This is a `formulation-difference`, not a tool bug, but it represents a fidelity gap on real-world networks.

G-FNM-4 is **informational**: ACPF failed to converge at all three relaxation levels (0%, 10%, 20%) on the ~28,000-bus FNM. This is consistent with expected behavior for large-scale NR without specialized initialization heuristics. The solver does not expose convergence residual, limiting root-cause analysis.

**Impact on Expressiveness:** The simplified B-matrix formulation difference weakens DCPF fidelity on networks with off-nominal tap transformers. This is moderate negative evidence.

**Impact on Scalability:** ACPF non-convergence at 28K buses is additive evidence of scale limitations, though the MEDIUM (10K) tests passed.

### Supplemental Data Representability

G-FNM-5 is **informational**: PowerSimulations.jl achieves the highest native coverage (50% N / 30% E / 20% X across 44 fields in 7 CSVs). Differentiators include first-class `Contingency` type hierarchy (83% native in CONTINGENCY.csv) and unique `TransmissionInterface` type (60% native). Trading hubs (75% external) and outage schedules (50% external) are the main gaps.

**Impact on Extensibility:** The `ext::Dict{String,Any}` mechanism on all components plus native contingency and interface types are positive evidence supporting the A- grade.

---

## 4. Cross-Cutting Observations

### API Friction Patterns

- **Time series boilerplate**: PSI requires deterministic time series data even for single-snapshot OPF -- adds ~10-15 lines per test. The time series value is a multiplier on `max_active_power`, which is undocumented (A-3, A-5, A-12, B-4).
- **Initialization failures**: PSI's built-in initialization model fails with HiGHS on multiple configurations (TINY SCUC, SMALL SCUC, multi-period models). The `initialize_model=false` + `JuMP.optimize!()` workaround is required for most optimization tests (A-5, A-6, A-12, C-3, C-4, C-8).
- **Result extraction breakage**: Bypassing `solve!()` breaks PSI's internal state tracking, forcing result extraction through internal APIs (`PSI.get_variables()`) rather than the public `OptimizationProblemResults` interface (A-5, A-6).
- **DC/AC result type inconsistency**: `DCPowerFlow()` returns `Dict{Union{Char,String}, Dict{String, DataFrame}}` (nested under period key) while `ACPowerFlow()` returns `Dict{String, DataFrame}` (flat) -- requires defensive coding (A-1, A-2, C-5).
- **Dual unit mismatch**: `read_variable()` returns MW but `read_dual()` returns per-unit-based values requiring manual division by `base_power` and negation -- undocumented (A-3).

### Documentation Gaps

- No documentation of dual value unit conversion to $/MWh (most impactful gap -- produces 100x wrong LMPs)
- No documentation of time series multiplier semantics
- No minimal "load MATPOWER + solve" example (tutorials require PowerSystemCaseBuilder)
- `initialize_model=false` workaround not documented despite being necessary for HiGHS
- Storage formulation absence (PSY has the type, PSI has no formulation) is silent
- PowerFlows.jl DC output claims MW but delivers per-unit -- documentation inconsistency

### Solver Ecosystem

- HiGHS is the best-performing open-source solver in this stack: 11.5s DCOPF on 10K buses, 404s SCUC on 2K buses
- HiGHS cannot solve MIQP or quadratic constraints (blocks A-10 DCPLLPowerModel and forces linear costs for SCUC)
- SCIP times out on 2K-bus SCUC within 600s
- GLPK lacks QP support entirely
- Ipopt is surprisingly fastest for LP at 10K scale (9.7s vs HiGHS 11.5s)
- Solver swap is a 1-parameter change via JuMP abstraction

### Architecture Quality

- 5-layer package architecture (data -> matrices -> flows -> optimization -> results) with clean DAG dependency structure is the strongest separation of concerns among evaluated tools (B-6)
- Julia's multiple dispatch provides compile-time-safe formulation selection -- no string-based configuration
- DataFrame-native results eliminate impedance mismatch between tool internals and analysis workflows
- The `ext::Dict{String,Any}` field on all components provides a clean extension mechanism for supplemental data

### FNM Data Model

- PSS/E v31 parser failure is a blocking gap for direct FNM ingestion
- MATPOWER fallback loses PSS/E-specific data (switched shunt steps, owner/zone assignments)
- Simplified B-matrix in PowerFlows.jl produces systematic DCPF angle deviations on networks with off-nominal tap transformers
- PowerFlows.jl DCPF incorrectly reports output units as MW when they are actually per-unit

---

## 5. Items Requiring Human Spot-Check

- [ ] **A-2 qualified_pass** -- PowerFlows.jl does not expose NR iteration count or convergence residual. Verify whether this is acceptable given that voltage profiles confirm genuine convergence.
- [ ] **A-5 qualified_pass (fragile)** -- SCUC works correctly but requires `initialize_model=false` + internal API extraction. Assess whether the initialization failure is a HiGHS-specific bug or a fundamental PSI issue (would GLPK work for initialization?).
- [ ] **A-6 qualified_pass (fragile)** -- UC-to-ED handoff requires manual JuMP variable fixing. Assess whether PSI's `SimulationSequence` + `FixValueFeedforward` API could replace this workaround.
- [ ] **A-9 qualified_pass (stable vs fragile boundary)** -- SCOPF uses `PSI.get_variables()` (internal) but LODF and JuMP APIs are public. The stable classification hinges on whether `get_jump_model()` is considered public API in practice.
- [ ] **A-12 qualified_pass (fragile)** -- Manual JuMP BESS injection. Verify whether PSI v0.31+ adds native storage formulations that would eliminate this workaround.
- [ ] **C-3 qualified_pass (fragile)** -- 5 stacked workarounds for 10K DCOPF. Assess whether `StaticBranchUnbounded` (removing flow limits) invalidates the DCOPF result for practical purposes.
- [ ] **C-8 qualified_pass (fragile)** -- HiGHS crashes on MEDIUM SCOPF with OTHER_ERROR. Verify whether multi-threaded HiGHS or a different solver (SCIP, commercial) would resolve this.
- [ ] **F-3 GLPK GPL-3.0** -- Confirm that removing GLPK from Project.toml eliminates all GPL exposure. Verify no transitive path pulls GLPK back in.
- [ ] **G-FNM-3 formulation difference** -- Simplified B-matrix ignores tap ratios. Assess whether this is version-specific (v0.30.2) or architectural in PowerNetworkMatrices.jl.
- [ ] **Accessibility C+ grade** -- This is the lowest passing grade. Verify whether the 0/10 example pass rate and 3/10 doc coverage justify C+ rather than C.

---

## 6. Methodology Notes

- **Scale cap:** MEDIUM (ACTIVSg 10k, 10,000 buses). Gate tests passed on all three tiers (TINY/SMALL/MEDIUM).
- **FNM status:** Suite G executed (FNM_PATH set). PSS/E ingestion failed; MATPOWER fallback used for G-FNM-3/4/5.
- **Tests skipped:** None.
- **Solver versions:** HiGHS 1.21.1 (JLL 1.13.1), Ipopt 1.14.1 (JLL 3.14.19), GLPK 1.2.1 (JLL 5.0.1), SCIP 0.12.8 (JLL 10.0.0).
- **Tool version:** PowerSimulations.jl v0.30.2 (latest v0.33.1; 3 minor versions behind). Companion packages: PowerSystems.jl v4.6.2, PowerFlows.jl v0.9.0, PowerNetworkMatrices.jl v0.12.1, InfrastructureSystems.jl v2.6.0.
- **Protocol version:** v10 for all suites.
- **Devcontainer environment:** Ubuntu 24.04 + Julia 1.10 + Python 3.12 + Octave.

### Phase 2 Readiness Summary

| Item | Status | Notes |
|------|--------|-------|
| P2-1: PSS/E RAW parsing | v33/v35 only; v31 needs 3-6 weeks effort | Fixed-width tokenizer absent |
| P2-2: Piecewise-linear costs | Fully supported (SOS2) | All 9 thermal formulations, all MIP solvers |
| P2-3: Commitment injection | Achievable; 5/9 ops need internal APIs | 2-3 weeks for robust production pipeline |
