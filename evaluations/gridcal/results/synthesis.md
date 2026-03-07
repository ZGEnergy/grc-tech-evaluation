# GridCal (VeraGridEngine 5.6.28) -- Phase 1 Synthesis Report

**Evaluator:** Automated agent evaluation
**Date:** 2026-03-06
**Protocol version:** v4
**Package:** `veragridengine` 5.6.28 (PyPI)
**License:** MPL-2.0

---

## Executive Summary

GridCal is a 100% pure-Python power systems analysis engine with clean APIs for core power flow and DC OPF. It excels at inspectability and network graph integration (NetworkX). However, its feature scope drops off sharply beyond basic PF/OPF: unit commitment constraints are non-functional, SCOPF is unimplemented, stochastic programming is absent, and a TapPhaseControl bug blocks time-series OPF on MATPOWER networks with transformers. The project has a bus factor of 1. No custom constraint API exists, which is a blocking gap for market-grade analysis.

**Overall assessment:** A capable tool for steady-state power flow and snapshot OPF that is not yet ready for production market clearing or advanced optimization workflows.

---

## Gate Results

### Data Import Gate: PASS

| Test | Network | Buses/Branches/Gens | Time | Status |
|------|---------|---------------------|------|--------|
| G-1 | TINY (IEEE 39) | 39/46/10 | 0.16s | PASS |
| G-2 | SMALL (ACTIVSg 2k) | 2000/3206/544 | 2.08s | PASS |
| G-3 | MEDIUM (ACTIVSg 10k) | 10000/12706/2485 | 7.17s | PASS |

**Scale cap:** MEDIUM. All three networks import cleanly via `vge.open_file()`.

### Supply Chain Gate: PASS (B)

See Criterion 6 below for detail. No disqualifying findings.

---

## Criterion Grades

| # | Criterion | Grade | Justification |
|---|-----------|-------|---------------|
| 1 | Problem Expressiveness | C+ | 4 pass + 2 qualified pass out of 11; UC, SCOPF, stochastic, distributed slack all fail |
| 2 | Extensibility | B | 7 pass + 1 qualified pass + 1 blocking fail; clean architecture but no custom constraint API |
| 3 | Accessibility | C+ | Install friction, no input validation, documentation requires source reading |
| 4 | Scalability | B- | Passing tests scale well to MEDIUM; 4 failures inherited from expressiveness |
| 5 | Maturity & Sustainability | B- | Very active development, but bus factor = 1, single-company backing |
| 6 | Supply Chain (GATE) | B | Pure Python, open solvers, MPL-2.0; no provenance verification |

---

## Criterion 1: Problem Expressiveness -- C+

### Test Results

