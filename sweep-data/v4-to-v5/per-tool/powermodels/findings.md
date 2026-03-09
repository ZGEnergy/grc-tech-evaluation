# PowerModels.jl -- Sweep Findings (v4)

## Summary

The PowerModels.jl evaluation is thorough and well-documented across 76 result files with zero gaps. The synthesis report is fair in its characterization of PowerModels as a research-grade steady-state OPF tool with strong core capabilities but significant gaps beyond built-in problem types. The primary sweep concerns are: (1) two scale tests scored as fails without execution, based on extrapolated estimates; (2) the distributed slack validation is defeated by uncongested test networks at both TINY and SMALL scale; (3) SCUC/SCED failures at SMALL conflate open-source solver limitations with tool capability; (4) the A-9 SMALL SCOPF uses 20 contingencies instead of the protocol-specified 50; and (5) timing comparisons across network sizes are unreliable due to Julia JIT cache effects. Three probes are recommended: verifying the C-5/C-8 infeasibility claims with actual execution attempts, validating the PTDF timing anomaly with cold-start measurements, and testing the A-2 MEDIUM ACPF convergence with exposed NLsolve parameters.

## Finding Details

### pm-F01: Distributed slack LMP validation defeated by uncongested network

**Category:** network_insufficiency | **Severity:** medium
**Tests:** A-11

The A-11 test is designed to verify that distributed slack changes LMP decomposition relative to single-slack. On both TINY (IEEE 39-bus) and SMALL (ACTIVSg 2000-bus), the distributed slack formulation is structurally correct but produces identical LMPs to single-slack because neither network has binding flow constraints (no congestion). The TINY result reports: "LMP range: 2.5e-6 (nearly uniform)." The SMALL result reports: "Max LMP difference: 0.0 (identical) ... no binding flow constraints in the LP-relaxed (linearized cost) DC OPF."

This means the distributed slack mechanism has never been differentially validated in this evaluation. The PTDF transformation `H_dist = H - H * w` is mathematically correct and the weights are settable, but the test cannot confirm that the LMP decomposition responds correctly under congestion -- which is the entire point of distributed slack from an ISO market clearing perspective.

This is likely a cross-tool issue: if ACTIVSg 2000 has no congestion under linearized costs, other tools' distributed slack tests may face the same limitation.

**Cross-tool relevance:** likely
**Proposed action:** redesign_test -- Either use a test network with known congestion, or artificially constrain flow limits to force binding constraints.

---

### pm-F02: A-9 SMALL SCOPF uses only 20 of 3,206 contingencies vs protocol's 50 requirement

**Category:** misleading_result | **Severity:** medium
**Tests:** A-9

The eval-config.yaml specifies "SMALL: 50 monitored branches" for A-9 SCOPF. The actual evaluation used only 20 contingencies (the 20 most-loaded branches from the base DC OPF). The result states: "Valid contingencies: 20 (no islanding excluded from top candidates)." The 4.74% security premium and OPTIMAL solve in 41.27s demonstrate SCOPF capability, but at 40% of the specified contingency count.

This deviation may be justified by practical constraints (model construction took ~70s for 21 networks), but it is not flagged as a protocol deviation in the result file. The qualified_pass status does not reflect this shortfall in contingency count.

**Cross-tool relevance:** likely -- other tools' SCOPF tests should be checked for the same deviation.
**Proposed action:** adjust_scoring -- Either note the deviation explicitly in the grade narrative or re-run with 50 contingencies.

---

### pm-F03: Scale tests C-5 and C-8 scored as fail without execution

**Category:** extraordinary_claim | **Severity:** medium
**Tests:** C-5, C-8

C-5 (N-M contingency sweep at MEDIUM, x=5, m=4) and C-8 (SCOPF at MEDIUM, 500 contingencies) are both recorded as "NOT ATTEMPTED (expected timeout)" and scored as fails. The infeasibility claims are based on extrapolation:

- C-5 estimates "500-2,000 branches in scope" at BFS depth 5 on 10k-bus, but the actual BFS was never run. The per-solve time of "0.2-0.5s" is estimated from TINY scaling, not measured.
- C-8 estimates "~10,000,000 constraints" for 500 contingencies, but does not attempt iterative contingency screening (which worked at SMALL with 20 contingencies in 41.27s).

