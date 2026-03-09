# PyPSA -- Sweep Findings (v4)

## Summary

The PyPSA v4 evaluation is thorough and generally well-executed, covering all 62 tests across 7 dimensions with detailed result files and test scripts. The evaluation demonstrates genuine tool strengths (2-LOC custom constraints, native SCOPF, clean Linopy model access) alongside real limitations (no stochastic optimization, broken lpf_contingency, SCUC solver scalability). The primary quality concerns are: (1) inconsistent data-fix treatment between expressiveness and scalability tests on the ACTIVSg10k network, creating contradictory pass/fail outcomes for the same capability; (2) several qualified_pass and pass classifications that are generous given the underlying evidence (ACPF non-convergence, C-5 with 3.3% completion, C-10 without completing the comparison); (3) a documentation audit claim that stochastic optimization is fully documented despite the feature not working. Three probes are recommended for extraordinary claims requiring verification.

## Finding Details

### pypsa-F01: Gencost import gap forces manual cost assignment across all OPF tests

**Category:** infrastructure_friction | **Severity:** medium
**Tests:** A-3, A-4, A-5, A-6, A-9, A-10, A-11, B-1, B-4, B-8

PyPSA's `import_from_pypower_ppc()` silently drops gencost data from MATPOWER files, emitting only a warning: "some PYPOWER features not supported: areas, gencosts, component status." This forces manual cost parsing and assignment (~5 LOC) as a prerequisite for every OPF-based test. The workaround is stable (uses `matpowercaseframes` for parsing and the documented `marginal_cost` attribute for assignment), but it represents test infrastructure friction rather than a PyPSA modeling limitation.

Every tool evaluated against MATPOWER .m files may face analogous import friction. The question is whether the friction is in the import path or in the modeling API -- for PyPSA it is clearly in the import path, as the optimization API works correctly once costs are set.

**Cross-tool relevance:** likely (other tools using MATPOWER format may have similar import gaps)
**Proposed action:** none (correctly documented as stable workaround)

---

### pypsa-F02: ACTIVSg10k zero-impedance branches cause cascading MEDIUM failures

**Category:** infrastructure_friction | **Severity:** high
**Tests:** A-1, A-3, A-4, A-7, B-1, B-3, B-5, B-9, C-1, C-3, C-5, C-7, C-8, C-9, C-10

The ACTIVSg10k MATPOWER case contains 2,462 branches with `s_nom=0` and 3 transformers with zero reactance. This data characteristic causes:
- DCOPF infeasibility (PyPSA interprets `s_nom=0` as zero-capacity constraint)
- Singular B-matrix in LPF (all flows NaN)
- PTDF computation failure (RuntimeError: Factor is exactly singular)

The evaluation applied data fixes (x=0.0001, s_nom=9999) in scalability tests (C-series) but NOT in expressiveness tests (A-series), creating an inconsistency. A-3 MEDIUM fails with infeasibility, but C-3 MEDIUM passes with the same tool on the same network after fixing the data.

From the synthesis: "MEDIUM-tier tests were executed where possible but several failed due to data-preparation issues with the ACTIVSg10k case (zero-impedance branches, zero s_nom) rather than tool limitations."

This is a protocol-level issue affecting all tools evaluated on ACTIVSg10k.

**Cross-tool relevance:** confirmed (affects all tools using ACTIVSg10k)
**Proposed action:** redesign_test -- standardize MEDIUM data preparation across all dimensions

---

### pypsa-F03: Contingency sweep C-5 qualified_pass with only 3.3% completion

**Category:** misleading_result | **Severity:** medium
**Tests:** C-5

C-5 is classified as `qualified_pass` but completed only 9 of 270 N-1 cases within the 600s timeout (3.3% completion rate). N-2 through N-4 sweeps were entirely skipped. The pass condition states: "Completes. Per-contingency-case average and total time recorded." Completing 3.3% of the minimum sweep order does not satisfy "completes."

From the result: "Each manual LPF call on 10k-bus takes ~65s (including topology re-determination). Only 9 of 270 N-1 cases completed within the 600s timeout."

The synthesis notes this as a finding for human spot-check: "Verify whether this is sufficient for a 'qualified pass' or should be reclassified as fail."

**Cross-tool relevance:** likely (contingency sweep scalability may challenge other tools similarly)
**Proposed action:** adjust_scoring -- reclassify as fail

