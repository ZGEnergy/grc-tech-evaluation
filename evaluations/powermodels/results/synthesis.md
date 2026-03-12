# powermodels — Phase 1 Evaluation Synthesis

## 1. Executive Summary

PowerModels.jl is a mature, LANL-backed Julia library for steady-state power network
optimization built on JuMP/MathOptInterface. Its primary strength is a clean four-layer
extensible architecture with first-class DCPF, DC OPF, PTDF extraction, and multi-period
multi-network formulations that scale reliably to 10,000-bus MEDIUM networks. The supply
chain is permissive (BSD 3-Clause/MIT) with no binary blobs and air-gap installability
confirmed. Three hard capability boundaries depress the expressiveness grade: no native
unit commitment (SCUC/SCED), no distributed slack OPF, and no stochastic scenario
formulation — these are architectural gaps, not missing features. ACPF is limited to TINY
scale (NLsolve fails on 10,000-bus networks), and the FNM PSS/E v31 parser crashes on line 1
due to a localized IC field type bug, leaving the entire Suite G blocked. The overall profile
is a strong DC-formulations tool with meaningful AC and combinatorial gaps.

---

## 2. Grade Recommendations Table

| Criterion | Grade | Confidence | Key Evidence |
|-----------|-------|------------|--------------|
| Problem Expressiveness | B- | High | Strong DC/OPF/SCOPF; SCUC, stochastic, distributed slack all blocking fails; ACPF capped at TINY; FNM parse blocked |
| Extensibility | B+ | High | Two-level API clean at MEDIUM; PTDF first-class; graph access requires 20-line BFS boilerplate; 4-layer dispatch architecture |
| Scalability | B- | High | DCPF/DC OPF scale to MEDIUM; ACPF fails at MEDIUM; SCOPF 595s at MEDIUM (1 iteration, not converged); C-4/C-10 blocked by upstream fails |
| Workforce Accessibility | B- | Medium | Clean install; Julia JIT tax; 3-arg API sig bug in docs; branch flows require post-processing; error quality mixed |
| Maturity & Sustainability | B+ | High | LANL/DOE backing, 5 releases in 24 months, 500+ citations, PGLIB reference platform; bus-factor risk (82.9% from one committer) |
| Supply Chain (Gate) | A- | High | BSD 3-Clause/MIT; no binary blobs; air-gap installable; SCIP ZIB Academic license is a minor non-commercial flag |

---

## 3. Per-Criterion Detail

### 3.1 Problem Expressiveness

#### Strengths

- Native DCPF at all scales: TINY (0.49s, [A-1 TINY](expressiveness/A-1_dcpf_TINY.md)) and MEDIUM 10k-bus (31.9s, [A-1 MEDIUM](expressiveness/A-1_dcpf_MEDIUM.md)) using `compute_dc_pf` direct B-matrix solve.
- DC OPF with LMPs: clean pass at TINY ([A-3 TINY](expressiveness/A-3_dcopf_TINY.md), HiGHS, 0.0015s solve) and MEDIUM ([A-3 MEDIUM](expressiveness/A-3_dcopf_MEDIUM.md), 89s LP). `lam_kcl_r` dual extraction is first-class API.
- ACPF at TINY: qualified pass ([A-2 TINY](expressiveness/A-2_acpf_TINY.md), NLsolve converged, 0.48s). Branch flows via `calc_branch_flow_ac`.
- AC feasibility check (DC OPF → ACPF workflow): qualified pass ([A-4 TINY](expressiveness/A-4_ac_feasibility_check_TINY.md)); correctly identifies 4 thermal violations in the AC solution.
- Lossy DCPF with LMP decomposition: qualified pass at both TINY ([A-10 TINY](expressiveness/A-10_lossy_dcopf_lmp_decomposition_TINY.md)) and SMALL ([A-10 SMALL](expressiveness/A-10_lossy_dcopf_lmp_decomposition_SMALL.md)); energy/congestion/loss components verified; requires Ipopt for DCPLLPowerModel.
- N-M contingency sweep at TINY: qualified pass ([A-7 TINY](expressiveness/A-7_contingency_sweep_TINY.md)); 1,081 cases in 0.9s using `deepcopy` + `br_status=0` pattern.
- SCOPF (iterative Benders): qualified pass at TINY ([A-9 TINY](expressiveness/A-9_scopf_TINY.md)), clean pass at SMALL ([A-9 SMALL](expressiveness/A-9_scopf_SMALL.md), 2 iterations, converged, +$697/h cost premium).
- Multi-period DCOPF with storage and cyclic SoC: pass at TINY ([A-12 TINY](expressiveness/A-12_multiperiod_dcopf_storage_TINY.md)); BESS arbitrage confirmed (charge $45/MWh, discharge $75/MWh).
- SCED (ED-only, no UC): qualified pass at TINY ([A-6 TINY](expressiveness/A-6_sced_TINY.md)) via `replicate` + ramp constraints; 24-period LP, 0 ramp violations.

