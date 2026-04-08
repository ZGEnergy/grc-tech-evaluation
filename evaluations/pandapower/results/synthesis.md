# Synthesis Report: pandapower 3.4.0

**Tool version:** pandapower 3.4.0
**Protocol version:** v11
**Scale cap:** MEDIUM
**FNM status:** Suite G executed (FNM_PATH set)
**Date:** 2026-03-24

---

## 1. Executive Summary

pandapower is a mature, well-architected Python power flow tool with a DataFrame-centric data model and an embedded PYPOWER solver. It excels at steady-state network analysis (AC/DC power flow, basic DC OPF, topology operations) with strong accessibility (sub-6-second install-to-first-solve, 39-package dependency tree, all permissive licenses) and operational adoption by European DSOs/TSOs including Netze BW, 50Hertz, and UK Power Networks. Gate status: all three networks ingested successfully (3/3 pass). The tool's primary limitations are architectural: no unit commitment, no multi-period optimization, no lossy DC OPF, no solver swap mechanism, and no public API for custom OPF constraint injection. The OPF solver is a hardcoded PYPOWER interior-point method with no extensibility points, constraining both expressiveness and scalability at the MEDIUM tier (62s DC OPF solve, 2.35 GB memory on 10k-bus network). Scale cap MEDIUM applied.

---

## 2. Test Results Summary

| Criterion | Tests Passed | Tests Failed | Partial/Qualified | Confidence | Key Evidence |
|-----------|-------------|-------------|-------------------|------------|--------------|
| Problem Expressiveness | 4/10 | 4/10 | 2/10 | High | Native PF/OPF strong; no UC, lossy OPF, distributed slack OPF, or multi-period |
| Extensibility | 6/8 | 0/8 | 2/8 | High | DataFrame model excellent; OPF extensibility blocked by closed solver |
| Scalability | 5/10 | 5/10 | 0/10 | High | PF scales to MEDIUM; DCOPF slow (62s); 2 cascaded, 3 independent fails |
| Workforce Accessibility | 5/5 informational | -- | -- | High | Sub-6s install, strong docs for core PF, weak OPF diagnostics |
| Maturity & Sustainability | 7/7 informational | -- | -- | High | 19 releases/24mo, 842 commits/12mo, European utility adoption |
| Supply Chain (Gate) | 9/9 informational | -- | -- | High | BSD license, clean deps, Sigstore provenance, air-gap installable |

**Note:** Gate tests (G-1/G-2/G-3) excluded from pass rate statistics. All informational tests (D/E/F series) are not counted in pass/fail tallies.

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness (Suite A)

#### Strengths
- Native DC power flow with structured DataFrame output ([A-1](expressiveness/A-1_dcpf_TINY.md))
- Native AC power flow with Newton-Raphson, flat/DC start, convergence in 4 iterations ([A-2](expressiveness/A-2_acpf_TINY.md))
- Native DC OPF with differentiated costs, LMP extraction via `res_bus.lam_p`, branch shadow prices ([A-3](expressiveness/A-3_dcopf_TINY.md))
- Clean DC OPF to ACPF feasibility workflow within a single network object ([A-4](expressiveness/A-4_ac_feasibility_check_TINY.md))

#### Weaknesses
- No unit commitment formulation -- no binary variables, startup costs, or temporal coupling [tool-specific] ([A-5](expressiveness/A-5_scuc_TINY.md))
- No lossy DC OPF and no LMP decomposition into energy/congestion/loss components [tool-specific] ([A-10](expressiveness/A-10_lossy_dcopf_lmp_decomposition.md))
- Distributed slack not available in OPF -- `rundcopp(distributed_slack=True)` silently ignored via `**kwargs` [tool-specific] ([A-11](expressiveness/A-11_distributed_slack_opf.md))
- No native multi-period DCOPF with inter-temporal storage coupling [tool-specific] ([A-12](expressiveness/A-12_multiperiod_dcopf_storage.md))

