# Synthesis Report: PowerModels.jl v0.21.5

**Contract:** FA714626C0006
**Tool version:** PowerModels.jl v0.21.5
**Evaluation date:** 2026-03-05
**Scale cap applied:** MEDIUM (10,000 buses)

---

## 1. Executive Summary

PowerModels.jl is a well-architected research-grade power systems optimization framework built on Julia's JuMP modeling language. It excels at core OPF/PF formulations with clean solver-agnostic design, native PTDF computation, and a composable four-layer architecture that enables formulation extension via Julia's multiple dispatch. However, it lacks built-in support for key operational analysis tasks (SCUC, SCED, SCOPF, stochastic programming, distributed slack), requiring 40-100 lines of custom JuMP code per missing formulation. The supply chain gate passes -- BSD-3-Clause core license, all open-source dependencies, GLPK GPL-3.0 is optional and removable. Scalability is strong for single-period DC analysis (DCPF in 0.35s at 10k buses) but degrades sharply for multi-period, multi-network, and AC formulations at scale, with only Ipopt reliably solving QP problems above 1,000 buses. The perpetual v0.x versioning, bus factor of 1, and absence of operational deployments are maturity concerns.

---

## 2. Grade Recommendations Table

| Criterion | Grade | Confidence | Key Evidence |

|-----------|-------|------------|--------------|

| Problem Expressiveness | B | High | All 11 TINY tests pass; 3 SMALL failures (A-6, A-8, A-9); 5 MEDIUM passes; SCUC/SCED/SCOPF/stochastic all require custom JuMP code |

| Extensibility | A- | High | All 9 tests pass at both TINY and grade scale; clean JuMP model access; PTDF native; custom constraints via documented API; minor Dict-navigation friction |

| Scalability | B- | Medium | DCPF excellent (0.35s at 10k); DC OPF adequate (Ipopt 60s); ACPF/SCOPF/stochastic fail or timeout at scale; HiGHS unusable for QP above 1k buses |

| Workforce Accessibility | B- | Medium | Clean install; 4/11 A-tests from docs alone; Julia JIT cold-start tax; undocumented LMP extraction; silent invalid-data acceptance |

| Maturity & Sustainability | C+ | Medium | 94% codecov and strong CI; but bus factor=1, no operational deployments, v0.x after 8 years, maintenance-phase commit activity |

| Supply Chain (Gate) | B+ | High | BSD-3-Clause core; GLPK GPL-3.0 optional/removable; all deps open-source; content-hashed distribution; no signing; airgap via depot copy |

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness (Grade: B)

#### Strengths
- Native DC PF via direct linear solve -- no JuMP overhead, fast for contingency loops ([A-1](expressiveness/A-1_dcpf.md))
- Native AC PF via Newton-Raphson with fallback to Ipopt ([A-2](expressiveness/A-2_acpf.md))
- DC OPF with dual extraction for LMPs ([A-3](expressiveness/A-3_dcopf.md))
- `DCPLLPowerModel` for lossy DC OPF is a first-class formulation type ([A-10](expressiveness/A-10_lossy_dcopf_lmp.md))
- Multi-network infrastructure (`replicate()`, `solve_mn_opf()`) provides building blocks for time-series and scenario analysis ([A-8](expressiveness/A-8_stochastic_timeseries.md))
- AC feasibility check on DC OPF dispatch achievable in same model context with no workaround ([A-4](expressiveness/A-4_ac_feasibility.md))

