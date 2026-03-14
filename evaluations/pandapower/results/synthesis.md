# Synthesis Report — pandapower (Contract )

**Tool version:** pandapower 3.4.0
**Protocol version:** v10
**Skill version:** v1
**Scale cap:** MEDIUM (all gate tests passed)
**Suite C SMALL gate:** Triggered (C-4 cascaded fail from A-5)
**FNM status:** Suite G executed (FNM_PATH set)

---

## 1. Executive Summary

pandapower is a mature, well-architected steady-state power system analysis tool with excellent AC/DC power flow capabilities, a clean DataFrame-based API, and strong supply chain properties (BSD license, fully inspectable pure-Python execution path, self-contained PYPOWER solver). However, it is fundamentally a network analysis tool, not a market simulation or optimization platform: it lacks SCUC, SCED, SCOPF, lossy OPF, distributed slack OPF, and multi-period OPF natively, resulting in 6 of 10 expressiveness tests failing with blocking workaround classifications. Supply chain passes the gate comfortably. The scale cap is MEDIUM; 8 MEDIUM-tier scalability tests were skipped due to a cascaded C-SMALL-gate failure from the missing SCUC capability (A-5), not from any actual scale limitation. FNM Suite G was completed: ingestion succeeded with stable workarounds, DCPF matched the reference on 99.6% of buses but triggered a hard-fail on localized outliers, and ACPF was infeasible at all relaxation levels.

---

## 2. Grade Recommendations

| Criterion | Recommended Grade | Confidence | Key Evidence |
|-----------|-------------------|------------|--------------|
| Problem Expressiveness | C+ | High | 4 pass + 6 independent blocking fails (SCUC, SCED, SCOPF, lossy OPF, distributed slack OPF, multi-period OPF); steady-state scope limitation |
| Extensibility | B | High | 6 pass + 1 qualified_pass (fragile) + 1 qualified_pass (stable); custom constraints require fragile monkey-patching; graph bridge and interop are exemplary |
| Scalability | C+ | Low | 2 executed (C-4 fail cascaded, C-5 SMALL pass); 8 MEDIUM tests skipped due to C-SMALL-gate; no actual scale failures observed; FNM DCPF solved 28K buses in 0.4s |
| Workforce Accessibility | B+ | High | Frictionless install (<2s to first solve); strong PF docs but no scope statement for missing features; OPF error diagnostics are poor; 15/16 examples pass |
| Maturity & Sustainability | A- | High | 19 releases in 24 months; 838 commits from 30 contributors; bus factor 3; Fraunhofer IEE + Uni Kassel backing; 72% test coverage; 952 citations |
| Supply Chain (Gate) | A | High | BSD license; all 37 deps permissive (1 optional MPL-2.0); no opaque binaries; Sigstore provenance; air-gap installable; self-contained solver |

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness (Suite A)

#### Strengths

- Native DC power flow with structured DataFrame output and sub-second solve times ([A-1](expressiveness/A-1_dcpf.md))
- Native AC power flow with Newton-Raphson, 4-iteration convergence on flat start, full P/Q/V/angle output ([A-2](expressiveness/A-2_acpf.md))
- Native DC OPF with LMP extraction via public `res_bus.lam_p` column and differentiated quadratic costs ([A-3](expressiveness/A-3_dcopf.md))
- Seamless DC OPF to AC feasibility check workflow within the same model context, no serialization needed ([A-4](expressiveness/A-4_ac_feasibility_check.md))

#### Weaknesses

- No SCUC capability — no binary variables, startup costs, or temporal coupling ([A-5](expressiveness/A-5_scuc.md))
- No SCED capability — blocked by A-5 and independently missing multi-period ED with ramp constraints ([A-6](expressiveness/A-6_sced.md))
- No SCOPF — contingency analysis is post-hoc only; OPF solver does not accept user-injected constraints ([A-9](expressiveness/A-9_scopf.md))
- No lossy DC OPF or LMP decomposition — PYPOWER DC OPF is hardcoded lossless B-theta ([A-10](expressiveness/A-10_lossy_dcopf_lmp_decomposition.md))
- No distributed slack OPF — `distributed_slack` parameter silently ignored by `rundcopp()` ([A-11](expressiveness/A-11_distributed_slack_opf.md))
- No multi-period DCOPF with storage — `run_timeseries()` runs independent solves without SoC linkage ([A-12](expressiveness/A-12_multiperiod_dcopf_storage.md))