#### Workarounds Required
- A-6 (SCED): Sequential single-period DCOPF with manual ramp-rate bound manipulation -- **fragile**, ed_only mode, blocked_by A-5 ([A-6](expressiveness/A-6_sced_TINY.md))
- A-9 (SCOPF): Manual PTDF/LODF construction + scipy.optimize.linprog, bypassing pandapower OPF entirely -- **blocking** ([A-9](expressiveness/A-9_scopf_TINY.md))

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| A-1 | TINY | pass | -- | -- | 5.78s | 134 |
| A-2 | TINY | pass | -- | -- | 17.23s | 181 |
| A-3 | TINY | pass | -- | -- | 4.77s | 305 |
| A-4 | TINY | pass | -- | -- | 6.31s | 293 |
| A-5 | TINY | fail | -- | blocking | 4.17s | 80 |
| A-6 | TINY | partial_pass | A-5 | fragile (ed_only) | 3.13s | 339 |
| A-9 | TINY | partial_pass | -- | blocking | 1.03s | 561 |
| A-10 | TINY | fail | -- | blocking | 2.24s | 242 |
| A-11 | TINY | fail | -- | blocking | 6.42s | 331 |
| A-12 | TINY | fail | -- | blocking | 2.34s | 289 |

**Independent failures: 4** (A-5, A-10, A-11, A-12). **Partial passes: 2** (A-6 blocked_by A-5; A-9 independent).

#### Findings Summary

pandapower demonstrates strong native capability for steady-state power flow and basic DC OPF with LMP extraction. The tool's core strength is its single-period PF/OPF pipeline backed by the embedded PYPOWER solver. Blocking limitations cluster around optimization extensibility: no unit commitment, no temporal coupling, no lossy formulation, and no distributed slack in OPF. These are all [tool-specific] architectural boundaries, not solver limitations. The A-6 SCED test achieves ed_only mode through a fragile sequential workaround. The A-9 SCOPF partial_pass required bypassing pandapower's OPF entirely to build a manual LP.

---

### 3.2 Extensibility (Suite B)

#### Strengths
- First-class NetworkX graph bridge via `create_nxgraph()` with impedance-weighted edges ([B-2](extensibility/B-2_graph_access.md))
- Clean N-M contingency sweep via in-service toggling, 3,276 cases at 6.4 ms each ([B-3](extensibility/B-3_contingency_sweep.md))
- Stochastic scenario wrapping with 240 sequential OPF solves, 22.3 ms per solve ([B-4](extensibility/B-4_stochastic_scenario_wrapping.md))
- DataFrame-native results with trivial CSV export (4 LOC) ([B-5](extensibility/B-5_interoperability.md))
- Clean 6-layer architecture with well-separated concerns ([B-6](extensibility/B-6_code_architecture.md))
- PTDF computation via native `makePTDF()` with machine-precision accuracy ([B-9](extensibility/B-9_ptdf_extraction.md))

#### Weaknesses
- No public API for custom OPF constraint injection -- requires monkey-patching `_optimal_powerflow` [tool-specific] ([B-1](extensibility/B-1_custom_constraints.md))
- OPF result dict (containing duals/multipliers) discarded during result extraction [tool-specific] ([B-1](extensibility/B-1_custom_constraints.md))

#### Workarounds Required
- B-1 (Custom constraints): Replicate `_optimal_powerflow`, monkey-patch module reference, capture PYPOWER result dict -- **fragile** ([B-1](extensibility/B-1_custom_constraints.md))
- B-8 (Reference bus): 5-6 API calls to remove/recreate ext_grid + gen elements with manual cost transfer -- **stable** ([B-8](extensibility/B-8_reference_bus_config.md))

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| B-1 | TINY | partial_pass | -- | fragile | 1.11s | 401 |
| B-2 | TINY | pass | -- | -- | 0.94s | 152 |
| B-3 | TINY | pass | -- | -- | 22.16s | 258 |
| B-4 | TINY | pass | -- | -- | 6.01s | 341 |
| B-5 | TINY | pass | -- | -- | 1.19s | 143 |
| B-6 | TINY | pass | -- | -- | 0.69s | 251 |
| B-8 | TINY | qualified_pass | -- | stable | 1.05s | 399 |
| B-9 | TINY | pass | -- | -- | 1.12s | 255 |