---

### pypsa-F04: PTDF C-9 qualified_pass with 702 MW flow prediction error

**Category:** misleading_result | **Severity:** medium
**Tests:** C-9

C-9 (PTDF at MEDIUM) is classified as `qualified_pass` with correct matrix dimensions (12,706 x 10,000) and 28s computation time, but the flow prediction accuracy has a max difference of 702 MW. The B-9 pass condition specifies "Flow predictions match DCPF results within numerical tolerance (1e-6)." The 702 MW error is attributable to the zero-impedance workaround (x=0.0001) altering the sensitivity structure, which is a data issue -- but the resulting PTDF matrix is not usable for practical congestion analysis at this accuracy level.

From the result: "PTDF matrix computes and has correct dimensions, but flow prediction accuracy is degraded by the required zero-impedance workaround."

**Cross-tool relevance:** likely (any tool computing PTDF on ACTIVSg10k with zero-impedance fixes will have similar issues)
**Proposed action:** adjust_scoring -- either re-run with properly prepared data or classify as data-limited rather than qualified_pass

---

### pypsa-F05: ACPF MEDIUM pass despite non-convergence warning

**Category:** extraordinary_claim | **Severity:** medium
**Tests:** A-2, C-2

A-2 MEDIUM reports `status: pass` and `converged: true`, but the result file documents that PyPSA emitted "Power flow did not converge for ['now']". The test classified it as a pass because voltage magnitudes fell in a reasonable range (0.96-1.08 pu).

Additionally concerning:
- Total real power losses of 3,935 MW are reported (this is approximately 6% of total generation for a 10k-bus network, which may be reasonable for AC PF but warrants verification)
- Transformer flows up to 14,700 MW suggest modeling artifacts
- C-2 reports voltage angles as all zero, which is physically impossible for a converged AC power flow on a 10k-bus network

A non-converged Newton-Raphson may produce voltage magnitudes that "look reasonable" while angles, flows, and reactive power are mathematically incorrect. The pass classification requires verification.

**Cross-tool relevance:** likely (ACPF convergence on ACTIVSg10k with data issues may challenge all tools)
**Proposed action:** add_verification -- verify residual magnitude, not just voltage range

---

### pypsa-F06: SCOPF objective equality masks test signal due to uniform costs

**Category:** missing_verification | **Severity:** medium
**Tests:** A-9

The SCOPF pass condition requires dispatch and cost to "differ from unconstrained DC OPF (A-3) -- SCOPF should be more expensive." On TINY, both objectives are identical ($1876.269) because all 10 generators have identical marginal costs (c1=0.3 $/MWh). The dispatch redistribution is verified (G8 goes from 0 to 865 MW), but the cost signal is absent.

From the result: "Both objectives are 1876.269 because all generators have identical marginal costs (C1=0.3 $/MWh). The SCOPF redistributes dispatch without changing total cost since the cost function is linear with uniform slope."

The evaluator correctly identified this but the cost comparison -- a key verification -- produces no signal. On SMALL (A-9), the SCOPF is 0.4% more expensive, providing some validation.

**Cross-tool relevance:** confirmed (all tools using case39 with uniform costs face this issue)
**Proposed action:** redesign_test -- use perturbed costs on TINY or require the cost comparison only on SMALL/MEDIUM

---

### pypsa-F07: SCUC on TINY shows no generator cycling

**Category:** network_insufficiency | **Severity:** low
**Tests:** A-5

The SCUC test on TINY produces a trivial result: all 10 generators stay committed for all 24 hours, the MIP gap is 0%, and the branch-and-bound tree has only 1 node. No unit commitment cycling occurs because load is high relative to total capacity, so min up/down time and startup cost constraints never bind.

From the result: "Generators always on: 10/10, Min simultaneous online: 10, B&B nodes: 1"

The test passes functionally (commitment schedule is extractable as a time-indexed binary matrix), but it does not exercise the combinatorial difficulty that makes UC interesting. The SMALL-tier test (A-5 SMALL) would exercise this but it fails due to solver timeout.

**Cross-tool relevance:** confirmed (case39 has the same load/capacity ratio for all tools)
**Proposed action:** none (this is a known limitation of TINY for UC tests, and SMALL is the grade network)

---