#### Weaknesses
- No built-in SCUC -- requires ~100 LOC custom JuMP code for binary commitment variables, startup/shutdown logic, min up/down times ([A-5](expressiveness/A-5_scuc.md))
- No built-in SCED -- requires ~50 LOC custom JuMP code ([A-6](expressiveness/A-6_sced.md))
- No native SCOPF -- requires PowerModelsSecurityConstrained.jl or ~80 LOC manual multi-network construction ([A-9](expressiveness/A-9_scopf.md))
- No native stochastic programming -- no probability weights, scenario trees, or non-anticipativity constraints ([A-8](expressiveness/A-8_stochastic_timeseries.md))
- No native distributed slack -- requires custom build function replacement (~40 LOC) ([A-11](expressiveness/A-11_distributed_slack_opf.md))
- LMP decomposition into energy/congestion/loss not built-in -- requires manual two-solve approach ([A-10](expressiveness/A-10_lossy_dcopf_lmp.md))
- SMALL-scale failures: A-6 SCED (solver infeasibility), A-8 stochastic (solver timeout), A-9 SCOPF (solver infeasibility at 100 contingencies)

#### Workarounds Required
- SCUC via `instantiate_model()` + JuMP binary variables -- **fragile** (depends on internal variable naming `PowerModels.var(pm, nw, :pg, gen_id)`)
- SCED via multi-network + JuMP ramp constraints -- **fragile** (same internal variable access pattern)
- SCOPF via multi-network + objective replacement -- **moderate** (multi-network API is stable, but objective replacement uses JuMP internals)
- Stochastic via `replicate()` + flat scenario indexing -- **moderate** (`replicate()` and `solve_mn_opf()` are stable public API)
- Distributed slack via custom build function -- **moderate** (public API `solve_model()` accepts custom build functions)
- LMP decomposition via two-solve residual -- **stable** (uses only public API)
- Contingency sweep via `compute_dc_pf()` loop -- **stable** (native solver, no JuMP overhead)

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | LOC |

|------|---------|--------|------------|------|-----|

| A-1 | TINY | pass | -- | 2.1s | 72 |

| A-1 | MEDIUM | pass | -- | 18.1s | -- |

| A-2 | TINY | pass | -- | 0.6s | 105 |

| A-2 | MEDIUM | pass | -- | 395.5s | -- |

| A-3 | TINY | pass | -- | 1.5s | 100 |

| A-3 | MEDIUM | pass | -- | 71.0s | -- |

| A-4 | TINY | pass | -- | 2.6s | 95 |

| A-4 | MEDIUM | pass | -- | 325.5s | -- |

| A-5 | TINY | pass | ~100 LOC custom JuMP | 45s | 164 |

| A-5 | SMALL | qualified_pass | same | 320.5s (TIME_LIMIT) | -- |

| A-6 | TINY | pass | ~50 LOC custom JuMP | 1.4s | 134 |

| A-6 | SMALL | **fail** | solver infeasibility | 151.8s | -- |

| A-7 | TINY | pass | ~90 LOC custom | 3.5s | 174 |

| A-7 | MEDIUM | pass | same | 984s | -- |

| A-8 | TINY | pass | ~60 LOC (no native stochastic) | 2.3s | 118 |

| A-8 | SMALL | **fail** | solver timeout | 300s | -- |

| A-9 | TINY | pass | ~80 LOC custom SCOPF | 2.7s | 165 |

| A-9 | SMALL | **fail** | solver infeasible | 360s | -- |

| A-10 | TINY | pass | ~40 LOC LMP decomposition | 1.2s | 125 |

| A-10 | SMALL | pass | same | 3.5s | -- |

| A-11 | TINY | pass | ~40 LOC custom build | 2.5s | 137 |

| A-11 | SMALL | pass | same | 1.5s | -- |

#### Grade Rationale
All 11 TINY tests pass, demonstrating that every required analysis type is achievable with PowerModels. However, 5 of 11 require major workarounds (40-100 LOC of custom JuMP code), and 3 SMALL-scale tests fail due to solver limitations on the workaround implementations. The pattern is consistent: PowerModels provides strong primitives (parse, formulate, solve) but lacks built-in support for multi-period operational formulations. This meets the B standard: "Supported with caveats, moderate friction." The workarounds are functional at TINY scale but fragile at SMALL scale, preventing a B+ grade.

---

### 3.2 Extensibility (Grade: A-)

