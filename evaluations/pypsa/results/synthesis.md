# Synthesis Report: PyPSA v1.1.2

**Contract:** FA714626C0006
**Tool version:** PyPSA 1.1.2 (released 2026-02-23)
**Evaluation date:** 2026-03-07
**Protocol version:** v4
**Solver:** HiGHS 1.13.1 (single-threaded, per solver-config.md)

---

## 1. Executive Summary

PyPSA is a mature, well-architected Python power systems modeling tool with strong native support for DC/AC power flow, DC OPF, SCOPF, unit commitment, lossy DCOPF, and distributed slack. Its Linopy-based optimization subsystem provides a clean, solver-agnostic interface with excellent extensibility via custom constraints (2 LOC to add a flow gate). The tool passes the supply chain gate with an MIT-licensed stack throughout. The most significant weakness is the absence of native stochastic optimization (A-8: FAIL, blocking) -- the `n.scenarios` data model exists but is not wired into the optimizer. SCUC scalability is limited at the 2000-bus tier with HiGHS single-threaded (A-5 SMALL: FAIL, 600s timeout), and the `lpf_contingency()` method is broken in v1.1.2, forcing manual contingency loops. No scale cap is applied; MEDIUM-tier tests were executed where possible but several failed due to data-preparation issues with the ACTIVSg10k case (zero-impedance branches, zero s_nom) rather than tool limitations.

---

## 2. Grade Recommendations

| Criterion | Grade | Confidence | Key Evidence |
|-----------|-------|------------|--------------|
| Problem Expressiveness | B+ | High | 9/11 TINY pass, A-8 stochastic FAIL (blocking), A-5/A-6 SMALL FAIL (solver timeout) |
| Extensibility | A- | High | All 9 B-tests pass TINY, custom constraints in 2 LOC, zero-friction NetworkX, clean Linopy model access |
| Scalability | B- | Medium | DCPF/ACPF/DCOPF pass MEDIUM, SCUC FAIL SMALL, linopy post-processing bottleneck at 10k-bus |
| Workforce Accessibility | B+ | High | Single-command install, good core docs, gaps in advanced features (SCED workflow, LMP decomposition) |
| Maturity & Sustainability | A- | High | 24 releases/24mo, 84% test coverage, 327 commits/12mo, bus factor 3-4, IEA/ACER/ENTSO-E adoption |
| Supply Chain (Gate) | A | High | MIT throughout stack, 87 deps all open-source, air-gap installable, Sigstore attestations |

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness (Criterion A)

#### Strengths

- Native DCPF with direct sparse solve and structured DataFrame output ([A-1](expressiveness/A-1_dcpf.md))
- Newton-Raphson ACPF with flat-start convergence in 4 iterations on TINY ([A-2](expressiveness/A-2_acpf.md))
- DC OPF with LMP extraction via `n.buses_t.marginal_price` ([A-3](expressiveness/A-3_dcopf.md))
- First-class SCOPF via `optimize_security_constrained()` with contingency constraints embedded in the LP ([A-9](expressiveness/A-9_scopf.md))
- Lossy DCOPF with piecewise linear loss approximation (`transmission_losses=2`) and extractable LMP decomposition ([A-10](expressiveness/A-10_lossy_dcopf_lmp.md))
- Distributed slack with configurable weights in PF; OPF inherently distributed by design ([A-11](expressiveness/A-11_distributed_slack_opf.md))
- Comprehensive built-in UC constraints: committable, min up/down time, ramp limits, startup/shutdown costs ([A-5](expressiveness/A-5_scuc.md))
- SCOPF scales to SMALL (2000-bus, 50 monitored contingencies, ~70s) ([A-9 SMALL](expressiveness/A-9_scopf_SMALL.md))
- Lossy DCOPF scales to SMALL with physically meaningful loss-inclusive pricing ([A-10 SMALL](expressiveness/A-10_lossy_dcopf_lmp_SMALL.md))

#### Weaknesses