### pypsa-F08: D-2 claims A-8 stochastic docs coverage YES but A-8 test FAILs

**Category:** extraordinary_claim | **Severity:** high
**Tests:** D-2

The documentation audit (D-2) rates A-8 stochastic optimization coverage as "Documented: YES (as of v1.x)" and references a dedicated page at `user-guide/optimization/stochastic/` with `n.set_scenarios()`, `n.set_risk_preference()`, and an example notebook.

However, A-8 itself FAILs with `workaround_class: blocking`. The A-8 result states: "n.scenarios exists as an empty Index in the data model but is not wired into the optimizer. No optimize_stochastic() or scenario-weighted objective method exists."

This is a direct contradiction. Either:
1. The documentation describes functionality that was added after the evaluation's TINY test but exists in the codebase
2. The documentation is aspirational and describes planned rather than implemented features
3. The evaluator tested an incorrect API path

The synthesis correctly flags this for human spot-check. This finding has high severity because it suggests the documentation audit may have accepted documentation existence as proof of functionality without runtime verification.

**Cross-tool relevance:** none (PyPSA-specific)
**Proposed action:** add_verification -- verify whether `n.set_scenarios()` and `n.set_risk_preference()` exist and function

---

### pypsa-F09: Lossy DCOPF LMP decomposition not validated against MATPOWER reference

**Category:** missing_verification | **Severity:** medium
**Tests:** A-10

The A-10 pass condition explicitly requires: "Validate against MATPOWER reference lossy DC OPF solution on same case (tolerance: 1% on total LMP, directional consistency on loss component signs)."

The result file demonstrates:
- Loss components are non-zero with physically correct signs
- LMP decomposition into energy/congestion/loss is performed
- Congestion rent reconciliation is computed

However, no cross-validation against MATPOWER's `rundcopf` with loss option is documented. The LMP values are self-consistent but not independently verified against a reference implementation.

**Cross-tool relevance:** confirmed (all tools must validate against MATPOWER reference per the pass condition)
**Proposed action:** add_verification -- run MATPOWER reference and compare

---

### pypsa-F10: Distributed slack OPF test has low signal

**Category:** low_signal | **Severity:** low
**Tests:** A-11

A-11 tests distributed slack OPF. For PyPSA, the OPF formulation inherently distributes generation (no slack bus concept in the optimizer). Changing the slack bus has zero effect on OPF LMPs, which is mathematically correct but means the test provides no signal about distributed slack OPF capability -- the tool trivially passes by design.

The meaningful distributed slack behavior is demonstrated in the PF path (`n.pf(distribute_slack=True)`), which does change voltage angles. But this is a PF feature, not an OPF feature.

The B-8 result confirms: "In PyPSA's DCOPF, the slack bus assignment does NOT affect LMPs because the optimizer enforces power balance as a constraint."

**Cross-tool relevance:** likely (tools with similar optimization-based formulations may trivially pass)
**Proposed action:** redesign_test -- clarify whether the test targets PF or OPF distributed slack; for OPF-native tools, the test may need a different formulation

---

### pypsa-F11: A-1 MEDIUM pass despite all flows being NaN

**Category:** misleading_result | **Severity:** medium
**Tests:** A-1

A-1 DCPF at MEDIUM is classified as `status: pass` with the justification: "Despite the NaN flows (caused by zero-impedance branches in the MATPOWER case, not a PyPSA limitation), the solver converges and outputs are structured pandas DataFrames."

All voltage angles and all line flows are NaN. The power flow produced no usable results. The pass is based on the structural format of the output (DataFrames) rather than the correctness of the computation.

A power flow with all-NaN results is not a converged power flow by any engineering definition. The `MatrixRankWarning: Matrix is exactly singular` confirms the solve did not produce meaningful results.

**Cross-tool relevance:** likely (data issue, but scoring philosophy applies to all tools)
**Proposed action:** adjust_scoring -- reclassify as fail or qualified_fail with data-limitation note

---

### pypsa-F12: Scalability wall-clock times dominated by linopy post-processing

**Category:** missing_verification | **Severity:** low
**Tests:** C-3, C-7, C-8, C-10

Multiple MEDIUM scalability tests report total wall-clock times of 600s+ while the actual HiGHS solver time is 6-21 seconds. The dominant cost is linopy's shadow-price assignment step (10+ minutes at 10k-bus scale). This creates a measurement challenge for cross-tool comparison:

| Test | Solver Time | Total Wall-Clock | Post-Processing |
|------|------------|-----------------|-----------------|
| C-3  | 19.9s      | 600s+           | 10+ min         |
| C-7  | 21.2s      | 600s+           | 10+ min         |
| C-8  | 7.1s       | 600s+           | 10+ min         |
| C-10 | 6.1s       | 600s+           | 10+ min         |

The post-processing overhead is a legitimate scalability concern (it is real wall-clock time), but comparing these total times against tools that do not extract dual variables by default would be misleading. The solver-time vs framework-overhead decomposition should be preserved in any cross-tool comparison.

**Cross-tool relevance:** none (linopy-specific issue)
**Proposed action:** add_verification -- verify whether `assign_all_duals=False` eliminates the overhead

---

### pypsa-F13: Inconsistent data fixes between expressiveness and scalability

**Category:** scoring_inconsistency | **Severity:** medium
**Tests:** A-3, C-3

A-3 MEDIUM (expressiveness): FAIL -- zero s_nom branches cause infeasibility, no data fixes applied.
C-3 MEDIUM (scalability): PASS -- same network, same tool, same analysis, but with s_nom=9999 and x=0.0001 fixes applied.

The synthesis notes: "MEDIUM data fixes applied in scalability tests: C-1/C-3/C-5/C-7/C-8/C-9/C-10 applied x=0.0001 on 3 zero-impedance transformers and s_nom=9999 on 2,462 zero-s_nom lines. These fixes were not applied in expressiveness tests A-3/A-4 MEDIUM."

This creates a contradictory narrative: PyPSA fails expressiveness DCOPF at MEDIUM but passes scalability DCOPF at MEDIUM. The protocol should standardize whether data fixes are applied universally or not at all for a given network tier.

**Cross-tool relevance:** confirmed (all tools face this data-preparation question on ACTIVSg10k)
**Proposed action:** redesign_test -- standardize data preparation for ACTIVSg10k across all test suites

---

### pypsa-F14: Solver swap test verifies only API, not actual multi-solver comparison

**Category:** test_design_gap | **Severity:** low
**Tests:** C-7

C-7 confirms solver swap is parameter-only (`solver_name="..."`) but only HiGHS was installed. The test verified the mechanism by API inspection and ran DCOPF with HiGHS only. No GLPK, SCIP, or other solver comparison was performed.

From the result: "GLPK available: No, SCIP available: No, Gurobi available: No, CPLEX available: No"

The pass condition ("Solver swap requires only a parameter change, not reformulation") is technically met by inspection, but the evaluation environment should have at least two solvers installed to demonstrate the claim with runtime evidence.

**Cross-tool relevance:** likely (evaluation environment may lack alternative solvers for other tools too)
**Proposed action:** add_verification -- install at least GLPK or SCIP alongside HiGHS

---

### pypsa-F15: B-5 interoperability test trivially passes for DataFrame-based tools

**Category:** low_signal | **Severity:** low
**Tests:** B-5

B-5 tests CSV export of DCPF results. PyPSA natively stores everything as pandas DataFrames, so export is `df.to_csv()` in 2 lines. This produces no discriminative signal among Python tools that use DataFrames. The test would differentiate Julia tools (where DataFrame export requires more steps) or tools with custom data structures, but among Python tools it is trivially passed.

**Cross-tool relevance:** confirmed (all DataFrame-based Python tools pass trivially)
**Proposed action:** none (test still provides baseline interoperability documentation)

---

### pypsa-F16: Maturity metrics based on research rather than runtime verification

**Category:** missing_verification | **Severity:** low
**Tests:** E-1, E-2, E-3, E-4, E-5, E-6, E-7

All E-series metrics (24 releases/24mo, 327 commits/12mo, 84% coverage, 21h median issue close time, IEA/ACER adoption) are research-based. The numbers are internally consistent and appear reasonable. This is expected for audit-type tests, but none were independently verified against GitHub API or PyPI data during this sweep.

**Cross-tool relevance:** confirmed (all tools have research-based maturity metrics)
**Proposed action:** none (standard approach for audit tests)

---

### pypsa-F17: C-10 distributed slack pass without completing the comparison

**Category:** extraordinary_claim | **Severity:** low
**Tests:** C-10

