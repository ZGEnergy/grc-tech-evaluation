# PowerSimulations.jl -- Sweep Findings (v4)

## Summary

The PowerSimulations.jl evaluation is thorough in coverage (all 57 test IDs have result files) and generally well-documented. The most significant quality concern is that four scalability tests (C-3, C-4, C-5, C-6) report only estimated timings without actual execution, which undermines the scalability grade's evidentiary basis. A potential reporting error in the A-4 unit mismatch finding -- where dispatch values labeled as "pu" in A-4 appear to actually be MW based on A-3's consistent labeling -- warrants verification since this finding cascades into multiple grades (expressiveness, extensibility, P2-readiness). Several tests operate on networks or configurations that are too small or uncongested to exercise the feature being tested (SCUC with no cycling, distributed slack with no congestion, SCOPF with 70% of contingencies filtered). Six probes are recommended, primarily for timing verification of unmeasured scalability claims.

## Finding Details

### psi-F01: Four scalability tests report estimated timings without actual measurement

**Category:** extraordinary_claim | **Severity:** high
**Tests:** C-3, C-4, C-5, C-6

C-3 (DCOPF scale on MEDIUM) states "HiGHS is expected to solve the MEDIUM DCOPF in < 60s" but `wall_clock_seconds: null` in its frontmatter. The result file mentions a test script but notes it "requires fix for RenewableDispatch accessor -- script bug, not tool limitation," suggesting the test was not successfully run. C-4 (SCUC on SMALL) provides only "Expected solve time | >300s (estimated)" and has no measured timing. C-5 (contingency sweep on MEDIUM) explicitly states "Wall-clock time not measured at MEDIUM scale" and references only the TINY-scale functional test. C-6 (stochastic on SMALL) says "Not measured at SMALL scale. Estimated 10-20 minutes."

The protocol is explicit: "Record everything. For each test, record: Wall-clock time (for scalability-relevant tests)." Four of ten scalability tests lack this mandatory data. These tests received `qualified_pass` status based on extrapolation from TINY results and theoretical analysis rather than measured evidence. This substantially weakens the scalability grade's confidence, as the synthesis itself acknowledges: "Several scalability tests lack measured wall-clock times (C-3, C-4, C-5, C-6 provide estimates only)."

**Cross-tool relevance:** likely -- other tool evaluations may have similar unmeasured estimates.
**Proposed action:** add_verification -- these tests should be re-run with actual measurements.

### psi-F02: Unit mismatch between PSI dispatch output and PowerSystems limits -- possible reporting error

**Category:** extraordinary_claim | **Severity:** high
**Tests:** A-4, B-7

This is the single most impactful finding in the evaluation, affecting the expressiveness, extensibility, and P2-readiness grades. The claim is that PSI's `read_variables()` returns dispatch values ~100x larger than `get_active_power_limits()`. However, comparing A-3 and A-4 reveals an inconsistency in the test reports themselves.

In A-3's dispatch table, gen-1 shows "660.85 MW" with "Pmax 1040.0 MW" -- consistent MW units, no mismatch. In A-4's dispatch table, gen-1 shows "660.85 pu" with "Dispatch (MW) 66,085" and "Pmax (pu) 10.40" -- here the same 660.85 value is labeled as pu rather than MW, and the MW column multiplies by 100 (system base MVA). The 660.85 value is the same in both tests, but A-3 calls it MW and A-4 calls it pu.

If gen-1's Pmax is 1040 MW (as shown in A-3) and the dispatch is 660.85 MW (as shown in A-3), there is no unit mismatch. But if gen-1's Pmax in the System is stored as 10.40 pu (on 100 MVA base), then PSI returning 660.85 would indeed be a ~63.5x mismatch. The question is: does `get_active_power_limits()` return values in pu (10.40) or MW (1040.0)? The B-7 result says "dispatch values from PSI are ~100x larger than Pmax values from the System" which suggests the System returns pu values. But this needs verification because the cascade of this finding is significant: it drives the "fragile" workaround classification for B-7, the qualified_pass for A-4, and the "partially ready" assessment for P2-3.

**Cross-tool relevance:** none -- this is specific to PSI's internal unit conventions.
**Proposed action:** add_verification -- re-run the dispatch-to-ACPF transfer with explicit unit logging.

### psi-F03: Custom constraint dual value verified only for non-binding case

**Category:** missing_verification | **Severity:** medium
**Tests:** B-1

