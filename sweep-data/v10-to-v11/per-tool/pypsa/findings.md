# pypsa — Sweep Findings (v10)

## Summary

The PyPSA v10 evaluation is well-executed: all 59 test IDs have result files, timings are measured (not estimated), convergence residuals are reported for all Newton-Raphson solves, and workaround classifications are consistently applied. The primary structural issues are a protocol design flaw (the C-SMALL gate conflates MILP and LP/PF scalability, causing 7 MEDIUM tests to be skipped despite strong LP/PF evidence), a test design gap in B-8 (slack reconfiguration cannot produce LMP variation in any standard DC OPF), and a scoring ambiguity in A-11 (qualified_pass with blocking workaround is functionally a fail for the stated test condition). One extraordinary claim — 0.0 deviation on a 27,862-bus DCPF — warrants a probe both for numerical verification and to resolve a discrepancy between the result file and the validation report. Two probes are recommended: one for the G-FNM-3 deviation claim and one for the A-10 LMP decomposition completeness.

## Finding Details

### pypsa-F01: B-8 slack reconfiguration produces zero LMP variation — pass condition is vacuous for DC OPF

**Category:** scoring_inconsistency | **Severity:** medium
**Tests:** B-8

B-8 requires solving DC OPF with three different slack bus configurations and checking that "LMP values change consistently across configurations." The result reports zero LMP variation across all three configurations (objective spread = 0.0, LMP shift mean = 0.0, std = 0.0). The evaluator correctly explains this is mathematically expected: in a standard LP-based DC OPF, the dual variables (LMPs) are invariant to the angle reference bus choice because the formulation uses nodal power balance constraints, not angle-based constraints. The angle reference only affects the primal solution (bus angles), not the dual (LMPs).

This means the B-8 pass condition as written — "LMP values change consistently" — is unsatisfiable for any tool implementing standard DC OPF. Every tool will pass B-8 on API configurability (the call succeeds, no model reconstruction needed) and fail on LMP variation (because there is none). The test currently measures only whether the API call succeeds, not whether the slack configuration has any computational consequence.

The result file says: "Objective spread: 0.0000 (identical across all three configs) / LMP spread variation: 0.0000 (identical across all three configs)" and explains the mathematical reason, which is correct.

**Cross-tool relevance:** confirmed — this is a protocol design issue that affects all tools implementing standard LP-based DC OPF.

**Proposed action:** redesign_test — either use DCPF (not DC OPF) where the slack bus absorbs power imbalance and produces angle differences, or rewrite the pass condition to check only API configurability (two DataFrame assignments, no model reconstruction, no error raised) without requiring LMP variation.

---

### pypsa-F02: A-5 SCUC on 10-generator TINY network cannot verify that min up/down constraints are binding

**Category:** network_insufficiency | **Severity:** medium
**Tests:** A-5

A-5 passes the numeric threshold (3 generators cycle, ≥2 required) on the 10-generator IEEE 39-bus with a capacity-to-peak ratio of 1.18. However, the result cannot confirm that min_up_time or min_down_time constraints are actually binding the commitment schedule. With only 10 generators across 4 cost tiers and 18% capacity headroom, the optimizer has substantial freedom to schedule generators without the min time constraints ever being the binding constraint. The cycling pattern shown (G9 shuts down hours 3-8, restarts hour 9, shuts down again hour 22; G6 shuts down hour 20; G3 shuts down hour 23) appears driven by economic merit, not minimum time constraints — the decommits happen over single-digit hour periods that are within the min up/down windows.

The protocol's intent is to verify that the SCUC formulation is correctly implemented. A claim that min up/down time constraints are active requires either (a) a network with tighter capacity margins forcing the optimizer to keep generators online longer than economics alone would dictate, or (b) an explicit check that removing the min time constraints changes the schedule.

The result states: "Capacity-to-peak-load ratio: 1.18. Load range: 4,237--6,254 MW." With 10 generators totaling 7,367 MW capacity against a 6,254 MW peak, economic dispatch can always find a valid solution without straining minimum time constraints.

**Cross-tool relevance:** confirmed — a 10-generator, 39-bus network is too small to stress min up/down time constraints for any tool. This affects all tools' A-5 results.

**Proposed action:** add_verification — add a supplementary check confirming at least one min up/down time constraint is binding in the A-5 solution, implemented by re-running with min_up_time=min_down_time=1 and comparing against min_up_time=min_down_time=0 to show a schedule difference.