While these estimates are physically plausible, a sweep should flag that these are projections, not measurements. The C-8 estimate is particularly questionable because iterative SCOPF could potentially work if only a small fraction of 500 contingencies are binding.

**Cross-tool relevance:** likely -- other tools may face the same N-M and SCOPF scale challenges.
**Proposed action:** add_verification -- At minimum, run the BFS at MEDIUM to determine actual scope, and attempt iterative SCOPF with progressive contingency screening.

---

### pm-F04: SCUC/SCED failures conflate tool capability with open-source solver limitations

**Category:** test_design_gap | **Severity:** high
**Tests:** A-5, A-6, C-4

A-5 SMALL fails because HiGHS cannot solve the LP relaxation of a ~500k constraint MILP within 300s single-threaded. A-6 SMALL fails because it depends on A-5. C-4 fails for the same reason as A-5. The evaluation correctly notes "The timeout is a solver capability issue, not a PowerModels expressiveness issue per se," but all three are scored as fails against PowerModels.

The protocol mandates single-threaded open-source solvers, which creates a fundamental confound at the 2000-bus UC scale. The ~39,168 binary variables and >500,000 constraints exceed what any current open-source single-threaded MIP solver can handle in 300s. This likely affects all tools that must manually assemble SCUC (since PowerModels has no built-in UC), but even tools with built-in SCUC may fail at this scale with these solver constraints.

The issue is cross-tool confirmed: the protocol's solver and threading constraints define a practical ceiling on SCUC scale that is independent of tool capability.

**Cross-tool relevance:** confirmed
**Proposed action:** adjust_scoring -- Consider separating the "can the tool express SCUC" question (which PowerModels answers via 140 LOC of JuMP) from the "can open-source solvers solve the resulting MILP at scale" question.

---

### pm-F05: A-8 blocking fail vs B-4 pass creates scoring tension

**Category:** scoring_inconsistency | **Severity:** medium
**Tests:** A-8, B-4

A-8 tests whether the tool natively supports scenario-indexed stochastic optimization. PowerModels does not -- the multi-network framework has one dimension (time periods) with no scenario indexing, probability weighting, or recourse structure. This is correctly scored as a blocking fail. B-4 tests whether the tool can be wrapped for scenario analysis in a loop. PowerModels passes cleanly: `deepcopy + replicate + solve_mn_opf` runs 20 scenarios x 12 periods at SMALL scale in 281.6s with consistent per-scenario timing.

The protocol correctly distinguishes these (A-8 = native stochastic, B-4 = wrapping), and the synthesis handles it properly. However, the operational impact is worth noting: from a user's perspective, the B-4 workflow is the practical approach to stochastic analysis regardless of whether the tool has native support. The A-8 fail penalizes PowerModels for lacking a feature that few power system optimization tools provide natively.

**Cross-tool relevance:** confirmed -- this A-8/B-4 tension likely appears for multiple tools.
**Proposed action:** None -- the protocol distinction is correct, but the grade narrative should acknowledge that B-4 provides operational mitigation.

---

### pm-F06: Lossy DCOPF MATPOWER reference comparison uses mismatched formulations

**Category:** missing_verification | **Severity:** low
**Tests:** A-10

The A-10 protocol requires: "Validate against MATPOWER reference lossy DC OPF solution on same case (tolerance: 1% on total LMP, directional consistency on loss component signs)." The evaluation could not perform this comparison because the MATPOWER reference used lossless DC OPF with post-hoc loss estimation, while PowerModels used DCPLLPowerModel (losses in optimization). The result acknowledges: "Direct 1% LMP comparison is not applicable."

The loss magnitudes are directionally consistent (0.73% vs 0.78% of load), but the protocol's 1% LMP tolerance validation is unmet.

**Cross-tool relevance:** confirmed -- other tools will face the same MATPOWER reference comparison challenge if their loss formulations differ from MATPOWER's.
**Proposed action:** redesign_test -- The protocol should specify what MATPOWER reference formulation to use for the lossy DCOPF comparison, or accept same-tool lossless-vs-lossy as the validation.

---

### pm-F07: SCOPF cost comparison uses incompatible cost functions

**Category:** extraordinary_claim | **Severity:** low
**Tests:** A-9