#### Workarounds Required

- A-5 (SCUC): No workaround — **blocking**
- A-6 (SCED): No workaround — **blocking** (also blocked by A-5)
- A-9 (SCOPF): Building a complete external LP from PTDF data — **blocking**
- A-10 (Lossy OPF): No workaround — **blocking**
- A-11 (Distributed slack OPF): No workaround — **blocking**
- A-12 (Multi-period OPF): PandaModels.jl bridge exists but requires Julia runtime — **blocking** for pure Python

#### Evidence Summary

| Test | Network | Status | Blocked By | Workaround | Time (s) | LOC |
|------|---------|--------|------------|------------|----------|-----|
| A-1 | TINY | pass | -- | -- | 1.45 | 138 |
| A-2 | TINY | pass | -- | -- | 2.02 | 190 |
| A-3 | TINY | pass | -- | -- | 0.90 | 309 |
| A-4 | TINY | pass | -- | -- | 1.88 | 289 |
| A-5 | TINY | fail | -- | blocking | 0.79 | 80 |
| A-6 | TINY | fail | A-5 | blocking | 0.75 | 73 |
| A-9 | TINY | fail | -- | blocking | 0.83 | 257 |
| A-10 | TINY | fail | -- | blocking | 0.78 | 246 |
| A-11 | TINY | fail | -- | blocking | 2.07 | 338 |
| A-12 | TINY | fail | -- | blocking | 0.80 | 290 |

**Failure breakdown:** 5 independent fails (A-5, A-9, A-10, A-11, A-12) + 1 blocked (A-6 blocked by A-5).

#### Grade Rationale

pandapower passes 4 of 10 expressiveness tests. The 6 failures are all blocking with no available workaround within the tool's API. These failures are not bugs or missing features -- they reflect pandapower's design scope as a steady-state network analysis tool rather than a market simulation platform. The 5 independent blocking failures (SCUC, SCOPF, lossy OPF, distributed slack OPF, multi-period OPF) place pandapower at C+ for expressiveness: "Significant gaps, but NOT disqualifying." The 4 tests that pass (DCPF, ACPF, DCOPF, AC feasibility) are strong and clean, preventing a lower grade. C+ is appropriate because the tool excels at power flow and basic OPF but fundamentally cannot express market-relevant optimization formulations.

---

### 3.2 Extensibility (Suite B)

#### Strengths

- Exemplary NetworkX graph bridge via `topology.create_nxgraph()` -- BFS in 3 lines of code ([B-2](extensibility/B-2_graph_access.md))
- Efficient N-M contingency sweep using in-service toggling without model reconstruction; 3,276 cases at 4.7 ms/case ([B-3](extensibility/B-3_contingency_sweep.md))
- DataFrame-native results make CSV/DataFrame export trivial -- 4 lines of code ([B-5](extensibility/B-5_interoperability.md))
- Clean 6-layer architecture with well-separated concerns ([B-6](extensibility/B-6_code_architecture.md))
- PTDF matrix accessible via native `makePTDF()` with machine-precision accuracy ([B-9](extensibility/B-9_ptdf_extraction.md))
- Stochastic scenario wrapping works cleanly with 240 independent solves at 22 ms/solve ([B-4](extensibility/B-4_stochastic_scenario_wrapping.md))

#### Weaknesses

- Custom OPF constraint injection requires replicating internal `_optimal_powerflow` and monkey-patching ([B-1](extensibility/B-1_custom_constraints.md))
- OPF constraint duals discarded during result extraction -- must be captured via monkey-patch ([B-1](extensibility/B-1_custom_constraints.md))
- Slack bus reconfiguration requires 5-6 API calls with element-type juggling ([B-8](extensibility/B-8_reference_bus_config.md))

#### Workarounds Required

- B-1 (Custom constraints): Replicate `_optimal_powerflow`, monkey-patch, capture PYPOWER result dict -- **fragile**
- B-8 (Reference bus config): Remove/recreate ext_grid and gen elements with manual cost transfer -- **stable**

#### Evidence Summary