---

### pypsa-F03: A-10 check (d) verifies LMP change, not the three-component additive decomposition required by protocol

**Category:** missing_verification | **Severity:** medium
**Tests:** A-10

The A-10 pass condition requires: "(d) loss component LMPs sum with energy and congestion components to total LMP within 1% tolerance." The result checks four conditions but implements check (d) as "Bus LMPs change between lossy and lossless: PASS (38/39 buses)" — a two-scenario comparison, not a three-component additive decomposition.

The protocol requires per-bus verification that energy_component + congestion_component + loss_component = total_LMP within 1%. The result provides a two-component decomposition (energy = slack bus LMP, loss = bus LMP - energy), but never isolates the congestion component separately. The congestion rent table shows "Lines with non-zero congestion rent: 35 of 35" but does not verify that these congestion rents, when decomposed to the bus level, add to a congestion LMP component that participates in the three-way additivity check.

The result file says: "| (d) Bus LMPs change between lossy and lossless | PASS (38/39 buses) |" — this is a different and weaker condition than what the protocol specifies.

**Cross-tool relevance:** likely — the three-component LMP decomposition check is the same protocol requirement for all tools solving A-10. If this verification was not done for PyPSA, it may not have been done for other tools either.

**Probe recommended:** claim_verification — compute per-bus loss component as (total LMP - energy component - congestion component) using the PTDF matrix and shadow prices, and verify the three sum to within 1% of total LMP for each bus. If PyPSA's `transmission_losses` formulation does not expose the congestion and loss components separately, that finding should be recorded.

---

### pypsa-F04: A-9 SCOPF protocol specifies all 46 branches but test runs with 19 — reduced contingency set may be insufficient

**Category:** test_design_gap | **Severity:** medium
**Tests:** A-9

The A-9 protocol specifies "DC OPF with N-1 contingency flow constraints on TINY (all 46 branches)." The result documents a progressive fallback: (1) all 35 lines → infeasible at any derating; (2) lines <70% utilization → infeasible; (3) lines <50% utilization → feasible with 19 lines. The test passes on this 19-line subset.

Two distinct issues compound here. First, PyPSA's `optimize_security_constrained()` API does not accept Transformer names, so 11 of the 46 branches (the transformers) are excluded regardless of feasibility. This is a genuine tool limitation. Second, the feasibility reduction from 35 to 19 lines is a consequence of the IEEE 39-bus network topology: 2 lines are already at 100% utilization in the base DC OPF, and any contingency set including them creates unavoidable infeasibility. No tool could pass A-9 as specified (all 46 branches) on this network, because the network itself does not have a feasible N-1 security-constrained dispatch when all branches are contingency candidates.

The test as designed cannot distinguish between "tool handles SCOPF well" and "network happens to have feasible SCOPF with the contingency subset tried." The result says: "The test used a progressive fallback strategy: all 35 lines -> lines <70% utilization -> lines <50% utilization. The SCOPF became feasible with 19 lines at <50% base-case utilization."

**Cross-tool relevance:** confirmed — this network topology characteristic affects all tools evaluating A-9.

**Proposed action:** redesign_test — pre-identify a contingency subset that is guaranteed to produce a feasible SCOPF on IEEE 39-bus (e.g., branches not in the active binding set at base-case OPF) and specify that subset as the protocol-required contingency set for A-9.

---

### pypsa-F05: G-FNM-1 failure blocks G-FNM-2, preventing field coverage assessment despite a complete MATPOWER fallback path

**Category:** infrastructure_friction | **Severity:** medium
**Tests:** G-FNM-1, G-FNM-2

G-FNM-1 fails because PyPSA lacks a PSS/E ingestion path. This correctly triggers G-FNM-2 to be skipped. However, G-FNM-5 (supplemental CSV representability) proceeds via the MATPOWER fallback and produces a complete field coverage analysis (73 fields, 20.5% N / 61.6% E / 17.8% X). The protocol gates G-FNM-2 on G-FNM-1, meaning field coverage can only be assessed for tools that support PSS/E ingestion.

The PSS/E ingestion capability is a format interoperability feature. The field coverage measured in G-FNM-2 is a data model fidelity feature. These are independent: a tool can have a complete data model for all DCPF-critical fields without a PSS/E parser (which PyPSA demonstrates via G-FNM-5). The current gate design systematically disadvantages tools with complete data models but no PSS/E parser by withholding the G-FNM-2 measurement.