A-9 TINY compares SCOPF objective (1,878.27, linearized cost via HiGHS LP) to unconstrained DC OPF objective (41,263.94, quadratic cost via Ipopt). The 20x cost difference is almost entirely due to the linearization, not the security constraints. The result includes a footnote: "Direct cost comparison is not meaningful because SCOPF uses linearized costs while PowerModels' DC OPF uses the full quadratic cost function." The key validation (dispatch differs) is correct, but the raw numbers could mislead a reader scanning the output.

**Cross-tool relevance:** likely
**Proposed action:** None -- the result file is transparent about the limitation.

---

### pm-F08: ACPF MEDIUM failure lacks convergence diagnostics

**Category:** missing_verification | **Severity:** medium
**Tests:** A-2, C-2

A-2 MEDIUM reports NLsolve convergence failure on the ACTIVSg 10k-bus network, but provides no diagnostic detail: no iteration count, no residual magnitude, no indication of divergence vs. slow convergence. The result states: "PowerModels does not expose NLsolve iteration count or convergence diagnostics through its API."

This matters because the failure could be resolvable by adjusting NLsolve parameters (iteration limit, tolerance, algorithm variant), but PowerModels' `compute_ac_pf` API does not expose these controls. The distinction between "NLsolve needs more iterations" and "the problem is fundamentally ill-conditioned" cannot be determined from the available output.

**Cross-tool relevance:** likely -- other tools' ACPF at 10k-bus should report convergence diagnostics.
**Proposed action:** add_verification -- Attempt ACPF via the Ipopt-based `solve_ac_pf` with a longer timeout, or directly configure NLsolve outside the PowerModels API.

---

### pm-F09: Gate tests have low discriminative value for MATPOWER-native tools

**Category:** low_signal | **Severity:** low
**Tests:** G-1, G-2, G-3

PowerModels has a built-in MATPOWER parser. G-1/G-2/G-3 pass trivially with `parse_file()`. These tests primarily differentiate tools that require format conversion (e.g., PyPSA, PowerSimulations). For MATPOWER-native tools (PowerModels, pandapower, MATPOWER itself), the gate tests provide minimal signal.

**Cross-tool relevance:** confirmed
**Proposed action:** None -- the tests serve their purpose for the full tool set even if individual tools pass trivially.

---

### pm-F10: A-4 MEDIUM AC feasibility check did not complete

**Category:** missing_verification | **Severity:** medium
**Tests:** A-4

A-4 MEDIUM is scored as qualified_pass, but the AC feasibility check never completed. Newton-Raphson failed to converge (118.73s), and the Ipopt fallback was killed after 46 minutes. The test verifies that the 3-line workflow pattern is correct, but it never identifies any voltage or thermal violations because no AC solution was obtained. The pass condition states: "Voltage violations and thermal limit violations identifiable from results" -- this was not achieved at MEDIUM scale.

The qualified_pass seems generous given that the core pass condition (identifying violations) was not met. The qualification should note that the feasibility check workflow is expressible but produces no usable results at 10k-bus scale.

**Cross-tool relevance:** likely -- ACPF convergence at 10k-bus is a known challenge.
**Proposed action:** adjust_scoring -- Consider whether a test that never completes its core function should receive qualified_pass.

---

### pm-F11: HiGHS QP failure on ACTIVSg2000 forces solver workarounds

**Category:** infrastructure_friction | **Severity:** low
**Tests:** A-3, A-10, C-3, C-7, A-11

HiGHS QP consistently fails on the ACTIVSg2000 network (returns objective=0.0, primal infeasibility, or times out), affecting A-10 SMALL (lossless comparison objective=0.0), A-11 SMALL (Ipopt fallback required), C-3 MEDIUM (300s timeout), and C-7 MEDIUM (same). Ipopt or cost linearization is used as workaround. This is not a PowerModels issue but it creates inconsistent cost function comparisons across network sizes: TINY uses HiGHS with quadratic costs, while SMALL/MEDIUM requires Ipopt or linearized costs.

**Cross-tool relevance:** confirmed -- all tools using HiGHS QP may face this at scale.
**Proposed action:** None -- this is a known HiGHS limitation.

---

### pm-F12: N-M contingency sweep conflates combinatorial complexity with tool capability

**Category:** test_design_gap | **Severity:** medium
**Tests:** A-7, C-5