B-1 successfully demonstrates JuMP model access and constraint injection via `@constraint`, which is a genuine strength. However, the flow gate was set at 80% of the unconstrained absolute flow sum, and the signed flow sum (-5.54 pu) was well below the limit (8.33 pu). The constraint was non-binding, so the dual was zero. A second test with a "very loose" limit of 100.0 pu also produced dual = 0.0. Neither test demonstrated a binding constraint with a non-zero dual value.

The protocol's pass condition states: "Dual value of custom constraint extractable and correctly reflects binding status." While zero-dual-for-non-binding is correct, the positive case (non-zero dual for binding constraint) was never tested. The result even acknowledges this gap. A tighter gate limit that forces the constraint to bind would complete the verification.

**Cross-tool relevance:** likely -- other tools may also test only non-binding constraints.
**Proposed action:** add_verification -- re-run with a gate limit that forces binding.

### psi-F04: A-7 scored as pass despite requiring stable workaround

**Category:** scoring_inconsistency | **Severity:** medium
**Tests:** A-6, A-7

A-7 (contingency sweep) has `status: pass` in its frontmatter but `workaround_class: stable`. The workarounds include manual adjacency graph construction (~40 LOC), manual BFS implementation, and using PowerFlows.jl instead of PSI's DecisionModel. These are all stable workarounds using public API, but the protocol convention states that tests requiring workarounds should be `qualified_pass`, not `pass`. The synthesis itself flags this: "Both have status: pass but workaround_class: stable. Convention suggests qualified_pass."

A-6 has `status: qualified_pass` in its frontmatter, which is consistent with its stable workaround. The inconsistency is with A-7 only.

**Cross-tool relevance:** likely -- workaround-vs-pass classification may be inconsistent across tools.
**Proposed action:** adjust_scoring -- A-7 should be qualified_pass.

### psi-F05: SCUC on 39-bus produces no unit cycling

**Category:** network_insufficiency | **Severity:** medium
**Tests:** A-5

The 39-bus case has 10 generators with total capacity closely matching peak load, so the SCUC solution has all generators committed ON for all 24 hours. This means the test does not exercise the core UC features: min up/down time constraints never bind, startup costs are never incurred, and shutdown decisions never occur. The SCUC degenerates to a dispatch problem with binary variables that are all trivially 1.

This is a known limitation of the IEEE 39-bus case for UC testing and affects all tools equally. The evaluation correctly identifies this ("expected for a system where total capacity closely matches peak load") but still grades the test as qualified_pass. The SCUC formulation features (built-in commitment variables, startup/shutdown modeling, ramp constraints) are verified as present in the formulation, but their correctness under binding conditions is not tested.

**Cross-tool relevance:** confirmed -- this affects all tools using case39 for SCUC.
**Proposed action:** redesign_test -- consider augmenting the case39 generator fleet with excess capacity to force cycling, or use a different test case.

### psi-F06: Distributed slack test cannot discriminate on uncongested network

**Category:** misleading_result | **Severity:** medium
**Tests:** A-11

A-11 compares PTDFPowerModel and DCPPowerModel on the uncongested case39 network. Both produce numerically identical dispatch (max difference 1.5e-5 MW) and objectives (difference 3.8e-13). The test cannot verify that the PTDF formulation actually distributes slack differently because there is no congestion to reveal the difference.

Furthermore, the pass condition requires "distributed slack weights are settable via API." The result explicitly states "Weights are not configurable." The qualified_pass is based on the argument that PTDF is "inherently" a distributed slack formulation, but this is an architectural claim about the mathematical formulation, not a demonstrated capability difference. On a congested network, PTDF produces a single system price while DCP produces differentiated nodal LMPs -- the formulations would diverge, but this was not tested.

**Cross-tool relevance:** confirmed -- this network limitation affects all tools using case39 for distributed slack testing.
**Proposed action:** redesign_test -- use a congested network or add artificial congestion to demonstrate formulation differences.

### psi-F07: A-6 SCED qualified_pass is generous given ramp enforcement failure

**Category:** scoring_inconsistency | **Severity:** low
**Tests:** A-6

The pass condition for A-6 explicitly requires "ramp rate constraints are demonstrably enforced between consecutive dispatch intervals in the ED stage." The test demonstrates 182 ramp violations with ThermalBasicDispatch (which has no ramp constraints by design), and ThermalRampLimited (which would enforce ramps) fails to build due to HiGHS initial condition issues. The core pass condition is unmet.