G-FNM-5 proceeds to report "61.6% extension-representable" fields — the same domain knowledge that G-FNM-2 would assess at the DCPF-critical vs. ACPF-critical level. The distinction is that G-FNM-5 uses the supplemental CSVs, while G-FNM-2 uses the core network tables. The result is an information gap that is attributable to protocol design, not tool capability.

**Cross-tool relevance:** likely — any tool without PSS/E ingestion (PowerModels.jl, pandapower without pypsa-converter, etc.) would face the same gate-induced gap in G-FNM-2 coverage.

**Proposed action:** add_test — allow G-FNM-2 to run via the MATPOWER fallback path for tools that fail G-FNM-1, with a note that PSS/E-specific field mappings cannot be assessed. The DCPF-critical fields (19 fields) in the FNM are derivable from the MATPOWER .m file regardless of PSS/E ingestion support.

---

### pypsa-F06: G-FNM-3 reports 0.0 deviation on 27,862-bus DCPF and has discrepancy with validation report

**Category:** extraordinary_claim | **Severity:** high
**Tests:** G-FNM-3

G-FNM-3 reports perfect 0.0 agreement (mean and max deviation for both bus angles and branch flows) between PyPSA and the MATPOWER reference on a 27,862-bus network. The reported values are: mean deviation = 0.0 deg, max deviation = 0.0 deg (buses); mean deviation = 0.0%, max deviation = 0.0% (branches).

Two concerns arise. First, the numerical claim: exact 0.0 agreement across 27,862 buses and 32,532 branches in a floating-point computation requires that both tools use identical B-matrix construction and identical sparse linear algebra. The evaluator's explanation — that both PyPSA and MATPOWER trace to the same formulation (b = 1/(x*tap)) and the shared matpower_loader applies the same branch status patch — is plausible. The 0.0 result would be expected if both tools solve the exact same linear system with the same coefficient matrix. However, the result tables report to one decimal place, so "0.0" could mean any deviation < 0.05 deg or < 0.05%. The raw numerical maximum is not reported.

Second, the metadata discrepancy: `validation-report.md` lists G-FNM-3 in the Failures table: "G-FNM-3 | DCPF verification failed — systematic impedance conversion differences via MATPOWER fallback." The G-FNM-3 result file has `status: pass` and the synthesis section on G-FNM-3 also records pass. The synthesis methodology notes include: "G-FNM-3 DCPF deviation resolved — Root cause identified: import_from_pypower_ppc ignores MATPOWER BR_STATUS column, including 74 inactive branches in the DCPF." This indicates the validation report was written before the branch status bug was identified and fixed, and was not regenerated after the result was updated. The current state of the result file appears to reflect the corrected evaluation, but the validation report creates ambiguity.

**Cross-tool relevance:** none — this is specific to PyPSA's implementation.

**Probe recommended:** convergence_check — re-run the G-FNM-3 DCPF and extract the raw (unrounded) maximum absolute bus angle deviation and maximum branch flow percent deviation. Confirm whether "0.0" is machine-zero or display-rounded. Also verify validation-report.md reflects the current result state.

---

### pypsa-F07: A-11 qualified_pass with blocking workaround is functionally a fail for the stated test condition

**Category:** misleading_result | **Severity:** low
**Tests:** A-11

A-11's pass condition requires: "Solve DC OPF on TINY with distributed slack (load-proportional)." The result confirms: "No Bus-v_ang variable. Distributed slack OPF is NOT achievable." The workaround_class is "blocking" — explicitly noted as architecturally impossible.

The result is classified qualified_pass because distributed slack works in the AC power flow context (n.pf(distribute_slack=True)). The result correctly demonstrates this capability. However, the test's pass condition is specifically DC OPF with distributed slack. Demonstrating a different capability (AC PF distributed slack) under different solver conditions does not satisfy the stated pass condition.

The qualified_pass label implies the tool partially meets the requirement, when in fact the requirement is unmet and a related but distinct capability is offered as context. This creates a misleading impression in cross-tool comparison: A-11 counts as neither a clean fail nor a clean pass, potentially inflating PyPSA's expressiveness score relative to a tool that honestly fails the test without offering a partial substitute.

The synthesis agrees this is a gap: "The meaningful gap is A-11 (distributed slack OPF) which is a blocking architectural limitation — no workaround exists in the OPF context." But the status is still qualified_pass, not fail.