**Independent failures: 0.** **Partial: 1** (B-1). **Qualified: 1** (B-8).

#### Findings Summary

pandapower's extensibility is strong for data access, graph operations, and scenario orchestration -- the DataFrame-centric design and NetworkX bridge are among its best architectural features. The critical gap is OPF extensibility: the embedded PYPOWER solver is a closed system with no public hook for custom constraints or dual extraction. This single limitation (B-1 fragile workaround) has cascading consequences for SCOPF (A-9), interface flow limits, and any formulation beyond the built-in constraint set. The B-8 reference bus workaround is verbose but stable [tool-specific: ext_grid/gen architectural distinction].

---

### 3.3 Scalability (Suite C)

#### Strengths
- DCPF on MEDIUM (10k buses) in 1.04s, 31 MB memory ([C-1](scalability/C-1_dcpf_medium.md))
- ACPF on MEDIUM in 2.53s (standard NR) / 0.13s (lightsim2grid), 5 NR iterations ([C-2](scalability/C-2_acpf_medium.md))
- AC feasibility converges at 0% relaxation on both SMALL and MEDIUM ([C-5 SMALL](scalability/C-5_ac_feasibility_progressive_SMALL.md), [C-5 MEDIUM](scalability/C-5_ac_feasibility_progressive_MEDIUM.md))
- PTDF on MEDIUM (12,706 x 10,000 matrix) computed in 10.3s ([C-9](scalability/C-9_ptdf_medium.md))

#### Weaknesses
- DCOPF on MEDIUM takes 62s and 2.35 GB memory using PYPOWER PIPS [solver-specific: PYPOWER interior-point at scale] ([C-3](scalability/C-3_dcopf_medium.md))
- No solver swap mechanism -- PYPOWER PIPS is hardcoded with no parameter to select alternatives [tool-specific] ([C-7](scalability/C-7_solver_swap.md))
- SCOPF at MEDIUM scale: OOM at ~32 GB due to full N-1 constraint matrix construction [tool-specific: no native SCOPF forces full matrix build] ([C-8](scalability/C-8_scopf_medium.md))

#### Workarounds Required
- None for passing tests. Failing tests have no viable workarounds at MEDIUM scale.

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | Memory |
|------|---------|--------|------------|------------|------|--------|
| C-1 | MEDIUM | pass | -- | -- | 1.04s | 31 MB |
| C-2 | MEDIUM | pass | -- | -- | 2.53s | 39 MB |
| C-3 | MEDIUM | pass | -- | -- | 62.4s | 2,351 MB |
| C-4 | SMALL | fail | A-5 | blocking (cascaded) | -- | -- |
| C-5 | SMALL | pass | -- | -- | 2.22s | 27 MB |
| C-5 | MEDIUM | pass | -- | -- | 2.77s | 39 MB |
| C-7 | MEDIUM | fail | -- | blocking | -- | -- |
| C-8 | MEDIUM | fail | -- | blocking (OOM) | >15min | ~32 GB |
| C-9 | MEDIUM | pass | -- | -- | 289s | 5,404 MB |
| C-10 | MEDIUM | fail | A-11 | blocking (cascaded) | -- | -- |

**Independent failures: 3** (C-7, C-8, C-3 passes but notable for slow time). **Cascaded failures: 2** (C-4 from A-5, C-10 from A-11).

#### Findings Summary

pandapower's power flow solvers scale well to MEDIUM -- DCPF and ACPF are fast with reasonable memory. The scalability bottleneck is the OPF: PYPOWER's PIPS interior-point solver takes 62 seconds on 10k-bus DCOPF with 2.35 GB memory [solver-specific], and there is no mechanism to swap to a faster solver like HiGHS [tool-specific]. SCOPF at MEDIUM fails with OOM because the only approach is full constraint matrix construction [tool-specific]. The two cascaded failures (C-4 from A-5, C-10 from A-11) reflect expressiveness gaps that propagate to scalability. The lightsim2grid accelerator provides a 19x speedup for ACPF but shows no benefit for DCOPF (which uses PYPOWER PIPS, not NR).