| Test | Network | Status | Blocked By | Workaround | Time (s) | LOC |
|------|---------|--------|------------|------------|----------|-----|
| B-1 | TINY | qualified_pass | -- | fragile | 0.95 | 396 |
| B-2 | TINY | pass | -- | -- | 0.86 | 156 |
| B-3 | TINY | pass | -- | -- | 16.60 | 262 |
| B-4 | TINY | pass | -- | -- | 6.01 | 341 |
| B-5 | TINY | pass | -- | -- | 1.19 | 143 |
| B-6 | TINY | pass | -- | -- | 0.69 | 251 |
| B-8 | TINY | qualified_pass | -- | stable | 1.05 | 399 |
| B-9 | TINY | pass | -- | -- | 1.12 | 255 |

**Failure breakdown:** 0 independent fails + 0 blocked. 2 qualified passes.

#### Grade Rationale

pandapower achieves 6 clean passes and 2 qualified passes in extensibility. The B-1 fragile workaround (custom constraint injection via monkey-patching) is a meaningful gap, but the underlying PYPOWER userfcn mechanism is architecturally sound and has been stable for years. B-8's stable workaround for slack bus reconfiguration is verbose but reliable. The DataFrame-native data model, graph bridge, and PTDF extraction are genuine strengths. This meets the B standard: "Supported with caveats, moderate friction." The B-1 fragile workaround prevents B+ ("one meaningful gap with stable workaround" -- this workaround is fragile, not stable).

---

### 3.3 Scalability (Suite C)

#### Strengths

- C-5 SMALL (AC feasibility): ACPF converged in 4 NR iterations at 0% relaxation on 2000-bus network, 1.3s solve time ([C-5 SMALL](scalability/C-5_ac_feasibility_progressive_SMALL.md))
- FNM DCPF (28K buses): Solved in 0.40 seconds -- strong DCPF scale performance (from [G-FNM-3](fnm_ingestion/G-FNM-3_dcpf_verification.md))

#### Weaknesses

- C-4 (SCUC SMALL): Blocked by A-5 -- cascaded failure from missing SCUC capability ([C-4](scalability/C-4_scuc_small.md))
- 8 MEDIUM-tier tests skipped (C-1, C-2, C-3, C-5M, C-7, C-8, C-9, C-10) due to C-SMALL-gate triggered by C-4

#### Workarounds Required

None tested at scale -- most tests were skipped.

#### Evidence Summary

| Test | Network | Status | Blocked By | Workaround | Time (s) | LOC |
|------|---------|--------|------------|------------|----------|-----|
| C-1 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-2 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-3 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-4 | SMALL | fail | A-5 | blocking | -- | -- |
| C-5 | SMALL | pass | -- | -- | 2.84 | 287 |
| C-5 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-7 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-8 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-9 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |
| C-10 | MEDIUM | skip | C-SMALL-gate | -- | -- | -- |

**Failure breakdown:** 0 independent fails + 1 blocked (C-4 blocked by A-5). 8 tests skipped due to C-SMALL-gate.

#### Grade Rationale

Scalability evidence is severely limited: only 2 tests were executed (C-4 fail cascaded, C-5 SMALL pass). The C-4 failure is entirely cascaded from A-5 (no SCUC) and does not reflect a scale limitation. The C-5 SMALL pass shows clean ACPF convergence on a 2000-bus network. FNM Suite G provides additional scale evidence: DCPF solves a 28K-bus network in 0.4s, demonstrating adequate DCPF scalability at the LARGE tier. However, ACPF was infeasible on the FNM. With only 1 passing test and 8 skipped tests, confidence is Low. C+ ("significant gaps but not disqualifying") is the conservative grade given the limited evidence -- the tool demonstrates scale capability for power flow (its core competency) but cannot be assessed for OPF, SCOPF, or SCUC at scale because those features do not exist. When uncertain, the lower grade is recommended.

---

### 3.4 Workforce Accessibility (Suite D)

#### Strengths

- Frictionless install: `uv sync` + first solve in under 2 seconds, no system dependencies ([D-1](accessibility/D-1_install_to_first_solve.md))
- Strong power flow documentation: DCPF, ACPF, basic OPF completable from docs alone ([D-2](accessibility/D-2_documentation_audit.md))
- 15 of 16 examples pass without modification ([D-3](accessibility/D-3_example_verification.md))
- Concise API for supported operations: DCPF is 1 call, results are DataFrame columns ([D-5](accessibility/D-5_code_volume_comparison.md))