**Cross-tool relevance:** none — this is specific to PyPSA's scoring.

**Proposed action:** adjust_scoring — reclassify A-11 as fail (the protocol's pass condition is not met). Document the AC PF distributed slack capability as an observation in the result file, which is appropriate context but not a pass signal.

---

### pypsa-F08: A-12 branch shadow price extraction depends on internal linopy naming — bug-dependent pass

**Category:** missing_verification | **Severity:** low
**Tests:** A-12

A-12 passes by extracting branch shadow prices via `n.model.constraints['Line-fix-s-upper'].dual` rather than the documented `n.lines_t.mu_upper` attribute. The evaluator classifies this as fragile and documents the underlying bug: "The solver log confirms shadow prices were computed ('shadow-prices of the constraints ... were not assigned to the network')."

Pass condition 1 (congestion reporting: ≥2 branches with non-zero shadow prices in ≥2 of 24 hours) depends entirely on these extracted duals. The result shows "Hours with >=2 binding branches: 24/24" — strong performance. But this result rests on working around a documented bug using an undocumented internal naming convention. If the constraint naming changes in PyPSA 1.2.x, A-12 would silently fail on shadow price extraction while appearing to pass on BESS arbitrage (condition 2) and SoC feasibility (condition 3).

The same bug is documented in A-3 (shadow price extraction), A-6 (SCED), and the cross-cutting observations section. This is a systematic tool defect that affects multiple tests, not a single-test workaround choice.

**Cross-tool relevance:** none — this is specific to PyPSA's shadow price assignment bug.

**Proposed action:** add_verification — document explicitly that A-12's pass on condition 1 depends on a bug workaround. The bug (n.lines_t.mu_upper empty after optimize()) is a tool defect that should be tracked as a separate observation, distinct from the workaround's success.

---

### pypsa-F09: C-SMALL gate triggered by MILP failure blocks 7 LP/PF scalability tests

**Category:** test_design_gap | **Severity:** medium
**Tests:** C-4, C-1, C-2, C-3, C-7, C-8, C-9, C-10

The C-SMALL gate design requires C-4 (SCUC/MILP on 2,000-bus SMALL) to pass before running MEDIUM-tier tests. C-4 fails for PyPSA: HiGHS cannot solve the root LP relaxation of 39,168-variable MILP within 600 seconds. This cascades to skip 7 MEDIUM tests: C-1 (DCPF), C-2 (ACPF), C-3 (DC OPF), C-7 (solver swap), C-8 (SCOPF), C-9 (PTDF), C-10 (distributed slack).

The 7 skipped tests cover LP and linear algebra problems — not MILP. PyPSA's LP/PF scalability is demonstrably strong from other evidence: C-5 passes ACPF on 10,000-bus MEDIUM in 19s, and G-FNM-3 passes DCPF on 27,862-bus LARGE in 31s. The gate design prevents collecting this evidence in the scalability dimension.

The MILP scalability ceiling is a real limitation. But conflating MILP scalability (C-4) with LP/PF scalability (C-1, C-2, C-3, C-7, C-9, C-10) in a single gate means that a tool's overall scalability assessment is determined by its weakest problem type, even when the other problem types scale well. The synthesis note says: "C+ is assigned rather than B- because the C-SMALL-gate prevents demonstrating MEDIUM-tier OPF capability." This is a protocol-driven grade depression that is not attributable to any tool failing a test it could have passed.

The result says: "C-4 SCUC SMALL fails: HiGHS cannot solve root LP relaxation of 544-generator 24hr SCUC within 600s on single thread (39,168 binary variables)."

**Cross-tool relevance:** confirmed — this gate design issue would affect any tool that fails MILP at SMALL scale but succeeds at LP/PF at MEDIUM or LARGE scale.

**Proposed action:** redesign_test — separate the MILP gate (C-4) from the LP/PF gate. LP/PF MEDIUM tests (C-1, C-2, C-3, C-7, C-9, C-10) should not be conditional on MILP SMALL success. Only a MILP MEDIUM test (if one exists) should be gated on C-4.

---

### pypsa-F10: G-FNM-1 determination based on API inspection without code execution

**Category:** missing_verification | **Severity:** low
**Tests:** G-FNM-1

The G-FNM-1 result states: "No test script was written. The verification was an API surface inspection confirming the absence of any PSS/E ingestion path in PyPSA's public interface." The conclusion is correct — PyPSA has no PSS/E parser. However, the protocol requires recording a failure_reason (psse_parse_error), which implies an actual parse attempt was made and produced an error.

An API inspection confirms the absence of the capability but does not produce an execution trace or a concrete error message that would confirm the exact failure mode. For comparison, G-FNM-3 and G-FNM-4 both produce actual execution records with timing and error messages. G-FNM-1 is recorded as a conclusion from inspection, not as an executed result.

This is a minor deviation from protocol standards. The conclusion is not in question.

**Cross-tool relevance:** none.

**Proposed action:** add_verification — a minimal one-line script attempting import_from_csv_folder on the intermediate CSV directory would produce an actual error message and constitute a proper execution record, consistent with the protocol's failure documentation standard.

---

### pypsa-F11: Gate ingestion tests G-1/G-2/G-3 are low-signal — pass/fail outcomes are predictable

**Category:** low_signal | **Severity:** low
**Tests:** G-1, G-2, G-3

The gate tests verify only that a tool loads MATPOWER .m files and returns correct counts. These tests would be passed by any tool with a MATPOWER importer. The only signal is in data quality notes — specifically, G-1 notes that PyPSA's import_from_pypower_ppc silently drops generator cost data. This finding is meaningful but is not part of the gate pass/fail outcome.

G-1 says: "Generator cost data NOT imported — import_from_pypower_ppc does not support gencost." This affects every downstream OPF test (the shared loader's gencost patch corrects this), but the gate test passes regardless.

**Cross-tool relevance:** confirmed — this is a protocol design issue. The gate tests serve their minimum-bar purpose but provide no discriminative information beyond pass/fail.

**Proposed action:** add_verification — gate tests should include a data quality checklist (cost data imported, branch flow limits populated, slack bus identified, NaN check) as part of the pass condition. This would make G-1's gencost finding a gated finding rather than an incidental note.

---

### pypsa-F12: qualified_pass status applied to both stable-workaround (A-6) and blocking-limitation (A-11) cases

**Category:** scoring_inconsistency | **Severity:** low
**Tests:** A-6, A-11

Both A-6 and A-11 receive qualified_pass status. The workaround_class values differ: "stable" for A-6 (two-stage UC/ED via documented API, ~15 LOC) and "blocking" for A-11 (distributed slack DC OPF architecturally impossible). These represent substantially different degrees of capability gap, but the same outcome label.

A-6 is a genuine partial pass: the required two-stage UC/ED workflow is achievable using documented public API, just without a convenience method. A-11 is a fail in the OPF context: the required capability (distributed slack DC OPF) cannot be achieved by any workaround because the model lacks bus angle variables. The synthesis correctly describes this distinction but both map to qualified_pass in the status field.

This inconsistency propagates to cross-tool aggregation where qualified_pass outcomes may be treated uniformly.

**Cross-tool relevance:** confirmed — the same status ambiguity would affect other tools receiving qualified_pass with blocking workarounds.

**Proposed action:** adjust_scoring — either introduce distinct status values (qualified_pass vs. capability_gap) or require workaround_class=blocking to map to fail rather than qualified_pass in the grading logic.

---

## Extraordinary Claims

### G-FNM-3: 0.0 mean and max deviation on 27,862-bus DCPF

**Concern:** Perfect 0.0 numerical agreement in a floating-point computation at this scale is unusual. Display precision (one decimal place) may round values <0.05 to zero. Additionally, the validation report lists G-FNM-3 as a failure with "systematic impedance conversion differences via MATPOWER fallback," conflicting with the result file's pass status.

**Evidence quality:** moderate — the explanation (identical B-matrix formulation) is plausible and would predict 0.0 agreement, but the raw unrounded deviations are not reported.

The probe should: (1) extract raw maximum absolute angle deviation and maximum branch flow percent deviation without display rounding, (2) confirm that the validation report's failure record reflects a superseded intermediate result rather than the current evaluation state. If the deviation is truly machine-zero, this is a strong positive finding (both tools trace to the same B-matrix formulation). If it is display-rounded from a non-zero value, the threshold checks (95% of buses within 1.0 deg, 90% of branches within 10%) may still pass but the "0.0" characterization is misleading.

---

## Test Outcome Matrix

| Test ID | Status | Workaround | Key Issue |
|---------|--------|------------|-----------|
| G-1 | pass | — | gencost silently dropped (note, not gate failure) |
| G-2 | pass | — | — |
| G-3 | pass | — | — |
| A-1 | pass | — | — |
| A-2 | pass | — | — |
| A-3 | pass | stable | shadow price extraction via linopy internals (bug workaround) |
| A-4 | pass | — | requires two loader paths (DC vs AC); not a workaround |
| A-5 | pass | — | min up/down binding not verified (pypsa-F02) |
| A-6 | qualified_pass | stable | no fix_commitment() API; manual bound manipulation |
| A-9 | pass | — | only 19/46 branches used; transformer contingencies excluded (pypsa-F04) |
| A-10 | pass | — | three-component LMP decomposition check not fully verified (pypsa-F03) |
| A-11 | qualified_pass | blocking | distributed slack DC OPF architecturally impossible; AC PF credited instead (pypsa-F07) |
| A-12 | pass | fragile | branch shadow prices via internal linopy naming (bug workaround) (pypsa-F08) |
| B-1 | pass | — | — |
| B-2 | pass | — | — |
| B-3 | pass | — | load loss = 0 (expected for unconstrained DCPF, documented) |
| B-4 | pass | — | — |
| B-5 | pass | — | — |
| B-6 | pass | — | — |
| B-8 | pass | — | LMPs identical across all slack configs (mathematically expected; pass condition vacuous) (pypsa-F01) |
| B-9 | pass | — | — |
| C-4 | fail | — | HiGHS MILP timeout (39,168 binary vars); SCIP not installed |
| C-5 (SMALL) | pass | — | converges 0% relaxation; 4 NR iterations |
| C-5 (MEDIUM) | pass | — | converges 0% relaxation; 5 NR iterations; 2099 MB peak memory |
| C-1 | skip | C-SMALL-gate | LP/PF unnecessarily blocked by MILP gate (pypsa-F09) |
| C-2 | skip | C-SMALL-gate | LP/PF unnecessarily blocked by MILP gate (pypsa-F09) |
| C-3 | skip | C-SMALL-gate | LP/PF unnecessarily blocked by MILP gate (pypsa-F09) |
| C-7 | skip | C-SMALL-gate | LP/PF unnecessarily blocked by MILP gate (pypsa-F09) |
| C-8 | skip | C-SMALL-gate | blocked by MILP gate (pypsa-F09) |
| C-9 | skip | C-SMALL-gate | LP/linear algebra unnecessarily blocked by MILP gate (pypsa-F09) |
| C-10 | skip | C-SMALL-gate | blocked by MILP gate (pypsa-F09) |
| D-1 | pass | — | — |
| D-2 | informational | — | 5/10 from docs, 3 need source, 2 need trial-and-error |
| D-3 | pass | — | 11/11 examples pass unmodified |
| D-4 | pass | — | — |
| D-5 | informational | — | median 259 LOC; range 111-415 |
| E-1 | pass | — | — |
| E-2 | pass | — | — |
| E-3 | pass | — | — |
| E-4 | pass | — | — |
| E-5 | pass | — | — |
| E-6 | pass | — | — |
| E-7 | pass | — | — |
| F-1 | pass | — | — |
| F-2 | informational | — | ~70 transitive deps, max depth 4; GCS cloud deps unnecessary |
| F-3 | qualified_pass | — | 1 GPL dep (Levenshtein); replaceable with MIT rapidfuzz |
| F-4 | pass | — | — |
| F-5 | pass | — | — |
| F-6 | pass | — | — |
| F-7 | pass | — | — |
| F-8 | pass | — | — |
| F-9 | pass | — | — |
| G-FNM-1 | fail | — | no PSS/E ingestion; API inspection only (pypsa-F10) |
| G-FNM-2 | skip | G-FNM-1 | field coverage blocked; MATPOWER fallback could enable partial assessment (pypsa-F05) |
| G-FNM-3 | pass | stable | 0.0 deviation extraordinary claim; validation-report.md discrepancy (pypsa-F06) |
| G-FNM-4 | informational | — | SuperLU factorization failure at all relaxation levels; consistent with MATPOWER |
| G-FNM-5 | informational | — | 20.5% N / 61.6% E / 17.8% X; 73 fields assessed |
| P2-1 | informational | — | no PSS/E RAW parsing; estimated 3-4 weeks effort |
| P2-2 | informational | — | no piecewise-linear cost curves; tracked as issue #1020 |
| P2-3 | informational | — | commitment injection workflow feasible via A-6 pattern |