#### Strengths
- Custom constraints via `instantiate_model()` + JuMP `@constraint` on `pm.model` -- documented, no source patching ([B-1](extensibility/B-1_custom_constraints.md))
- Clean four-layer architecture (I/O, Core, Formulations, Problems) with ~19K LOC ([B-6](extensibility/B-6_code_architecture.md))
- PTDF matrix via native `calc_basic_ptdf_matrix()` API with machine-precision accuracy (1.3e-14 error) ([B-9](extensibility/B-9_ptdf_extraction.md))
- Custom build functions accepted by `solve_model()` -- enables formulation-level extension without forking ([B-8](extensibility/B-8_reference_bus_config.md))
- Julia multiple dispatch as extension mechanism -- new formulations via subtyping `AbstractPowerModel` ([B-6](extensibility/B-6_code_architecture.md))
- Contingency loop via `deepcopy` + `br_status` toggle avoids JuMP model reconstruction ([B-3](extensibility/B-3_contingency_loop.md))
- All tests pass at both TINY and grade-level scale (MEDIUM or SMALL)

#### Weaknesses
- No Graphs.jl integration -- graph traversal requires ~30 LOC manual adjacency construction ([B-2](extensibility/B-2_graph_access.md))
- No native DataFrame/CSV export -- Dict-based results require manual tabular conversion ([B-5](extensibility/B-5_interoperability.md))
- Untyped `Dict{String,Any}` data model provides no schema validation ([B-6](extensibility/B-6_code_architecture.md))
- Distributed slack requires custom build function that reproduces ~30 lines of standard OPF boilerplate ([B-8](extensibility/B-8_reference_bus_config.md))

#### Workarounds Required
- Graph access: manual adjacency list from `data["branch"]` -- **stable** (dict structure is core API)
- CSV export: manual I/O or add DataFrames.jl -- **stable** (trivial)
- Distributed slack: custom build function -- **moderate** (relies on public `solve_model()` API but requires reproducing boilerplate)

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | LOC |

|------|---------|--------|------------|------|-----|

| B-1 | TINY | pass | -- | 2.5s | 10 |

| B-1 | MEDIUM | pass | -- | 9.2s | -- |

| B-2 | TINY | pass | ~30 LOC manual adjacency | 0.36s | 30 |

| B-2 | MEDIUM | pass | same | 3.2s | -- |

| B-3 | TINY | pass | -- | 0.51s | -- |

| B-3 | MEDIUM | pass | -- | 66.6s | -- |

| B-4 | TINY | pass | -- | 8.3s | -- |

| B-4 | SMALL | pass | -- | 3613s | -- |

| B-5 | TINY | pass | manual I/O (4 LOC) | 0.7s | 4 |

| B-5 | MEDIUM | pass | same | 2.5s | -- |

| B-6 | N/A | pass | -- | -- | -- |

| B-7 | TINY | pass | no workaround | -- | -- |

| B-7 | MEDIUM | pass | no workaround | 53.4s | -- |

| B-8 | TINY | pass | ~15 LOC distributed slack | -- | 15 |

| B-8 | SMALL | pass | same | 3.25s | -- |

| B-9 | TINY | pass | -- | 2.37s | -- |

| B-9 | MEDIUM | pass | -- | 9.4s | -- |

#### Grade Rationale
All 9 extensibility tests pass at both functional and grade-level scales with no failures. The architecture is clean, the extension mechanisms (custom build functions, direct JuMP access, type dispatch) are well-designed, and key facilities like PTDF extraction are native. The minor caveat is the lack of Graphs.jl integration and the untyped Dict data model. This meets the A- standard: "Strong overall, one minor caveat."

---

### 3.3 Scalability (Grade: B-)