The N-M contingency sweep (A-7) demonstrates PowerModels' capability at TINY scale: BFS graph scoping, combinatorial enumeration with pruning, and efficient re-solve via `deepcopy + br_status=0 + compute_dc_pf`. The failure at MEDIUM is due to combinatorial explosion (C(1000,3) = 166M combinations), not a tool API limitation. No tool can enumerate N-4 contingencies on a 10k-bus network in polynomial time.

Meanwhile, B-3 (N-1 contingency loop) passes at MEDIUM scale with 50 contingencies in 3.43s, demonstrating that the per-contingency workflow scales adequately. The N-M test design punishes tools for mathematical impossibility rather than measuring tool capability at the higher orders.

**Cross-tool relevance:** confirmed -- N-M combinatorial explosion affects all tools equally.
**Proposed action:** redesign_test -- Consider capping the N-M test at N-2 for MEDIUM, or scoring based on N-1/N-2 performance with N-3+ as informational.

---

### pm-F13: C-4 is a duplicate of A-5 SMALL with no additional measurement

**Category:** redundant_test | **Severity:** low
**Tests:** C-4, A-5

C-4 explicitly states: "The result is derived from the A-5 SMALL test, which demonstrated the same problem." Same script, same wall-clock (494.5s), same fail classification. The protocol calls for C-4 to include "Wall-clock time per solver, MIP gap, peak memory, CPU utilization" with both HiGHS and SCIP. Only HiGHS was tested, no memory/CPU was measured, and SCIP was not attempted "given that HiGHS could not even solve the LP relaxation."

**Cross-tool relevance:** likely
**Proposed action:** None -- the deduplication is reasonable given the A-5 failure, but the missing SCIP attempt should be noted.

---

### pm-F14: Peak memory not measured on several scalability tests

**Category:** missing_verification | **Severity:** low
**Tests:** C-2, C-4, C-5, C-6, C-7, C-8

Six of ten C-suite tests report `peak_memory_mb: null`. The protocol lists peak_memory as a recorded metric for all C-tests. C-1 (121 MB), C-3 (184 MB), C-9 (2,452 MB), and C-10 (1,017 MB) do report memory, providing useful data points. The gap makes cross-tool memory comparison incomplete for SCUC, stochastic, and contingency tests.

**Cross-tool relevance:** likely
**Proposed action:** add_verification

---

### pm-F15: C-7 qualified_pass for solver swap mechanism that actually works trivially

**Category:** scoring_inconsistency | **Severity:** low
**Tests:** C-7

The C-7 result explicitly states: "Solver swapping is trivial from the API perspective. The qualification is due to solver-specific limitations, not PowerModels API friction." The pass condition asks: "Whether solver swap requires reformulation or just a parameter change." The answer is unambiguously "just a parameter change." The qualified_pass conflates solver performance (HiGHS QP timeout, GLPK/SCIP need linearized costs) with the swap mechanism itself.

The cost linearization workaround for LP-only solvers could be considered a mild reformulation, which would justify qualified_pass. But the result file attributes the qualification to solver performance, not to the linearization requirement.

**Cross-tool relevance:** likely
**Proposed action:** adjust_scoring -- Either score as pass with a note about solver-specific cost linearization, or clarify that the qualification is for the linearization requirement (a mild reformulation), not for solver performance.

---

### pm-F16: PTDF computation faster at MEDIUM than SMALL due to JIT warm cache

**Category:** extraordinary_claim | **Severity:** low
**Tests:** C-10

C-10 reports PTDF computation taking 3.03s at 10k-bus vs ~20s at 2k-bus (SMALL). The PTDF matrix at MEDIUM has 127M elements vs ~6.4M at SMALL (20x larger), so computation should take longer, not less. The result attributes this to "warm JIT cache from prior Julia session operations," which is plausible for Julia but means the SMALL measurement includes JIT compilation overhead while MEDIUM does not.

This makes the scaling analysis table in C-10 unreliable. The 0.15x ratio for PTDF compute (MEDIUM/SMALL) cannot be used for cross-tool scaling comparisons without noting the JIT confound.

**Cross-tool relevance:** none -- Julia-specific issue.
**Proposed action:** add_verification -- Measure PTDF computation at MEDIUM with a cold Julia session for accurate scaling comparison.

---

## Extraordinary Claims

### C-5: N-M contingency sweep at MEDIUM would take 28-70 hours

