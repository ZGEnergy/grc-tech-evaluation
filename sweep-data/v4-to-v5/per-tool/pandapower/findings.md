# pandapower -- Sweep Findings (v4)

## Summary

The pandapower v4 evaluation is generally well-executed with thorough documentation of both capabilities and limitations. The tool's architectural scope (steady-state PF and basic OPF) is clearly identified, and the 6 expressiveness failures are correctly classified as architectural gaps rather than bugs. However, several findings warrant attention: the most significant is the C-6/B-4 stochastic wrapping result, where a 2.1% solver convergence rate receives a qualified_pass status that masks practical unusability. The PTDF flow prediction divergence on MEDIUM (7.43 pu max error) is accepted without root-cause verification. Three scalability tests fail solely as cascades from expressiveness failures, inflating the fail count without adding signal. Uniform LMPs across the entire 10k-bus network in A-3/C-3 suggest the DC OPF test does not exercise congestion, limiting the value of the LMP extraction verification. Three probes are recommended: convergence rate verification for the stochastic DCOPF, PTDF flow prediction root-cause analysis, and PYPOWER solver stability characterization.

## Finding Details

### pandapower-F01: Qualified pass with 2.1% solver convergence rate masks practical unusability

**Category:** misleading_result | **Severity:** high
**Tests:** C-6, B-4

Both C-6 (scalability) and B-4 (extensibility) report qualified_pass for the stochastic DCOPF wrapping approach. The loop-based methodology is sound -- modify DataFrames in-place, call `rundcopp()` per scenario/hour pair -- and is classified with workaround_class "stable." However, only 5 of 240 DC OPF solves converge (2.1%). The result narrative acknowledges the low convergence rate but attributes it to "a PYPOWER interior point solver quality issue" and maintains the qualified_pass status.

The concern is that "qualified_pass" with "stable" workaround conveys to a reader that the approach works with some caveats. In reality, a user following this approach on the SMALL network would get results for only 1 out of every 48 solves. The qualification is severe enough that the result could reasonably be classified as a fail for practical purposes. The workaround_class "stable" correctly describes the mechanical stability of the loop approach, but the solver failure rate is a separate dimension that the current schema does not adequately capture.

This finding has cross-tool relevance: other tools using the same SMALL network with load/generation perturbations may also encounter solver difficulties, making this a potential protocol-level issue with the stochastic perturbation methodology or the ACTIVSg2000 case data's sensitivity to scaling.

**Cross-tool relevance:** likely
**Proposed action:** adjust_scoring -- consider whether the scoring rubric should distinguish between "approach is mechanically sound" and "approach produces usable results at the target scale"

### pandapower-F02: Uniform LMPs on 10k-bus network suggest no binding constraints

**Category:** missing_verification | **Severity:** medium
**Tests:** A-3, C-3

A-3 (DC OPF on MEDIUM) and C-3 (DC OPF scalability) both report perfectly uniform LMPs of 20.738 across all 10,000 buses. This means no line flow constraints are binding in the solution. While this may be a property of the ACTIVSg10k case data (the lines may have sufficient capacity for the base load), it means the test does not actually exercise pandapower's ability to produce spatially differentiated LMPs from congestion.

The pass condition for A-3 states: "Converges. Optimal dispatch and LMPs/shadow prices extractable from solution." This is technically met -- LMPs are extractable. But the test provides no evidence that pandapower correctly computes congestion-driven LMP variation, which is the primary use case for LMPs in market analysis. On TINY (case39), the same uniform LMP pattern appears (13.517 everywhere), suggesting neither test network produces congestion under the DC OPF with existing line limits.

This is a cross-tool concern: if all tools produce uniform LMPs on these networks, the LMP extraction test has low discriminative value for congestion-related capabilities.

**Cross-tool relevance:** confirmed
**Proposed action:** add_verification -- consider tightening line limits on the test network to force congestion, or add a secondary test with artificial congestion

### pandapower-F03: PTDF flow prediction diverges on MEDIUM but test still passes

**Category:** extraordinary_claim | **Severity:** medium
**Tests:** B-9, C-9

B-9 reports a maximum flow prediction difference of 7.43 pu between PTDF-predicted flows and DCPF-solved flows on the 10k-bus network. The pass condition for B-9 states: "Flow predictions match DCPF results within numerical tolerance (1e-6)." On TINY, this tolerance is met. On MEDIUM, it is violated by 7 orders of magnitude.

The result attributes the divergence to "shunt elements and tap-ratio effects in transformers not fully captured by the basic PTDF formulation." This is a plausible explanation -- the standard DC PTDF assumes lossless lines with unity tap ratios -- but is stated as speculation rather than verified root cause. The test passes as qualified_pass because the PTDF matrix has correct dimensions and structural properties (slack column zeros, physically reasonable density).