| Test | Description | TINY | Scale | Status | Notes |
|------|-------------|------|-------|--------|-------|
| A-1 | DCPF | PASS (0.13s, 30 LOC) | MEDIUM PASS (1.84s) | pass | Named `SolverType.Linear` |
| A-2 | ACPF | PASS (1.41s, 45 LOC) | MEDIUM PASS (12.7s) | pass | Flat-start converged, Newton-Raphson default |
| A-3 | DC OPF | PASS (0.10s, 45 LOC) | MEDIUM PASS (15.2s) | pass | HiGHS + SCIP both functional; CBC fails |
| A-4 | AC Feasibility | PASS (~1.6s, 50 LOC) | MEDIUM PASS | pass | OPF-to-PF pipeline clean |
| A-5 | SCUC | FAIL | SMALL FAIL | fail | TS-OPF crashes (TapPhaseControl), UC constraints not enforced (#397) |
| A-6 | SCED | FAIL | SMALL FAIL | fail | Depends on A-5; UC/ED not separable |
| A-7 | N-M Contingency | QUAL PASS (0.73s, 85 LOC) | MEDIUM QUAL PASS (297.6s) | qualified_pass | Stable workaround: manual loop via branch.active + NetworkX |
| A-8 | Stochastic TS DCOPF | FAIL | SMALL FAIL | fail | No native stochastic programming; TS-OPF crash blocks workaround |
| A-9 | SCOPF | FAIL | SMALL FAIL | fail | Not implemented; `consider_contingencies` does nothing (#364) |
| A-10 | Lossy DCOPF | QUAL PASS (50 LOC) | SMALL QUAL PASS | qualified_pass | Losses work; no LMP decomposition into energy/congestion/loss components |
| A-11 | Distributed Slack OPF | FAIL | SMALL FAIL | fail | Distributed slack exists for PF but not OPF |

Score: 4 pass, 2 qualified_pass, 5 fail (36% pass, 55% fail)

### Grade Rationale

Core power flow (DC and AC) and snapshot DC OPF work well with concise APIs. However, five of eleven expressiveness tests fail outright. The failures are not edge cases -- they represent fundamental capabilities for market clearing: unit commitment, economic dispatch separation, SCOPF, stochastic optimization, and distributed-slack OPF. The TapPhaseControl bug cascades across A-5, A-6, and A-8, amplifying a single defect into three test failures.

The two qualified passes (A-7 contingency, A-10 lossy DCOPF) use stable workarounds but have real limitations: A-7 requires manual loop code rather than a built-in N-M sweep, and A-10 lacks LMP decomposition.

C+ rather than C because the core PF/OPF capabilities that do work are solid, and the tool is not outside its design scope -- it attempts these features but has bugs and incomplete implementations. C+ is the lowest passing grade for gate criteria; for expressiveness as a weighted criterion, it indicates significant gaps that would require substantial remediation for Phase 2 use.

### Spot-Check Items

- [ ] A-7: Verify manual contingency loop workaround produces correct post-contingency flows
- [ ] A-10: Confirm loss approximation is physically reasonable on MEDIUM network

---

## Criterion 2: Extensibility -- B

### Test Results

| Test | Description | Status | Notes |
|------|-------------|--------|-------|
| B-1 | Custom Constraints | FAIL (blocking) | No API to add constraints to OPF; PuLP model not exposed |
| B-2 | Graph Access | PASS | `build_graph()` returns native `nx.MultiDiGraph`; zero adapter code |
| B-3 | Contingency Loop | PASS | `branch.active` toggle, 4.6ms/case TINY, scales to MEDIUM |
| B-4 | Stochastic Wrapping | QUAL PASS (fragile) | Snapshot OPF loop works (240 solves in 19.8s); TS-OPF crashes |
| B-5 | Interoperability | PASS | `get_bus_df()`/`get_branch_df()` to pandas; 4 LOC to CSV |
| B-6 | Code Architecture | PASS | Clean 3-tier: MultiCircuit -> NumericalCircuit -> solver |
| B-7 | AC Feasibility Extension | PASS | No workaround needed; OPF dispatch injects directly into PF |
| B-8 | Ref Bus Config | PASS | Slack bus reconfigurable via API |
| B-9 | PTDF/LODF | PASS | `linear_power_flow()` returns both matrices; flows match DCPF exactly |

Score: 7 pass, 1 qualified_pass (fragile), 1 fail (blocking)

### Grade Rationale

The architecture is genuinely extensible for analysis workflows that stay within the tool's feature scope. NetworkX graph integration (B-2) and PTDF/LODF extraction (B-9) are standout strengths -- both are first-class APIs requiring minimal code. The 3-tier architecture (B-6) is clean and navigable.

The single blocking fail (B-1, custom constraints) is significant: it means users cannot add interface flow limits, zonal reserve requirements, or any custom linear constraint to the OPF. This is a hard wall for market-grade analysis. The PuLP model is constructed internally and not accessible.

B rather than B+ because the custom constraint gap is meaningful (not just a missing convenience feature) and B-4's fragility (forced into snapshot loop by the TapPhaseControl bug) reduces confidence in time-series extensibility.

### Spot-Check Items

- [ ] B-4: Verify snapshot OPF loop produces meaningful price variation across scenarios
- [ ] B-9: Verify PTDF matrix dimensions and slack-bus column treatment on MEDIUM

---

## Criterion 3: Accessibility -- C+

### Test Results

| Test | Description | Status | Key Finding |
|------|-------------|--------|-------------|
| D-1 | Install to First Solve | QUAL PASS | Package rename friction (GridCalEngine -> veragridengine); `SolverType.Linear` naming |
| D-2 | Documentation Audit | INFORMATIONAL | 2/11 Suite A tests doable from docs alone; 9/11 require source reading |
| D-3 | Example Verification | QUAL PASS | Most examples run; some not self-contained; TS-OPF example blocked by bug |
| D-4 | Error Quality | FAIL | All 3 deliberate errors silently accepted; no input validation |
| D-5 | Code Volume | INFORMATIONAL | 30-85 LOC for passing tests; concise for core workflows |

### Grade Rationale

The API is concise for core use cases (30 LOC for DCPF, 45 LOC for DC OPF). Installation is mechanically simple (pure Python, `pip install`). However:

1. **No input validation (D-4 FAIL):** Rate=0 silently treated as unlimited. Zero-cost generators produce arbitrary dispatch with no warning. Invalid bus types accepted without error. This is a safety concern -- users get "converged" results from incorrectly specified models.

2. **Documentation gaps (D-2):** Only 2 of 11 expressiveness tests can be completed from documentation alone. Advanced features are exposed as options but not explained.

3. **Rename friction (D-1):** The GridCal-to-VeraGridEngine transition creates real onboarding confusion. The deprecation message contains a typo. No migration guide exists.

C+ rather than B- because the D-4 failure (silent acceptance of invalid inputs) is a serious usability and safety issue that goes beyond documentation friction. A tool that never validates its inputs will produce wrong answers without warning.

---

## Criterion 4: Scalability -- B-

### Test Results

| Test | Description | Status | Performance |
|------|-------------|--------|-------------|
| C-1 | DCPF Scale | PASS | MEDIUM: 1.84s, 82.6 MB |
| C-2 | ACPF Scale | PASS | MEDIUM: 12.7s, 91.1 MB |
| C-3 | DC OPF Scale | PASS | MEDIUM: 15.2s, 127.2 MB |
| C-4 | SCUC Scale | FAIL | Blocked (A-5 failed) |
| C-5 | Contingency Scale | PASS | MEDIUM: 575s for 385 cases |
| C-6 | Stochastic Scale | FAIL | Blocked (A-8 failed) |
| C-7 | Solver Swap | PASS | HiGHS 14.1s vs SCIP 11.9s (parameter change only) |
| C-8 | SCOPF Scale | FAIL | Blocked (A-9 failed) |
| C-9 | PTDF Scale | QUAL PASS | MEDIUM: 49.9s, 7.6 GB memory (dense matrices) |
| C-10 | Distributed Slack Scale | FAIL | Blocked (A-11 failed) |

Score: 5 pass, 1 qualified_pass, 4 fail (all blocked by expressiveness)

### Grade Rationale

Where GridCal can solve a problem, it scales adequately to MEDIUM (10k buses). PF and OPF times are reasonable. Solver swapping (C-7) is trivial -- a single parameter change.

The four failures are all inherited from expressiveness failures, not independent scalability problems. This means the scalability grade is dragged down by feature scope, not performance.

C-9 (PTDF at MEDIUM) is qualified because it produces dense 12706x10000 matrices consuming 7.6 GB -- this would not scale to WECC without sparse reformulation.

B- rather than B because four of ten scalability tests are blocked, and the PTDF memory scaling is a concern for larger networks.

### Spot-Check Items

- [ ] C-9: Verify PTDF memory measurement methodology (dense vs sparse)

---

## Criterion 5: Maturity & Sustainability -- B-

### Test Results

| Test | Description | Status | Key Finding |
|------|-------------|--------|-------------|
| E-1 | Release Cadence | PASS | ~40 PyPI releases in 24 months; no gaps >6 weeks |
| E-2 | Commit Activity | PASS | 2,434 commits/12 months; substantive changes |
| E-3 | Contributor Breadth | QUAL PASS | 30 contributors; 83% from eRoots Analytics |
| E-4 | Bus Factor | FAIL | Bus factor = 1 (SanPen: 70.3% of commits, sole release authority) |
| E-5 | Funding Model | QUAL PASS | eRoots open-core model (GSLV commercial variant); no public financials |
| E-6 | Issue Responsiveness | QUAL PASS | SanPen responds personally; batch-close pattern; no formal triage |
| E-7 | Operational Adoption | QUAL PASS | One distribution utility (NGN, Germany); no ISO/transmission deployment |

### Grade Rationale

The project is exceptionally active (2,434 commits/year, frequent releases) and the sponsoring company has a viable open-core business model. However, three structural risks temper the grade:

1. **Bus factor = 1 (E-4 FAIL):** SanPen is the sole maintainer with commit, release, and triage authority across all subsystems. No other contributor has demonstrated ability to maintain the project independently. If SanPen becomes unavailable, the project stalls.

2. **Single-organization concentration (E-3):** 83% of contributions come from eRoots Analytics employees. The project's health is coupled to one small company's commercial success.

3. **Limited operational adoption (E-7):** One confirmed utility deployment at the distribution level. No transmission, ISO, or government agency adoption evidence.

B- rather than B because the bus factor = 1 is a concrete sustainability risk, not a theoretical concern. The project's velocity is high but fragile -- it depends on a single individual continuing to contribute at an extraordinary rate.

---

## Criterion 6: Supply Chain, Inspectability & Licensing -- B (GATE: PASS)

### Test Results

| Test | Description | Status | Key Finding |
|------|-------------|--------|-------------|
| F-1 | Core License | QUAL PASS | MPL-2.0 (since v5.2.0, Nov 2024); prior LGPL-3.0 |
| F-2 | Dependency Tree | PASS | 29 direct / ~83 total; all open-source |
| F-3 | Dependency Licenses | PASS | All permissive or weak-copyleft; one LGPL dep (chardet) |
| F-4 | Compiled Extensions | PASS | Core is 100% pure Python (866 .py files, 0 .so/.pyd) |
| F-5 | Code Inspectability | PASS | Full execution path traceable through Python source |
| F-6 | Air-Gap Install | PASS | All deps available as wheels; no runtime network access |
| F-7 | Provenance Verification | FAIL | No signed tags, no GPG/Sigstore on PyPI, no SLSA/SBOM |
| F-8 | Solver Openness | PASS | HiGHS (MIT) bundled; SCIP available; no commercial solver needed |
| F-9 | Dependency Surface | QUAL PASS | Large surface (83 pkgs); opencv, xlwt unusual for power systems |

### Grade Rationale

GridCal's supply chain profile has genuine strengths: 100% pure Python core with full source traceability, MPL-2.0 licensing, bundled open-source solvers, and clean air-gap installability. These are strong properties for classified or regulated environments.

The F-7 failure (no provenance verification) is common among academic open-source projects but relevant for government deployment under EO 14028 / NIST SSDF requirements. Organizations can mitigate by building from pinned source commits.

The dependency surface (F-9) is larger than expected for a power systems engine -- opencv-python, windpowerlib, xlwt, and websockets are not needed for core analysis but cannot be excluded (no optional dependency groups).

B rather than B+ because the provenance gap and bloated dependency surface are real concerns, even though the core inspectability story is strong.

---

## Phase 2 Readiness

| Test | Description | Status | Impact |
|------|-------------|--------|--------|
| P2-1 | PSS/E RAW Parsing | PASS | v29-35 supported natively (v31 absent) |
| P2-2 | Piecewise Linear Cost | FAIL | No PWL cost curves; polynomial only; DC OPF silently ignores quadratic terms |
| P2-3 | UC -> ED -> AC PF Pipeline | FAIL | Pipeline non-functional: TS-OPF crash, no commitment injection API, UC constraints broken |

### Assessment

GridCal can parse PSS/E RAW files (P2-1), which is necessary for working with the CAISO FNM. However, two critical Phase 2 capabilities are absent:

- **No piecewise-linear cost curves (P2-2):** Market-grade dispatch requires PWL cost curves to model generator heat rates. GridCal's polynomial cost model is insufficient. Adding PWL support would require modifying the internal LP formulation -- difficult without a custom constraint API (B-1).

- **No UC/ED pipeline (P2-3):** The SCUC -> SCED -> AC PF workflow that ISOs use for market clearing cannot be reproduced. The time-series OPF crash, non-functional UC constraints, and absence of a commitment injection API combine to make this pipeline infeasible.

**Phase 2 readiness: LOW.** GridCal would require substantial internal modification to support ISO market clearing workflows.

---

## Cross-Cutting Observations

### TapPhaseControl Bug Cascade

A single bug in the time-series OPF compiler (`ValueError: 0 is not a valid TapPhaseControl`) cascades across multiple test results:

- **A-5 (SCUC):** Cannot run multi-period UC
- **A-6 (SCED):** Cannot test ED (depends on A-5)
- **A-8 (Stochastic TS-OPF):** Cannot run time-series scenarios
- **B-4 (Stochastic Wrapping):** Downgraded to fragile qualified_pass (forced into snapshot loop)
- **C-4, C-6 (Scalability):** Blocked by expressiveness failures

This single defect is responsible for 3 test failures and 1 downgrade. It affects any MATPOWER network with transformers, which includes all standard IEEE test cases. The bug is in the numerical circuit compiler's handling of transformer tap control data during time-series compilation.

### Strengths Worth Noting

1. **NetworkX integration (B-2):** `build_graph()` returning a native `nx.MultiDiGraph` is the cleanest graph API of any tool in this evaluation class. Zero adapter code needed.

2. **PTDF/LODF extraction (B-9):** One function call returns both sensitivity matrices with flows matching DCPF exactly. This is a strong foundation for sensitivity-based contingency screening.

3. **100% pure Python (F-4):** Complete source traceability through the entire execution path. No opaque compiled extensions in the core package.

4. **Concise core API:** DCPF in 30 LOC, DC OPF in 45 LOC. The convenience functions (`vge.power_flow()`, `vge.linear_opf()`, `vge.open_file()`) are well-designed for common workflows.

### Weaknesses Worth Noting

1. **No custom constraint API (B-1):** The inability to add constraints to the OPF is a hard wall for any analysis requiring interface limits, zonal reserves, or non-standard constraints. This is not fixable with workarounds.

2. **No input validation (D-4):** The tool never raises errors for invalid modeling data. This is a safety concern for production use.

3. **Bus factor = 1 (E-4):** The project's continuity depends on a single individual. This is the highest-risk finding for long-term adoption.

4. **SCOPF not implemented (A-9):** The `consider_contingencies` OPF option exists but does nothing. Preventive SCOPF -- the formulation ISOs use for market clearing -- is absent.

---

## Qualified Pass Registry (Spot-Check Required)

The following items received qualified_pass status and should be verified by a human reviewer:

| Test | Qualification Reason | Risk if Wrong |
|------|---------------------|---------------|
| A-7 | Manual contingency loop (stable workaround) | Incorrect post-contingency flows |
| A-10 | Losses work but no LMP decomposition | Loss factors may be inaccurate |
| B-4 | Snapshot OPF loop (fragile, TS-OPF crash forces workaround) | Inter-temporal constraints lost |
| C-9 | PTDF at MEDIUM uses 7.6 GB (dense matrices) | Memory-bound at larger scales |
| D-1 | Rename friction, non-obvious solver naming | Onboarding friction underestimated |
| D-3 | Examples work but some not self-contained | Example quality may degrade with updates |
| E-3 | 30 contributors but 83% from one company | Organizational concentration risk |
| E-5 | Open-core business model, no public financials | Funding sustainability uncertain |
| E-6 | Responsive maintainer but single-responder pattern | Response quality inconsistent |
| E-7 | One distribution utility deployment | Operational track record thin |
| F-1 | MPL-2.0 (recent license change from LGPL) | License transition may need legal review |
| F-8 | Getting-started examples not version-pinned | Examples may drift from release |
| F-9 | Large dependency surface (83 packages) | Attack surface larger than necessary |

---

## Summary Table

| Criterion | Grade | Pass/Qual/Fail |
|-----------|-------|----------------|
| Gate (Import) | PASS | 3/0/0 |
| 1. Expressiveness | **C+** | 4/2/5 |
| 2. Extensibility | **B** | 7/1/1 |
| 3. Accessibility | **C+** | 0/2/1 + 2 informational |
| 4. Scalability | **B-** | 5/1/4 |
| 5. Maturity | **B-** | 2/4/1 |
| 6. Supply Chain (GATE) | **B** | 5/3/1 |
| P2 Readiness | -- | 1/0/2 |