#### Weaknesses

- No explicit scope statement: docs never state what pandapower *cannot* do -- users must infer from absence ([D-2](accessibility/D-2_documentation_audit.md))
- 7 of 10 Suite A tests needed source code inspection (either to confirm missing features or use internal APIs) ([D-2](accessibility/D-2_documentation_audit.md))
- OPF error diagnostics are poor: `converged=False` with no infeasibility reason, no constraint violation info ([D-4](accessibility/D-4_error_quality.md))
- `**kwargs` silently absorbs invalid parameters without warning ([D-4](accessibility/D-4_error_quality.md), observation from A-11)
- Disconnected buses with loads silently produce NaN -- no warning ([D-4](accessibility/D-4_error_quality.md))

#### Evidence Summary

| Test | Status | Key Finding |
|------|--------|-------------|
| D-1 | informational | Install + first solve in <2s; no friction |
| D-2 | informational | 3/10 completable from docs; 7 need source code |
| D-3 | informational | 15/16 examples pass; case9 DC OPF fails silently |
| D-4 | informational | OPF diagnostics poor; input validation mixed; disconnected bus silent |
| D-5 | informational | LOC compact for supported features; high for unsupported |

#### Grade Rationale

pandapower provides an excellent onboarding experience for its core competency (power flow) with frictionless installation, clean API, and strong documentation. The documentation gaps and poor OPF diagnostics are meaningful weaknesses but do not affect the primary use case. The `**kwargs` silent parameter absorption is an API design issue. This meets B+: "Mostly strong, one meaningful gap with stable workaround" -- the meaningful gap being the absence of scope documentation and poor OPF diagnostics, neither of which requires a workaround but both reduce usability for advanced use cases.

---

### 3.5 Maturity & Sustainability (Suite E)

#### Sub-criterion 5a: Demonstrated Maturity

- **E-1 (Release cadence):** 19 releases in 24 months, consistent semver, multi-branch maintenance
- **E-2 (Commit activity):** 838 commits, 30 unique committers in trailing 12 months
- **E-5 (Issue tracker):** 100% acknowledgment, 29-day median time-to-close, substantive responses
- **E-7 (Operational adoption):** Government-commissioned DSO planning study (Hessen), RTE France Grid2Op backend, 952 citations, 232K monthly PyPI downloads

**5a sub-grade: A**

#### Sub-criterion 5b: Sustainability Risk

- **E-3 (Contributor concentration):** Bus factor 3; top 3 contributors = 51.2% of lifetime commits; 3 active reviewers
- **E-4 (Funding model):** Dual-anchored in Fraunhofer IEE + University of Kassel; diversified funding (base + contract + EU grants)
- **E-6 (CI/test coverage):** 28-job CI pipeline; core tests pass on Python 3.10-3.14; 72% coverage; mypy, linting, docs build

**5b sub-grade: B+** (moderate concentration risk; reviewer pool of only 3)

#### Evidence Summary

| Test | Sub-criterion | Key Metric |
|------|---------------|------------|
| E-1 | 5a | 19 releases / 24 months |
| E-2 | 5a | 838 commits / 30 committers |
| E-3 | 5b | Bus factor 3; top reviewer 39.6% |
| E-4 | 5b | Fraunhofer IEE + Uni Kassel dual anchor |
| E-5 | 5a | 100% acknowledged; 29d median close |
| E-6 | 5b | 72% coverage; 28 CI jobs; core green |
| E-7 | 5a | Hessen DSO study; RTE Grid2Op; 952 citations |

#### Grade Rationale

pandapower demonstrates strong maturity with active development, diversified institutional backing, government-commissioned operational use, and comprehensive CI. The reviewer concentration (3 individuals cover 100% of code review) is a moderate sustainability risk but is mitigated by the broadening contributor base (30 active in last year vs. concentrated lifetime top 3). The composite grade of 5a=A and 5b=B+ yields A-: "Strong overall, one minor caveat" -- the caveat being reviewer concentration risk.

---

### 3.6 Supply Chain — Gate (Suite F)

#### Strengths