If the divergence is genuinely due to transformer tap ratios, it means the PTDF matrix is not suitable for accurate flow prediction on networks with transformers -- a significant practical limitation for congestion analysis. If it is due to a bug in bus injection vector reconstruction (the result mentions "ordering differences"), it may be fixable.

**Cross-tool relevance:** likely -- other tools computing PTDF on the same MEDIUM network will face similar transformer modeling questions
**Proposed action:** add_verification -- probe should compute PTDF flows on a subnetwork without transformers and on the full network with explicit tap-ratio correction

### pandapower-F04: Contingency sweep scope reduced without clear impact assessment

**Category:** test_design_gap | **Severity:** medium
**Tests:** A-7, C-5

C-5 limits BFS computation to 200 of 10,701 seed branches on the MEDIUM network. The protocol specifies x=5, m=4 for MEDIUM, which would generate an enormous combinatorial space. The scope reduction is pragmatic and acknowledged in the result ("Full enumeration for all branches is O(n * E) and exceeded the time budget"), but the impact is not fully assessed.

The result reports 10,000 cases evaluated out of 31,045 pruned cases, but it is unclear how many total cases the full-scope test would have produced. The per-contingency time (0.054s) is well-documented and useful for cross-tool comparison. The scope reduction does not invalidate the result but makes the "PASS" somewhat qualified -- the tool handles the scope that was tested, but the full protocol parameters were not exercised.

**Cross-tool relevance:** likely -- all tools will face the same combinatorial explosion on MEDIUM with x=5, m=4
**Proposed action:** adjust_scoring -- document scope reduction consistently across tools and assess whether x=5, m=4 on MEDIUM is feasible for any tool

### pandapower-F05: Distributed slack silently ignored in OPF -- scoring inconsistency

**Category:** scoring_inconsistency | **Severity:** medium
**Tests:** B-8

B-8 tests three slack configurations: (a) default, (b) different bus, (c) distributed. Config (c) runs `rundcopp(net, distributed_slack=True)` which silently ignores the parameter and produces results identical to config (a). The test receives qualified_pass because configs (a) and (b) succeed.

The inconsistency is with A-11, which correctly assigns "fail" for distributed slack OPF. B-8's qualified_pass could mislead a reader into thinking distributed slack is partially functional in OPF when it is not functional at all -- the parameter is silently swallowed by `**kwargs`. The observation file (api-friction-extensibility-B-8) correctly flags this as a medium-severity API friction point, but the test outcome does not fully reflect the finding.

The silent parameter swallowing is itself a significant finding: a user calling `rundcopp(net, distributed_slack=True)` receives no indication that the parameter has no effect. This is worse than raising an error because it produces silently incorrect results (single-slack when the user expects distributed slack).

**Cross-tool relevance:** none
**Proposed action:** adjust_scoring -- B-8 pass/fail should be based on the 2 functional configs; the distributed slack aspect should carry a note rather than contributing to the qualified_pass status

### pandapower-F06: Gate tests are trivially passed

**Category:** low_signal | **Severity:** low
**Tests:** G-1, G-2, G-3

All gate tests pass without issues. pandapower's MATPOWER converter handles all three reference networks cleanly. This is expected for any tool with a MATPOWER format parser and does not differentiate pandapower from other tools.

**Cross-tool relevance:** confirmed
**Proposed action:** none -- gate tests serve their purpose as a prerequisite filter even if they don't discriminate among passing tools

### pandapower-F07: Solver lock-in prevents protocol-specified multi-solver comparison

**Category:** infrastructure_friction | **Severity:** low
**Tests:** A-3, C-3, C-7

pandapower's `rundcopp()` is hard-wired to PYPOWER's interior point solver. The protocol specifies HiGHS and GLPK for DC OPF tests and requires multi-solver comparison in C-3 and C-7. This is correctly classified as a tool limitation (C-7 fails), and the evaluator appropriately notes the deviation. However, it means timing comparisons for DC OPF between pandapower and tools using HiGHS/GLPK are not directly comparable -- different solver architectures (interior point vs simplex) have different scaling characteristics.

**Cross-tool relevance:** none
**Proposed action:** none -- correctly handled as a tool finding

### pandapower-F08: Peak memory not measured for multiple tests

**Category:** missing_verification | **Severity:** medium
**Tests:** A-1, A-2, A-3, A-4, A-7

Several expressiveness tests on the MEDIUM network report "Peak memory: not measured." The scalability tests (C-1 through C-9) do measure memory, so the data exists for the same operations when run under the scalability suite. The gap means cross-tool memory comparison for expressiveness tests at scale will have missing data points.

**Cross-tool relevance:** likely
**Proposed action:** add_verification -- memory measurement should be standard for all tests at MEDIUM scale

### pandapower-F09: AC PF solver deviation from protocol

