# Synthesis Report -- PowerSimulations.jl (FA714626C0006)

**Tool:** PowerSimulations.jl v0.30.2 (Sienna/NREL ecosystem)
**Protocol Version:** v4
**Evaluation Date:** 2026-03-07
**Scale Cap:** MEDIUM (all gate tests pass through ACTIVSg 10k)

---

## 1. Executive Summary

PowerSimulations.jl is an NREL-backed, Julia-native production simulation framework with strong multi-period optimization capabilities (SCUC, SCED) and excellent separation of concerns across four complementary packages. It passes the supply chain gate with BSD-3 licensing, all open-source solvers, and air-gap installability. Its primary strengths are built-in unit commitment formulations, clean solver abstraction via JuMP, and robust type safety. Its primary weaknesses are the absence of native SCOPF, stochastic optimization, lossy DCOPF, and distributed slack -- combined with mandatory time series boilerplate that creates significant friction for single-period workflows. A unit mismatch between PSI optimization output and PowerSystems.jl component accessors is a notable API deficiency that blocks the DCOPF-to-ACPF pipeline. The ACPF solver (PowerFlows.jl) does not converge on MEDIUM networks, limiting AC analysis to TINY scale.

---

## 2. Grade Recommendations Table

| Criterion | Grade | Confidence | Key Evidence |
|-----------|-------|------------|--------------|
| Problem Expressiveness | B- | High | 7/11 pass or qualified pass; 2 FAIL (stochastic, lossy DCOPF); SCOPF only via manual JuMP injection |
| Extensibility | B+ | High | JuMP model access enables arbitrary constraints; clean architecture; fragile unit-mismatch workaround for ACPF |
| Scalability | B- | Medium | DCPF/PTDF scale to MEDIUM; ACPF FAIL on MEDIUM; SCOPF/distributed slack blocked at scale |
| Workforce Accessibility | C+ | High | Mandatory time series boilerplate; Julia niche language; 4/11 tests achievable from docs alone |
| Maturity & Sustainability | B | Medium | NREL-funded, 22 releases/24mo, 100% CI coverage; but bus-factor risk and limited adoption outside NREL |
| Supply Chain (Gate) | A- | High | BSD-3, all open-source, air-gap installable; GLPK GPL-3 is optional and excludable |

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness

#### Strengths

- Native DC power flow via PowerFlows.jl with clean single-call API ([A-1](expressiveness/A-1_dcpf.md))
- Native AC power flow with Newton-Raphson convergence on TINY ([A-2](expressiveness/A-2_acpf.md))
- Rich built-in SCUC formulations including commitment/startup/shutdown variables, min up/down times, ramp constraints ([A-5](expressiveness/A-5_scuc.md))
- Clean UC/ED separation via formulation selection -- `ThermalStandardUnitCommitment` vs `ThermalBasicDispatch` ([A-6](expressiveness/A-6_sced.md))
- Efficient contingency sweep with in-place branch toggling via `set_available!()`, 2.5ms/case on TINY ([A-7](expressiveness/A-7_contingency.md))
- PTDF and LODF matrices natively accessible via PowerNetworkMatrices.jl ([B-9](extensibility/B-9_ptdf_extraction.md))

#### Weaknesses

- No native stochastic optimization -- `Scenarios` time series type exists in data model but PSI formulations are deterministic-only ([A-8](expressiveness/A-8_stochastic.md))
- No lossy DCOPF -- all DC formulations are lossless; LMP loss component is always zero ([A-10](expressiveness/A-10_lossy_dcopf.md))
- No native SCOPF -- requires manual LODF computation and JuMP constraint injection (~100 LOC) ([A-9](expressiveness/A-9_scopf.md))
- Distributed slack is implicit in PTDFPowerModel but weights are not configurable ([A-11](expressiveness/A-11_distributed_slack.md))
- Unit mismatch between PSI dispatch output and PowerSystems component limits (~100x) blocks DCOPF-to-ACPF pipeline ([A-4](expressiveness/A-4_ac_feasibility.md))
- HiGHS fails on SCUC during initial condition computation; only SCIP works for MIP with UC ([A-5](expressiveness/A-5_scuc.md))

#### Workarounds Required