#### Strengths
- DCPF at 10k buses: 0.35s solve time via native linear algebra, no JuMP overhead ([C-1](scalability/C-1_dcpf_scale.md))
- DC OPF at 10k buses: 60.5s with Ipopt ([C-3](scalability/C-3_dcopf_scale.md))
- PTDF at 10k buses: 11.3s computation, ~1 GB dense matrix ([C-9](scalability/C-9_ptdf_scale.md))
- Distributed slack at 10k buses: 27.5s, identical results to single-slack ([C-10](scalability/C-10_distributed_slack_scale.md))
- Solver swap requires zero reformulation -- one argument change ([C-7](scalability/C-7_solver_swap.md))

#### Weaknesses
- ACPF at 10k buses: >30 minutes without completing ([C-2](scalability/C-2_acpf_scale.md))
- SCOPF at 10k buses: >15 GB memory, did not complete -- multi-network approach does not scale ([C-8](scalability/C-8_scopf_scale.md))
- Stochastic DCPF at 2k buses: >45 minutes per scenario with HiGHS -- HiGHS QP unusable at this scale ([C-6](scalability/C-6_stochastic_dcpf_scale.md))
- SCUC at 2k buses: no feasible solution in 300s with either HiGHS or SCIP ([C-4](scalability/C-4_scuc_scale.md))
- HiGHS QP solver has systematic numerical stability failures on 10k-bus networks ([solver-issues-scalability](observations/solver-issues-scalability.md))
- Only Ipopt reliably solves QP problems above 1,000 buses

#### Workarounds Required
- DC OPF at scale: use Ipopt instead of HiGHS -- **stable** (one argument change)
- Multi-period OPF: use Ipopt -- **stable** but masks underlying HiGHS limitation
- SCOPF at scale: requires PowerModelsSecurityConstrained.jl with iterative screening -- **not tested**

#### Evidence Summary Table

| Test | Network | Status | Time | Memory | Solver |

|------|---------|--------|------|--------|--------|

| C-1 DCPF | MEDIUM | pass | 0.35s (solve) | 8.3 MB | Native |

| C-2 ACPF | MEDIUM | qualified_pass | >30 min | 2.9 GB | Native NR |

| C-3 DC OPF | MEDIUM | pass | 60.5s (Ipopt) | 30.8 MB | Ipopt |

| C-4 SCUC | SMALL | qualified_pass | 300s (TIME_LIMIT) | 72 MB | SCIP |

| C-5 Contingency | MEDIUM | qualified_pass | >40 min | 642 MB | Native |

| C-6 Stochastic | SMALL | **fail** | >45 min/scenario | 1.8 GB | HiGHS |

| C-7 Solver swap | MEDIUM | pass | 20.6s (Ipopt) | 30.8 MB | Multiple |

| C-8 SCOPF | MEDIUM | **fail** | >20 min | 15.4 GB | Ipopt |

| C-9 PTDF | MEDIUM | pass | 11.3s | 972 MB | Native |

| C-10 Dist. slack | MEDIUM | pass | 27.5s | 19.0 MB | Ipopt |

#### Grade Rationale
Core DC analysis (DCPF, DC OPF, PTDF, distributed slack) scales well to 10,000 buses. However, AC analysis, multi-network formulations (SCOPF, stochastic), and MILP (SCUC) fail or timeout at 2k-10k bus scale. The HiGHS QP limitation forces Ipopt for all QP problems, constraining the effective solver set. Two outright failures (C-6, C-8) and three qualified passes (C-2, C-4, C-5) indicate significant gaps in scalability for operational analysis. This meets the B- standard: "Multiple workarounds, some fragile." The solver ecosystem is the binding constraint, not the modeling framework.

---

### 3.4 Workforce Accessibility (Grade: B-)

#### Strengths
- Cleanest install of all six tools -- `Pkg.instantiate()` resolved all deps on first attempt with no conflicts ([D-1](accessibility/D-1_install_to_first_solve.md))
- Two-line API for first solve: `parse_file()` + `compute_dc_pf()` ([D-1](accessibility/D-1_install_to_first_solve.md))
- Core PF/OPF tests (A-1 through A-4) average 93 LOC ([D-5](accessibility/D-5_code_volume_comparison.md))
- 10/14 Quick Guide examples run unmodified on v0.21.5 ([D-3](accessibility/D-3_example_verification.md))
- Infeasibility diagnostics from solver propagate cleanly ([D-4](accessibility/D-4_error_quality.md))