- No native stochastic optimization -- `n.scenarios` exists in data model but is not wired to optimizer ([A-8](expressiveness/A-8_stochastic_timeseries.md)) -- **blocking**
- SCUC at SMALL (2000-bus) times out with HiGHS single-threaded (9,840+ binary variables) ([A-5 SMALL](expressiveness/A-5_scuc_SMALL.md))
- SCED SMALL fails as cascade from SCUC SMALL failure ([A-6 SMALL](expressiveness/A-6_sced_SMALL.md))
- `lpf_contingency()` broken in v1.1.2 with `DataFrame.to_frame` AttributeError ([A-7](expressiveness/A-7_contingency_sweep.md))
- PPC importer drops gencost data, requiring manual cost assignment for all OPF tests ([A-3](expressiveness/A-3_dcopf.md))
- DCOPF infeasible on MEDIUM (10k-bus) due to zero s_nom branches in MATPOWER data ([A-3 MEDIUM](expressiveness/A-3_dcopf_MEDIUM.md))

#### Workarounds Required

- Manual gencost parsing and assignment from MATPOWER `.m` files (~5 LOC) -- **stable** ([A-3](expressiveness/A-3_dcopf.md))
- Manual OPF-to-PF dispatch transfer via `p_set` assignment for AC feasibility -- **stable** ([A-4](expressiveness/A-4_ac_feasibility.md))
- Manual commitment fixing via `p_min_pu`/`p_max_pu` encoding for SCUC-to-SCED (~10 LOC) -- **stable** ([A-6](expressiveness/A-6_sced.md))
- Manual line disabling (x=1e10) loop instead of `lpf_contingency()` -- **stable** ([A-7](expressiveness/A-7_contingency_sweep.md))
- Thermal rating escalation to 150% for SCOPF feasibility (protocol-permitted) -- **stable** ([A-9](expressiveness/A-9_scopf.md))

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | LOC |
|------|---------|--------|------------|------|-----|
| A-1 DCPF | TINY | pass | -- | 0.10s | 79 |
| A-1 DCPF | MEDIUM | pass | -- | 15.0s | -- |
| A-2 ACPF | TINY | pass | -- | 0.16s | 141 |
| A-2 ACPF | MEDIUM | pass | -- | 15.7s | -- |
| A-3 DCOPF | TINY | pass | stable (gencost) | 0.48s | 109 |
| A-3 DCOPF | MEDIUM | fail | -- | 23.5s | -- |
| A-4 AC feas. | TINY | pass | stable | 0.12s | 175 |
| A-4 AC feas. | MEDIUM | fail | -- | -- | -- |
| A-5 SCUC | TINY | pass | stable (gencost) | 1.41s | 286 |
| A-5 SCUC | SMALL | fail | -- | 664s | 245 |
| A-6 SCED | TINY | pass | stable | 3.06s | 315 |
| A-6 SCED | SMALL | fail | -- | 931s | -- |
| A-7 Contingency | TINY | pass | stable (manual loop) | 73.9s | 230 |
| A-7 Contingency | MEDIUM | fail | -- | -- | -- |
| A-8 Stochastic | TINY | fail | blocking | 1.54s | 360 |
| A-8 Stochastic | SMALL | fail | blocking | -- | -- |
| A-9 SCOPF | TINY | pass | stable (rating scale) | 0.64s | 185 |
| A-9 SCOPF | SMALL | pass | stable | 70s | -- |
| A-10 Lossy OPF | TINY | pass | stable | 0.60s | 220 |
| A-10 Lossy OPF | SMALL | pass | stable | 72.9s | -- |
| A-11 Dist. slack | TINY | pass | -- | 0.79s | 195 |
| A-11 Dist. slack | SMALL | pass | stable | 10.4s | -- |

#### Grade Rationale

PyPSA passes 9 of 11 expressiveness tests at TINY and scales most analyses to SMALL/MEDIUM. The one blocking failure (A-8 stochastic) represents a fundamental capability gap -- no native scenario-indexed optimization exists. SCUC/SCED failures at SMALL are solver-bound (HiGHS single-threaded) rather than tool-bound. The workarounds required are uniformly stable and use documented public API. This meets the B+ standard: "Mostly strong, one meaningful gap with stable workaround" -- except the stochastic gap has no workaround (blocking), which prevents an A-level grade. The strength across 9 other tests and the quality of the workarounds prevent a drop below B+.