- Time series boilerplate for all PSI optimization tests (~30 LOC per test) ([A-3](expressiveness/A-3_dcopf.md)) -- **stable**
- UC parameter injection for MATPOWER data (ramp rates, min up/down, Pmin) ([A-5](expressiveness/A-5_scuc.md)) -- **stable** (data limitation, not tool limitation)
- SCOPF via manual LODF + JuMP constraint injection ([A-9](expressiveness/A-9_scopf.md)) -- **stable** (uses `get_jump_model()` and public LODF API)
- Unit scaling for dispatch transfer from PSI to PowerFlows ([A-4](expressiveness/A-4_ac_feasibility.md)) -- **fragile** (undocumented conversion factor)

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | LOC |
|------|---------|--------|------------|------|-----|
| A-1 | TINY | pass | -- | 16.5s | 130 |
| A-2 | TINY | pass | -- | 1.4s | 178 |
| A-3 | TINY | qualified_pass | stable (time series boilerplate) | 70.4s | 297 |
| A-4 | TINY | qualified_pass | stable (unit mismatch) | 84.6s | 264 |
| A-5 | TINY | qualified_pass | stable (UC params, SCIP required) | 158.8s | 430 |
| A-6 | TINY | pass | stable (time series) | 47.7s | 502 |
| A-7 | TINY | pass | stable (manual graph) | 14.7s | 361 |
| A-8 | TINY | **fail** | blocking (no native stochastic) | 47.6s | 348 |
| A-9 | TINY | qualified_pass | stable (JuMP + LODF injection) | 42.2s | 456 |
| A-10 | TINY | **fail** | blocking (no loss formulation) | 47.0s | 299 |
| A-11 | TINY | qualified_pass | stable (implicit PTDF slack) | 47.2s | 452 |

#### Grade Rationale

Grade: **B-**. Two outright FAILs (stochastic A-8, lossy DCOPF A-10) represent meaningful missing capabilities for a power system modeling tool. SCOPF is achievable but only through extensive manual construction. The time series boilerplate is stable but adds substantial friction. Meets the B- standard: "Multiple workarounds, some fragile." The fragile unit mismatch (A-4/B-7) and two blocking gaps prevent a B grade.

---

### 3.2 Extensibility

#### Strengths

- Full JuMP model access via `PSI.get_jump_model()` enables arbitrary constraint/variable injection ([B-1](extensibility/B-1_custom_constraints.md))
- Efficient contingency loop with in-place branch toggling, 0.082s for 46 N-1 contingencies ([B-3](extensibility/B-3_contingency_loop.md))
- Scenario wrapping achievable with programmatic time series injection; sub-second per scenario after JIT warmup ([B-4](extensibility/B-4_stochastic.md))
- Native DataFrame output -- zero-overhead interoperability with Julia data ecosystem ([B-5](extensibility/B-5_interoperability.md))
- Excellent separation of concerns across 4 packages with clean responsibilities ([B-6](extensibility/B-6_code_architecture.md))
- PTDF/LODF matrices directly accessible via public API, verified against DCPF results ([B-9](extensibility/B-9_ptdf_extraction.md))

#### Weaknesses

- No native Graphs.jl integration -- manual adjacency construction required (~32 LOC) ([B-2](extensibility/B-2_graph_access.md))
- AC feasibility workaround is fragile due to undocumented unit mismatch between PSI and PowerFlows ([B-7](extensibility/B-7_ac_feasibility_extension.md))
- Distributed slack weights not configurable -- implicit in PTDF formulation ([B-8](extensibility/B-8_reference_bus_config.md))
- Time series immutable after transform -- must reload System from file per scenario ([B-4](extensibility/B-4_stochastic.md))

#### Workarounds Required

- Manual adjacency graph construction for BFS/graph algorithms ([B-2](extensibility/B-2_graph_access.md)) -- **stable**
- Unit conversion for dispatch transfer between PSI and PowerFlows ([B-7](extensibility/B-7_ac_feasibility_extension.md)) -- **fragile**
- System reload per scenario due to immutable time series ([B-4](extensibility/B-4_stochastic.md)) -- **stable**

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | LOC |
|------|---------|--------|------------|------|-----|
| B-1 | TINY | pass | -- | 89.0s | 328 |
| B-2 | TINY | qualified_pass | stable (manual graph) | 10.9s | 190 |
| B-3 | TINY | pass | -- | 14.1s | 205 |
| B-4 | TINY | pass | stable (reload per scenario) | 47.5s | 369 |
| B-5 | TINY | pass | -- | 103.1s | 112 |
| B-6 | N/A | pass | -- | -- | -- |
| B-7 | TINY | qualified_pass | **fragile** (unit mismatch) | -- | -- |
| B-8 | TINY | qualified_pass | stable (partial distributed) | -- | -- |
| B-9 | TINY | pass | -- | 16.5s | 45 |