- BSD license with no copyleft obligations ([F-1](supply_chain/F-1_core_license.md))
- All 37 dependencies permissive (BSD/MIT/Apache); only LightSim2Grid is MPL-2.0 and optional ([F-3](supply_chain/F-3_dependency_license_audit.md))
- No opaque binaries; entire execution path is pure Python + auditable scipy ([F-4](supply_chain/F-4_compiled_extension_audit.md), [F-5](supply_chain/F-5_code_inspectability.md))
- Sigstore provenance attestations on PyPI artifacts ([F-6](supply_chain/F-6_distribution_integrity.md))
- Air-gap installable via wheel download; no runtime network access ([F-7](supply_chain/F-7_airgap_installability.md))
- Self-contained PYPOWER solver -- no external solver procurement needed ([F-8](supply_chain/F-8_solver_dependency.md))

#### Weaknesses

- Getting-started docs use unversioned `pip install pandapower` without pinning ([F-9](supply_chain/F-9_getting_started_integrity.md))
- Tutorials not shipped in pip package (must clone GitHub repo) ([F-9](supply_chain/F-9_getting_started_integrity.md))

#### Evidence Summary

| Test | Status | Key Finding |
|------|--------|-------------|
| F-1 | informational | BSD license, no copyleft |
| F-2 | informational | 37 packages, depth 3, all pinned via uv.lock |
| F-3 | informational | 29/37 BSD/MIT; 1 optional MPL-2.0 |
| F-4 | informational | All compiled components source-available |
| F-5 | informational | Full Python trace from API to spsolve |
| F-6 | informational | Sigstore provenance, semver, immutable PyPI |
| F-7 | informational | Fully air-gap installable |
| F-8 | informational | Self-contained PYPOWER solver; no external solver needed |
| F-9 | informational | Docs use unversioned install; tutorials not in package |

#### Grade Rationale

pandapower has an exemplary supply chain profile. BSD license, all-permissive dependency tree, fully inspectable execution path, Sigstore provenance, and a self-contained solver with no external binary dependencies. The only minor items are unversioned install commands in docs and tutorials not shipped in the pip package. This meets A: "Strong native support, well-tested at scale."

---

## 4. FNM Ingestion Findings (Suite G)

### Data Model Fidelity (G-FNM-1, G-FNM-2)

**G-FNM-1 (Ingestion):** All primary component counts match the manifest (30,307 buses, 33,840 merged branches, 100.0 baseMVA). Two stable workarounds were required: (1) manual PPC construction via `scipy.io.loadmat` because `from_mpc()` fails on the missing `version` field, and (2) pre-setting 28 zero RATE_A values to 9999 to work around a `from_ppc()` IndexError bug. Load aggregation reduced 15,062 individual loads to 8,576 per-bus entries (PPC format limitation). Branch classification differs from the intermediate format (voltage-level-based vs tap-ratio-based split) but the merged total matches exactly.

**G-FNM-2 (Field coverage):** 100% DCPF-critical field coverage (19/19). ACPF-critical coverage is 55.8% (29/52) -- gaps include area interchange controls, switched shunt discrete parameters, and remote regulation bus assignments, all inherent to the PPC import path's data flattening. These gaps are consistent with pandapower's ACPF non-convergence on the FNM (G-FNM-4).

### Power Flow Verification (G-FNM-3, G-FNM-4)

**G-FNM-3 (DCPF verification):** FAIL. Aggregate performance is strong: 99.64% of buses pass the 1.0-degree angle tolerance, 99.67% of branches pass the 10% flow tolerance. The hard-fail is triggered by a localized cluster of ~101 buses with 14-21 degree systematic deviations in the subtransmission/distribution network. The maximum branch flow deviation is 596.6% (exceeding the 50% threshold). These outliers have 0% transformer adjacency, ruling out formulation difference classification -- they are classified as data ingestion errors attributable to the MATPOWER PPC import path's handling of specific impedance details in a weakly-connected radial sub-network. The DCPF solver itself performs well (0.40s solve on 27,862 buses).

**G-FNM-4 (ACPF convergence):** INFORMATIONAL -- infeasible at all relaxation levels (0%, 10%, 20%). All five available NR algorithms (nr, iwamoto_nr, fdbx, fdxb, gs) failed to converge. Contributing factors: (1) PPC import path loses AC-critical transformer data, (2) localized topology anomalies from G-FNM-3, (3) possible Q-limit misinterpretation, (4) pandapower uses internal NR (not Ipopt) for ACPF. Peak memory: 97.7 MB. DCPF warm-start angles were extreme (max 536.9 degrees), indicating network-level conditioning issues.

