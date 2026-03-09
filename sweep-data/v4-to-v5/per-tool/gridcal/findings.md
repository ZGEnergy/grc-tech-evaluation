# GridCal -- Sweep Findings (v4)

## Summary

The GridCal evaluation is thorough and generally well-executed. The evaluator correctly identifies the tool's core strengths (clean PF/OPF APIs, NetworkX integration, pure Python inspectability) and weaknesses (no custom constraint API, non-functional SCOPF, TapPhaseControl bug cascade). The primary concerns identified in this sweep are: (1) a single bug (TapPhaseControl) cascading into five separate test failures, which inflates the apparent breadth of gaps; (2) missing MATPOWER cross-validation for the lossy DC OPF (A-10) as required by the protocol; (3) a significant PTDF flow prediction mismatch on MEDIUM that is scored as qualified_pass without adequate investigation; and (4) uniform generator costs on case39 reducing the discriminative value of LMP-dependent tests. Three probes are recommended: PTDF flow mismatch investigation, lossy DC OPF reference validation, and B-4 SMALL convergence failure analysis.

## Finding Details

### gridcal-F01: Uniform LMPs on case39 mask congestion-dependent test differentiation

**Category:** low_signal | **Severity:** low
**Tests:** A-3, B-8, C-3, C-7

All 10 generators in IEEE 39-bus have identical cost curves (0.3 $/MWh), so LMPs are always uniform when no branches bind. This renders multiple tests unable to verify economically meaningful signals. The B-8 TINY result explicitly notes: "LMPs are identical across all three configurations. This is mathematically correct: in a DC OPF LP formulation, the slack bus determines the voltage angle reference but does not affect the economic dispatch or LMPs." While this is true, it means the test provides zero discriminative value on this network.

The evaluator mitigated this partially by running B-8 on SMALL (ACTIVSg 2000), where the heterogeneous cost structure produced a meaningful LMP spread of 11.128 to 32.923 $/MWh with the two-slack configuration. This demonstrates good test design awareness.

On MEDIUM, the DC OPF produces uniform LMPs at $20.064/MWh with zero binding branches (max loading 84.7%). This affects A-3 MEDIUM, C-3, and C-7, where congestion signal is absent.

**Cross-tool relevance:** confirmed -- all tools use the same reference networks.
**Proposed action:** adjust_scoring -- consider whether MEDIUM network parameterization should be modified to produce binding constraints, or whether the no-binding-constraint result is itself a finding about the test network.

---

### gridcal-F02: TapPhaseControl bug cascades single defect into five test failures

**Category:** misleading_result | **Severity:** high
**Tests:** A-5, A-6, A-8, C-4, C-6

A single bug (`ValueError: 0 is not a valid TapPhaseControl`) in GridCal's time-series OPF compiler causes failures across five tests. The bug triggers on any MATPOWER network with transformers, which includes all standard IEEE test cases. The synthesis correctly identifies this cascade: "This single defect is responsible for 3 test failures and 1 downgrade."