#### Weaknesses

- **SCUC (A-5):** Blocking fail at TINY ([A-5 TINY](expressiveness/A-5_scuc_TINY.md)) and SMALL ([A-5 SMALL](expressiveness/A-5_scuc_SMALL.md)). No binary commitment variables, no min up/down constraints, no startup costs. Requires ~140 lines of custom JuMP MILP from scratch — not a workaround, an architectural boundary.
- **Distributed slack OPF (A-11):** Blocking fail at TINY ([A-11 TINY](expressiveness/A-11_distributed_slack_opf_TINY.md)) and SMALL ([A-11 SMALL](expressiveness/A-11_distributed_slack_opf_SMALL.md)). No native formulation; ~150 lines of custom PTDF-based JuMP OPF required.
- **Stochastic OPF (A-8):** Blocking fail at TINY ([A-8 TINY](expressiveness/A-8_stochastic_timeseries_TINY.md)) and SMALL ([A-8 SMALL](expressiveness/A-8_stochastic_timeseries_SMALL.md)). `replicate()` creates time-period coupling only; no scenario tree, no non-anticipativity, no probability-weighted objective.
- **ACPF at MEDIUM (A-2 MEDIUM):** Independent fail ([A-2 MEDIUM](expressiveness/A-2_acpf_MEDIUM.md)). NLsolve Newton-Raphson fails on 10k-bus network after both flat start (581s) and DC warm-start (621s). Total 1,261s with no converged solution.
- **FNM PSS/E v31 parsing (G-FNM-1):** Blocked. IC field type mismatch on line 1 ([P2-1](p2_readiness/P2-1_psse_raw_parsing.md)). Blocks all downstream FNM tests (G-FNM-2 through G-FNM-5). Fix is localized (1–2 days), but unresolved at evaluation time.

#### Workarounds Required

- Branch flows from `compute_dc_pf`/`compute_ac_pf` require manual post-processing via `(va_from - va_to - shift) / (br_x * tap)` or `calc_branch_flow_ac` — **stable**
- DCPLLPowerModel requires Ipopt (not HiGHS) — **stable**
- Quadratic cost linearization required for HiGHS DC OPF at MEDIUM scale — **stable**
- SCIP required for multi-period storage OPF (MIQP) — **stable**, but SCIP has ZIB Academic license
- Cyclic SoC requires manual `@constraint(pm.model, se[T] == energy_initial)` injection — **stable**
- A-6 SCED bypasses UC stage (all units assumed committed) — **stable** scope reduction

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| A-1 DCPF | TINY | qualified_pass | — | stable (branch flows) | 0.49s | 155 |
| A-1 DCPF | MEDIUM | qualified_pass | — | stable (branch flows) | 31.9s | 135 |
| A-2 ACPF | TINY | qualified_pass | — | stable | 0.48s | 185 |
| A-2 ACPF | MEDIUM | **fail** | — | none available | 1261s | 165 |
| A-3 DC OPF | TINY | pass | — | — | 2.38s | 215 |
| A-3 DC OPF | MEDIUM | qualified_pass | — | stable (cost linearize) | 164s | 155 |
| A-4 AC feasibility | TINY | qualified_pass | — | stable | 2.29s | 155 |
| A-5 SCUC | TINY | **fail** | — | blocking | — | — |
| A-5 SCUC | SMALL | **fail** | — | blocking | — | — |
| A-6 SCED | TINY | qualified_pass | — | stable | 37.3s | 260 |
| A-6 SCED | SMALL | **fail** | A-5 | — (cascaded) | — | — |
| A-7 Contingency | TINY | qualified_pass | — | stable | 1.7s | 180 |
| A-8 Stochastic | TINY | **fail** | — | blocking | — | — |
| A-8 Stochastic | SMALL | **fail** | — | blocking | — | — |
| A-9 SCOPF | TINY | qualified_pass | — | stable | 61.5s | 420 |
| A-9 SCOPF | SMALL | pass | — | stable | 109.6s | 220 |
| A-10 Lossy DCPF | TINY | qualified_pass | — | stable (Ipopt) | 92.6s | 210 |
| A-10 Lossy DCPF | SMALL | qualified_pass | — | stable (Ipopt) | 135s | 195 |
| A-11 Dist. slack | TINY | **fail** | — | blocking | — | — |
| A-11 Dist. slack | SMALL | **fail** | — | blocking | — | — |
| A-12 Multi-period+BESS | TINY | pass | — | stable (3 workarounds) | 120s | 320 |