#### Weaknesses
- Julia JIT cold-start tax (~1.5s per invocation) penalizes scripted/CI workflows ([D-1](accessibility/D-1_install_to_first_solve.md))
- Only 4/11 Suite A tests completable from documentation alone; LMP extraction, multi-network variable access, and custom formulations require source reading ([D-2](accessibility/D-2_documentation_audit.md))
- 4/14 Quick Guide examples fail on relative file paths that reference bundled test data ([D-3](accessibility/D-3_example_verification.md))
- Invalid bus type (bus_type=99) accepted silently with no warning or error -- no input validation ([D-4](accessibility/D-4_error_quality.md))
- Missing cost key produces raw Julia `KeyError` with no domain-specific message ([D-4](accessibility/D-4_error_quality.md))
- Advanced tests (workaround-required) average 155 LOC, 2x core tests ([D-5](accessibility/D-5_code_volume_comparison.md))
- Dual extraction requires undocumented `setting = Dict("output" => Dict("duals" => true))` parameter ([D-2](accessibility/D-2_documentation_audit.md))

#### Evidence Summary Table

| Test | Status | Key Metric |

|------|--------|------------|

| D-1 Install | qualified_pass | 1.5s cold start; clean install |

| D-2 Docs audit | qualified_pass | 4/11 from docs alone |

| D-3 Examples | qualified_pass | 10/14 run unmodified |

| D-4 Error quality | qualified_pass | 1 meaningful, 1 raw exception, 1 silent |

| D-5 Code volume | pass | 72-174 LOC range |

#### Grade Rationale
The install experience is excellent and the core API is minimal. However, the documentation gaps around LMP extraction, multi-network workflows, and custom formulation construction significantly impair the experience for advanced use cases. The silent acceptance of invalid data values and lack of input validation is a reliability concern. Julia's REPL-oriented workflow model imposes a learning curve for Python-native teams. This meets the B- standard: "Multiple workarounds, some fragile" -- specifically, the documentation gaps require source-code reading for 7 of 11 test types, which is a meaningful accessibility barrier.

---

### 3.5 Maturity & Sustainability (Grade: C+)

#### Strengths
- 94% code coverage with 6-configuration CI matrix (Linux/macOS/Windows x Julia 1.10/latest) ([E-6](maturity/E-6_ci_test_coverage.md))
- LANL/DOE institutional funding under contract DE-AC52-06NA25396 -- durable government-lab backing ([E-4](maturity/E-4_funding_model.md))
- 8 releases in 24 months, consistent ~3 month cadence ([E-1](maturity/E-1_release_cadence.md))
- ARPA-E GOC benchmark algorithm -- DOE programmatic investment ([E-4](maturity/E-4_funding_model.md))
- ~300+ academic citations (PSCC 2018 paper) ([E-7](maturity/E-7_operational_adoption.md))

#### Weaknesses
- Bus factor = 1: ccoffrin accounts for 82% of all commits ([E-3](maturity/E-3_contributor_concentration.md))
- No evidence of operational deployment at any utility, ISO/RTO, or government agency ([E-7](maturity/E-7_operational_adoption.md))
- Perpetual v0.x after 8+ years signals API instability ([E-1](maturity/E-1_release_cadence.md))
- Maintenance-phase activity: 37 commits/24mo from 6 committers, declining trend ([E-2](maturity/E-2_commit_activity.md))
- 83 open issues, ~194 day median time-to-close ([E-5](maturity/E-5_issue_tracker_health.md))

#### Evidence Summary Table

| Test | Status | Key Metric |

|------|--------|------------|

| E-1 Release cadence | qualified_pass | 8 releases/24mo, still v0.x |