#### Grade Rationale

Grade: **B+**. The JuMP model access mechanism is a genuine strength -- it enables SCOPF, custom constraints, and arbitrary extensions without source patching. Architecture is cleanly layered. One meaningful gap: the fragile unit-mismatch workaround for the ACPF pipeline (B-7) and the absence of native graph primitives. Meets the B+ standard: "Mostly strong, one meaningful gap with stable workaround." The fragile B-7 workaround is the primary reason this is B+ rather than A-.

---

### 3.3 Scalability

#### Strengths

- DCPF scales cleanly to MEDIUM (10k buses) in 9.4s ([C-1](scalability/C-1_dcpf_scale.md))
- PTDF matrix computation scales to MEDIUM in 6.44s ([C-9](scalability/C-9_ptdf_scale.md))
- Solver swap requires only parameter change -- no reformulation ([C-7](scalability/C-7_solver_swap.md))
- JIT warmup amortizes well -- subsequent solves are sub-second for TINY problems

#### Weaknesses

- ACPF fails to converge on MEDIUM -- Newton-Raphson lacks robustness features for large networks ([C-2](scalability/C-2_acpf_scale.md))
- SCOPF does not scale to MEDIUM -- no native implementation, manual approach generates millions of constraints ([C-8](scalability/C-8_scopf_scale.md))
- Distributed slack OPF does not scale to MEDIUM -- no native implementation ([C-10](scalability/C-10_distributed_slack_scale.md))
- Several scalability tests lack measured wall-clock times (C-3, C-4, C-5, C-6 provide estimates only)

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | Notes |
|------|---------|--------|------------|------|-------|
| C-1 | MEDIUM | pass | -- | 9.4s | Direct linear solve |
| C-2 | MEDIUM | **fail** | -- | 4.4s | NR diverged |
| C-3 | MEDIUM | qualified_pass | stable | est. <60s | Mixed gen types |
| C-4 | SMALL | qualified_pass | stable | est. >300s | SCIP only, HiGHS fails |
| C-5 | MEDIUM | qualified_pass | stable | est. serial | No parallel DCPF |
| C-6 | SMALL | qualified_pass | stable | est. 10-20min | Serial scenario loop |
| C-7 | MEDIUM | pass | -- | -- | Parameter-only swap |
| C-8 | MEDIUM | **fail** | blocking | -- | No native SCOPF |
| C-9 | MEDIUM | pass | -- | 6.44s | Sparse representation |
| C-10 | MEDIUM | **fail** | blocking | -- | No native distributed slack |

#### Grade Rationale

Grade: **B-**. Three FAIL results at MEDIUM scale (ACPF, SCOPF, distributed slack) represent significant scalability gaps. The DCPF and PTDF scale well, and solver swap is clean. Several tests have only estimated timings. Meets the B- standard: "Multiple workarounds, some fragile." The ACPF convergence failure is particularly impactful since it blocks the AC feasibility workflow at scale. The qualified passes on C-3 through C-6 lack measured evidence, lowering confidence.

---

### 3.4 Workforce Accessibility

#### Strengths

- Clean installation via Julia's package manager with no manual intervention ([D-1](accessibility/D-1_install_to_first_solve.md))
- Strong type safety -- Julia's dispatch system catches many errors at compile/call time ([D-4](accessibility/D-4_error_quality.md))
- Native DataFrame output across the entire ecosystem ([B-5](extensibility/B-5_interoperability.md))
- PowerFlows.jl has a simple, intuitive API for power flow ([A-1](expressiveness/A-1_dcpf.md), [A-2](expressiveness/A-2_acpf.md))

#### Weaknesses