**Independent fails:** A-2 MEDIUM, A-5 TINY/SMALL, A-8 TINY/SMALL, A-11 TINY/SMALL
**Cascaded fail:** A-6 SMALL blocked by A-5 SMALL

#### Grade Rationale

B- reflects the strong DC OPF capability profile (DCPF, DC OPF, SCOPF, multi-period, storage all pass or qualified-pass) offset by three independent blocking architectural gaps (SCUC, stochastic, distributed slack) plus ACPF's hard ~1000-bus ceiling. The B- standard ("multiple workarounds, some fragile areas, or notable capability gaps") fits: the DC formulations are genuinely strong with stable workarounds, but the AC scale ceiling and three missing problem types represent substantial expressiveness reduction relative to a general-purpose power systems tool. The FNM PSS/E parsing failure, while technically a fixable bug, blocked all LARGE-scale FNM validation and reinforces the B- placement.

---

### 3.2 Extensibility

#### Strengths

- Custom constraint injection via two-level API passes at both TINY ([B-1 TINY](extensibility/B-1_custom_constraints_TINY.md)) and MEDIUM ([B-1 MEDIUM](extensibility/B-1_custom_constraints_MEDIUM.md)). Pattern: `instantiate_model` → `var(pm, :p)` → `@constraint(pm.model, ...)` → `optimize_model!`. Dual extraction via `JuMP.dual()` works cleanly. No source patching required.
- PTDF extraction first-class API: `calc_basic_ptdf_matrix` pass at TINY and MEDIUM ([B-9 MEDIUM](extensibility/B-9_ptdf_extraction_MEDIUM.md)). 12706×10000 matrix in 35.5s, 969 MB, max error 2.18e-11 pu. Phase-shifter handling transparent via `make_basic_network`.
- Four-layer dispatch architecture with clean separation: network data / problem formulation / solver interface / results all separated ([B-6](extensibility/B-6_code_architecture.md)). Julia multiple dispatch is the extension mechanism — no plugin registry, no inheritance.
- Graph access at MEDIUM ([B-2 MEDIUM](extensibility/B-2_graph_access_MEDIUM.md)): pass with ~20-line BFS from `f_bus`/`t_bus` fields. 10k-bus adjacency build in 2.5s; BFS in 0.23ms.
- Contingency loop via `deepcopy` + in-place `br_status` toggle scales cleanly ([B-3 MEDIUM](extensibility/B-3_contingency_loop_MEDIUM.md)).

#### Weaknesses

- No native `Graphs.jl` integration. Graph algorithms require building adjacency list manually. `PowerModelsAnalytics.jl` (not installed) provides a bridge but focuses on visualization.
- `build_opf` has an empty docstring. Formulation-specific methods in `form/*.jl` have no docstrings. Extending the tool requires source code reading.
- Phase-shift correction: `make_basic_network` absorbs phase shifts silently ([B-9 observation](observations/api-friction-extensibility-B9_make_basic_network_absorbs_phase_shifts.md)); users must be aware this changes the basic network representation.

#### Workarounds Required

- Graph adjacency construction: ~20 lines manual BFS from data dict fields — **stable**
- Phase-shift branches excluded from PTDF basic network — **stable** (documented behavior)

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time | LOC |
|------|---------|--------|------------|------------|------|-----|
| B-1 Custom constraints | TINY | pass | — | — | ~3s | ~125 |
| B-1 Custom constraints | MEDIUM | pass | — | — | 286s | 125 |
| B-2 Graph access | TINY | pass | — | stable | ~2s | ~75 |
| B-2 Graph access | MEDIUM | pass | — | stable | 30.8s | 75 |
| B-3 Contingency loop | MEDIUM | pass | — | stable | ~120s | ~180 |
| B-6 Architecture audit | N/A | pass | — | — | — | — |
| B-9 PTDF extraction | MEDIUM | pass | — | stable | 106s | 130 |

#### Grade Rationale

B+ reflects an excellent two-level extensibility API that works cleanly at MEDIUM scale, with PTDF as a genuinely first-class feature and a well-architected four-layer dispatch model. The only qualification is the absence of a Graphs.jl bridge and thin internal documentation on formulation-specific methods. Meets the B+ standard: "mostly strong with one meaningful gap and stable workaround."

---

### 3.3 Scalability

#### Strengths