The evaluation handles this fairly: it notes that A-5 has additional independent issues (UC constraints not enforced per GitHub issue #397) and A-8 lacks native stochastic formulation regardless of the bug. However, the aggregate failure count (5 fail out of 11 expressiveness tests = 45% failure rate) overstates the breadth of independent capability gaps. A fairer characterization would distinguish between: (a) features that are architecturally absent (SCOPF, distributed slack OPF, native stochastic), (b) features blocked by a single fixable bug (time-series OPF on transformer networks), and (c) features that are present but not enforced (UC constraints).

The C-4 and C-6 scalability failures are purely inherited -- they add no new information and could be marked as "blocked by expressiveness" without counting against the scalability dimension.

**Cross-tool relevance:** likely -- other tools may have bugs that cascade similarly, and the protocol should have guidance on how to count cascaded failures.
**Proposed action:** none (the evaluation already notes the cascade clearly in synthesis; this is a protocol-level design consideration).

---

### gridcal-F03: Contingency sweep correctness not verified against reference

**Category:** missing_verification | **Severity:** medium
**Tests:** A-7

The A-7 contingency sweep reports load loss values for 129 cases (TINY, x=3, m=3) and 793 cases (MEDIUM, x=5, m=4), all converging. However, post-contingency flow correctness is not validated against any reference (e.g., a separate DCPF solve with the branch removed and a fresh model). The synthesis flags this: "A-7: Verify manual contingency loop workaround produces correct post-contingency flows" -- but this spot-check was not performed.

The pruning ratio of 0.0 on both networks is also notable. Every N-1 contingency produced measurable load loss (> 1e-3 MW threshold on MEDIUM). For a well-meshed network like ACTIVSg 10k, this is somewhat surprising -- many branch removals in a well-connected region would be expected to redistribute flow without measurable load loss. This could indicate that "load loss" is being measured incorrectly (e.g., using total generation mismatch rather than actual unserved load), or that the threshold is too low.

**Cross-tool relevance:** likely -- contingency sweep verification methodology is shared across tools.
**Proposed action:** add_verification -- validate a sample of post-contingency flows against fresh-solve reference; verify load loss measurement methodology.

---

### gridcal-F04: PTDF flow predictions diverge significantly from DCPF on MEDIUM network

**Category:** extraordinary_claim | **Severity:** medium
**Tests:** C-9, B-9

On TINY (39-bus), the LinearAnalysis PTDF-predicted flows match DCPF exactly (max diff 0.0). On MEDIUM (10k-bus), the discrepancy is dramatic: 743 MW max absolute difference for direct flows, and 15,139 MW for PTDF @ Sbus. The result attributes this to "differences in island handling, slack bus treatment, or network topology processing between the two solvers" and scores it as qualified_pass.

This is a significant finding that warrants investigation. A 743 MW flow error on a network with max flows of ~2,000 MW means the error is ~37% of the maximum flow. The scale-dependent nature (exact on TINY, large on MEDIUM) suggests either: (a) the ACTIVSg 10k has electrical islands that are handled differently by DCPF vs LinearAnalysis, (b) there is a bug in the PTDF computation for multi-island networks, or (c) the slack bus convention difference compounds with network size.

The evaluation's conclusion that the PTDF is "usable for relative sensitivity analysis" despite this mismatch is not adequately supported.

**Cross-tool relevance:** none (tool-specific behavior).
**Proposed action:** add_verification -- investigate island count in ACTIVSg 10k, compare PTDF on a single-island subnetwork, verify slack bus handling.

---

### gridcal-F05: No binding branches on MEDIUM DC OPF reduces congestion test signal

**Category:** network_insufficiency | **Severity:** medium
**Tests:** A-3, A-10, C-3

The ACTIVSg 10k DC OPF produces zero binding branches with max loading 84.7% and perfectly uniform LMPs. This means the MEDIUM grade network does not stress the congestion dimension of DC OPF testing. For A-3 (DC OPF), the pass/fail is clear (it converges and produces dispatch), but the lack of binding constraints means shadow price quality, congestion rent, and LMP decomposition cannot be tested in a meaningful way at the grade-assessment scale.

This is a network sufficiency issue that affects all tools equally: if the ACTIVSg 10k DC OPF has no binding branches, no tool can demonstrate congestion-aware dispatch on this network.

**Cross-tool relevance:** confirmed -- same network used for all tools.
**Proposed action:** redesign_test -- consider reducing some branch ratings in ACTIVSg 10k to create binding constraints, or select a different grade network with natural congestion.

---

### gridcal-F06: ACPF convergence claimed but iteration count not reported

**Category:** missing_verification | **Severity:** medium
**Tests:** A-2, C-2

The convergence error values (3.32e-11 on TINY, 2.73e-07 on MEDIUM) provide strong evidence of convergence. However, the iteration count is not reported. The A-2 TINY result explicitly states: "Solver iterations: not directly exposed in results." The protocol lists "iterations" as a recorded metric for C-2. While the convergence error is sufficient to establish that the solver converged, the missing iteration count is a protocol compliance gap. It also means cross-tool comparison of NR efficiency (iterations to convergence) is not possible for GridCal.

**Cross-tool relevance:** likely -- other tools may also omit iteration counts if not easily accessible.
**Proposed action:** none (the convergence error is a stronger verification than iteration count alone).

---

### gridcal-F08: Lossy DC OPF not validated against MATPOWER reference

**Category:** missing_verification | **Severity:** medium
**Tests:** A-10

The protocol explicitly requires: "Validate against MATPOWER reference lossy DC OPF solution on same case (tolerance: 1% on total LMP, directional consistency on loss component signs)." No such validation appears in either the TINY or SMALL A-10 result files.

On TINY, the loss-inclusive LMP spread is only 0.000031 $/MWh (from 0.3 to 0.300031), which is at the edge of numerical noise. This could mean: (a) the loss approximation is correct but all generators have identical costs so loss effects are minimal, (b) the loss approximation is barely active, or (c) the implementation is incorrect but the uniform costs mask the error. Without MATPOWER cross-validation, these cannot be distinguished.

The SMALL result shows a more convincing spread (17.580 to 17.751 $/MWh, 0.172 range), with total generation increasing by 80.1 MW to cover losses. This is more physically plausible but still lacks reference validation.

**Cross-tool relevance:** likely -- MATPOWER cross-validation is required for all tools.
**Proposed action:** add_verification -- run MATPOWER rundcopf with loss option on case39 and ACTIVSg 2000 to establish reference LMPs.

---

### gridcal-F09: E-6 file content appears to duplicate E-5 (issue responsiveness instead of CI/test coverage)

**Category:** scoring_inconsistency | **Severity:** low
**Tests:** E-5, E-6

The E-6 result file (E-6_ci_test_coverage.md) is titled "Issue Responsiveness" and contains content about SanPen's issue response patterns, batch-close behavior, and notable open issues. This is identical in topic to E-5 (which should be issue tracker health per the eval-config). Per the protocol, E-6 should assess "CI configuration and test suite" -- CI existence, test suite existence, coverage estimates, and whether CI passes on the current release. This CI/test assessment appears to be missing from the results entirely.

The synthesis table maps E-6 to "CI/Test Coverage" with a "QUAL PASS" status, but the underlying result file does not contain CI/test coverage content.

**Cross-tool relevance:** none (result file content issue).
**Proposed action:** none (the finding is documented; the missing CI assessment is a gap but is not critical to the overall evaluation quality).

---

### gridcal-F10: B-4 SMALL stochastic wrapping has 53% solve failure rate

**Category:** test_design_gap | **Severity:** medium
**Tests:** B-4

On TINY, B-4 achieves 240/240 converged solves (100%). On SMALL (ACTIVSg 2000), only 113/240 converge (47%). The result attributes failures to "infeasibility at extreme perturbation levels" and is scored as qualified_pass. Several questions arise:

1. Are the perturbation magnitudes (sigma=0.05 for resource types, sigma=0.05 for load) appropriate for the SMALL network, or do they need to be scaled with network size?
2. Is the 47% convergence rate a GridCal robustness issue (poor handling of near-infeasible cases) or a test design issue (perturbations too aggressive)?
3. Does the evaluate establish whether other tools experience similar failure rates with the same perturbation methodology?

The wall-clock time of 1444.5 seconds (~24 minutes) for only 113 successful solves (12.8s per solve) also raises questions about whether the OPF formulation on SMALL includes slack variables for load shedding that prevent infeasibility. If the OPF lacks slack variables, aggressive perturbations will naturally produce infeasible problems.

**Cross-tool relevance:** likely -- perturbation methodology is shared.
**Proposed action:** add_verification -- compare convergence rates across tools with identical perturbation seeds; investigate whether OPF formulations include slack variables.

---

### gridcal-F13: Install-to-first-solve wall-clock is an estimate, not a measurement

**Category:** extraordinary_claim | **Severity:** medium
**Tests:** D-1

The D-1 result reports "approximately 2-3 minutes" as the install-to-first-solve time, broken down as "install ~60s, writing 4-line script ~30s, debugging SolverType naming ~60s." These are estimates, not actual measurements. The protocol requires wall-clock time. The narrative provides good qualitative detail about friction points (rename confusion, SolverType.Linear naming) but the quantitative claim is unverified.

**Cross-tool relevance:** likely -- D-1 timing methodology may be imprecise across all tools.
**Proposed action:** none (the qualitative findings are more valuable than precise timing for this test).

---

### gridcal-F14: Maturity audit results lack verifiable citations

**Category:** test_design_gap | **Severity:** low
**Tests:** E-4, E-5, E-6, E-7

The maturity results cite specific numbers (2,434 commits, 70.3% from SanPen, 30 contributors, ~40 PyPI releases) without linking to data sources. E-7 claims a deployment at NGN (Germany) with "Specific use case details not public." These audit findings are plausible and consistent with each other but are not independently verifiable from the result files alone.

This is inherent to the audit-evaluator archetype -- the protocol does not require automated data collection for maturity metrics. However, including git commands used, date range boundaries, and links to specific evidence (PyPI release history URLs, GitHub contributor pages) would strengthen the findings.

**Cross-tool relevance:** confirmed -- all tools undergo the same audit methodology.
**Proposed action:** none (this is a protocol-level improvement opportunity, not a finding-specific issue).

---

## Extraordinary Claims

### C-9: PTDF matrix is usable despite 743 MW flow prediction mismatch on MEDIUM

**Concern:** A 743 MW maximum absolute difference (37% of max flow) between PTDF-predicted and DCPF-solved flows on the 10k-bus network is a substantial discrepancy. The result claims the PTDF is "usable for relative sensitivity analysis" but this claim is not verified. The mismatch does not appear on TINY (exact match), suggesting a scale-dependent issue that could be an island handling bug, a slack bus convention error, or a numerical accumulation problem.

**Evidence quality:** moderate -- the TINY-vs-MEDIUM comparison is well-documented, but the root cause is not investigated.

A probe should: (1) count electrical islands in ACTIVSg 10k as seen by both DCPF and LinearAnalysis, (2) test PTDF on the largest single-island subnetwork, (3) compare unit-injection PTDF rows against DCPF for a sample of buses.

### A-10: Loss approximation produces physically meaningful LMPs

**Concern:** The TINY LMP spread from loss approximation is only 0.000031 $/MWh, essentially at numerical noise level. No MATPOWER cross-validation was performed as required by the protocol. The SMALL spread (0.172 $/MWh) is more convincing but also unvalidated. Without reference comparison, we cannot confirm whether the loss approximation is physically correct or merely producing small perturbations that happen to be non-zero.

**Evidence quality:** weak -- the required MATPOWER validation is entirely absent.

A probe should: (1) run MATPOWER rundcopf with loss option on case39 and ACTIVSg 2000, (2) compare total LMPs within 1% tolerance, (3) verify directional consistency of loss components.

### D-1: Install to first solve takes 2-3 minutes

**Concern:** Estimate rather than measurement. The detailed breakdown (install ~60s, script writing ~30s, debugging ~60s) makes the estimate plausible, and the qualitative friction findings are well-documented.

**Evidence quality:** moderate -- plausible estimate with supporting detail but not measured.

## Test Outcome Matrix

| Test ID | Status | Workaround | Key Issue |
|---------|--------|------------|-----------|
| G-1 | pass | -- | -- |
| G-2 | pass | -- | -- |
| G-3 | pass | -- | -- |
| A-1 (TINY) | pass | -- | SolverType.Linear naming non-obvious |
| A-1 (MEDIUM) | pass | -- | Solve time 0.36s, file load 7.3s dominates |
| A-2 (TINY) | pass | -- | Iteration count not reported |
| A-2 (MEDIUM) | pass | -- | Convergence error 2.73e-07, good |
| A-3 (TINY) | pass | -- | Uniform LMPs due to identical costs |
| A-3 (MEDIUM) | pass | -- | Zero binding branches, uniform LMPs |
| A-4 (TINY) | pass | -- | 2 voltage violations identified |
| A-4 (MEDIUM) | pass | -- | 143 voltage + 22 thermal violations, max 1587% loading |
| A-5 (TINY) | fail | blocking | TapPhaseControl crash + UC constraints not enforced |
| A-5 (SMALL) | fail | blocking | Same as TINY, not re-tested |
| A-6 (TINY) | fail | blocking | No UC/ED separation API; depends on A-5 |
| A-6 (SMALL) | fail | blocking | Same as TINY, not re-tested |
| A-7 (TINY) | qualified_pass | stable | Manual loop with NetworkX; no correctness validation |
| A-7 (MEDIUM) | qualified_pass | stable | 793 cases, 297.6s, no pruning |
| A-8 (TINY) | fail | blocking | No native stochastic + TS-OPF crash |
| A-8 (SMALL) | fail | blocking | Same as TINY, not re-tested |
| A-9 (TINY) | fail | -- | consider_contingencies flag non-functional |
| A-9 (SMALL) | fail | -- | Same as TINY, not re-tested |
| A-10 (TINY) | qualified_pass | -- | Losses work; no LMP decomposition; no MATPOWER validation |
| A-10 (SMALL) | qualified_pass | -- | Wider LMP spread; still no reference validation |
| A-11 (TINY) | fail | -- | Distributed slack in PF only, not OPF |
| A-11 (SMALL) | fail | -- | Same as TINY, not re-tested |
| B-1 (TINY) | fail | blocking | No custom constraint API; PuLP model not exposed |
| B-1 (MEDIUM) | fail | blocking | Same architectural limitation |
| B-2 (TINY) | pass | -- | Native NetworkX MultiDiGraph |
| B-2 (MEDIUM) | pass | -- | 87ms graph build on 10k buses |
| B-3 (TINY) | pass | -- | 4.6ms per N-1 case, model integrity verified |
| B-3 (MEDIUM) | pass | -- | 262ms per case, 50 contingencies |
| B-4 (TINY) | qualified_pass | fragile | 240/240 converged; TS-OPF crash forces snapshot loop |
| B-4 (SMALL) | qualified_pass | fragile | Only 113/240 converged; high failure rate |
| B-5 (TINY) | pass | -- | 4 LOC for DataFrame + CSV export |
| B-5 (MEDIUM) | pass | -- | Scales linearly |
| B-6 | pass | -- | Clean 3-tier architecture documented |
| B-7 (TINY) | pass | -- | No workaround needed for DC OPF -> ACPF |
| B-7 (MEDIUM) | pass | -- | Same clean pipeline at scale |
| B-8 (TINY) | pass | -- | Slack reconfigurable; LMPs uniform (uninformative) |
| B-8 (SMALL) | pass | -- | Two-slack produces meaningful LMP variation |
| B-9 (TINY) | pass | -- | Exact PTDF/DCPF flow match |
| B-9 (MEDIUM) | qualified_pass | -- | 743 MW flow mismatch; needs investigation |
| C-1 | pass | -- | 1.84s, 82.6 MB |
| C-2 | pass | -- | 12.7s, 91.1 MB, flat start converged |
| C-3 | pass | -- | 15.2s, 127 MB; uniform LMPs |
| C-4 | fail | blocking | Blocked by A-5 |
| C-5 | pass | stable | 575s for 385 cases; manual loop |
| C-6 | fail | blocking | Blocked by A-8 |
| C-7 | pass | -- | HiGHS vs SCIP, one-line swap |
| C-8 | fail | -- | Blocked by A-9 |
| C-9 | qualified_pass | -- | 49.9s, 7.6 GB; flow mismatch |
| C-10 | fail | -- | Blocked by A-11 |
| D-1 | qualified_pass | -- | Rename friction; timing is estimate |
| D-2 | informational | -- | 2/11 from docs alone |
| D-3 | qualified_pass | -- | Most examples run; TS-OPF blocked by bug |
| D-4 | fail | -- | All 3 errors silently accepted |
| D-5 | informational | -- | 30-85 LOC for passing tests |
| E-1 | pass | -- | ~40 releases in 24 months |
| E-2 | pass | -- | ~2,434 commits/12 months |
| E-3 | qualified_pass | -- | 83% from one organization |
| E-4 | fail | -- | Bus factor = 1 |
| E-5 | qualified_pass | -- | Open-core model; no public financials |
| E-6 | qualified_pass | -- | Content appears to be issue responsiveness, not CI/test coverage |
| E-7 | qualified_pass | -- | One distribution utility deployment |
| F-1 | qualified_pass | -- | MPL-2.0; recent license change |
| F-2 | pass | -- | Content is license audit (see F-15 finding) |
| F-3 | pass | -- | 100% pure Python core |
| F-4 | pass | -- | Full execution path traceable |
| F-5 | pass | -- | HiGHS bundled; SCIP available |
| F-6 | pass | -- | Air-gap installable |
| F-7 | fail | -- | No signed tags, no SLSA/SBOM |
| F-8 | qualified_pass | -- | Examples not version-pinned |
| F-9 | qualified_pass | -- | Large dep surface (83 pkgs); opencv unusual |
| P2-1 | pass | -- | RAW v29-35 (v31 absent) |
| P2-2 | fail | -- | No PWL costs; quadratic ignored in DC OPF |
| P2-3 | fail | -- | Pipeline non-functional |