- Only 4 of 11 Suite A tests achievable from documentation alone; 2 required guessing ([D-2](accessibility/D-2_documentation_audit.md))
- MATPOWER single-period workflow undocumented -- most common newcomer use case ([D-2](accessibility/D-2_documentation_audit.md))
- Zero-rate line silently accepted as "no limit" with no warning ([D-4](accessibility/D-4_error_quality.md))
- High code volume: median 255 LOC per test, with ~30 LOC mandatory boilerplate per optimization test ([D-5](accessibility/D-5_code_volume.md))
- Julia language niche limits available workforce ([E-7](maturity/E-7_operational_adoption.md))
- Significant JIT compilation overhead on first invocation (15-60s) ([D-1](accessibility/D-1_install_to_first_solve.md))
- Documentation reorganization effort open since October 2024 with incomplete tasks ([D-3](accessibility/D-3_example_verification.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| D-1 | qualified_pass | Install clean; time series boilerplate is first-solve barrier |
| D-2 | informational | 4/11 tests from docs alone; contingency and SCOPF required guessing |
| D-3 | informational | 7 tutorials across 3 packages; ~20% use case coverage |
| D-4 | qualified_pass | Strong type safety but zero-rate line silent acceptance |
| D-5 | informational | Median 255 LOC; 30 LOC boilerplate overhead per optimization test |

#### Grade Rationale

Grade: **C+**. Significant documentation gaps, high conceptual overhead (multi-period framework paradigm), mandatory boilerplate, and Julia's niche status create substantial barriers for new users. The tool is functional once understood, but the learning curve is steep. Meets the C+ standard: "Significant gaps, but NOT disqualifying." The type safety and clean PowerFlows API prevent a lower grade.

---

### 3.5 Maturity & Sustainability

#### Strengths

- 22 releases in 24 months with strict semver compliance ([E-1](maturity/E-1_release_cadence.md))
- 1,040 commits in 12 months from 21 unique committers ([E-2](maturity/E-2_commit_activity.md))
- NREL/DOE institutional backing with multi-year programmatic funding ([E-4](maturity/E-4_funding_model.md))
- 100% code coverage, 8 CI workflows, cross-package integration testing ([E-6](maturity/E-6_ci_test_coverage.md))
- Comprehensive test suite with 37 test files and 3-platform testing ([E-6](maturity/E-6_ci_test_coverage.md))
- Contributor concentration improving: top contributor dropped from 71% lifetime to 38% recent ([E-3](maturity/E-3_contributor_concentration.md))

#### Weaknesses

- Lifetime bus factor of 1 -- Jose Daniel Lara has 70.7% of all commits ([E-3](maturity/E-3_contributor_concentration.md))
- Limited adoption outside NREL -- 311 GitHub stars, 264 monthly downloads, no confirmed utility/ISO use ([E-7](maturity/E-7_operational_adoption.md))
- Single-institution risk: all significant contributors appear NREL-affiliated ([E-3](maturity/E-3_contributor_concentration.md))
- Pre-1.0 version indicates API not yet considered stable by maintainers ([E-1](maturity/E-1_release_cadence.md))
- 183 total dependencies, including 51 compiled binary wrappers ([F-2](supply_chain/F-2_dependency_tree.md))
- Issue tracker shows bimodal closure: median 66 days, max 1,026 days ([E-5](maturity/E-5_issue_tracker_health.md))

#### Grade Rationale

Grade: **B**. Strong institutional backing and active development are offset by the bus-factor risk and limited external adoption. The improving contributor concentration is encouraging but recent. Meets the B standard: "Supported with caveats, moderate friction." The DOE funding provides stability, but the single-institution dependency and pre-1.0 status introduce uncertainty.

---

### 3.6 Supply Chain (Gate)

#### Strengths

- BSD-3-Clause license across all Sienna packages -- fully permissive ([F-1](supply_chain/F-1_core_license.md))
- All compiled components have available source and are buildable ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- Full execution path inspectable -- no opaque steps ([F-5](supply_chain/F-5_code_inspectability.md))
- Content-addressed distribution via Julia General Registry with SHA-1/SHA-256 hashes ([F-6](supply_chain/F-6_distribution_integrity.md))
- Air-gap installable via depot copying ([F-7](supply_chain/F-7_airgap_installability.md))
- All use cases functional on open-source solvers ([F-8](supply_chain/F-8_solver_dependency.md))

#### Weaknesses

- GLPK dependency is GPL-3.0 (strong copyleft) -- but optional and excludable ([F-3](supply_chain/F-3_dependency_license_audit.md))
- 183 total dependencies is a large attack surface ([F-2](supply_chain/F-2_dependency_tree.md))
- MKL_jll and IntelOpenMP_jll are proprietary but optional (OpenBLAS is default) ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- No cryptographic signatures on registry entries or artifacts ([F-6](supply_chain/F-6_distribution_integrity.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| F-1 | pass | BSD-3-Clause, no copyleft |
| F-2 | informational | 183 deps, 51 JLL binary wrappers |
| F-3 | informational | GLPK GPL-3 flagged; optional |
| F-4 | pass | All source available and buildable |
| F-5 | pass | Full path inspectable |
| F-6 | pass | Versioned, content-addressed |
| F-7 | pass | Air-gap via depot copy |
| F-8 | pass | All open-source solvers sufficient |
| F-9 | informational | Standard Julia conventions |

#### Grade Rationale

Grade: **A-**. Strong across all supply chain criteria. The only flag is the GLPK GPL-3 dependency, which is optional and trivially excludable. The high dependency count (183) is typical for a Julia optimization project bundling 4 solver backends but warrants awareness. Meets the A- standard: "Strong overall, one minor caveat."

---

### 3.7 Phase 2 Readiness (Informational)

| Test | Finding | Readiness |
|------|---------|-----------|
| P2-1 | PSS/E RAW parsing native (v30, v32, v33) | Ready |
| P2-2 | Piecewise linear costs native (PiecewiseLinearData, SOS2) | Ready |
| P2-3 | SCUC-to-DCOPF native via SimulationSequence; ED-to-ACPF blocked by unit mismatch | Partially ready |

The SCUC-to-DCOPF pipeline has native support through `SimulationSequence` and `SemiContinuousFeedforward`. The DCOPF-to-ACPF step is blocked by the undocumented unit mismatch between PSI optimization output and PowerSystems component accessors. Resolving this unit convention would be a priority for Phase 2.

---

## 4. Cross-Cutting Observations

### API Friction Patterns

- **Mandatory time series boilerplate:** PSI's `DecisionModel` requires forecast data even for single-period OPF. Every optimization test requires ~30 LOC of `SingleTimeSeries` creation, `add_time_series!`, and `transform_single_time_series!`. This is the single largest friction pattern, appearing in tests A-3 through A-11 and B-4. ([api-friction A-3](observations/api-friction-expressiveness-A-3_dcopf.md))

- **Unit mismatch between PSI and PowerFlows:** `ActivePowerVariable` values from `read_variables()` differ from `get_active_power_limits()` by ~100x. Undocumented, workflow-breaking for the DCOPF-to-ACPF pipeline. ([api-friction A-4](observations/api-friction-expressiveness-A-4_ac_feasibility.md))

- **Time series multiplier semantics:** Values must be multipliers (0-1 range), not absolute power. Using absolute values produces a model that builds successfully but is silently infeasible. No input validation or helpful error message. ([doc-gaps A-3](observations/doc-gaps-expressiveness-A-3_dcopf.md))

- **Zero-rate line silent acceptance:** Setting `rate=0` is treated as "no limit" rather than "zero capacity" with no warning. Produces silently incorrect results. ([D-4](accessibility/D-4_error_quality.md))

### Documentation Gaps

- No recipe for MATPOWER single-period OPF workflow (most common newcomer use case)
- No documentation of dispatch unit conventions between PSI and PowerSystems
- No solver compatibility matrix (GLPK/quadratic, HiGHS/SCUC failures undocumented)
- No documentation for contingency analysis, SCOPF, lossy OPF, or stochastic capabilities/limitations
- Documentation reorganization effort (issue #1165) open since October 2024, incomplete ([D-2](accessibility/D-2_documentation_audit.md))

### Solver Ecosystem

- **HiGHS:** Primary solver for LP/QP. Fails on SCUC during initial condition computation (NO_SOLUTION error). ([solver-issues A-5](observations/solver-issues-expressiveness-A-5_scuc.md))
- **SCIP:** Required for SCUC/MIP problems where HiGHS fails. Slower but reliable.
- **GLPK:** Cannot handle quadratic cost curves (fails at build). GPL-3 license. Limited utility. ([solver-issues A-3](observations/solver-issues-expressiveness-A-3_dcopf.md))
- **Ipopt:** Required for NLP/ACOPF. Not tested at scale in this evaluation.
- **Solver swap is clean:** Parameter-only change via JuMP's `optimizer_with_attributes()`. ([C-7](scalability/C-7_solver_swap.md))

### Architecture Quality

- Excellent separation of concerns across 4 packages: PowerSystems (data), PowerNetworkMatrices (topology), PowerFlows (power flow), PowerSimulations (optimization). ([B-6](extensibility/B-6_code_architecture.md))
- JuMP model access via `get_jump_model()` is a powerful extensibility mechanism -- enables arbitrary constraint injection without source patching. ([B-1](extensibility/B-1_custom_constraints.md))
- Julia's type dispatch system provides natural type safety but requires Julia expertise for extension. ([B-6](extensibility/B-6_code_architecture.md))
- Immutable time series after transform forces system reload per scenario -- design tradeoff for data integrity. ([B-4](extensibility/B-4_stochastic.md))

---

## 5. Items Requiring Human Spot-Check

- [ ] **A-3 (DCOPF) qualified pass** -- The time series boilerplate is stable but adds ~30 LOC. Review whether this should lower expressiveness grade further or is acceptable as documented API usage.
- [ ] **A-4 (AC feasibility) unit mismatch** -- Dispatch values from PSI are ~100x larger than component limits. Verify whether this is a genuine unit convention issue or a test script error. This significantly impacts the expressiveness and extensibility grades.
- [ ] **A-5 (SCUC) HiGHS failure** -- HiGHS returns NO_SOLUTION during initial condition computation. Confirm this is a persistent PSI-HiGHS interaction issue, not a configuration error.
- [ ] **A-6 and A-7 status/workaround inconsistency** -- Both have `status: pass` but `workaround_class: stable`. Convention suggests `qualified_pass` for tests requiring workarounds. Review whether the time series boilerplate constitutes a meaningful workaround for these tests.
- [ ] **A-9 (SCOPF) native vs. manual distinction** -- SCOPF achieved via JuMP model access + LODF injection. The workaround is stable but requires ~100 LOC and deep understanding of both PSI internals and SCOPF theory. Review whether this represents B- or C+ level expressiveness for this specific capability.
- [ ] **A-11 (distributed slack) qualification** -- PTDFPowerModel is described as "inherently distributed slack." Review whether implicit, non-configurable slack weights satisfy the distributed slack criterion.
- [ ] **B-7 (AC feasibility extension) fragile classification** -- The unit conversion factor (~100x, likely system base MVA) is empirically determined. Confirm this is correctly classified as fragile rather than stable.
- [ ] **C-3, C-4, C-5, C-6 missing wall-clock times** -- Several scalability tests provide only estimated timings. Verify whether the qualified pass status is appropriate given the lack of measured evidence.
- [ ] **D-4 zero-rate line behavior** -- Setting rate=0 treated as "no limit." Verify this is the tool's actual behavior and not a PTDF formulation artifact.
- [ ] **Expressiveness grade B- vs C+** -- Two FAILs (A-8 stochastic, A-10 lossy DCOPF) and multiple qualified passes. The grade is at the B-/C+ boundary. Review whether the working capabilities (SCUC, SCED, contingency sweep, DCOPF) are sufficient for a B-.
- [ ] **Scalability grade B- vs C+** -- Three FAILs at scale (C-2 ACPF, C-8 SCOPF, C-10 distributed slack). The working scale tests (DCPF, PTDF, solver swap) are strong. Review the grade against the rubric's "multiple workarounds" standard.

---

## 6. Methodology Notes

- **Scale cap:** MEDIUM (ACTIVSg 10k, 10,000 buses). All three gate tests (G-1 through G-3) pass through MEDIUM. No LARGE network was tested.
- **Tests skipped:** None. All 57 test IDs from eval-config.yaml have result files.
- **Solver versions:** HiGHS (via HiGHS.jl), GLPK (via GLPK.jl), SCIP (via SCIP.jl), Ipopt (via Ipopt.jl). Exact native solver versions not recorded in test outputs.
- **Tool version:** PowerSimulations.jl v0.30.2, PowerSystems.jl v4.x, PowerFlows.jl v0.9.0, PowerNetworkMatrices.jl (version not recorded).
- **Environment:** Julia 1.10, Ubuntu 24.04 (devcontainer), 183 manifest dependencies.
- **JIT timing note:** All Julia timings include JIT compilation overhead on first invocation. Subsequent runs in the same REPL session would be significantly faster. First-run timings are reported for reproducibility.
- **Devcontainer environment hash:** Not recorded.