- DCPF scales to MEDIUM cleanly: 10k-bus in 32s ([C-1 MEDIUM](scalability/C-1_dcpf_scale_MEDIUM.md)), dominated by branch flow post-processing (20s), not the solve (2s).
- DC OPF scales to MEDIUM with cost linearization workaround: HiGHS LP in 99s ([C-3 MEDIUM](scalability/C-3_dcopf_scale_MEDIUM.md)). 34,924 rows, 24,643 columns, 89,902 nonzeros.
- Solver swap requires zero reformulation: one-line `optimizer_with_attributes(...)` change across HiGHS/GLPK/SCIP ([C-7 MEDIUM](scalability/C-7_solver_swap_MEDIUM.md)).
- N-1 contingency sweep at MEDIUM: 50 candidates in 551s ([C-5 MEDIUM](scalability/C-5_contingency_sweep_scale_MEDIUM.md)), 74% pruned for islanding, no diverged cases.
- PTDF matrix at MEDIUM: 12706×10000 in 33s, 969 MB ([C-9 MEDIUM](scalability/C-9_ptdf_matrix_computation_MEDIUM.md)). Max accuracy error 0.0 pu.
- Stochastic DC OPF (loop) at SMALL: 20 scenarios × 12 periods = 240 solves at 14s/scenario ([C-6 SMALL](scalability/C-6_stochastic_dcopf_scale_SMALL.md)); 100% optimal.
- SCOPF at MEDIUM: 1 Benders iteration, 17 binding contingencies, 595s ([C-8 MEDIUM](scalability/C-8_scopf_scale_MEDIUM.md)). Not fully converged at budget but demonstrates scale capability.

#### Weaknesses

- **ACPF fails at MEDIUM (C-2):** Cascaded from A-2 MEDIUM ([C-2 MEDIUM](scalability/C-2_acpf_scale_MEDIUM.md)). NLsolve Newton-Raphson cannot converge on 10k-bus network. 1,261s wall-clock, no solution. This is the most significant scalability limitation.
- **SCUC scalability untestable (C-4):** Cascaded from A-5 blocking fail ([C-4 SMALL](scalability/C-4_scuc_scale_SMALL.md)).
- **Distributed slack scalability untestable (C-10):** Cascaded from A-11 blocking fail ([C-10 MEDIUM](scalability/C-10_distributed_slack_dcopf_scale_MEDIUM.md)).
- GLPK fails on MEDIUM DC OPF (TIME_LIMIT at 300s) — only HiGHS is viable for MEDIUM-scale LP.
- SCOPF at MEDIUM (595s, 1 iteration): post-contingency DCPF screening is the bottleneck at 8.3s/case inside the Benders loop; full convergence would exceed memory (extrapolated ~3 GB for 17 blocks).

#### Evidence Summary Table

| Test | Network | Status | Blocked By | Workaround | Time |
|------|---------|--------|------------|------------|------|
| C-1 DCPF | MEDIUM | qualified_pass | — | stable | 31.9s |
| C-2 ACPF | MEDIUM | **fail** | A-2 | none | 1261s |
| C-3 DC OPF | MEDIUM | qualified_pass | — | stable (cost linearize) | 98.7s |
| C-4 SCUC | SMALL | **fail** | A-5 | — (cascaded) | — |
| C-5 Contingency sweep | MEDIUM | pass | — | — | 551s |
| C-6 Stochastic DC OPF | SMALL | pass | — | stable | 282s |
| C-7 Solver swap | MEDIUM | qualified_pass | — | stable (cost linearize) | 98.7s |
| C-8 SCOPF | MEDIUM | pass | — | stable | 595s |
| C-9 PTDF | MEDIUM | pass | — | — | 148s |
| C-10 Dist. slack | MEDIUM | **fail** | A-11 | — (cascaded) | — |

**Independent fails:** C-2 (cascaded from A-2, same root cause)
**Cascaded fails:** C-4 (from A-5), C-10 (from A-11)

#### Grade Rationale

B- reflects DC workflows scaling reliably to MEDIUM while AC is hard-capped at TINY. The ACPF wall at 10k buses is a significant limitation for users needing full AC analysis at scale. The SCOPF/contingency results are promising but slow. Meets the B- standard: "multiple capability gaps at scale, some independent from expressiveness fails."

---

### 3.4 Workforce Accessibility

#### Strengths

- Clean install: Julia pkg workflow, no system libraries beyond Julia artifacts ([D-1](accessibility/D-1_install_to_first_solve.md)). First solve in 2.96s wall-clock (cache warm).
- Core OPF and power flow tests implementable from official docs without GitHub/Stack Overflow ([D-2](accessibility/D-2_documentation_audit.md)). A-3 (DC OPF + LMPs) and A-10 (PTDF) are fully documented.
- Error handling for infeasible OPF: clean `INFEASIBLE`/`INFEASIBLE_POINT` status propagated from JuMP/HiGHS ([D-4](accessibility/D-4_error_quality.md)).
- 4-layer architecture is clearly described in official documentation.