C-10 is classified as pass, but the result file states: "The full test (DCOPF + single-slack PF + distributed-slack PF comparison) could not complete within 600s due to linopy's shadow-price assignment overhead after the DCOPF solve."

The pass is based on:
1. DCOPF solving in 6.1s (not distributed-slack-specific)
2. The `distribute_slack` API existing

The actual distributed slack PF comparison at MEDIUM scale was not performed. The pass is inferred from capability rather than demonstrated at scale.

**Cross-tool relevance:** none
**Proposed action:** adjust_scoring -- classify as qualified_pass with note that PF comparison was not completed

---

## Extraordinary Claims

### A-2 MEDIUM: ACPF converges on 10k-bus network despite solver reporting non-convergence

**Concern:** The Newton-Raphson solver explicitly warns "Power flow did not converge" but the test classifies the result as pass based on voltage magnitude ranges being in a reasonable band. Additionally, C-2 reports all voltage angles as zero, which is physically impossible for a converged AC PF. A non-converged NR iteration may produce plausible-looking voltage magnitudes while angles and flows are incorrect.

**Evidence quality:** moderate

A probe should: (1) check the final NR residual magnitude, (2) verify power balance at each bus, (3) confirm whether voltage angles are truly zero or just not reported. If the residual exceeds the convergence tolerance, the test should be reclassified as fail regardless of voltage magnitude appearance.

### D-2: A-8 stochastic optimization is documented with dedicated page and example notebook

**Concern:** The A-8 test demonstrates that `n.scenarios` is not wired to the optimizer, yet D-2 claims full documentation coverage with `n.set_scenarios()` and `n.set_risk_preference()` documented on a dedicated page. This is either aspirational documentation or the evaluator found a different API path than the one tested in A-8.

**Evidence quality:** moderate

A probe should: (1) verify whether `user-guide/optimization/stochastic/` exists in the PyPSA v1.1.2 docs, (2) test whether `n.set_scenarios()` and `n.set_risk_preference()` are callable methods, (3) if they exist, determine whether they produce a joint stochastic optimization or just set metadata.

### C-10: Distributed slack OPF passes at MEDIUM scale

**Concern:** The PF comparison that constitutes the actual test was not completed within the time budget. The pass is based on DCOPF convergence (not distributed-slack-specific) and API existence.

**Evidence quality:** weak

A probe should: run the distributed slack PF comparison without the linopy shadow-price overhead (e.g., skip `assign_all_duals` or run PF independently of OPF) to verify whether distributed slack PF actually functions at 10k-bus scale.

## Test Outcome Matrix