### Supplemental Data Representability (G-FNM-5)

**G-FNM-5:** 34% native (N), 23% extension (E), 43% external (X) across 44 supplemental CSV fields. pandapower has no native market-layer concepts: interfaces (100% X), trading hubs (75% X), and outage schedules (50% X) must be maintained externally. The custom DataFrame column mechanism provides a clean extension path for E-classified fields (RATE_B/C/D, CKT, effective dates). This is the lowest native coverage among the six evaluated tools, reflecting pandapower's scope as a power flow tool without market abstractions.

**FNM impact on grades:** The FNM findings are additive evidence that strengthens the expressiveness C+ assessment (strong power flow, no market-layer concepts) and provides scalability data unavailable from Suite C (DCPF scales to 28K buses). The ACPF infeasibility on the FNM is attributable to the MATPOWER import path rather than the solver, consistent with the 55.8% ACPF-critical field coverage gap.

---

## 5. Cross-Cutting Observations

### API Friction Patterns

Five api-friction observations were recorded:

1. **Bus indexing mismatch:** `from_mpc` converts MATPOWER 1-indexed bus numbers to 0-indexed pandas indices without documentation (A-3, severity: low)
2. **Silent parameter absorption:** `rundcopp()` accepts `distributed_slack=True` via `**kwargs` with zero effect, no warning (A-11, severity: medium)
3. **Custom constraint injection barrier:** PYPOWER `userfcn` mechanism exists but requires replicating private `_optimal_powerflow` function (B-1, severity: high)
4. **Slack bus reconfiguration verbosity:** 5-6 API calls required due to ext_grid/gen element-type coupling (B-8, severity: medium)
5. **Convergence diagnostics via private attributes:** NR iteration count only accessible through `net._ppc["iterations"]` (C-5, severity: low)

The dominant pattern is that pandapower's public API covers basic use cases well but exposes internals through underscore-prefixed attributes and discards solver metadata during result extraction. The `**kwargs` passthrough in OPF functions is a notable design issue.

### Documentation Gaps

One doc-gaps observation was recorded:

1. **PYPOWER userfcn mechanism undocumented:** The `add_userfcn` callback system for custom OPF constraints is used internally but not documented in pandapower's own docs (B-1, severity: medium)

The broader documentation gap pattern (from D-2) is the absence of an explicit scope statement. pandapower's docs never state what the tool *cannot* do. Users must infer scope limitations from feature absence rather than from explicit documentation.

### Solver Ecosystem

pandapower embeds a fork of PYPOWER as its sole solver backend. No external solver binary is required for any standard operation. The internal solver stack includes:

- **DCPF:** Direct sparse linear solve via `scipy.sparse.linalg.spsolve` (SuperLU)
- **ACPF:** Newton-Raphson (5 algorithm variants) implemented in pure Python
- **DC OPF:** PYPOWER interior-point method (bundled)
- **AC OPF:** PYPOWER interior-point method (bundled)

The self-contained architecture is a supply chain strength but creates a solver quality limitation: users cannot swap in more robust solvers (e.g., Ipopt for ACPF, HiGHS for OPF) without the optional PandaModels.jl Julia bridge. The PYPOWER interior-point solver has documented convergence limitations (case9 DC OPF fails silently in D-3).

### Architecture Quality

Two arch-quality observations were recorded:

1. **Exemplary NetworkX graph bridge:** `topology.create_nxgraph()` is a model of how power system tools should expose topology to general-purpose graph libraries (B-2, severity: low/positive)
2. **OPF duals discarded during result extraction:** The 6-layer architecture is clean, but constraint multipliers and shadow prices from the PYPOWER result dict are dropped during DataFrame conversion (B-6, severity: medium)

pandapower's DataFrame-centric data model (input DataFrames mirror result DataFrames, in-place modification for contingency analysis, custom columns for extension data) is a significant architectural strength. The PYPOWER fork approach (embedded rather than external dependency) reduces deployment complexity but creates a maintenance and upgrade burden.

### FNM Data Model