| E-2 Commit activity | qualified_pass | 37 commits/24mo, 6 committers |

| E-3 Contributor concentration | qualified_pass | Bus factor=1 (ccoffrin 82%) |

| E-4 Funding model | qualified_pass | LANL/DOE institutional |

| E-5 Issue tracker | qualified_pass | 83 open, ~194 day median close |

| E-6 CI/test coverage | pass | 94% codecov, 6-config matrix |

| E-7 Operational adoption | **fail** | No operational deployment evidence |

#### Grade Rationale
The CI/testing infrastructure is strong (94% coverage is excellent). The DOE/LANL institutional backing provides funding durability. However, the bus factor of 1 is a significant continuity risk, the project is in maintenance phase with declining commit activity, and there is zero evidence of operational use. The E-7 failure (no operational adoption) is the most significant finding -- this tool is explicitly positioned as a research platform, not an operational tool. This meets the C+ standard: "Significant gaps, NOT disqualifying" -- the CI quality and institutional funding prevent a lower grade, but the operational adoption gap and bus factor are genuine concerns.

---

### 3.6 Supply Chain -- Gate (Grade: B+)

#### Strengths
- BSD-3-Clause core license with LANL/DOE preamble -- fully permissive ([F-1](supply_chain/F-1_core_license.md))
- All 114 dependencies use open-source licenses; zero proprietary or unknown licenses ([F-3](supply_chain/F-3_dependency_license_audit.md))
- Full code path from API to solver is inspectable in pure Julia source down to JLL boundary ([F-5](supply_chain/F-5_code_inspectability_trace.md))
- Solver-agnostic via JuMP -- no commercial solver required; all four tested solvers are open-source ([F-8](supply_chain/F-8_solver_dependency_assessment.md))
- Content-hashed distribution via Julia General Registry with tree-hash integrity ([F-6](supply_chain/F-6_distribution_integrity.md))

#### Weaknesses
- GLPK (GPL-3.0) in dependency tree -- optional and removable, but present in evaluation ([F-3](supply_chain/F-3_dependency_license_audit.md))
- 35 JLL binary packages increase supply chain surface area ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- No cryptographic signing of packages or registry entries ([F-6](supply_chain/F-6_distribution_integrity.md))
- No first-class airgap bundle mechanism -- requires depot copy or containerization ([F-7](supply_chain/F-7_airgap_installability.md))
- Examples not version-pinned ([F-9](supply_chain/F-9_getting_started_integrity.md))

#### Evidence Summary Table

| Test | Status | Key Finding |

|------|--------|-------------|

| F-1 Core license | pass | BSD-3-Clause (LANL) |

| F-2 Dependency tree | qualified_pass | 114 packages, 35 JLL binaries |

| F-3 License audit | qualified_pass | GLPK GPL-3.0 optional |

| F-4 Compiled extensions | qualified_pass | All JLL open-source, Yggdrasil builds |

| F-5 Inspectability | pass | Full trace readable |

| F-6 Distribution integrity | qualified_pass | Content-hashed, no signing |

| F-7 Airgap | qualified_pass | Possible via depot copy |

| F-8 Solver deps | pass | All open-source |

| F-9 Examples integrity | qualified_pass | Not version-pinned |

#### Grade Rationale
The supply chain is fundamentally clean: permissive core license, all open-source dependencies, full code inspectability, and solver-agnostic architecture. The GLPK GPL-3.0 concern is fully mitigated by removal. The qualified passes reflect Julia ecosystem limitations (no package signing, no native airgap bundling) rather than PowerModels-specific issues. This meets the B+ standard: "Mostly strong, one meaningful gap with stable workaround" -- the signing gap is the meaningful caveat, mitigated by content hashing.

---

## 4. Cross-Cutting Observations