| Test ID | Status | Workaround | Key Issue |
|---------|--------|------------|-----------|
| G-1 | pass | -- | -- |
| G-2 | pass | -- | -- |
| G-3 | pass | -- | 2,462 zero-s_nom branches noted |
| A-1 TINY | pass | -- | -- |
| A-1 MEDIUM | pass | -- | All flows NaN (singular matrix) -- misleading pass |
| A-2 TINY | pass | -- | 4 NR iterations, clean convergence |
| A-2 MEDIUM | pass | -- | Non-convergence warning, zero angles -- needs verification |
| A-3 TINY | pass | stable (gencost) | Uniform LMPs (no congestion) |
| A-3 MEDIUM | fail | -- | Zero s_nom causes infeasibility (data issue) |
| A-4 TINY | pass | stable | 2 voltage violations, 1 thermal violation |
| A-4 MEDIUM | fail | -- | Cascading from A-3 MEDIUM failure |
| A-5 TINY | pass | stable (gencost) | All gens committed all hours (trivial UC) |
| A-5 SMALL | fail | -- | HiGHS timeout, no feasible solution |
| A-6 TINY | pass | stable | Ramp constraints demonstrably binding |
| A-6 SMALL | fail | -- | Cascading from A-5 SMALL failure |
| A-7 TINY | pass | stable (manual loop) | lpf_contingency bug, 674 cases in 72s |
| A-7 MEDIUM | fail | -- | ~65s per LPF, impractical runtime |
| A-8 TINY | fail | blocking | No native stochastic optimization |
| A-8 SMALL | fail | blocking | Same capability gap |
| A-9 TINY | pass | stable (rating 1.5x) | Objective equality due to uniform costs |
| A-9 SMALL | pass | stable | SCOPF 0.4% more expensive, 70s |
| A-10 TINY | pass | stable | Loss components non-zero, no MATPOWER reference validation |
| A-10 SMALL | pass | stable | 2.71% objective increase from losses |
| A-11 TINY | pass | -- | OPF LMPs unaffected by slack (by design) |
| A-11 SMALL | pass | stable (gencost) | LMPs identical across configs |
| B-1 TINY | pass | -- | 2 LOC, dual value verified |
| B-1 MEDIUM | fail | -- | Cascading from A-3 MEDIUM infeasibility |
| B-2 TINY | pass | -- | 4 LOC NetworkX access |
| B-2 MEDIUM | pass | -- | 0.84s, works at scale |
| B-3 TINY | pass | stable | 87ms/contingency, lpf_contingency bug |
| B-3 MEDIUM | fail | -- | Impractical runtime (~1 iter/min) |
| B-4 TINY | pass | stable | 20 scenarios, 9.68s total |
| B-4 SMALL | pass | stable | 20 scenarios, 2217s total |
| B-5 TINY | pass | -- | 2 LOC trivial DataFrame export |
| B-5 MEDIUM | pass | -- | Works despite NaN flows |
| B-6 | informational | -- | 5-layer architecture, 85% docstring coverage |
| B-7 TINY | pass | stable | Both workarounds stable, low effort |
| B-7 MEDIUM | pass | stable | Audit only, references TINY result |
| B-8 TINY | pass | -- | Slack change via DataFrame edit, no model rebuild |
| B-8 SMALL | pass | -- | All configs produce identical LMPs |
| B-9 TINY | pass | -- | Machine-precision flow match (1.88e-12) |
| B-9 MEDIUM | fail | -- | Singular B-matrix from zero-impedance branches |
| C-1 | pass | data_prep | 28.3s solve, zero-impedance fix applied |
| C-2 | pass | -- | 18.1s flat-start convergence, zero angles suspicious |
| C-3 | pass | data_prep | 19.9s solver, 10+ min post-processing |
| C-4 | fail | -- | HiGHS timeout, no feasible solution |
| C-5 | qualified_pass | data_prep | Only 9/270 N-1 cases -- should be fail |
| C-6 | pass | stable | 20 scenarios, 2219s, 7.1 GB |
| C-7 | pass | data_prep | Only HiGHS tested (others not installed) |
| C-8 | fail | data_prep | Post-processing timeout, SCOPF not reached |
| C-9 | qualified_pass | data_prep | 702 MW flow error from data fix |
| C-10 | pass | data_prep | PF comparison not completed |
| D-1 | pass | -- | 3 steps to first solve |
| D-2 | qualified_pass | -- | 7/11 tests from docs; A-8 docs claim contradicts A-8 result |
| D-3 | pass | -- | All 3 examples run unmodified |
| D-4 | qualified_pass | -- | Missing-cost: A; Infeasible: B+; Invalid enum: D |
| D-5 | informational | -- | 158-485 LOC per test |
| E-1 | informational | -- | 24 releases/24mo, strict SemVer |
| E-2 | informational | -- | 327 commits, 32 contributors |
| E-3 | informational | -- | Bus factor 3-4, 53% recent concentration |
| E-4 | informational | -- | TU Berlin + OET hybrid funding |
| E-5 | informational | -- | 21h median close time |
| E-6 | informational | -- | 84% coverage, 3-platform CI |
| E-7 | informational | -- | IEA, ACER, ENTSO-E, Shell adoption |
| F-1 | pass | -- | MIT throughout |
| F-2 | qualified_pass | -- | 87 packages, moderate footprint |
| F-3 | qualified_pass | -- | 1 GPL (Levenshtein), replaceable |
| F-4 | pass | -- | Pure Python core, 1 HiGHS .so |
| F-5 | pass | -- | 4 Python layers to solver |
| F-6 | pass | -- | Sigstore attestations |
| F-7 | pass | -- | All wheels available offline |
| F-8 | pass | -- | HiGHS covers all modes |
| F-9 | qualified_pass | -- | Version-tagged downloads, optional version check |
| P2-1 | informational | -- | No PSS/E RAW parser |
| P2-2 | informational | -- | No PWL costs; quadratic works (QP) |
| P2-3 | informational | -- | Full UC-to-DCOPF-to-ACPF pipeline works |