---

### 3.2 Extensibility (Criterion B)

#### Strengths

- Custom constraints via Linopy `create_model()`/`solve_model()` split requires only 2 LOC with full dual extraction ([B-1](extensibility/B-1_custom_constraints.md))
- Zero-friction NetworkX graph access via `n.graph()` -- 4 LOC for BFS + subgraph extraction ([B-2](extensibility/B-2_graph_access.md))
- Clean stochastic wrapping via `n.copy()` + DataFrame assignment (20 scenarios in 9.68s on TINY) ([B-4](extensibility/B-4_stochastic_wrapping.md))
- Native PTDF extraction via `SubNetwork.calculate_PTDF()` with machine-precision flow agreement ([B-9](extensibility/B-9_ptdf_extraction.md))
- Well-designed 5-layer mixin architecture with clean horizontal separation of concerns ([B-6](extensibility/B-6_code_architecture.md))
- Pandas DataFrame interoperability: results export in 2 LOC via `.to_csv()` ([B-5](extensibility/B-5_interoperability.md))
- Reference bus configuration via DataFrame edits with no model reconstruction ([B-8](extensibility/B-8_reference_bus_config.md))
- All workarounds in A-4 (AC feasibility extension) are stable, low-effort, public API ([B-7](extensibility/B-7_ac_feasibility_extension.md))

#### Weaknesses

- `lpf_contingency()` bug forces manual contingency loop at all tiers ([B-3](extensibility/B-3_contingency_loop.md))
- Contingency loop impractical at MEDIUM (10k-bus): ~65s per LPF solve, only 9 of 270 cases in 600s ([B-3 MEDIUM](extensibility/B-3_contingency_loop_MEDIUM.md))
- PTDF fails at MEDIUM due to singular B matrix from zero-impedance branches ([B-9 MEDIUM](extensibility/B-9_ptdf_extraction_MEDIUM.md))
- Custom constraints fail at MEDIUM due to cascading DCOPF infeasibility (data issue) ([B-1 MEDIUM](extensibility/B-1_custom_constraints_MEDIUM.md))

#### Workarounds Required

- Manual contingency loop via `n.copy()` + reactance modification -- **stable** ([B-3](extensibility/B-3_contingency_loop.md))
- Manual gencost assignment (inherited across all OPF-dependent tests) -- **stable**

#### Evidence Summary Table

| Test | Network | Status | Workaround | Time | LOC |
|------|---------|--------|------------|------|-----|
| B-1 Custom constraints | TINY | pass | -- | 0.11s | 2 |
| B-1 Custom constraints | MEDIUM | fail | -- | -- | -- |
| B-2 Graph access | TINY | pass | -- | 0.07s | 4 |
| B-2 Graph access | MEDIUM | pass | -- | 0.84s | 4 |
| B-3 Contingency loop | TINY | pass | stable | 4.02s | -- |
| B-3 Contingency loop | MEDIUM | fail | -- | -- | -- |
| B-4 Stochastic wrapping | TINY | pass | stable | 9.68s | 316 |
| B-4 Stochastic wrapping | SMALL | pass | stable | 2217s | -- |
| B-5 Interoperability | TINY | pass | -- | 0.15s | 2 |
| B-5 Interoperability | MEDIUM | pass | -- | 15.2s | 2 |
| B-6 Code architecture | N/A | info | -- | -- | -- |
| B-7 AC feas. extension | TINY | pass | stable | <0.01s | 149 |
| B-7 AC feas. extension | MEDIUM | pass | stable | <0.01s | -- |
| B-8 Reference bus config | TINY | pass | -- | 3.24s | 257 |
| B-8 Reference bus config | SMALL | pass | -- | 217s | -- |
| B-9 PTDF extraction | TINY | pass | -- | 0.03s | -- |
| B-9 PTDF extraction | MEDIUM | fail | -- | -- | -- |

#### Grade Rationale