**Category:** test_design_gap | **Severity:** low
**Tests:** C-2

The protocol specifies Ipopt for C-2 (ACPF at scale), but pandapower uses its internal Newton-Raphson implementation. This is the correct solver for AC power flow in pandapower (Ipopt is typically used for NLP optimization, not PF). The deviation reflects a protocol design choice that may not match all tools' solver architectures -- AC PF is typically solved by Newton-Raphson, not by a general NLP solver.

**Cross-tool relevance:** likely -- tools with dedicated NR solvers for PF will all deviate from the Ipopt specification
**Proposed action:** none -- the protocol's Ipopt specification for AC PF may need clarification on whether it means "any NLP solver" or specifically Ipopt

### pandapower-F10: PYPOWER solver produces lambda values of 1e25 when generators decommitted

**Category:** extraordinary_claim | **Severity:** high
**Tests:** P2-3

The P2-3 commitment injection test reveals that using `in_service=False` to decommit generators causes the PYPOWER interior point solver to produce lambda values on the order of 1e25 on the IEEE 39-bus case. This indicates severe numerical instability in the solver when the generator set changes. The workaround (setting `max_p_mw=0` instead) achieves the same functional result but is semantically less clear.

This finding connects to the broader PYPOWER solver fragility theme: the 2.1% convergence rate in C-6/B-4, the solver lock-in in C-7, and the numerical instability in P2-3 all point to the PYPOWER interior point solver being a significant quality limitation for pandapower's OPF capabilities. The solver works on clean, unmodified test cases but degrades rapidly when the problem is perturbed.

**Cross-tool relevance:** none
**Proposed action:** none -- this is an informational finding but the probe should verify whether the 1e25 lambda values are reproducible and whether they affect the B-4/C-6 convergence rate

### pandapower-F11: Three scalability tests fail solely due to upstream expressiveness failures

**Category:** redundant_test | **Severity:** low
**Tests:** C-4, C-8, C-10

C-4 (SCUC scale), C-8 (SCOPF scale), and C-10 (distributed slack scale) all fail because their prerequisite expressiveness tests (A-5, A-9, A-11) failed. These results add no new information. The cascade is correctly documented in each result file, but the raw fail count (14 fails) overstates the number of independent findings. The actual independent failure count is 11: 6 expressiveness failures, 1 scalability failure (C-7 solver swap), plus these 3 cascaded fails and 1 stochastic scale failure (C-6 is more nuanced).

**Cross-tool relevance:** confirmed -- tools with similar expressiveness gaps will show the same cascade pattern
**Proposed action:** adjust_scoring -- consider whether cascaded fails should be counted separately in the evaluation summary, or whether the total should distinguish "independent fails" from "cascaded fails"

### pandapower-F12: ACPF convergence claimed without residual verification

**Category:** missing_verification | **Severity:** medium
**Tests:** A-2, C-2

A-2 and C-2 report ACPF convergence on MEDIUM but do not extract or report the achieved power mismatch residual. The results show that the solver converged (Boolean flag) and report voltage magnitudes/angles, but do not verify the convergence tolerance. pandapower's default NR tolerance is 1e-8 and the solver likely achieves this, but the result files do not document the achieved residual for audit purposes.

**Cross-tool relevance:** confirmed -- all tools' ACPF results should report achieved residuals
**Proposed action:** add_verification

### pandapower-F13: Tutorial verification tests import availability, not execution

**Category:** test_design_gap | **Severity:** low
**Tests:** D-3

D-3 reports 8/8 tutorials pass, but tutorials 7 (contingency analysis) and 8 (plotting) only verify that the relevant modules are importable, not that the tutorial workflows execute successfully. The plotting limitation is understandable (headless container), but the contingency analysis test could have been run. Reporting import checks as "PASS" slightly overstates tutorial completeness.

**Cross-tool relevance:** likely -- headless container limitations may affect tutorial verification across all tools
**Proposed action:** adjust_scoring -- distinguish between "tutorial executed successfully" and "API importable" in the results

## Extraordinary Claims

### C-6: Stochastic DCOPF wrapping qualified pass despite 2.1% convergence rate

**Concern:** A 97.9% solver failure rate makes the approach practically unusable on the SMALL network. The qualified_pass status with "stable" workaround classification conveys that the approach works with caveats, when in reality almost no scenarios produce results. The convergence rate on TINY (where case39 OPF converges reliably) should be checked to isolate whether this is SMALL-network-specific solver sensitivity or a general PYPOWER OPF fragility under perturbation.

**Evidence quality:** strong -- the 2.1% rate is documented from actual execution of 240 solves with captured output.

A probe should: (1) Run the same 240 solves on TINY to establish PYPOWER convergence rate on a smaller network, (2) test whether tighter perturbation bounds improve convergence on SMALL, and (3) verify whether other tools' solvers (HiGHS, Ipopt) achieve higher convergence rates on the same perturbed SMALL scenarios.