Three fnm-data-model observations were recorded:

1. **Load aggregation and branch reclassification:** PPC import aggregates loads per bus (15,062 to 8,576) and reclassifies branches by voltage level instead of tap ratio (G-FNM-1, severity: medium)
2. **ACPF-critical field coverage limited by PPC path:** Only 55.8% ACPF-critical coverage; transformer control modes, area interchange, and switched shunt parameters lost (G-FNM-2, severity: medium)
3. **No native market-layer data structures:** 43% of supplemental CSV fields require tool-external storage; no hub, interface, contingency definition, or outage schedule model (G-FNM-5, severity: medium)

The common theme is that pandapower's data model is designed for power flow analysis, not market operations. The PPC import path is the primary bottleneck for FNM data fidelity.

---

## 6. Items Requiring Human Spot-Check

- [ ] **B-1 (Custom constraints) — fragile workaround classification:** The monkey-patching approach depends on `_optimal_powerflow` internal structure, classified as fragile. However, the underlying PYPOWER userfcn mechanism has been architecturally stable for years. Reviewer should assess whether the practical breakage risk merits fragile vs. stable classification.
- [ ] **B-8 (Reference bus config) — qualified_pass with stable workaround:** The 5-6 API call process is verbose but uses only public API. Reviewer should confirm this appropriately receives qualified_pass rather than pass.
- [ ] **Scalability grade (C+) — Low confidence:** Only 2 of 10 scalability tests were executed. The C-SMALL-gate was triggered by a cascaded failure from A-5 (SCUC), not a scale failure. Reviewer should assess whether the available evidence (C-5 SMALL pass + FNM DCPF 28K bus solve) warrants a higher grade given that all skipped tests were blocked by feature absence, not scale limitations.
- [ ] **G-FNM-3 hard-fail — localized outlier impact:** DCPF passes aggregate thresholds (99.6% buses, 99.7% branches) but triggers hard-fail on 596.6% max branch flow deviation in a localized radial cluster. Reviewer should assess whether this hard-fail appropriately reflects tool quality or is an artifact of the ingestion path.
- [ ] **Expressiveness C+ boundary:** pandapower passes 4 of 10 expressiveness tests cleanly but the 6 failures are all by design (steady-state tool). Reviewer should confirm C+ is the correct grade vs. C (the difference being whether the gaps are "NOT disqualifying" at C+ or "disqualifying" at C).

---

## 7. Methodology Notes

- **Scale cap applied:** MEDIUM. All three gate tests (G-1, G-2, G-3) passed. The Suite C SMALL gate was triggered because C-4 (SCUC on SMALL) failed due to cascaded dependency on A-5 (SCUC not supported). This blocked all 8 MEDIUM-tier scalability tests, though the failure reflects feature absence rather than a scale limitation.
- **FNM status:** Suite G executed (FNM_PATH set). Five FNM tests completed: G-FNM-1 pass, G-FNM-2 pass, G-FNM-3 fail, G-FNM-4 informational (infeasible), G-FNM-5 informational.
- **Tests skipped:** C-1, C-2, C-3, C-5 MEDIUM, C-7, C-8, C-9, C-10 -- all skipped due to C-SMALL-gate triggered by C-4 cascaded failure from A-5.
- **Solver versions:** PYPOWER interior-point (bundled in pandapower 3.4.0); scipy 1.16.3 (SuperLU sparse solver); no external solvers used.
- **Tool version:** pandapower 3.4.0
- **Protocol version:** v10 (consistent across all tests)
- **P2 readiness findings:** P2-1 (PSS/E RAW parsing): Not supported, medium-high effort to add. P2-2 (Piecewise-linear costs): Supported natively via `create_pwl_cost()`. P2-3 (Commitment injection): Straightforward via `in_service` column -- low friction.

---

## 8. Phase 2 Readiness Summary

| Capability | Status | Notes |
|------------|--------|-------|
| PSS/E RAW parsing | Not available | No parser; converter from RAW to MATPOWER via external tool is viable |
| Piecewise-linear costs | Native support | `create_pwl_cost()` API, tested with DC and AC OPF |
| Commitment injection | Low friction | `gen.in_service = False` cleanly removes generators from OPF; P2 UC+ED pipeline viable via external SCUC solver + pandapower ED |