The qualified_pass is reasonable in that the tool has a formulation that should enforce ramps (`ThermalRampLimited`) but it cannot be demonstrated due to a solver interaction issue. The result honestly documents the failure. However, the distinction between "feature exists but doesn't work" and "feature doesn't exist" is thin from the user's perspective.

**Cross-tool relevance:** likely -- other tools may have similar edge cases where features exist but cannot be demonstrated.
**Proposed action:** adjust_scoring -- consider whether this should be scored as fail with a note about the ThermalRampLimited formulation's existence.

### psi-F08: SCOPF contingency filtering removes 70% of contingencies

**Category:** test_design_gap | **Severity:** medium
**Tests:** A-9

The SCOPF test filters out 32 of 46 contingencies as "near-radial" using a max |LODF| > 0.9 threshold, leaving only 14 contingencies and 156 additional constraints. The 0.51% cost increase over baseline is modest. While near-radial contingency filtering is standard practice in production SCOPF, the aggressiveness of the filter on this small network (removing 70%) makes it difficult to assess whether the approach would work with a realistic contingency set. The resulting problem (56 variables, ~200 constraints) is trivial for HiGHS.

The test does demonstrate that contingency constraints affect dispatch (gen-1 increases by 282 MW, gen-3 decreases by 135 MW), confirming the constraints are operational. The approach is sound in principle, but the test's discriminative value is limited by the small remaining contingency set.

**Cross-tool relevance:** confirmed -- all tools face the same case39 near-radial topology issue.
**Proposed action:** none -- the finding is acknowledged and documented.

### psi-F09: Mandatory time series boilerplate inflates LOC and qualified_pass count

**Category:** infrastructure_friction | **Severity:** low
**Tests:** A-3, A-4, A-5, A-6, A-8, A-9, A-10, A-11, B-4

PSI is a multi-period simulation framework, not a single-period OPF tool. The ~30 LOC of time series boilerplate required for every optimization test is a genuine design characteristic, not an artifact of the evaluation. However, it produces a systematic pattern: 8 of 9 optimization tests require identical boilerplate and receive qualified_pass partly because of it. This inflates the qualified_pass count and may make PSI's expressiveness grade appear worse than if the test protocol accounted for framework paradigm differences.

The time series requirement is stable, well-documented (though not as a standalone recipe), and reflects the tool's intended use case. It is a legitimate accessibility and expressiveness finding but should be weighted as a single recurring friction pattern rather than eight independent workarounds.

**Cross-tool relevance:** none -- this is specific to PSI's architecture.
**Proposed action:** none -- the synthesis already handles this correctly by describing it as a systematic pattern.

### psi-F10: ACPF scale failure lacks convergence diagnostics

**Category:** missing_verification | **Severity:** medium
**Tests:** C-2

C-2 reports ACPF failure on MEDIUM with only the error message "The NewtonRaphsonACPowerFlow solver failed to converge." No iteration count, residual history, or convergence trajectory is provided. The root cause analysis speculates about missing robustness features but does not verify:
- How many NR iterations were attempted before failure
- What the final residual was
- Whether manually setting voltages from a DCPF solution would improve convergence
- Whether Ipopt as an alternative NR solver could converge

The result states "PowerFlows.jl does not support DC warm start initialization" but does not confirm whether voltage setpoints could be manually set via `set_voltage!()` before calling ACPF. This would be a straightforward check.

**Cross-tool relevance:** likely -- ACPF convergence on MEDIUM is a common challenge across tools.
**Proposed action:** add_verification -- re-run with iteration/residual logging and attempt manual warm start.

### psi-F11: Gate tests are low-signal across tools

**Category:** low_signal | **Severity:** low
**Tests:** G-1, G-2, G-3

Gate tests serve their intended screening purpose but produce identical outcomes for any tool with a functional MATPOWER parser. All counts match, all three networks load successfully. This is expected and by design. No action needed.

**Cross-tool relevance:** confirmed
**Proposed action:** none

### psi-F12: 100% code coverage claim from badge without verification

**Category:** extraordinary_claim | **Severity:** medium
**Tests:** E-6

The result reports 100% code coverage from the Codecov badge. This is an unusual claim for any substantial project. The result itself correctly notes the limitation: "Julia coverage tools measure line coverage which may not reflect branch coverage or edge case coverage." The coverage was not independently verified by examining the Codecov report detail or running coverage locally. 100% line coverage can be achieved with auto-generated tests that execute every function without testing edge cases.

The finding does not impugn the test suite quality (37 test files, 3-platform CI, cross-package integration tests are all strong signals), but the specific "100%" number should be presented with appropriate caveats.