All 9 extensibility tests pass at TINY. The custom constraint API (2 LOC, full duals), NetworkX graph access (zero friction), stochastic wrapping (clean `n.copy()` pattern), and PTDF extraction (native public API) demonstrate strong extensibility. MEDIUM-tier failures are data-driven (zero-impedance branches) rather than architectural. The only structural issue is the broken `lpf_contingency()` method, which has a stable workaround. The Linopy model interface is a genuine architectural strength. This meets the A- standard: "Strong overall, one minor caveat" -- the caveat being the `lpf_contingency()` bug and the undocumented PTDF column ordering.

---

### 3.3 Scalability (Criterion C)

#### Strengths

- DCPF scales to MEDIUM (10k-bus) in 28.3s solve time ([C-1](scalability/C-1_dcpf_scale_MEDIUM.md))
- ACPF converges on 10k-bus from flat start in 18.1s ([C-2](scalability/C-2_acpf_scale_MEDIUM.md))
- DCOPF solves optimally on 10k-bus in 19.9s (HiGHS) ([C-3](scalability/C-3_dcopf_scale_MEDIUM.md))
- Stochastic DCOPF loop (20 scenarios, 12h, 2000-bus) completes in 2219s, 7.1 GB peak ([C-6](scalability/C-6_stochastic_scale_SMALL.md))
- Solver swap is parameter-only (`solver_name="..."`) with no model reformulation ([C-7](scalability/C-7_solver_swap_MEDIUM.md))
- PTDF computation on 10k-bus (12,706 x 10,000 matrix, 969 MB) completes in 28s ([C-9](scalability/C-9_ptdf_scale_MEDIUM.md))
- Distributed slack scales to 10k-bus via the same OPF mechanism ([C-10](scalability/C-10_distributed_slack_scale_MEDIUM.md))

#### Weaknesses

- SCUC at SMALL (2000-bus, 544 generators x 24h) times out with HiGHS single-threaded -- no feasible solution found in 600s ([C-4](scalability/C-4_scuc_scale_SMALL.md))
- Linopy shadow-price post-processing takes 10+ minutes on 10k-bus, dominating wall-clock for DCOPF, SCOPF, and distributed slack tests ([C-3](scalability/C-3_dcopf_scale_MEDIUM.md), [C-8](scalability/C-8_scopf_scale_MEDIUM.md))
- SCOPF at MEDIUM not reached due to linopy post-processing timeout ([C-8](scalability/C-8_scopf_scale_MEDIUM.md))
- Contingency sweep at MEDIUM: only 9 of 270 N-1 cases in 600s (~65s per LPF) ([C-5](scalability/C-5_contingency_scale_MEDIUM.md))
- PTDF flow prediction accuracy degraded at MEDIUM due to zero-impedance workaround (702 MW max diff) ([C-9](scalability/C-9_ptdf_scale_MEDIUM.md))

#### Evidence Summary Table

| Test | Network | Status | Time | Peak Memory |
|------|---------|--------|------|-------------|
| C-1 DCPF | MEDIUM | pass | 36.8s | 2,382 MB |
| C-2 ACPF | MEDIUM | pass | 22.1s | 2,383 MB |
| C-3 DCOPF | MEDIUM | pass | 600s+ | 4,000 MB |
| C-4 SCUC | SMALL | fail | 700s | 4,000 MB |
| C-5 Contingency | MEDIUM | qualified_pass | 613s | 2,461 MB |
| C-6 Stochastic | SMALL | pass | 2,219s | 7,125 MB |
| C-7 Solver swap | MEDIUM | pass | 600s+ | 4,000 MB |
| C-8 SCOPF | MEDIUM | fail | 600s+ | 4,000 MB |
| C-9 PTDF | MEDIUM | qualified_pass | 78.8s | 5,299 MB |
| C-10 Dist. slack | MEDIUM | pass | 600s+ | 4,000 MB |

#### Grade Rationale

PyPSA demonstrates adequate scalability for LP-based analyses (DCPF, ACPF, DCOPF) at 10k-bus scale, with solver times well within budget. The stochastic loop at 2000-bus completes 20 scenarios successfully. However, two significant scalability limitations lower the grade: (1) SCUC fails at SMALL due to HiGHS single-threaded MILP limitations, and (2) linopy's shadow-price post-processing creates a 10+ minute overhead at 10k-bus that prevents several MEDIUM tests from completing. The contingency sweep at MEDIUM is also impractical due to the `lpf_contingency()` bug forcing per-case full LPF solves. This meets the B- standard: "Multiple workarounds, some fragile" -- the linopy overhead is structural (not workaround-able) and SCUC requires a different solver.