**Concern:** The estimate projects TINY timing (0.0014s per DCPF solve) to MEDIUM scale (0.2-0.5s per solve) and combines it with an estimated BFS scope of 500-2,000 branches. Neither the per-solve time at MEDIUM nor the actual BFS scope were measured. The BFS scope estimate has a 4x range, and the per-solve time estimate has a 2.5x range, producing a combined uncertainty of 10x on the total runtime projection.

**Evidence quality:** weak

A probe should: (1) run BFS from a representative seed bus at depth 5 on ACTIVSg 10k to determine actual scope, (2) measure per-DCPF solve time at 10k-bus with a cold JIT, and (3) run the N-1 portion to validate the per-solve estimate. N-2+ can remain projected.

### C-8: SCOPF at MEDIUM with 500 contingencies exceeds solver capacity

**Concern:** The constraint count estimate (~10M) assumes full N-1 SCOPF without iterative screening. At SMALL scale, iterative SCOPF with 20 contingencies solved in 41.27s. It is plausible that iterative screening at MEDIUM would converge with a manageable number of binding contingencies (typical SCOPF experience is 5-15% binding rate). The estimate does not attempt this approach.

**Evidence quality:** moderate

A probe should: attempt iterative SCOPF at MEDIUM starting with a small contingency set (e.g., 20 most-loaded branches), screening for violations, and progressively adding contingencies until convergence or timeout.

### C-10: PTDF computation 6.6x faster at MEDIUM than SMALL

**Concern:** This violates expected computational scaling. Julia JIT compilation can produce significant first-call overhead, making subsequent calls in the same session much faster. If the SMALL PTDF was the first large computation in that session while the MEDIUM PTDF ran after warm-up, the comparison is invalid.

**Evidence quality:** weak

A probe should: measure PTDF computation at both SMALL and MEDIUM in fresh Julia sessions with no prior computations, ensuring JIT overhead is included consistently or excluded consistently.

## Test Outcome Matrix