**Cross-tool relevance:** likely -- coverage claims from badges are common across evaluations.
**Proposed action:** add_verification -- examine the Codecov detail page for actual coverage methodology.

### psi-F13: B-4 stochastic wrapping ran only 5 of 20 specified scenarios

**Category:** misleading_result | **Severity:** low
**Tests:** B-4

The test specification calls for 20 scenarios, but only 5 were run. Of those 5, 2 were infeasible (40% failure rate). The extrapolated timing of ~50s for 20 scenarios assumes the infeasibility rate doesn't increase with more diverse scenarios. The result is honest about running only 5 scenarios and provides a clear rationale for the extrapolation, but the reduced scenario count weakens the evidence.

**Cross-tool relevance:** likely -- other tools may also run fewer scenarios than specified.
**Proposed action:** add_verification -- run the full 20 scenarios.

### psi-F14: B-8 and B-9 verified via interactive probe without test scripts

**Category:** missing_verification | **Severity:** low
**Tests:** B-8, B-9

Both B-8 (reference bus config) and B-9 (PTDF extraction) state they were "verified via interactive probe in the devcontainer" with no dedicated test script. The protocol requires "one test script per tool per test case." The findings are credible (changing the reference bus via `set_bustype!()` and computing PTDF via `PTDF(sys)` are straightforward operations) but cannot be independently reproduced from the evaluation artifacts.

**Cross-tool relevance:** likely
**Proposed action:** add_verification -- create reproducible test scripts.

### psi-F15: Solver swap test lacks timing data

**Category:** test_design_gap | **Severity:** low
**Tests:** C-7

C-7 confirms the most important finding (solver swap is parameter-only, no reformulation needed) but provides no comparative timing data across solvers. The protocol specifies "Time per solver" as a recorded metric.

**Cross-tool relevance:** likely
**Proposed action:** add_verification

## Extraordinary Claims

### C-3: DCOPF on MEDIUM expected to solve in <60s

**Concern:** This is an estimate based on problem size analysis, not a measured result. The test script had a bug preventing execution on MEDIUM. The qualified_pass status relies on extrapolation from TINY results and theoretical QP scaling.
**Evidence quality:** weak

A probe should execute the DCOPF on MEDIUM with all generator types properly handled and measure actual wall-clock time. The test script bug ("requires fix for RenewableDispatch accessor") should be fixed first.

### C-4: SCUC on SMALL expected to take >300s with SCIP

**Concern:** No execution on SMALL. The estimate is based on problem size scaling (13,056 binary variables vs 240 on TINY). MIP problems scale nonlinearly and the estimate of ">300s" could be off by an order of magnitude in either direction.
**Evidence quality:** weak

A probe should execute the SCUC on SMALL with SCIP and measure wall-clock time, MIP gap at termination, and peak memory.

### C-5: Contingency sweep approach scales to MEDIUM

**Concern:** No execution at MEDIUM scale. The estimate of "2-7 hours serial" for N-1 alone suggests serious scalability concerns. No MEDIUM-scale test was attempted.
**Evidence quality:** weak

A probe should run at least N-1 contingencies on MEDIUM and measure per-contingency time.

### C-6: 20-scenario stochastic DCOPF on SMALL estimated at 10-20 minutes

**Concern:** No execution on SMALL. The TINY-scale test showed 40% scenario infeasibility, which may worsen on SMALL with tighter constraints. The estimate does not account for the file reload overhead scaling with system size.
**Evidence quality:** weak

A probe should execute 20 scenarios on SMALL and measure total time, per-scenario time, and infeasibility rate.

### E-6: 100% code coverage

**Concern:** Reported from the Codecov badge without examining the detail page. Line coverage may be inflated by Julia's coverage tooling. Independent verification would require examining which files/functions contribute to the 100% figure.
**Evidence quality:** moderate

A probe should check the Codecov detail page for actual per-file coverage and the methodology used.

### A-4: PSI dispatch values ~100x larger than component limits

**Concern:** The same dispatch value (660.85 for gen-1) is labeled as MW in A-3 and as pu in A-4. If PSI returns values in MW and `get_active_power_limits()` returns values in pu, the "mismatch" is simply a unit convention difference that requires dividing by base MVA. But if both should be in the same units, there is a genuine bug. The A-3 result showing "660.85 MW" with "Pmax 1040.0 MW" suggests consistent MW units.
**Evidence quality:** moderate