---

### 3.4 Workforce Accessibility (Suite D)

#### Strengths
- Sub-6-second install-to-first-solve, no system dependencies or compiler toolchain ([D-1](accessibility/D-1_install_to_first_solve.md))
- 3/10 Suite A tests implementable from documentation alone (A-1, A-2, A-3) ([D-2](accessibility/D-2_documentation_audit.md))
- 14/16 examples run without modification ([D-3](accessibility/D-3_example_verification.md))
- Concise API for core operations: 1 call for PF, 1 + N cost calls for OPF ([D-5](accessibility/D-5_code_volume_comparison.md))

#### Weaknesses
- No explicit scope statement in documentation -- users cannot distinguish "not documented" from "not implemented" without source code ([D-2](accessibility/D-2_documentation_audit.md))
- OPF diagnostics are poor -- boolean `converged` flag only, no infeasibility or convergence progress information [tool-specific] ([D-4](accessibility/D-4_error_quality.md))
- `**kwargs` passthrough silently absorbs invalid parameters (`distributed_slack=True` on `rundcopp`) ([D-4](accessibility/D-4_error_quality.md))
- Convergence residual not extractable; iteration count requires private `net._ppc["iterations"]` ([D-4](accessibility/D-4_error_quality.md))
- Getting-started example fails (zero-length line divide-by-zero); case9 DC OPF silently fails ([D-3](accessibility/D-3_example_verification.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| D-1 | informational | 5.35s cold install-to-first-solve |
| D-2 | informational | 3/10 from docs only; 7/10 need source |
| D-3 | informational | 14/16 examples pass; 2 failures |
| D-4 | informational | OPF error quality: POOR; element creation: GOOD |
| D-5 | informational | 2,185 LOC total Suite A; core API concise |

#### Findings Summary

pandapower has excellent first-contact accessibility (fast install, clean Python API, DataFrame results) but degrades for advanced use cases. Core power flow documentation is strong; OPF and advanced optimization documentation has significant gaps, particularly the absence of explicit scope boundaries. The OPF solver's silent failure mode (boolean-only convergence flag with no diagnostics) is the most significant accessibility concern for production use.

---

### 3.5 Maturity & Sustainability (Suite E)

#### Strengths
- 19 releases in 24 months with consistent semver and multi-branch maintenance ([E-1](maturity/E-1_release_cadence.md))
- 842 commits by 45 unique committers in trailing 12 months, no dormant months ([E-2](maturity/E-2_commit_activity.md))
- Bus factor of 3; top reviewer at 43.8% (below 60% threshold) ([E-3](maturity/E-3_contributor_concentration.md))
- Dual institutional anchoring (University of Kassel + Fraunhofer IEE) with diversified funding ([E-4](maturity/E-4_funding_model.md))
- 100% issue acknowledgment rate, 14-day median close time (excluding outliers) ([E-5](maturity/E-5_issue_tracker_health.md))
- Comprehensive CI: 28 jobs, Python 3.10-3.14, mypy, Codecov 72% ([E-6](maturity/E-6_ci_test_coverage.md))
- Confirmed production deployments at Netze BW, 50Hertz, UK Power Networks; government-commissioned grid studies ([E-7](maturity/E-7_operational_adoption.md))

#### Weaknesses
- Reviewer pool concentrated in 3 individuals (heckstrahler, vogt31337, KS-HTK) -- all code quality gates depend on this group ([E-3](maturity/E-3_contributor_concentration.md))
- Persistent CI "failures" from non-core jobs (downstream compat, deprecation warnings) -- CI hygiene concern ([E-6](maturity/E-6_ci_test_coverage.md))
- 72% test coverage is adequate but below industry best practice ([E-6](maturity/E-6_ci_test_coverage.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| E-1 | informational | 19 releases/24mo, multi-branch maintenance |
| E-2 | informational | 842 commits/12mo, 45 contributors |
| E-3 | informational | Bus factor 3; reviewer pool of 3 |
| E-4 | informational | Uni Kassel + Fraunhofer IEE dual anchor |
| E-5 | informational | 152 open issues, 14-day median close |
| E-6 | informational | 72% coverage, 28 CI jobs, Python 3.10-3.14 |
| E-7 | informational | 3 confirmed DSO/TSO production deployments |

#### Findings Summary

pandapower demonstrates strong maturity for an academic-origin tool. The combination of institutional backing (Fraunhofer IEE), operational adoption (European DSOs/TSOs), active development (842 commits/year), and production-grade release practices (semver, multi-branch, Sigstore) indicates a project operating at a level above most academic power system tools. The primary maturity risk is reviewer concentration -- the 3-person review pool is a single point of failure for code quality.

---

### 3.6 Supply Chain (Suite F)

#### Strengths
- BSD license (permissive, no copyleft) ([F-1](supply_chain/F-1_core_license.md))
- 39-package dependency tree, max depth 3, all versions pinned via uv.lock ([F-2](supply_chain/F-2_dependency_tree.md))
- All dependencies permissive except optional LightSim2Grid (MPL 2.0, weak copyleft, file-level only) ([F-3](supply_chain/F-3_dependency_license_audit.md))
- All compiled extensions have publicly available source; no opaque binaries ([F-4](supply_chain/F-4_compiled_extension_audit.md))
- Entire PF execution path is readable Python; sole compiled step is scipy SuperLU ([F-5](supply_chain/F-5_code_inspectability.md))
- Sigstore provenance attestations, Trusted Publishing via GitHub Actions ([F-6](supply_chain/F-6_distribution_integrity.md))
- Air-gap installable via pre-downloaded wheels; no runtime network access ([F-7](supply_chain/F-7_airgap_installability.md))
- Self-contained solver (embedded PYPOWER) -- no external solver binary required ([F-8](supply_chain/F-8_solver_dependency.md))

#### Weaknesses
- Tutorials not shipped inside pip package (must clone repo) ([F-9](supply_chain/F-9_getting_started_integrity.md))
- Unversioned `pip install pandapower` in official docs ([F-9](supply_chain/F-9_getting_started_integrity.md))

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| F-1 | informational | BSD license |
| F-2 | informational | 39 packages, depth 3 |
| F-3 | informational | 1 MPL 2.0 (optional); rest permissive |
| F-4 | informational | 216 .so files, all source-available |
| F-5 | informational | Full PF path in readable Python |
| F-6 | informational | Sigstore attestations, Trusted Publishing |
| F-7 | informational | Air-gap installable |
| F-8 | informational | Embedded PYPOWER, no external solver |
| F-9 | informational | Versioned ReadTheDocs; tutorials not in pip |

#### Findings Summary

pandapower has an exemplary supply chain profile. The BSD license, fully inspectable execution path, embedded solver, air-gap installability, and Sigstore provenance make it one of the cleanest supply chain profiles possible for a Python power system tool. The only non-permissive dependency (LightSim2Grid, MPL 2.0) is optional and excludable.

---

### 3b. FNM Ingestion Findings (Suite G)

#### Data Model Fidelity

**G-FNM-1 (Intermediate Ingestion):** FAIL. pandapower has no PSS/E parser of any kind. The tool cannot ingest the 17-table intermediate CSV format. All FNM testing proceeds via MATPOWER fallback path (`fnm_main_island.m` via `matpowercaseframes` + `from_ppc`). The MATPOWER path aggregates per-load records (8,576 vs ~15,000 expected) and reclassifies branches by voltage level rather than PSS/E record type. ([G-FNM-1](fnm_ingestion/G-FNM-1_intermediate_ingestion.md))

**G-FNM-2 (Field Coverage):** SKIP, blocked by G-FNM-1. Prior v10 assessment via MATPOWER path found 100% DCPF-critical coverage (19/19), 55.8% ACPF-critical coverage (29/52), and 27.6% informational coverage (24/87). The 55.8% ACPF-critical gap includes area interchange controls, switched shunt parameters, and transformer control modes. ([G-FNM-2](fnm_ingestion/G-FNM-2_field_coverage_audit.md))

*Expressiveness implication:* The absence of PSS/E parsing is a blocking gap for workflows starting from ISO-provided RAW files, the standard North American interchange format.

#### Power Flow Verification

**G-FNM-3 (DCPF Verification):** FAIL (hard-fail triggered). Aggregate performance is strong: 99.64% of buses pass VA tolerance, 99.67% of branches pass flow tolerance, and bus injection power balance passes at machine precision (max mismatch 8.6e-11 p.u.). However, a localized cluster of ~101 subtransmission buses produces systematic 14-21 degree angle deviations, causing one branch to exceed the 50% flow deviation hard-fail ceiling (596.6%). The outlier cluster has zero transformer adjacency, ruling out formulation difference classification. This is attributed to localized impedance handling differences in the MATPOWER PPC import path [tool-specific]. ([G-FNM-3](fnm_ingestion/G-FNM-3_dcpf_verification.md))

**G-FNM-4 (ACPF Convergence):** INFORMATIONAL -- infeasible at all relaxation levels (0%, 10%, 20%). pandapower's internal Newton-Raphson solver fails to converge on the ~28,000-bus FNM at 100 iterations per attempt. Contributing factors: PPC import flattens transformer AC data (tap control modes, switched shunt steps), the ~101 outlier buses create Jacobian ill-conditioning, and pandapower uses its own NR implementation (not Ipopt) which may have different convergence properties on ill-conditioned large-scale networks. ([G-FNM-4](fnm_ingestion/G-FNM-4_acpf_convergence.md))

*Scalability implication:* DCPF solves the ~28,000-bus FNM in 2.9 seconds, demonstrating adequate LARGE-tier DCPF scalability. ACPF cannot be assessed at LARGE tier due to convergence failure, which is primarily an ingestion fidelity issue.

#### Supplemental Data Representability

**G-FNM-5:** 34% native, 23% extension, 43% external across 44 supplemental CSV fields. pandapower has no native concept of transmission interfaces/flowgates (INTERFACE.csv: 100% external), contingency definitions, trading hubs, or outage schedules. Extension mechanism (custom DataFrame columns) is stable and survives JSON round-trip, but cannot make the solver aware of interface constraints. ([G-FNM-5](fnm_ingestion/G-FNM-5_supplemental_csv_representability.md))

*Extensibility implication:* The 43% external rate means nearly half of FNM supplemental data requires parallel data structures outside pandapower, increasing integration complexity for congestion analysis workflows.

#### P2 Readiness

| Test | Finding |
|------|---------|
| P2-1 | No PSS/E parser; medium-high effort (2-4 weeks) for production converter ([P2-1](p2_readiness/P2-1_psse_raw_parsing.md)) |
| P2-2 | PWL costs work natively via `create_pwl_cost()` -- clean, documented API ([P2-2](p2_readiness/P2-2_piecewise_linear_costs.md)) |
| P2-3 | Commitment injection works via `in_service` flag -- low friction, idiomatic ([P2-3](p2_readiness/P2-3_commitment_injection.md)) |

---

## 4. Cross-Cutting Observations

### API Friction Patterns

- **Silent parameter absorption:** `rundcopp()` and `runopp()` accept arbitrary `**kwargs` without validation. `distributed_slack=True` is silently ignored on OPF functions, potentially misleading users. (Source: [A-11 observation](observations/api-friction-expressiveness-A-11_distributed_slack_opf.md))
- **Bus index mismatch:** `from_mpc` remaps MATPOWER 1-indexed bus numbers to 0-indexed pandas indices without prominent documentation. External data cross-referencing requires manual offset. (Source: [A-3 observation](observations/api-friction-expressiveness-A-3_dcopf.md))
- **PYPOWER userfcn hidden:** The `add_userfcn` callback system for OPF constraint injection exists internally but is not exposed through pandapower's public API. (Source: [A-9 observation](observations/api-friction-expressiveness-A-9_scopf.md), [B-1 observation](observations/api-friction-extensibility-B-1_custom_constraints.md))
- **Convergence diagnostics private:** NR iteration count accessible only via `net._ppc["iterations"]`; final residual not stored anywhere. (Source: [C-5 observation](observations/api-friction-scalability-C-5_ac_feasibility_progressive_SMALL.md))
- **Slack bus reconfiguration verbose:** Changing reference bus requires 5-6 API calls with element type juggling (ext_grid/gen distinction). (Source: [B-8 observation](observations/api-friction-extensibility-B-8_reference_bus_config.md))
- **No PSS/E parser:** Blocks intermediate CSV ingestion for all FNM workflows. (Source: [G-FNM-1 observation](observations/api-friction-fnm_ingestion-G-FNM-1_intermediate_ingestion.md))

### Documentation Gaps

- **No scope boundary statement:** Documentation never explicitly states what pandapower *cannot* do (no SCUC, no SCOPF, no multi-period OPF). Users must infer limits from feature absence. (Source: [D-2](accessibility/D-2_documentation_audit.md))
- **PYPOWER userfcn undocumented:** The OPF extensibility mechanism exists but is absent from pandapower's own documentation. Users must read PYPOWER source to discover it. (Source: [B-1 observation](observations/doc-gaps-extensibility-B-1_custom_constraints.md))
- **LMP interpretation absent:** `res_bus.lam_p` produced by OPF but not documented as an LMP or explained in economic terms. (Source: [D-2](accessibility/D-2_documentation_audit.md))

### Solver Ecosystem

- **Embedded PYPOWER solver only:** pandapower's OPF uses PYPOWER PIPS (interior-point) exclusively. No mechanism to swap to HiGHS, GLPK, or any external LP/MIP solver via parameter change [tool-specific]. (Source: [C-7](scalability/C-7_solver_swap.md))
- **PYPOWER PIPS scales poorly for OPF:** 62s and 2.35 GB for 10k-bus DCOPF [solver-specific]. Power flow scales well (DCPF 1s, ACPF 2.5s on same network). (Source: [C-3](scalability/C-3_dcopf_medium.md))
- **lightsim2grid provides 19x ACPF speedup** on MEDIUM but shows no benefit at MEDIUM scale due to Python pre/post-processing bottleneck. (Source: [C-2](scalability/C-2_acpf_medium.md))
- **Internal NR for ACPF, not Ipopt:** pandapower uses its own Newton-Raphson, not an external NLP solver. This affects convergence comparison with Ipopt-based tools on ill-conditioned networks [tool-specific]. (Source: [G-FNM-4 observation](observations/formulation-difference-fnm_ingestion-G-FNM-4_acpf_convergence.md))

### Architecture Quality

- **Positive:** Clean 6-layer architecture with well-separated concerns (public API, orchestration, data model conversion, problem formulation, solver, result extraction). DataFrame-to-numpy boundary is a well-defined data model separation. (Source: [B-6 observation](observations/arch-quality-extensibility-B-6_code_architecture.md))
- **Positive:** DataFrame-backed network model enables clean in-place contingency toggling and scenario orchestration. (Source: [B-3 observation](observations/arch-quality-extensibility-B-3_contingency_sweep.md))
- **Positive:** Exemplary NetworkX graph bridge design -- composable, well-documented, clean integration. (Source: [B-2 observation](observations/arch-quality-extensibility-B-2_graph_access.md))
- **Negative:** OPF result dict (duals, multipliers, shadow prices) discarded during result extraction back to DataFrames. Users needing constraint duals must access undocumented internals or monkey-patch the pipeline. (Source: [B-1 observation](observations/arch-quality-extensibility-B-1_custom_constraints.md))

### FNM Data Model

- **Load aggregation in PPC import:** Multiple PSS/E loads per bus aggregated into single pandapower load element, losing per-load granularity (8,576 vs ~15,000 expected). (Source: [G-FNM-1 observation](observations/fnm-data-model-fnm_ingestion-G-FNM-1_intermediate_ingestion.md))
- **ACPF-critical field coverage limited:** 55.8% via MATPOWER path (missing area interchange, switched shunt parameters, transformer control modes). (Source: [G-FNM-2 observation](observations/fnm-data-model-fnm_ingestion-G-FNM-2_field_coverage_audit.md))
- **No interface/flowgate or contingency definition models:** 43% of supplemental CSV fields are tool-external. Interface flow limits cannot be enforced in OPF. (Source: [G-FNM-5 observation](observations/fnm-data-model-fnm_ingestion-G-FNM-5_supplemental_csv_representability.md))
- **Thermal rating unit difference:** `line.max_i_ka` uses current (kA) not power (MVA), requiring voltage-dependent conversion at ingestion. (Source: [G-FNM-5 observation](observations/formulation-difference-fnm_ingestion-G-FNM-5_supplemental_csv_representability.md))

---

## 5. Items Requiring Human Spot-Check

- [ ] **A-9 (SCOPF) partial_pass classification** -- The workaround bypasses pandapower's OPF entirely (pandapower used only for PTDF extraction + data container). Verify whether "blocking workaround with partial capability demonstrated" warrants partial_pass vs fail.
- [ ] **B-1 (Custom constraints) partial_pass with fragile workaround** -- Monkey-patching `_optimal_powerflow` is classified as fragile. Verify this classification vs the underlying PYPOWER mechanism stability.
- [ ] **B-8 (Reference bus) qualified_pass with stable workaround** -- The workaround uses only public API but is verbose (5-6 calls). Verify qualified_pass is appropriate for a stable but friction-heavy workaround.
- [ ] **C-3 (DCOPF MEDIUM) pass at 62s** -- The test passes but the 62-second solve time and 2.35 GB memory are notable. Verify whether this timing is acceptable for the pass condition or should affect the scalability assessment.
- [ ] **G-FNM-3 hard-fail attribution** -- The 596.6% branch deviation is localized to ~101 buses with zero transformer adjacency. Verify whether "data ingestion error in PPC import path" is the correct attribution vs a potential formulation difference.
- [ ] **G-FNM-4 ACPF infeasibility** -- Non-convergence at all relaxation levels. Verify attribution split between ingestion path data loss (PPC flattening) vs solver limitation (internal NR vs Ipopt).
- [ ] **Solver-specific vs tool-specific attribution for C-3 timing** -- PYPOWER PIPS interior-point is slow at 10k scale. Is this solver-specific (a different solver in the same tool would be faster) or tool-specific (the tool cannot use a different solver)?
- [ ] **A-6 SCED mode classification** -- Confirmed `ed_only` (no commitment from A-5, sequential greedy dispatch). Verify this is correctly flagged as partial_pass with fragile workaround.

---

## 6. Methodology Notes

- **Scale cap applied:** MEDIUM (10,000-bus ACTIVSg10k). LARGE-tier testing conducted only via Suite G (FNM ingestion).
- **FNM status:** Suite G executed (FNM_PATH set). FNM ingested via MATPOWER fallback (`fnm_main_island.m`); no native PSS/E or intermediate CSV ingestion.
- **Tests skipped:** G-FNM-2 (blocked by G-FNM-1 PSS/E parser absence).
- **Solver versions:** PYPOWER PIPS interior-point (bundled, version tied to pandapower 3.4.0); scipy 1.16.3 (HiGHS via linprog for A-9 workaround); lightsim2grid 0.12.2 (optional ACPF accelerator).
- **Tool version:** pandapower 3.4.0 (installed via `uv sync` in devcontainer).
- **Python version:** 3.12 (Ubuntu 24.04 devcontainer).
- **Devcontainer environment:** Ubuntu 24.04 + Python 3.12 + Julia 1.10 + Octave + uv.