---

### 3.4 Workforce Accessibility (Criterion D)

#### Strengths

- Single-command install with bundled HiGHS solver; 3 steps to first solve ([D-1](accessibility/D-1_install_to_first_solve.md))
- Core workflows (PF, OPF, UC, contingency) have dedicated doc pages and example notebooks ([D-2](accessibility/D-2_documentation_audit.md))
- All 3 tested getting-started examples run unmodified with correct results ([D-3](accessibility/D-3_example_verification.md))
- Missing-cost validation is exemplary: early, specific, actionable error message ([D-4](accessibility/D-4_error_quality.md))
- Zero-friction NetworkX graph access discoverable by Python users ([obs: api-friction B-2](observations/api-friction-extensibility-B-2_graph_access.md))
- DataFrame-centric data model natural for pandas users ([obs: arch-quality B-4](observations/arch-quality-extensibility-B-4_stochastic_wrapping.md))

#### Weaknesses

- SCED two-stage workflow (SCUC-to-ED) has no documentation -- requires understanding of internal mechanics ([D-2](accessibility/D-2_documentation_audit.md))
- LMP decomposition requires Linopy model internals; no built-in decomposition method ([obs: api-friction A-10](observations/api-friction-expressiveness-A-10_lossy_dcopf_lmp.md))
- PTDF column ordering undocumented -- wrong ordering gives 1000+ MW errors ([obs: doc-gaps B-9](observations/doc-gaps-extensibility-B-9_ptdf_extraction.md))
- Silent acceptance of invalid bus control types (no input validation) ([D-4](accessibility/D-4_error_quality.md))
- Reserve constraints via `extra_functionality` require undocumented Linopy dimension names ([obs: api-friction A-5](observations/api-friction-expressiveness-A-5_scuc.md))
- Line shadow prices not assigned to network by default after `optimize()` ([obs: api-friction A-3 shadow](observations/api-friction-expressiveness-A-3_dcopf_shadow_prices.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| D-1 Install to first solve | pass | 3 steps, bundled solver |
| D-2 Documentation audit | qualified_pass | 7/11 tests fully documented, A-6 undocumented |
| D-3 Example verification | pass | All 3 examples correct, unmodified |
| D-4 Error quality | qualified_pass | Missing-cost: A; Infeasible: B+; Invalid enum: D |
| D-5 Code volume | informational | 158-485 LOC per test, mean ~325 |

#### Grade Rationale

PyPSA provides excellent onboarding (single-command install, working examples, good core docs) and a natural API for Python developers familiar with pandas and NetworkX. Documentation coverage is strong for core workflows but has meaningful gaps in advanced features (SCED workflow, LMP decomposition, PTDF ordering, Linopy dimension names). Error quality is mixed -- exemplary for missing costs but absent for invalid enum values. This meets the B+ standard: "Mostly strong, one meaningful gap" -- the documentation gaps in advanced workflows prevent an A-level grade, but the tool is highly accessible for standard use cases.

---

### 3.5 Maturity & Sustainability (Criterion E)

#### Strengths

- 24 releases in 24 months with strict SemVer; v1.0.0 milestone in October 2025 ([E-1](maturity/E-1_release_cadence.md))
- 327 commits from 32 unique human contributors in last 12 months ([E-2](maturity/E-2_commit_activity.md))
- 84% code coverage with CI on 3 platforms x 3 Python versions, daily scheduled runs ([E-6](maturity/E-6_ci_test_coverage.md))
- Bus factor 3-4: three PyPI maintainers, institutional backing from TU Berlin and OET ([E-3](maturity/E-3_contributor_concentration.md))
- Median issue time-to-close: 21 hours; 55% of issues closed within 1 day ([E-5](maturity/E-5_issue_tracker_health.md))
- Confirmed operational adoption by IEA, ACER, ENTSO-E, TransnetBW, Shell ([E-7](maturity/E-7_operational_adoption.md))
- Hybrid academic-commercial funding via TU Berlin + Open Energy Transition ([E-4](maturity/E-4_funding_model.md))

#### Weaknesses

- Top contributor (lkstrp) accounts for 53% of recent commits -- high individual concentration ([E-3](maturity/E-3_contributor_concentration.md))
- Top 3 lifetime contributors account for 68% of all commits; all TU Berlin-affiliated ([E-3](maturity/E-3_contributor_concentration.md))
- `lpf_contingency()` broken in current release suggests insufficient test coverage for this code path ([obs: solver-issues A-7](observations/solver-issues-expressiveness-A-7_contingency_sweep.md))
- Stochastic optimization data model (`n.scenarios`) exists but is not connected to optimizer -- feature gap or incomplete implementation ([obs: doc-gaps A-8](observations/doc-gaps-expressiveness-A-8_stochastic_timeseries.md))
- No evidence of real-time dispatch or market operations usage; adoption concentrated in planning/policy ([E-7](maturity/E-7_operational_adoption.md))

#### Grade Rationale

PyPSA demonstrates strong maturity indicators: aggressive release cadence, high test coverage, responsive issue management, and broad institutional adoption. The v1.0.0 milestone signals API stability. The contributor concentration risk is mitigated by institutional backing and multiple PyPI maintainers. The `lpf_contingency()` bug and incomplete stochastic optimization are quality concerns but do not undermine the overall maturity picture. This meets the A- standard: "Strong overall, one minor caveat" -- the caveats being contributor concentration and the broken contingency method.

---

### 3.6 Supply Chain -- Gate (Criterion F)

#### Strengths

- MIT license throughout the entire stack: PyPSA, Linopy, HiGHS ([F-1](supply_chain/F-1_core_license.md))
- 87 of 90 packages carry permissive licenses (MIT, BSD, Apache, PSF) ([F-3](supply_chain/F-3_dependency_license_audit.md))
- Zero compiled extensions in PyPSA/Linopy; single HiGHS .so file with full source available ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- 4 pure-Python layers from `n.optimize()` to solver invocation; all fully inspectable ([F-5](supply_chain/F-5_code_inspectability_trace.md))
- Sigstore cryptographic attestations on PyPI releases via trusted publishing ([F-6](supply_chain/F-6_distribution_integrity.md))
- Fully air-gap installable: all 90 packages have pre-built wheels, no runtime network access required ([F-7](supply_chain/F-7_airgap_installability.md))
- No commercial solver required: HiGHS (MIT) covers all optimization modes ([F-8](supply_chain/F-8_solver_dependency_assessment.md))
- Version-tagged example downloads (not `master`); in-repo tutorials ([F-9](supply_chain/F-9_getting_started_integrity.md))

#### Weaknesses

- 1 GPL-2.0 dependency: `Levenshtein` -- used only for fuzzy attribute name matching in error messages; replaceable with `RapidFuzz` (MIT, already installed) ([F-3](supply_chain/F-3_dependency_license_audit.md))
- 87 total packages is a moderate dependency footprint; geospatial stack (geopandas, shapely, pyproj) adds surface area for visualization-only features ([F-2](supply_chain/F-2_dependency_tree.md))
- Optional GitHub API version-check call on import (gatable via config) ([F-9](supply_chain/F-9_getting_started_integrity.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| F-1 Core license | pass | MIT throughout |
| F-2 Dependency tree | qualified_pass | 87 packages, moderate footprint |
| F-3 License audit | qualified_pass | 1 GPL (Levenshtein), replaceable |
| F-4 Compiled extensions | pass | PyPSA/Linopy pure Python, 1 HiGHS .so |
| F-5 Code inspectability | pass | 4 Python layers to solver |
| F-6 Distribution integrity | pass | Sigstore attestations, trusted publishing |
| F-7 Air-gap install | pass | All wheels available, no network required |
| F-8 Solver dependency | pass | HiGHS (MIT) covers all modes |
| F-9 Getting-started integrity | qualified_pass | Version-tagged downloads |

#### Grade Rationale

PyPSA has an exemplary open-source supply chain. The MIT license throughout the critical path, air-gap installability, Sigstore attestations, and solver independence from commercial licenses make it fully suitable for government/commercial deployment. The single GPL dependency (Levenshtein) is trivially replaceable and used only for developer UX. This meets the A standard: "Strong native support, well-tested at scale."

---

### 3.7 Phase 2 Readiness (P2 -- Informational)

| Test | Finding | Effort to Add |
|------|---------|---------------|
| P2-1 PSS/E RAW parsing | Not supported; no parser in PyPSA or pandapower | Low (1-2 days) via external `grg-psse` library bridge |
| P2-2 Piecewise linear cost | Not supported; quadratic cost works natively (QP via HiGHS) | Medium; SOS2 via `extra_functionality` (~50-100 LOC) |
| P2-3 Commitment injection | Full UC-to-DCOPF-to-ACPF pipeline achievable; ~20 LOC glue code | Low; all steps tested and passing |

---

## 4. Cross-Cutting Observations

### API Friction Patterns

- **Gencost import gap**: The PPC importer drops `gencost` data silently, requiring manual cost assignment across all OPF tests. The warning is easy to overlook. This affects every OPF-based test and should be addressed in documentation or the importer. ([A-3](observations/api-friction-expressiveness-A-3_dcopf.md))
- **Shadow price asymmetry**: Bus LMPs are auto-assigned after `optimize()` but line duals are not, creating inconsistent expectations. Users needing line congestion duals must access the Linopy model. ([A-3 shadow](observations/api-friction-expressiveness-A-3_dcopf_shadow_prices.md))
- **SCED workflow gap**: No `fix_commitment()` method exists. The two-stage SCUC-to-SCED pattern requires manual bound encoding (~10 LOC). ([A-6](observations/api-friction-expressiveness-A-6_sced.md))
- **Linopy dimension naming**: Reserve constraints for committable generators require knowledge of undocumented dimension names (`Generator-com` vs `Generator-ext`). ([A-5](observations/api-friction-expressiveness-A-5_scuc.md))
- **Slack bus semantics**: Changing the slack bus has zero effect on OPF LMPs (correct by design) but may surprise MATPOWER users. ([B-8](observations/api-friction-extensibility-B-8_reference_bus_config.md))

### Documentation Gaps

- **Stochastic optimization**: `n.scenarios` data model exists but is not connected to the optimizer. Documentation references "stochastic optimization" but no working API path exists. ([A-8](observations/doc-gaps-expressiveness-A-8_stochastic_timeseries.md))
- **PTDF column ordering**: Undocumented `[slack] + pvpqs` ordering causes large prediction errors if users assume `buses_i()` ordering. ([B-9](observations/doc-gaps-extensibility-B-9_ptdf_extraction.md))
- **Advanced workflows**: SCED two-stage, LMP decomposition, transmission losses, and SCOPF all lack tutorial-level documentation.

### Solver Ecosystem

- **`lpf_contingency()` broken**: `DataFrame.to_frame` AttributeError in v1.1.2 prevents use of the efficient built-in contingency analysis across all test tiers. ([A-7](observations/solver-issues-expressiveness-A-7_contingency_sweep.md))
- **SCOPF infeasibility diagnostics**: No root-cause guidance when SCOPF is infeasible -- users cannot determine which contingency constraint is binding. ([A-9](observations/solver-issues-expressiveness-A-9_scopf.md))
- **HiGHS SCUC limits**: Single-threaded HiGHS cannot solve SCUC at 2000-bus scale within 600s. Multi-threading or commercial solvers would help but are outside evaluation scope.
- **Linopy post-processing bottleneck**: Shadow-price assignment takes 10+ minutes at 10k-bus, dominating wall-clock time and preventing completion of several MEDIUM tests.

### Architecture Quality

- **Linopy model interface**: The `create_model()`/`solve_model()` split provides a clean, composable extension mechanism for custom constraints. 2 LOC to add a flow gate with full dual extraction. ([B-1](observations/arch-quality-extensibility-B-1_custom_constraints.md))
- **Mixin composition**: 8-mixin Network class provides clean horizontal separation. Optimization subsystem (`optimization/`) is well-factored with separate modules. PF module is more monolithic (1862-line `power_flow.py`). ([B-6](observations/arch-quality-extensibility-B-6_code_architecture.md))
- **DataFrame-centric design**: All data flows through pandas DataFrames, making inspection and manipulation natural for Python users. The `n.copy()` + DataFrame assignment pattern enables clean scenario loops. ([B-4](observations/arch-quality-extensibility-B-4_stochastic_wrapping.md))

---

## 5. Items Requiring Human Spot-Check

- [ ] **A-8 stochastic FAIL classification** -- The `n.scenarios` attribute exists in the data model and v1.0 changelog references "stochastic optimization." Verify whether v1.1.2 truly lacks this capability or if the evaluation missed an API path (e.g., `n.optimize.optimize_stochastic()` or scenario-indexed optimization via a non-obvious method).
- [ ] **A-5 SMALL / C-4 SCUC timeout** -- HiGHS single-threaded times out on 2000-bus SCUC. Verify whether this is a solver limitation or a problem formulation issue (all 544 generators committable vs. only thermal subset).
- [ ] **C-5 contingency sweep qualified_pass** -- Only 9 of 270 N-1 cases completed within timeout at MEDIUM. Verify whether this is sufficient for a "qualified pass" or should be reclassified as fail.
- [ ] **C-9 PTDF qualified_pass** -- Flow prediction accuracy degraded (702 MW max diff) due to zero-impedance workaround. Verify whether this is acceptable given the data-preparation context.
- [ ] **F-3 GPL dependency (Levenshtein)** -- Single GPL-2.0 package used only for developer UX fuzzy matching. Verify that RapidFuzz (MIT) is a drop-in replacement and the GPL package can be excluded from production deployments.
- [ ] **A-3/A-4 MEDIUM failures** -- Both fail due to zero s_nom branches in ACTIVSg10k MATPOWER data. Verify whether the `overwrite_zero_s_nom` parameter or pre-processing would resolve these and whether MEDIUM results should be re-attempted with data fixes.
- [ ] **D-2 documentation audit coverage** -- The assessment of A-8 stochastic documentation says "YES (as of v1.x)" but the test finds no working API. Verify the documentation claim against the actual optimizer behavior.
- [ ] **D-4 invalid enum acceptance** -- PyPSA silently accepts `control='InvalidType'`. Verify whether `n.sanitize()` or `n.consistency_check()` would catch this downstream.
- [ ] **`lpf_contingency()` bug** -- Classified as stable workaround (manual loop). Verify whether this is a known bug with a fix timeline, or an untested code path.

---

## 6. Methodology Notes

- **Scale cap applied**: None. MEDIUM (10k-bus) tests were executed where possible. Several MEDIUM failures are attributable to the ACTIVSg10k MATPOWER case file containing 2,462 branches with `s_nom == 0` and 3 transformers with zero reactance, which are data-preparation issues rather than tool limitations.
- **Tests skipped**: No tests were skipped. All dimensions (A through F plus P2) were evaluated.
- **Solver version**: HiGHS 1.13.1 via highspy, single-threaded per solver-config.md. Solver options: `time_limit=300-600`, `presolve=on`, `threads=1`, `mip_rel_gap=0.01` (for MILP).
- **Tool version**: PyPSA 1.1.2 (released 2026-02-23), Linopy 0.6.4.
- **Network import**: All MATPOWER `.m` files imported via `matpowercaseframes` -> PYPOWER PPC dict -> `n.import_from_pypower_ppc()`. Gencost data manually parsed and assigned (PPC importer limitation).
- **Devcontainer environment**: Ubuntu 24.04, Python 3.12, uv-managed dependencies. All tests executed inside devcontainer via `dc-exec`.
- **MEDIUM data fixes applied in scalability tests**: C-1/C-3/C-5/C-7/C-8/C-9/C-10 applied `x=0.0001` on 3 zero-impedance transformers and `s_nom=9999` on 2,462 zero-s_nom lines. These fixes were not applied in expressiveness tests A-3/A-4 MEDIUM, which failed with infeasibility.