### B-9: PTDF matrix correctly computed despite 7.43 pu max flow prediction error on MEDIUM

**Concern:** The B-9 pass condition requires flow predictions to match within 1e-6. The 7.43 pu max error on MEDIUM exceeds this by 7 orders of magnitude. The attributed cause ("shunt elements and tap-ratio effects") is plausible but unverified. If transformer tap ratios are the root cause, the PTDF matrix is not practically useful for flow prediction on the MEDIUM network -- a significant limitation for congestion analysis.

**Evidence quality:** moderate -- the error magnitudes are documented but the root cause is speculative.

A probe should: (1) Compute PTDF-predicted flows on a subset of branches that are lines (not transformers) and verify 1e-6 match, (2) compute PTDF with explicit tap-ratio corrections and check whether errors reduce, (3) verify that the bus injection vector reconstruction correctly maps pandapower's bus indices to the ppc's internal ordering.

### P2-3: PYPOWER solver numerical instability with lambda values ~1e25

**Concern:** The solver's inability to handle generator decommitment on a 39-bus network raises questions about the robustness of all pandapower OPF results where the generator set differs from the default. The 2.1% convergence rate in C-6/B-4 may be a manifestation of the same underlying solver fragility.

**Evidence quality:** strong -- the lambda values are reported from actual execution with specific generator decommitment scenarios.

A probe should: (1) Reproduce the 1e25 lambda values on case39 with `in_service=False`, (2) test whether the same issue occurs on case9 (smaller network), (3) test whether the `max_p_mw=0` workaround produces identical dispatch to a reference solver.

## Test Outcome Matrix

| Test ID | Status | Workaround | Key Issue |
|---------|--------|------------|-----------|
| G-1 | pass | -- | -- |
| G-2 | pass | -- | -- |
| G-3 | pass | -- | -- |
| A-1 | pass | -- | -- |
| A-2 | pass | -- | No residual reported |
| A-3 | qualified_pass | stable (PYPOWER only) | Uniform LMPs, no congestion exercised |
| A-4 | pass | -- | -- |
| A-5 | fail | blocking | No SCUC capability |
| A-6 | fail | blocking | Depends on A-5 |
| A-7 | pass | -- | -- |
| A-8 | fail | blocking | No native stochastic OPF |
| A-9 | fail | blocking | No SCOPF capability |
| A-10 | fail | blocking | No lossy DC OPF |
| A-11 | fail | blocking | Distributed slack not in OPF |
| B-1 | qualified_pass | fragile (_ppc duals) | Internal access for dual values |
| B-2 | pass | -- | -- |
| B-3 | pass | -- | -- |
| B-4 | qualified_pass | stable (manual loop) | 2.1% convergence on SMALL |
| B-5 | pass | -- | -- |
| B-6 | pass | -- | -- |
| B-7 | pass | -- | -- |
| B-8 | qualified_pass | stable | Distributed slack silently ignored |
| B-9 | qualified_pass | fragile (_ppc internals) | 7.43 pu flow prediction error on MEDIUM |
| C-1 | pass | -- | -- |
| C-2 | pass | -- | NR instead of Ipopt per protocol |
| C-3 | qualified_pass | -- | Single solver only |
| C-4 | fail | blocked (A-5) | Cascaded failure |
| C-5 | pass | -- | Reduced scope (200/10701 seeds) |
| C-6 | qualified_pass | stable | 2.1% convergence rate |
| C-7 | fail | -- | No solver swap capability |
| C-8 | fail | blocked (A-9) | Cascaded failure |
| C-9 | pass | -- | -- |
| C-10 | fail | blocked (A-11) | Cascaded failure |
| D-1 | pass | -- | -- |
| D-2 | qualified_pass | stable | OPF docs gaps |
| D-3 | pass | -- | 2/8 tests are import-only |
| D-4 | qualified_pass | -- | Silent cost curve fallback |
| D-5 | informational | -- | -- |
| E-1 | pass | -- | -- |
| E-2 | pass | -- | -- |
| E-3 | pass | -- | -- |
| E-4 | pass | -- | -- |
| E-5 | pass | -- | -- |
| E-6 | pass | -- | -- |
| E-7 | pass | -- | -- |
| F-1 | pass | -- | -- |
| F-2 | pass | -- | -- |
| F-3 | pass | -- | -- |
| F-4 | pass | -- | -- |
| F-5 | pass | -- | -- |
| F-6 | pass | -- | -- |
| F-7 | pass | -- | -- |
| F-8 | pass | -- | -- |
| F-9 | qualified_pass | -- | Unversioned install commands |
| P2-1 | informational | -- | -- |
| P2-2 | informational | -- | -- |
| P2-3 | informational | -- | Solver fragility with decommitment |