A probe should log the exact return values and units from both `read_variables()` and `get_active_power_limits()` in the same script, with explicit base MVA tracking.

## Test Outcome Matrix

| Test ID | Status | Workaround | Key Issue |
|---------|--------|------------|-----------|
| G-1 | pass | -- | -- |
| G-2 | pass | -- | -- |
| G-3 | pass | -- | -- |
| A-1 | pass | -- | -- |
| A-2 | pass | -- | -- |
| A-3 | qualified_pass | stable | Time series boilerplate; GLPK fails on quadratic costs |
| A-4 | qualified_pass | stable | Unit mismatch claim needs verification; ACPF does not converge on scaled dispatch |
| A-5 | qualified_pass | stable | HiGHS fails on SCUC; no cycling on case39; MATPOWER lacks UC params |
| A-6 | qualified_pass | stable | Ramp constraints not enforced (ThermalBasicDispatch); ThermalRampLimited build fails |
| A-7 | pass | stable | Manual graph construction; should be qualified_pass per convention |
| A-8 | fail | blocking | No native stochastic optimization |
| A-9 | qualified_pass | stable | No native SCOPF; manual JuMP+LODF injection; 70% contingencies filtered |
| A-10 | fail | blocking | No lossy DC OPF formulation |
| A-11 | qualified_pass | stable | Implicit distributed slack; weights not configurable; uncongested network |
| B-1 | pass | -- | Dual only verified for non-binding constraint |
| B-2 | qualified_pass | stable | No native Graphs.jl integration |
| B-3 | pass | -- | -- |
| B-4 | pass | stable | 5 of 20 scenarios run; 2 infeasible; system reload per scenario |
| B-5 | pass | -- | Native DataFrame output |
| B-6 | pass | -- | Excellent separation of concerns |
| B-7 | qualified_pass | fragile | Undocumented unit convention between PSI and PowerFlows |
| B-8 | pass | -- | No test script; interactive probe only; distributed slack not configurable |
| B-9 | pass | -- | No test script; interactive probe only |
| C-1 | pass | -- | 9.4s on MEDIUM |
| C-2 | fail | -- | NR diverges on MEDIUM; no diagnostic detail |
| C-3 | qualified_pass | stable | Estimated timing only; no actual measurement |
| C-4 | qualified_pass | stable | Estimated timing only; SCIP only |
| C-5 | qualified_pass | stable | No MEDIUM measurement; serial-only |
| C-6 | qualified_pass | stable | No SMALL measurement; estimated 10-20min |
| C-7 | pass | -- | Parameter-only swap; no timing data |
| C-8 | fail | blocking | No native SCOPF; manual approach prohibitive at scale |
| C-9 | pass | -- | 6.44s on MEDIUM |
| C-10 | fail | blocking | No native distributed slack |
| D-1 | qualified_pass | -- | JIT overhead; time series boilerplate barrier |
| D-2 | informational | -- | 4/11 tests from docs alone |
| D-3 | informational | -- | 7 tutorials; ~20% use case coverage |
| D-4 | qualified_pass | -- | Zero-rate line silently accepted |
| D-5 | informational | -- | Median 255 LOC; 30 LOC boilerplate overhead |
| E-1 | informational | -- | 22 releases/24mo; pre-1.0 |
| E-2 | informational | -- | 1,040 commits; 21 contributors |
| E-3 | informational | -- | Bus factor 1 lifetime; improving recently |
| E-4 | informational | -- | DOE/NREL funded; single-institution risk |
| E-5 | informational | -- | Median 66 days to close; bimodal |
| E-6 | informational | -- | 100% coverage claim; 8 CI workflows |
| E-7 | informational | -- | Limited adoption outside NREL; 311 stars |
| F-1 | pass | -- | BSD-3-Clause |
| F-2 | informational | -- | 183 deps; 51 JLL binary wrappers |
| F-3 | informational | -- | GLPK GPL-3 flagged; optional |
| F-4 | pass | -- | All source available; MKL optional |
| F-5 | pass | -- | Full path inspectable |
| F-6 | pass | -- | Content-addressed distribution |
| F-7 | pass | -- | Air-gap installable via depot copy |
| F-8 | pass | -- | All open-source solvers sufficient |
| F-9 | informational | -- | Standard Julia conventions |
| P2-1 | informational | -- | PSS/E RAW v30/v32/v33 native |
| P2-2 | informational | -- | Piecewise linear native (SOS2) |
| P2-3 | informational | -- | UC-to-ED native; ED-to-ACPF blocked by unit mismatch |