#### Weaknesses

- **Julia JIT overhead:** 5-15 minute first-install compile time; 5-15s load tax per fresh process invocation. Mitigated by REPL persistence but creates friction in CI/scripted contexts.
- **API signature bug in docs:** Official docs show deprecated 3-argument `solve_dc_opf(data, DCPPowerModel, optimizer)` form; actual v0.21.5 signature is 2-argument. First-use `MethodError` mentions `InitializeInfrastructureModel` without pointing to the API mismatch.
- **Branch flows not in result dict:** `compute_dc_pf` and `compute_ac_pf` omit `result["solution"]["branch"]`. Manual post-processing required in every test. This is the most consistent friction pattern across the entire evaluation (affects A-1, A-2, A-4, B-3, C-1, C-2).
- **Dict-based result access:** String-keyed nested dicts require explicit per-unit conversion and iterating boilerplate. Script verbosity is high: A-4 is 310 NBNCL, A-7 is 326 NBNCL ([D-5](accessibility/D-5_code_volume.md)).
- **NR convergence diagnostics absent:** `compute_ac_pf` returns only `Bool` termination status; no iteration count, no residual ([convergence observation](observations/convergence-quality-expressiveness-A2_acpf_no_nr_diagnostics.md)).
- **Silent failure on invalid bus_type:** `check_connectivity`, `check_reference_bus`, `check_status` all silently accept `bus_type=99` with no warning; OPF returns OPTIMAL ([D-4](accessibility/D-4_error_quality.md)).
- Missing cost key produces `KeyError: key "cost" not found` with deep stack trace — developer-readable but not domain-user-friendly.

#### Evidence Summary Table

| Test | Status | Key Finding |
|------|--------|-------------|
| D-1 Install to first solve | qualified_pass | JIT overhead + 3-arg API sig bug |
| D-2 Documentation audit | qualified_pass | Core tests doc'd; branch flow gap; SCUC/SCOPF undocumented |
| D-3 Example verification | (not listed in top results) | — |
| D-4 Error quality | qualified_pass | INFEASIBLE OK; missing cost cryptic; invalid bus_type silent |
| D-5 Code volume | informational | 94–326 NBNCL; API friction drives verbosity |

#### Grade Rationale

B- reflects a clean install and mostly usable documentation qualified by recurring API friction points — especially the branch flow post-processing gap and the Julia startup overhead — that meaningfully increase the time-to-productivity for new users. The 3-argument API signature discrepancy in official docs is a concrete first-use barrier. Meets the B- standard: "functional but with friction that would slow a new user materially."

---

### 3.5 Maturity and Sustainability

#### Strengths

- LANL/DOE institutional backing via the Advanced Network Science Initiative ([E-4](maturity/E-4_funding_model.md)). Not grant-dependent; multi-decade institutional stability.
- 5 releases in 24 months, all semver-compliant, changelog maintained ([E-1](maturity/E-1_release_cadence.md)). Latest: v0.21.5 (2025-08-12).
- 500+ citations of the original PSCC 2018 paper; PGLIB-OPF reference platform role.
- 457 GitHub stars, 167 forks — strong awareness in the academic power systems community.
- NREL Sienna ecosystem (PowerSystems.jl, PowerSimulations.jl) uses PowerModels as a data/modeling layer — constitutes genuine operational adoption in DOE-adjacent contexts ([E-7](maturity/E-7_operational_adoption.md)).
- Active CI/test coverage (GitHub Actions); Julia General Registry integration maintained.

#### Weaknesses