### API Friction Patterns
- **Inconsistent mutability**: `compute_dc_pf()` returns a result dict while `compute_ac_pf!()` mutates in-place. The `!` convention is standard Julia but the asymmetry for the same conceptual operation is a friction point ([api-friction-expressiveness](observations/expressiveness-api-friction.md), [api-friction-A-4](observations/api-friction-expressiveness-A-4_ac_feasibility.md))
- **String-keyed Dict throughout**: All data and results use `Dict{String,Any}` with no typed structs, no IDE autocomplete, and no compile-time checking. Generator ID `3` is `data["gen"]["3"]` -- string conversion required everywhere ([api-friction-expressiveness](observations/expressiveness-api-friction.md))
- **Undiscoverable dual extraction**: LMPs require `setting = Dict("output" => Dict("duals" => true))` which is not in any function docstring ([api-friction-expressiveness](observations/expressiveness-api-friction.md))
- **No tabular output**: All results require manual Dict iteration for export; no DataFrame integration ([api-friction-B-5](observations/api-friction-extensibility-B-5_interoperability.md))

### Documentation Gaps
- **LMP/dual extraction** not documented in function signatures or guides -- discovered via test files ([doc-gaps-expressiveness](observations/expressiveness-doc-gaps.md))
- **Multi-network variable access** pattern `PowerModels.var(pm, nw, :pg, gen_id)` undocumented -- critical for SCUC/SCOPF customization ([doc-gaps-expressiveness](observations/expressiveness-doc-gaps.md))
- **No formulation-solver compatibility matrix** -- users discover incompatibilities at solve time ([doc-gaps-expressiveness](observations/expressiveness-doc-gaps.md))
- **Stochastic/scenario workflow** undocumented despite `replicate()` infrastructure existing ([doc-gaps-B-4](observations/doc-gaps-extensibility-B-4_stochastic_wrapping.md))
- **No extension/developer guide** despite clean architecture ([arch-quality-B-6](observations/arch-quality-extensibility-B-6_code_architecture.md))

### Solver Ecosystem
- **HiGHS QP failures at scale**: Systematic numerical stability issues on 10k-bus QP problems -- primal infeasibilities, solve errors, extreme slowness. Unusable for DC OPF above ~1,000 buses ([solver-issues-scalability](observations/solver-issues-scalability.md))
- **HiGHS cannot solve MIQP**: Unit commitment with quadratic costs is rejected outright ([solver-issues-expressiveness](observations/expressiveness-solver-issues.md))
- **GLPK LP-only**: Cannot handle PowerModels' standard quadratic cost objective ([solver-issues-expressiveness](observations/expressiveness-solver-issues.md))
- **Ipopt is the only reliable open-source solver at scale** for QP problems -- effective solver set is 1 ([solver-issues-scalability](observations/solver-issues-scalability.md))
- **No upfront solver-capability validation**: Incompatibilities discovered only at solve time, after model construction ([solver-issues-expressiveness](observations/expressiveness-solver-issues.md))

### Architecture Quality
- **Clean four-layer design**: I/O (4K LOC), Core (7.8K LOC), Formulations (4.3K LOC), Problems (2K LOC) ([B-6](extensibility/B-6_code_architecture.md))
- **Julia multiple dispatch is the extension mechanism**: New formulations via subtyping + method override. Cleanest extension pattern among evaluated tools ([arch-quality-B-6](observations/arch-quality-extensibility-B-6_code_architecture.md))
- **Untyped Dict data model is reliability risk**: No schema validation means typos and invalid values pass silently. `bus_type=99` produces no error ([D-4](accessibility/D-4_error_quality.md))
- **Heavy InfrastructureModels.jl dependency**: Core instantiation and optimization delegated to a sibling package -- users must understand both packages for deep extension ([arch-quality-B-6](observations/arch-quality-extensibility-B-6_code_architecture.md))

---

## 5. Items Requiring Human Spot-Check