| Test ID | Network | Status | Workaround | Key Issue |
|---------|---------|--------|------------|-----------|
| G-1 | TINY | pass | -- | -- |
| G-2 | SMALL | pass | -- | -- |
| G-3 | MEDIUM | pass | -- | -- |
| A-1 | TINY | pass | -- | -- |
| A-1 | MEDIUM | pass | -- | -- |
| A-2 | TINY | pass | -- | -- |
| A-2 | MEDIUM | fail | -- | NLsolve convergence failure, no diagnostics exposed |
| A-3 | TINY | pass | -- | -- |
| A-3 | MEDIUM | pass | stable (data fix) | 1,349 gens needed cost array fixes |
| A-4 | TINY | pass | -- | -- |
| A-4 | MEDIUM | qualified_pass | stable | AC PF never completed; workflow expressible but no results |
| A-5 | TINY | qualified_pass | stable | No native SCUC; ~140 LOC JuMP; MIP gap 0.0% |
| A-5 | SMALL | fail | stable | HiGHS MIP timeout; solver limitation not tool limitation |
| A-6 | TINY | qualified_pass | stable | No native SCED; ~200 LOC JuMP; ramp constraints verified |
| A-6 | SMALL | fail | stable (blocked) | Blocked by A-5 SMALL failure |
| A-7 | TINY | qualified_pass | stable | No native graph/sweep; 1,561 solves in 2.25s |
| A-7 | MEDIUM | fail | stable | Combinatorial explosion; not a tool limitation |
| A-8 | TINY | fail | blocking | No native stochastic; architectural limitation |
| A-8 | SMALL | fail | blocking | Same limitation as TINY |
| A-9 | TINY | qualified_pass | stable | No native SCOPF; ~180 LOC JuMP; 1.5x rating relaxation |
| A-9 | SMALL | qualified_pass | stable | 20 contingencies (protocol: 50); 4.74% security premium |
| A-10 | TINY | qualified_pass | stable | DCPLLPowerModel requires Ipopt (QCQP); LMP decomposition manual |
| A-10 | SMALL | qualified_pass | stable | Ipopt required; HiGHS QP objective=0 on ACTIVSg2000 |
| A-11 | TINY | qualified_pass | stable | No native distributed slack; ~150 LOC; no congestion to validate |
| A-11 | SMALL | qualified_pass | stable | ~350 LOC; no congestion; LMPs identical |
| B-1 | TINY | pass | -- | -- |
| B-1 | MEDIUM | pass | -- | -- |
| B-2 | TINY | qualified_pass | stable | ~15 LOC manual adjacency graph |
| B-2 | MEDIUM | qualified_pass | stable | Same approach scales |
| B-3 | TINY | pass | -- | 46 N-1 in 0.22s |
| B-3 | MEDIUM | pass | -- | 50 N-1 in 3.43s |
| B-4 | TINY | pass | -- | Scenario wrapping clean |
| B-4 | SMALL | pass | -- | 20 scenarios x 12 periods in 281.6s |
| B-5 | TINY | pass | -- | < 5 lines to DataFrame/CSV |
| B-5 | MEDIUM | pass | -- | -- |
| B-6 | N/A | pass | -- | Clean 4-layer architecture |
| B-7 | TINY | pass | -- | AC feasibility clean 3-line workflow |
| B-7 | MEDIUM | pass | -- | -- |
| B-8 | TINY | pass | stable | Ref bus via data dict mod + re-solve |
| B-8 | SMALL | pass | stable | -- |
| B-9 | TINY | pass | -- | Native PTDF; error < 1e-11 |
| B-9 | MEDIUM | pass | -- | 127M elements in 3.73s |
| C-1 | MEDIUM | pass | -- | 0.234s solve, 121 MB |
| C-2 | MEDIUM | fail | -- | NLsolve convergence failure |
| C-3 | MEDIUM | pass | stable | Ipopt 3.13s; HiGHS QP timeout; GLPK 50.91s |
| C-4 | SMALL | fail | stable | Duplicate of A-5 SMALL; SCIP not attempted |
| C-5 | MEDIUM | fail | stable | Not executed; projected infeasibility |
| C-6 | SMALL | pass | -- | 281.6s for 20 scenarios |
| C-7 | MEDIUM | qualified_pass | stable | Swap trivial; qualification is solver performance |
| C-8 | MEDIUM | fail | stable | Not executed; projected infeasibility |
| C-9 | MEDIUM | pass | -- | 6.65s, 2,452 MB |
| C-10 | MEDIUM | qualified_pass | stable | 12.2s, 1,017 MB; PTDF timing anomaly |
| D-1 | N/A | qualified_pass | -- | 5.2s load-to-solve; Julia startup overhead |
| D-2 | N/A | qualified_pass | -- | 4/11 from docs alone; 4/11 no docs |
| D-3 | N/A | qualified_pass | -- | All examples work; tutorial 7 years old |
| D-4 | N/A | qualified_pass | -- | 1/3 good, 2/3 poor error messages |
| D-5 | N/A | informational | -- | Built-in ~100 LOC, manual ~269 LOC mean |
| E-1 | N/A | pass | -- | 5-7 releases in 24 months |
| E-2 | N/A | qualified_pass | -- | 24 commits/yr, 3 human committers |
| E-3 | N/A | fail | -- | Bus factor = 1 (ccoffrin 82.4%) |
| E-4 | N/A | informational | -- | DOE/LANL funding; no commercial backing |
| E-5 | N/A | qualified_pass | -- | 81-day median close; batch triage |
| E-6 | N/A | pass | -- | 94% coverage, cross-platform CI |
| E-7 | N/A | fail | -- | No operational deployment evidence |
| F-1 | N/A | pass | -- | BSD-3-Clause |
| F-2 | N/A | informational | -- | 114 packages |
| F-3 | N/A | qualified_pass | -- | GLPK GPL-3.0 and SCIP ZIB optional |
| F-4 | N/A | pass | -- | Pure Julia core |
| F-5 | N/A | pass | -- | Full path inspectable |
| F-6 | N/A | pass | -- | Content-addressed hashes |
| F-7 | N/A | pass | -- | Airgap via depot cloning |
| F-8 | N/A | pass | -- | HiGHS + Ipopt cover all formulations |
| F-9 | N/A | pass | -- | No mutable URLs |
| P2-1 | N/A | informational | -- | Built-in v33 parser; v34+ unsupported |
| P2-2 | TINY | informational | -- | Native PWL; lambda formulation; LP-compatible |
| P2-3 | TINY | informational | -- | Steps 2-4 trivial; Step 1 needs manual SCUC |