- **Contributor concentration:** 82.9% of lifetime commits from a single contributor (@ccoffrin/LANL) ([E-3](maturity/E-3_contributor_concentration.md)). Bus factor for core domain knowledge is 1. In the last 12 months, @ccoffrin has 0 direct commits; @odow (JuMP ecosystem expert) is the active maintainer — partial transfer of maintenance but not domain expertise.
- 12+ open PSS/E parser issues as of March 2026, including RAW v34 unsupported (issue #921 unresolved since Jul 2024).
- No commercial ISO/utility deployment evidence — adoption is national-lab and academic.

#### Grade Rationale

B+ reflects strong institutional backing and demonstrated longevity (>150 citations, active Sienna ecosystem integration, maintained changelog) offset by a high bus-factor risk (82.9% single-contributor). The maturity signals are real but concentrated. Meets the B+ standard: "mostly strong with one meaningful risk." The bus-factor concern is notable but not immediately disqualifying given LANL institutional continuity.

---

### 3.6 Supply Chain (Gate Criterion)

#### Strengths

- Core license: BSD 3-Clause equivalent (LANL government origin) — permissive, no copyleft, commercial use allowed ([F-1](supply_chain/F-1_core_license.md)).
- Pure Julia with no binary blobs or native C extensions beyond vendored solver artifacts. Fully inspectable source ([F-5](supply_chain/F-5_code_inspectability.md)).
- Air-gap installable: `Pkg` offline mode with `JULIA_PKG_OFFLINE=true` + pre-downloaded registry supports air-gapped deployment ([F-7](supply_chain/F-7_air_gap_installability.md)).
- HiGHS (MIT) and Ipopt (EPL 2.0) cover all primary use cases without commercial solvers ([F-8](supply_chain/F-8_solver_dependency_assessment.md)).
- Distribution integrity confirmed via Julia registry sha256 hashes ([F-6](supply_chain/F-6_distribution_integrity.md)).

#### Weaknesses

- **SCIP ZIB Academic License:** SCIP is required for multi-period storage OPF (MIQP, `build_mn_opf_strg` with binary complementarity). ZIB Academic License prohibits commercial use ([F-8](supply_chain/F-8_solver_dependency_assessment.md)). SCIP is optional — core DC and AC OPF do not need it — but A-12 (multi-period BESS) currently requires SCIP.
- GLPK (GPL v3) cannot handle quadratic costs without linearization; practically limited to LP-only use cases.

#### Grade Rationale

A- reflects an excellent supply chain posture with the SCIP commercial-use flag as the sole qualification. The flag is minor because SCIP is not required for core functionality (DCPF, DC OPF, ACPF, SCOPF all work without it); the only affected capability is multi-period storage with binary complementarity constraints. Meets the A- standard: "strong overall, one minor flag requiring awareness."

---

## 3b. FNM Ingestion Findings (Suite G)

Suite G was executed. FNM_PATH was set to the RAW v31 file. G-FNM-1 failed; G-FNM-2 through G-FNM-5 are all blocked by G-FNM-1.

### Data Model Fidelity (G-FNM-1, G-FNM-2)

**G-FNM-1 failed.** PowerModels.jl's PSS/E parser crashed on line 1 of the FNM RAW v31 file with:

```

[error | PowerModels]: value '0    100.00 31  0  0    0.0' for IC in section
  CASE IDENTIFICATION is not of type Int64.

```

Root cause: the RAW v31 CASE IDENTIFICATION format places multiple space-separated fields on line 1; the parser expects a plain `Int64` for the IC field but the first token is not isolated before type conversion. This is a localized bug — P2-1 estimates 1–2 days to fix. PowerModels.jl documents support for RAW v33 only; the FNM file is v31.

A MATPOWER fallback was attempted but showed a 42.7% load count discrepancy against the manifest (scope mismatch: cleaned island vs. full model). G-FNM-2 (field coverage audit) is therefore blocked.

**DCPF-critical coverage:** Could not be assessed — G-FNM-2 blocked.

### Power Flow Verification (G-FNM-3, G-FNM-4)

Both blocked by G-FNM-1. No DCPF or ACPF verification against the FNM network was possible. Given that ACPF fails independently at MEDIUM scale (10k buses), FNM ACPF would also be expected to fail even if ingestion were resolved, unless the FNM bus count is below ~1000 buses.

### Supplemental Data Representability (G-FNM-5)

Blocked by G-FNM-1. Cannot assess whether PowerModels data model can represent FNM-specific supplemental fields (BESS, HVDC, switched shunts, etc.).

### FNM Impact on Grades

The G-FNM-1 failure is additive negative evidence for Expressiveness: PowerModels.jl cannot ingest utility-scale networks in PSS/E format without a parser fix. This reinforces the B- Expressiveness grade. The Extensibility and Supply Chain grades are unchanged by the FNM findings — the limitation is a parser bug, not an architectural or licensing issue.

---

## 4. Cross-Cutting Observations

### API Friction Patterns

1. **Branch flows absent from compute_* result dicts.** Both `compute_dc_pf` and `compute_ac_pf` omit `result["solution"]["branch"]`. This forces manual post-processing (DC formula or `calc_branch_flow_ac`) in every test involving branch flows. Observed in: A-1 TINY/MEDIUM, A-2 TINY, A-4 TINY, B-3, C-1, C-2. This is the single most pervasive friction point in the evaluation.

2. **3-argument API signature discrepancy in docs.** Official documentation shows `solve_dc_opf(data, DCPPowerModel, optimizer)` (deprecated 3-argument form); v0.21.5 requires `solve_dc_opf(data, optimizer)`. The error message (`MethodError` for `InitializeInfrastructureModel`) does not point to the API mismatch. Affects first-use experience.

3. **Quadratic costs silently trigger QP at scale.** `solve_dc_opf` with polynomial cost model 2 (c2 ≠ 0) produces a QP, not an LP. HiGHS hits TIME_LIMIT at MEDIUM scale (10k buses). No warning from PowerModels. Users must diagnose and apply cost linearization manually. Observed in: A-3 MEDIUM, C-3, B-1 MEDIUM, C-8.

4. **DCPLLPowerModel requires Ipopt, not HiGHS.** `ScalarQuadraticFunction GreaterThan` constraints in the loss approximation model are rejected by HiGHS. Must use Ipopt. Observed in: A-10 TINY, A-10 SMALL. Consistent and documented once discovered.

5. **`baseMVA` returns `Int` not `Float64`.** MATPOWER parser reads `100` as `Int64`. Functions with `::Float64` type annotations fail. Fix: use `::Real`. Observed in A-6 TINY.

6. **Branch flow variable arc key format.** `var(pm, :p)` returns a dict keyed by `(branch_idx, f_bus, t_bus)` tuples. Both forward and reverse arcs may exist. Requires careful arc direction handling in custom constraint injection.

### Documentation Gaps

1. **SCOPF and SCUC absence not called out in docs.** Users exhausting the problem type list (`pf.jl`, `opf.jl`, `opb.jl`, `ots.jl`, `tnep.jl`) will find no mention of unit commitment or security-constrained OPF. No guidance on implementing them.

2. **`build_opf` empty docstring.** The primary build function has `""` as its docstring. Formulation-specific methods in `form/*.jl` have no docstrings on most methods.

3. **Storage data model underdocumented.** `solve_mn_opf_strg` is listed but the storage component fields (energy capacity, charge/discharge efficiency, SoC bounds, sign conventions) are not explained with a worked example. `ps = sc - sd` sign convention (positive = charging) requires source code reading.

4. **NR convergence diagnostics gap.** `compute_ac_pf` exposes only `Bool` termination status; no iteration count, no mismatch residual. This makes it impossible to distinguish slow-converging from genuinely diverged runs without the timing diagnostic gap.

5. **LODF computation for SCOPF not documented.** The LODF formula from PTDF is not in the official docs; requires independent derivation. Noted in [doc-gap observation](observations/doc-gap-expressiveness-A9_scopf_lodf_not_documented.md).

### Solver Ecosystem

1. **HiGHS is the primary solver.** MIT license, reliable at MEDIUM LP scale, correct dual extraction. Required for most DC formulations.

2. **Ipopt is the primary NLP solver.** EPL 2.0 license, handles AC OPF and DCPLLPowerModel. AC OPF at TINY with Ipopt is confirmed (F-8, LOCALLY_SOLVED). Ipopt was not tested on MEDIUM ACPF as an alternative to `compute_ac_pf`; this represents an untested path that might partially address the MEDIUM ACPF gap.

3. **SCIP required for MIQP (multi-period storage).** ZIB Academic License prohibits commercial use. For commercial deployments, multi-period storage OPF (`build_mn_opf_strg`) requires a different solver or binary relaxation.

4. **GLPK cannot handle quadratic costs** and fails the MEDIUM DC OPF within 300s. Viable only for LP with pre-linearized costs on small networks.

### Architecture Quality

1. **Four-layer dispatch architecture** (public API → model lifecycle → formulation build → solver) is clean and consistent. Julia multiple dispatch is the idiomatic extension mechanism. No plugin registry or callback hooks needed.

2. **`deepcopy` overhead at MEDIUM scale** for contingency loops: `deepcopy(base_data)` for a 10k-bus dict is expensive. In-place `br_status` toggle with restore is the recommended performance pattern. Observed in [B-3 MEDIUM observation](observations/arch-quality-extensibility-B3_deepcopy_overhead_at_medium_scale.md).

3. **Multi-network `replicate` is first-class** for multi-period and scenario analysis (though scenarios are not truly stochastic — they are independent time-step networks, not a scenario tree).

---

## 5. Items Requiring Human Spot-Check

- [ ] **A-7 TINY (contingency sweep) — qualified_pass:** No built-in N-x solver; implemented via `deepcopy` + `br_status=0` loop. Verify that the pass classification is appropriate given the manual loop pattern and that the 1,081-case sweep at 0.7ms/case is considered acceptable throughput.

- [ ] **A-9 TINY (SCOPF) — qualified_pass:** Network is N-1 infeasible with Modified Tiny load profile (full SCOPF LP is INFEASIBLE). The qualified pass relies on the SCOPF API mechanism being correctly demonstrated on individual contingencies. Verify that a network with N-1 infeasibility is appropriate for SCOPF mechanism verification, vs. requiring a physically N-1 feasible network.

- [ ] **A-9 SMALL (SCOPF) — pass:** Iterative Benders converges in 2 iterations with +$697/h cost premium. Verify that 50-branch contingency selection (by loading fraction) is representative and that the 2-iteration convergence is not artificially fast due to the specific contingency set.

- [ ] **C-8 SCOPF MEDIUM — pass:** Only 1 Benders iteration completed in 595s; algorithm did not converge. The pass is based on demonstrating the scale mechanism, not full SCOPF optimality. Verify whether a non-converged result should be classified as pass vs. qualified_pass.

- [ ] **A-12 TINY (multi-period BESS) — pass with stable workarounds:** Three workarounds required (SCIP MIQP, cyclic SoC manual constraint, two-phase LMP extraction). Verify whether three simultaneous workarounds on one test should remain "pass" or be reclassified as "qualified_pass."

- [ ] **A-6 TINY (SCED) — qualified_pass:** UC stage bypassed (all generators assumed committed). The pass condition asks for SCED following SCUC; the qualified pass reflects ED-only. Verify whether the bypass should downgrade the expressiveness score more severely.

- [ ] **B- Expressiveness grade boundary:** The B- grade requires judgment on weighting the three architectural gaps (SCUC, stochastic, distributed slack) vs. the strong DC formulation performance. A C+ grade would be defensible if those three gaps are considered critical blocking criteria. Confirm with evaluator.

- [ ] **A-2 MEDIUM ACPF — Ipopt path not tested:** C-2 result notes that an Ipopt-backed ACPF via `instantiate_model(ACPPowerModel, ...)` + `optimize_model!` might succeed where `compute_ac_pf` (NLsolve) fails. This path was not executed. Consider whether the Ipopt AC OPF path (which is AC OPF, not pure ACPF) should be tested as a qualified workaround.

- [ ] **Supply chain — SCIP ZIB Academic License:** A-12 (multi-period storage OPF) currently requires SCIP. Verify whether this represents an operational block for commercial use, or whether HiGHS with a manual binary relaxation (LP approximation) is an acceptable workaround.

- [ ] **G-FNM-1 fix effort estimate:** P2-1 estimates 1–2 days to fix the PSS/E v31 IC field parser. Verify whether the fix would be upstreamed or maintained as a local patch, and whether this changes the Expressiveness grade for Phase 2 planning.

---

## 6. Methodology Notes

- **Scale cap:** MEDIUM. All three gate tests passed (G-1 TINY, G-2 SMALL, G-3 MEDIUM). No scale cap was needed beyond the MEDIUM tier defined in the protocol.
- **FNM status:** Suite G executed; G-FNM-1 failed (PSS/E v31 header parse crash). G-FNM-2 through G-FNM-5 blocked. FNM grades rely on the G-FNM-1 finding only; no power flow or field coverage data from the actual FNM network was obtained.
- **Tests skipped:** None explicitly skipped. A-5, A-8, A-11 were not executed (capability documented as absent per research phase); SMALL/MEDIUM repeats of blocking fails were documented by reference without re-execution.
- **Solver versions:** HiGHS 1.13.1 (MIT), Ipopt 3.14.x (EPL 2.0), GLPK 5.0 (GPL v3), SCIP 8.x / Julia binding v0.2.1 (ZIB Academic).
- **Tool version evaluated:** PowerModels.jl v0.21.5 (git-tree-sha1: `b8e410e1d827b621e82e7e670967f0efc5845c30`).
- **Protocol version:** v9 for all tests (Suites A–F, G). Mixed-version not applicable; all tests used v9.
- **Devcontainer:** Ubuntu 24.04, Julia 1.10, Python 3.12; container provided solver binaries as Julia artifacts.
- **Timing methodology:** All wall-clock times measured from Julia REPL after JIT warm-up on case39 (unless noted). First-invocation JIT times are reported separately where relevant. Fresh subprocess times are not used as performance baselines.
- **MEDIUM preprocessing:** 2,462/12,706 branches (19.4%) had rate_a = Inf/0 in the raw ACTIVSg10k file; set to 9999 MVA. No zero-reactance branches required correction. Congestion induction (per protocol) not applied in most tests — the network is uncongested at base case, producing uniform LMPs ($20.064/MWh). Branch derating was applied only in tests where congestion was operationally required (A-3 TINY: 70% derating; MEDIUM tests used raw network).