- [ ] **A-7 (Contingency Sweep):** Graph-distance pruning via manual BFS -- verify that the BFS-based branch selection within distance x of the focus bus correctly identifies the right candidate set. The MEDIUM result (984s) suggests significant overhead from data dict deepcopy.
- [ ] **A-8 (Stochastic):** The multi-network solve produces mathematically independent scenario solves (confirmed by objective matching deterministic sum). Verify this is acceptable as a "stochastic" test result given the rubric requires "the stochastic structure is part of the optimization formulation."
- [ ] **A-9 (SCOPF):** Corrective SCOPF was used instead of preventive because preventive is infeasible on case39. Verify whether corrective SCOPF meets the rubric requirement that "contingency constraints are part of the optimization."
- [ ] **Qualified passes (12 total):** A-5 SMALL (builds but TIME_LIMIT), C-2 (ACPF >30 min), C-4 (SCUC no feasible in 300s), C-5 (contingency >40 min), D-1 (JIT cold-start), D-2 (4/11 from docs), D-3 (10/14 examples), D-4 (mixed error quality), E-1 through E-5, F-2/F-3/F-4/F-6/F-7/F-9.
- [ ] **Workaround durability classifications:** SCUC (A-5) and SCED (A-6) classified as "fragile" due to dependence on `PowerModels.var(pm, nw, :pg, gen_id)` internal variable access -- verify whether this pattern is part of the stable API or subject to change.
- [ ] **SMALL-scale failures (A-6, A-8, A-9):** All three fail due to solver limitations (Ipopt LOCALLY_INFEASIBLE or HiGHS QP errors) on multi-network formulations at 2,000 buses. Verify whether these failures are inherent to the workaround approach or could be resolved with better solver configuration.
- [ ] **C-6 FAIL classification:** The failure was tested with HiGHS only. The report notes Ipopt would likely solve each scenario in ~60s (based on C-3 data). Verify whether this should be reclassified as qualified_pass with solver note.
- [ ] **E-7 (Operational Adoption) FAIL:** Confirm no operational deployments exist beyond the ARPA-E benchmark competition and academic citations.
- [ ] **Supply chain grade at B+:** With 7 qualified_pass results in the F-suite and the GLPK GPL concern, verify the B+ grade is not too generous.

---

## 6. Methodology Notes

- **Scale cap:** MEDIUM (10,000 buses, ACTIVSg10k). All gate tests (G-1 through G-3) pass at TINY/SMALL/MEDIUM.
- **Tests skipped:** None. All tests in the evaluation config were attempted.
- **Solver versions:** HiGHS 1.13.1 (via HiGHS_jll), Ipopt 300.1400.1901 (via Ipopt_jll), SCIP 0.2.1 (via SCIP_jll), GLPK 5.0.1 (via GLPK_jll)
- **Tool version:** PowerModels.jl v0.21.5 with InfrastructureModels.jl v0.7.8, JuMP v1.29.4, MathOptInterface v1.49.0
- **Julia version:** 1.10 (per devcontainer configuration)
- **Environment:** Devcontainer (Ubuntu 24.04, single-threaded execution)
- **Data preprocessing:** MEDIUM network (ACTIVSg10k) required preprocessing: 1,349 generators missing cost data received $20/MWh default linear cost; 2,462 branches with rate_a=0 received 9999 (unconstrained). This preprocessing was applied consistently across all MEDIUM tests.
- **Concurrent execution note:** Multiple Julia processes ran simultaneously during some tests, which may have inflated wall-clock times (noted in A-2 MEDIUM, B-4 SMALL). Relative comparisons within a test are still valid.

---

## 7. Phase 2 Readiness (Informational)

| Test | Status | Key Finding |

|------|--------|-------------|

| P2-1 PSS/E parsing | qualified_pass | v33 supported; v34 not (open issue #921); transformer/generator edge cases open |

| P2-2 PWL costs | pass | Lambda model with SOS2 for non-convex; MATPOWER-compatible data format |

PSS/E v33 support is functional but the v34 gap and open parser issues (#932, #918) mean production network models should be validated before Phase 2 use. PWL cost support is comprehensive and ready for Phase 2.
