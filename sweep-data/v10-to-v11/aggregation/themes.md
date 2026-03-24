# Cross-Tool Themes — v10-to-v11 Sweep Narrative Analysis

This document provides full narrative context for each cross-cutting theme identified in the sweep. Themes describe patterns in the evaluation protocol and rubric design — they are framed as opportunities to improve evaluation accuracy and cross-tool comparability, not as criticisms of individual tools.

**Evidence threshold:** Protocol and rubric changes require 3+ tools. Skill-only changes require 2+ tools.

**Probe integration:** Eight probes were executed during this sweep. Their classifications (claim_debunked, claim_supported, confirmed_issue, inconclusive) are integrated into the relevant theme narratives below.

---

## T-01: C-SMALL Gate Cascades Block LP/PF MEDIUM Tests When Only MILP Fails

**Affected tools:** pypsa, pandapower, matpower, powermodels
**Signal level:** High | **Dominant factor:** test_design
**Proposed change:** PC-01

### Pattern

The C-SMALL gate requires C-4 (SCUC on 2000-bus SMALL network) to pass before any MEDIUM-tier scalability tests execute. This design made sense when the gate was introduced: SCUC is a representative stress test that exercises the full optimization stack at scale. If a tool cannot run SCUC at SMALL scale, the implicit assumption was that MEDIUM-scale LP and power flow would also be stressed.

In practice, C-4 failures in this evaluation arise from three distinct causes, each with different implications for LP/PF scalability:

1. **SCUC absent from tool scope** (pandapower, powermodels): These tools have no MILP unit commitment formulation. Their C-4 failure is a scope boundary, not a scale failure. pandapower's pandapower-F01 is explicit: "The SMALL gate failure was a cascaded failure from A-5 (SCUC unsupported), not a scale-related failure." The tool demonstrably solves 28,000-bus DCPF in 0.4 seconds in G-FNM-3.

2. **MILP solver timeout at scale** (pypsa): PyPSA's HiGHS single-threaded cannot solve a 39,168-variable binary problem within 600 seconds. This is a MILP scalability limitation. But PyPSA's LP and power-flow scalability are demonstrably strong: G-FNM-3 passes DCPF at 27,862 buses. The gate prevents formally recording LP/PF MEDIUM capability because the MILP test failed.

3. **SCUC genuinely infeasible for the solver** (matpower/GLPK): Probe-016 debunked the original matpower finding (matpower-F01 claimed a GLPK exit-flag mapping bug). The actual situation is that GLPK returns GLP_ETMLIM (time limit, errnum=9, status=-1) — no feasible integer solution was found. The SCUC problem is genuinely failing, not producing a solution that cannot be extracted. This means matpower's C-4 fail is a real solver capability gap on this problem instance, but MATPOWER's LP capability (which is excellent) is still obscured by the gate cascade.

**Consequence:** Seven to eight MEDIUM-tier tests per affected tool receive 'skipped' status rather than outcomes, producing structurally incomplete scalability grades. Cross-tool comparison at MEDIUM scale is only possible for gridcal, powermodels, and powersimulations — the three tools that pass C-4 (or have an alternative path to MEDIUM tests).

### Probe integration

Probe-016 (matpower, claim_debunked) is critical here: it established that the GLPK failure in matpower is genuine (GLP_ETMLIM, status=-1, no feasible solution), not a one-line exit-flag-mapping fix as claimed in matpower-F01. This means:

- The original matpower finding was overclaiming about the nature of the C-4 failure (suggesting a fixable bug was obscuring a solved result)
- The cascade to MEDIUM tests remains appropriate for matpower — GLPK genuinely cannot solve the SCUC
- But the gate design still blocks LP/PF MEDIUM measurement for matpower, where MIPS is demonstrably capable

### Protocol implication

The fix (PC-01) is structural: C-SMALL gate should conditionally block MILP MEDIUM tests only. LP/PF MEDIUM tests (C-1, C-2, C-3, C-9, C-10) should run unconditionally. This preserves the gate's minimum-bar function (a tool that fails MILP at small scale should not get credit for MILP at MEDIUM) while allowing LP and power-flow scalability evidence to be collected regardless of MILP outcome.

---

## T-02: SCUC Test Network Insufficient to Verify Min Up/Down Binding

**Affected tools:** pypsa, powermodels, powersimulations, matpower, gridcal
**Signal level:** High | **Dominant factor:** network
**Proposed change:** PC-02

### Pattern

A-5's pass condition requires at least two generators to cycle (commit/decommit) in the 24-hour TINY horizon. All five tools that attempt SCUC on the 39-bus network meet this threshold. However, no tool's result verifies that the min up/down time constraints are actually binding — that is, that removing them would change the commitment schedule.

The structural reason is the 10-generator IEEE 39-bus network's characteristics: 7,367 MW total capacity against 6,254 MW peak load (1.18x ratio). With this headroom, the optimizer can satisfy peak demand with the cheapest generators committed and simply shut down expensive units during load valleys. The cycling pattern observed (typically 2-3 gas CC units shutting down during hours 3-8 and restarting at hour 9) is driven by economic dispatch logic, not by min up/down constraints binding. The temporal constraints are present in the MILP formulation but not necessarily active at the optimal solution.

**Specific evidence:**
- powermodels (pm-F09): "Total shutdowns: 3. Total startups: 0 (generators only decommit toward end of horizon, no recommitment needed within 24h)." This is exactly the pattern expected when min up/down constraints are not binding.
- matpower (matpower-F05): The qualified_pass was validated on ex_case3b (3 buses, 5 generators) rather than case39 due to the solver failure. The 3-bus result had only 1 cycling generator, below the protocol's 2-generator threshold.
- gridcal (gridcal-F04): "MIP gap note: The MIP gap is not directly extractable from the OptimalPowerFlowTimeSeriesResults object." Commitment is inferred from generator power output thresholding, not from binary variables. This creates ambiguity about whether the MILP is genuinely solved or an LP relaxation is producing near-binary values.

### Protocol implication

PC-02 proposes a binding verification sub-step: re-run SCUC with min_up_time=min_down_time=0 and compare the commitment schedule. If the schedule changes, at least one constraint was binding. This is feasible computationally (two solves on TINY) and would provide behavioral evidence rather than formulation completeness evidence. The TINY network may also need capacity margin reduction to force genuine cycling under temporal constraints.

---

## T-03: SCOPF MEDIUM Result Is Vacuous — ACTIVSg10k Is Uncongested

**Affected tools:** gridcal, powermodels, powersimulations
**Signal level:** High | **Dominant factor:** network
**Proposed change:** PC-03

### Pattern

C-8 (SCOPF on MEDIUM) is intended to test whether a tool can solve a large-scale security-constrained OPF with N-1 contingency constraints and produce meaningful redispatch relative to the base-case DCOPF. The ACTIVSg10k network has a maximum branch loading of ~84.72% at base case. With this much headroom, no N-1 contingency creates post-contingency violations — the network is too lightly loaded to stress any security constraint.

All three tools that executed C-8 MEDIUM confirmed this independently:
- **gridcal (gridcal-F02):** "The maximum dispatch difference is 2.67e-07 MW and the maximum LMP difference is 1.49e-08 $/MWh — effectively zero. No generators show dispatch changes above 1 MW, and no branches become binding." Status: pass (technically correct — the SCOPF ran to completion, produced a valid result, and it happens to equal the base case because there are no security constraints to enforce).
- **powermodels (pm-F02):** SCOPF awarded pass despite Benders decomposition completing only 1 iteration in 595 seconds. The non-convergence is not flagged in the pass condition because the C-8 protocol states it is a 'measurement test.' But a non-converged SCOPF on an uncongested network is doubly uninformative.
- **powersimulations (powersimulations-F09):** HiGHS crashes with OTHER_ERROR after 438 seconds on MEDIUM. The SCOPF crash is on a problem with no meaningful security constraints to enforce.

**Consequence:** C-8 MEDIUM currently differentiates tools by solver robustness on an uncongested problem rather than by SCOPF expressiveness or security-constrained redispatch quality. A SCOPF on an uncongested network is equivalent to an LP that produces no active constraints — the only discrimination is whether the solver completes without error.

### Protocol implication

PC-03 proposes replacing ACTIVSg10k with a congested MEDIUM network for C-8, or stressing the current network until at least 5% of branches exceed 95% loading. The pass condition must include a minimum redispatch magnitude requirement. The SMALL SCOPF (C-8 SMALL on ACTIVSg2000) does produce meaningful redispatch (gridcal: up to 164 MW) and should serve as the model for the MEDIUM redesign.

---

## T-04: Convergence Accepted Without Residual Across ACPF Implementations

**Affected tools:** pandapower, powermodels, powersimulations
**Signal level:** Medium | **Dominant factor:** capability
**Proposed change:** PC-04

### Pattern

The protocol requires reporting the convergence residual for ACPF solves. At least three tools have no public API path to extract the Newton-Raphson residual value after solve completion. Result files record convergence_residual: null and justify convergence via indirect proxies:

- **pandapower (pandapower-F02):** Iteration count via private `net._ppc["iterations"]` attribute; residual reported as "below 1e-8 (tolerance_mva setting; exact value not extractable)."
- **powermodels (pm-F05):** `compute_ac_pf` returns only a Bool termination_status. No NR iteration count or residual exposed in the result dictionary.
- **powersimulations (powersimulations-F02):** PowerFlows.jl `solve_powerflow` returns a `Dict{String, DataFrame}` on convergence, `missing` on non-convergence. No residual in the return value.

**Probe-013 (powersimulations, claim_debunked)** is the most important finding here. The claim that "PowerFlows.jl provides no convergence diagnostics" is falsified:

1. The iteration count IS emitted at @info log level: `[ Info: The NewtonRaphsonACPowerFlow solver converged after 1 iterations. ]` — the original evaluation set `global_logger(ConsoleLogger(stderr, Logging.Error))`, suppressing @info messages.
2. The return type structurally guarantees convergence: `solve_powerflow` returns `missing` on non-convergence. A returned `Dict` is a binary convergence indicator.
3. The powersimulations A-2 qualified_pass annotation overstates the tool limitation — the API provides stronger convergence guarantees than the evaluation recognized.

This probe result means the powersimulations A-2 status should arguably be upgraded from qualified_pass to pass, as the convergence verification methodology was unnecessarily weak.

**The underlying pattern remains real** for pandapower (tolerance_mva bug unfixed, residual inaccessible) and powermodels (Bool-only return, NR internals not exposed). The protocol's residual requirement assumes all tools have this API capability, which is false for the Julia ecosystem tools and pandapower.

### Protocol implication

PC-04 proposes a tiered evidence hierarchy: (1) residual value, (2) iteration count via any API including logging, (3) binary convergence indicator via return type or exception, (4) voltage profile proxy as last resort. Evaluators should attempt all tiers and document which tier was achieved. The skill should enable Julia @info logging during ACPF solves and capture the iteration count from the log stream.

---

## T-05: Ramp Constraints Not Binding in A-6/SCED

**Affected tools:** matpower, powermodels, powersimulations
**Signal level:** Medium | **Dominant factor:** network
**Proposed change:** PC-05

### Pattern

The A-6 SCED pass condition requires that ramp rate constraints are "demonstrably enforced between consecutive dispatch intervals." In all tools that attempt A-6 with ramp constraints, the constraints are formulated correctly but never bind. The root cause is that RTS-GMLC technology-median ramp rates (used to populate gen_temporal_params.csv) are derived from large generating units and are orders of magnitude larger than the dispatch changes required by the 39-bus load profile.

**Specific evidence:**
- matpower (matpower-F04): Most constrained generator (G1) uses 48.5 MW/hr of a 62,400 MW/hr ramp limit. "No generators hit binding ramp limits."
- powersimulations (powersimulations-F08): "460 ramp constraints added. 1 binding ramp constraint observed." The single binding constraint is not identified; LMP extraction failed.
- powermodels (pm-F13): A-6 reduced to pure ED (UC absent), so ramp constraints bind only if the LP dispatch changes between hours — which requires some other constraint to force a discontinuous dispatch pattern.

The test demonstrates that multi-period OPF formulation includes ramp terms without numerical error, but any tool that successfully runs multi-period OPF would pass this criterion trivially.

### Protocol implication

PC-05 proposes scaling ramp rates down (by 10x or more) in gen_temporal_params.csv to force binding. The pass condition should require at least one ramp constraint dual value greater than zero with identification of the constrained generator, hour, and dual magnitude.

---

## T-06: SCED Degrades to ED-Only When SCUC Is Absent

**Affected tools:** powermodels, pandapower, powersimulations
**Signal level:** Medium | **Dominant factor:** test_design
**Proposed change:** PC-06

### Pattern

When A-5 SCUC fails or is unsupported, A-6 SCED loses the UC stage: the tool assumes all generators are committed and performs only the multi-period economic dispatch. The rubric criterion for A-6 is Security-Constrained Economic Dispatch (which includes commitment-status inputs from SCUC), but the result receives the same qualified_pass label regardless of whether UC was performed. The 'security-constrained' component (binding N-1 contingency constraints on dispatch) is also absent for most tools attempting A-6.

This means a tool performing full two-stage SCED (UC → ED with security constraints) and a tool performing pure unconstrained multi-period ED both receive qualified_pass for A-6 — which conflates genuinely different capability levels.

### Protocol implication

PC-06 proposes explicit sub-categorization: `sced_mode: full_sced | ed_only | ed_with_security`. Only `full_sced` should map to pass; `ed_only` should map to fail with context. The skill needs to check A-5 outcome before setting A-6 grade.

---

## T-07: qualified_pass Applied at Inconsistent Severity Levels

**Affected tools:** pypsa, powermodels, powersimulations, pandapower, matpower
**Signal level:** High | **Dominant factor:** test_design
**Proposed change:** PC-07

### Pattern

The qualified_pass status label is the most overloaded outcome in the current protocol. It is applied to:

- **Stable workarounds with minimal friction:** pypsa A-6 (two-stage dispatch pattern, undocumented but functional), gridcal C-4 (snapshot workaround, explicitly documented)
- **Blocking architectural impossibilities:** pypsa A-11 (distributed slack DC OPF is impossible in optimize() path) — the workaround_class is 'blocking' but the label is the same qualified_pass
- **Non-converged results:** powermodels C-8 (1 Benders iteration, time budget, not converged) — awarded 'pass', not even qualified_pass, but the underlying concern about grade inflation is the same
- **Solver crashes on the grade network:** powersimulations C-8 (HiGHS OTHER_ERROR on MEDIUM) — qualified_pass despite the solver crashing before producing any result on the primary test network
- **Three simultaneous non-trivial workarounds:** powermodels A-12 (SCIP solver switch, cyclic SoC manual injection, two-phase LMP extraction) — awarded 'pass', not qualified_pass, despite three compounding non-obvious workarounds that a new user would not discover

The workaround_class field (stable / fragile / blocking) documents the severity within qualified_pass, but this information is not surfaced in the aggregated outcome that drives grade calculations. A cross-tool comparison matrix entry of 'QP' is equally opaque for a near-pass and a near-fail.

### Protocol implication

PC-07 proposes three severity tiers to replace or supplement qualified_pass:

- **qualified_pass:** Stable workaround exists, full capability demonstrated, low friction. Current meaning.
- **partial_pass:** Non-trivial workaround, some criterion unmet, moderate friction. Maps to workaround_class: fragile or blocking. Should score lower than qualified_pass in grade calculations.
- **constrained_pass:** Capability demonstrated under constraints that affect generalizability (e.g., uncongested network, single-threaded solver, simplified formulation). Informative but weaker evidence than qualified_pass.

Additionally: non-converged SCOPF runs should be constrained_pass at best; solver crashes on the grade network should be fail with context; workaround_class: blocking should never map to qualified_pass — it should map to partial_pass or fail.

---

## T-08: G-FNM Result Precision — 6-Decimal Rounding Obscures Floating-Point Accuracy

**Affected tools:** pypsa, matpower
**Signal level:** Low | **Dominant factor:** test_design
**Proposed change:** PC-08

### Pattern

Result files store deviation values with `round(..., 6)` (6 decimal places). Probe-001 (pypsa G-FNM-3, claim_debunked) confirmed that the reported 0.0 deviation values are display artifacts: the actual maximum bus angle deviation is 1.07e-8 degrees (non-zero floating-point noise from two independently implemented DCPF solvers that round to 0.000000 at 6 decimal places).

The PASS grade for pypsa is fully warranted — the deviations are at the limit of float64 precision for values of this scale, and all buses pass the 1.0-degree tolerance by a factor of ~100 million. The validation-report.md discrepancy (which listed G-FNM-3 as FAIL) was confirmed to be a stale artifact from before the shared matpower_loader fix was applied.

The probe also resolved the discrepancy between the result file (PASS) and validation-report.md (FAIL): the validation report reflects an older intermediate state and was not regenerated after the loader fix. The result file is the authoritative source.

The display precision issue is minor but matters for cross-tool comparison: a tool with true machine-zero agreement (identical code paths as MATPOWER) would be indistinguishable from a tool with correctly equivalent but independently coded formulations (float64 noise at ~1e-8). The former would indicate something potentially concerning (shared code dependency), the latter is expected and correct.

### Protocol implication

PC-08 proposes requiring scientific notation (:.6e format) for deviation values in G-FNM results. The change is cosmetic and does not affect grades.

---

## T-09: PSS/E v31 Parser Failures Force MATPOWER Fallback Across the FNM Suite

**Affected tools:** pypsa, pandapower, gridcal, powermodels
**Signal level:** High | **Dominant factor:** infrastructure
**Proposed change:** PC-09

### Pattern

The FNM data is provided as a PSS/E v31 RAW file with an intermediate CSV export derived from PSS/E v31 record types. Zero of the six evaluated tools successfully ingested the FNM via the PSS/E native path:

- **pypsa:** No PSS/E importer exists in the codebase (architecture gap)
- **pandapower:** No intermediate CSV import capability; no PSS/E import path
- **gridcal:** PSS/E parser hardcoded to v35 field counts; v31 RAW triggers "1 elements expected, 18 expected" exceptions
- **powermodels:** PSS/E v31 parser crashes on the Case Identification header line

All non-MATPOWER tools fall back to the fnm_main_island.m MATPOWER file (a pre-cleaned main-island subset with documented record deficits: bus -8.1%, load -42.7% vs the PSS/E manifest). This means all G-FNM test results measure tool performance on a MATPOWER-preprocessed representation of the FNM, not on the FNM directly.

**Consequences:**

1. The FNM suite was designed to test format interoperability (G-FNM-1) and power-system modeling capability (G-FNM-2 through G-FNM-5) as distinct dimensions. The universal PSS/E failure collapses these: all tools receive the same pre-processed MATPOWER input, making the "does the tool support the format?" question separately assessable only for MATPOWER.

2. Cross-tool G-FNM-3 DCPF comparisons are conditioned on the same fallback preprocessor, making them more comparable than if different tools had ingested different format versions — but this comparability comes at the cost of measuring the preprocessor rather than the tools.

3. G-FNM-4 ACPF non-convergence findings for pandapower and gridcal are attributed partly to "PPC import path loses AC-critical transformer data" — a characteristic of the fallback path, not necessarily of the tool's ACPF solver.

### Protocol implication

PC-09 proposes separating PSS/E format support assessment from power-system capability assessment: G-FNM-1 should be a pure format support test (informational) that does not cascade to block G-FNM-2 through G-FNM-5. Field coverage and DCPF accuracy should always be assessed via the best available path, with the path explicitly tagged in results. Providing the FNM in both PSS/E and MATPOWER formats as first-class named inputs (not fallbacks) would normalize this across tools.

---

## T-10: GridCal DCOPF Uses Soft Branch Flow Constraints (Confirmed by Probe)

**Affected tools:** gridcal
**Signal level:** High | **Dominant factor:** capability
**Proposed change:** PC-10

### Pattern

Probe-005 (gridcal A-3, confirmed_issue) provided definitive evidence that GridCal's `linear_opf` uses soft branch flow constraints: explicit LP slack variables `flow_slacks_pos` and `flow_slacks_neg` per branch. The source code inspection (`VeraGridEngine/Simulations/OPF/opf_driver.py` line 170-171) and runtime verification (branch 2_3_1 reaches 103.5% loading in the optimal solution — 103.5% is only achievable with soft constraints) together establish this as a confirmed formulation characteristic, not an inference.

The A-3 pass verdict is misleading: the three pass conditions (convergence, LMP extractability, binding branch count) do not verify that thermal limits are enforced as hard constraints. A standard DCOPF enforces hard thermal limits — this is universally required for correct market clearing (hard limits produce LMPs reflecting true congestion; soft limits produce LMPs reflecting penalty costs that may not correspond to marginal congestion relief).

The D-4 error quality test corroborates this: setting all branch ratings to zero was expected to produce an infeasible LP, but GridCal instead produced a 'feasible' solution where all branches violated their limits via slack absorption. This is internally consistent with the soft-constraint formulation but was incorrectly interpreted as an error reporting quality failure — partially unfair to GridCal's design choice (soft constraints are a legitimate numerical stabilization technique) while also missing the harder question of whether they are appropriate defaults for market applications.

This is currently a GridCal-specific confirmed issue — no other evaluated tool uses soft branch flow constraints by default in DCOPF. However, the protocol gap (A-3 does not verify hard constraint enforcement) is a cross-tool issue: any tool that used a soft-constraint OPF by default would also pass A-3 as currently written.

### Protocol implication

PC-10 proposes adding a hard constraint enforcement check to A-3: `max(loading_percent) <= 1.0 + epsilon`. Soft-constraint DCOPF should be explicitly classified as `partial_pass` with the penalty coefficient documented. This provides discriminative signal that the current pass condition cannot provide.

---

## T-11: B-8 LMP Variation from Slack Reconfiguration Is Mathematically Vacuous for DC OPF

**Affected tools:** pypsa, matpower
**Signal level:** Medium | **Dominant factor:** test_design
**Proposed change:** PC-11

### Pattern

B-8 requires that "LMP values change consistently across configurations" when the slack bus is moved. In standard DC OPF, the dual variables of KCL constraints (which equal the LMPs) are invariant to the choice of reference bus — the angle reference cancels out. Any correctly implemented DC OPF will show identical LMPs across all slack configurations.

pypsa A-3 (pypsa-F01): All three slack configurations produce identical objectives (spread 0.0) and identical LMPs (spread 0.0). The evaluator correctly explains this is mathematically expected, but the pass condition language ("LMP values change consistently") is ambiguous — it could mean "change consistently between buses" (which they do, reflecting cost gradients) or "change between configurations" (which they don't, which is correct).

matpower A-11 distributed slack (matpower-F06): The distributed slack formulation produces only a uniform LMP shift across all buses (std dev $0.00), which the result acknowledges is correct for lossless DC OPF.

The test successfully measures API configurability (can the tool set a different reference bus without error?), which is a valid dimension. But the LMP variation component of the pass condition is vacuous for all correct DC OPF implementations.

### Protocol implication

PC-11 proposes rewriting the pass condition to explicitly test API configurability (three configurations must complete without error) and to remove the LMP variation requirement for DC OPF. For tools supporting AC OPF, an optional AC OPF sub-test where slack choice does affect LMPs could provide genuine discriminative signal.

---

## T-12: G-FNM-3 Reference Is Self-Generated for the Reference Tool

**Affected tools:** matpower
**Signal level:** Medium | **Dominant factor:** test_design
**Proposed change:** PC-12

### Pattern

The MATPOWER reference solution for G-FNM-3 DCPF is generated by MATPOWER itself from the same .m file it will use as input. This makes MATPOWER's zero-deviation result mathematically guaranteed — a round-trip consistency check, not an accuracy verification.

Probe-001 (pypsa, claim_debunked) provides indirect validation: PyPSA's deviations from the MATPOWER reference are at float64 noise levels (~1e-8 degrees), confirming the reference is correctly computing a DCPF solution for the network's line-dominated segments. However, the reference cannot independently validate transformer-branch flows, which is where both gridcal (probe-007) and powersimulations show systematic failures.

### Protocol implication

PC-12 proposes adding a cross-reference independence check to G-FNM-3: either a bus-injection power balance check (necessary condition for solution validity, tool-independent) or comparison against an independently implemented DCPF for a subset of buses. This would validate that the MATPOWER reference is correct for transformer branches, not just line segments.

---

## T-13: SCIP License Conflict — ZIB Academic at Pinned Version, Not Apache 2.0

**Affected tools:** powermodels
**Signal level:** High | **Dominant factor:** infrastructure
**Proposed change:** PC-13

### Pattern

Two PowerModels supply chain tests reach conflicting conclusions about the SCIP license:
- **F-3** classifies SCIP_jll v0.2.1 as ZIB Academic (non-commercial only) — correct per probe-010.
- **F-8** claims SCIP_jll v0.2.1 is Apache 2.0, explicitly overriding F-3's classification — incorrect.

**Probe-010 (powermodels, claim_supported)** resolved this definitively by checking the JuliaBinaryWrappers release timeline:

| SCIP_jll version | SCIP version | License |
|-----------------|--------------|---------|
| v0.2.1+0 (pinned) | 8.0.0 | ZIB Academic |
| v800.0.300+0 | 8.0.3 | Apache 2.0 |

The Apache 2.0 license switch happened at SCIP 8.0.3 (December 2022), not at SCIP 8.0.0. F-8's claim that "SCIP v8.0 switched to Apache 2.0" is factually wrong — the JLL package versioning scheme changed at the same time, and `SCIPversion()` returning "8.0" maps to 8.0.0, not 8.0.3+.

**Supply chain implication:** The pinned SCIP_jll v0.2.1 = SCIP 8.0.0 is ZIB Academic. Any commercial deployment using this manifest requires either a SCIP commercial license or exclusion of SCIP from the solver stack. F-8's upgrade of the supply chain grade to pass is unwarranted.

**Broader implication:** In the Julia JLL ecosystem, binary artifact licenses frequently differ from Julia package wrapper licenses. The SCIP_jll wrapper package uses MIT for its Julia code; the bundled SCIP binary uses ZIB Academic for the artifact. The binary license governs actual deployments. The evaluation skill should explicitly check both.

---

## T-14: Gate Tests (G-1/2/3) Are Low-Signal Universal Passes

**Affected tools:** all six
**Signal level:** Low | **Dominant factor:** test_design
**Proposed change:** PC-14

### Pattern

All six tools pass all three gate tests. The tests verify element counts after loading a standard MATPOWER .m file — a trivially satisfied minimum bar for any tool that has reached the maturity level required to participate in this evaluation. Five of six per-tool finding files explicitly note this. The gate tests serve their intended purpose (a fail would be informative) but their pass outcomes have zero discriminative signal and uniformly inflate apparent pass rates.

### Protocol implication

PC-14 proposes tagging gate tests as `test_category: gate_minimum_bar` and excluding their pass outcomes from cross-tool pass rate numerators and denominators. An optional enhancement: add a data quality sub-check for cost function import completeness, which would provide discriminative signal (pypsa-F11 notes that PyPSA's `import_from_pypower_ppc` silently drops gencost data).

---

## T-15: C-4 Timing Comparability Compromised by Solver Thread Count Variation

**Affected tools:** powersimulations
**Signal level:** Low | **Dominant factor:** infrastructure
**Proposed change:** PC-15

### Pattern

powersimulations C-4 records 404 seconds for 2K-bus SCUC with HiGHS at 1 thread on a machine with 32 available cores. MILP solvers scale significantly with thread count — multi-threaded HiGHS on the same problem would likely solve in 15-30 seconds. The 404s result is reproducible and technically correct, but it is not representative of practical deployment on the same hardware.

This is a single-tool finding but exposes a protocol gap: without standardized thread count specification (or at minimum, thread count reporting), MILP timing results are not comparable across tools.

### Protocol implication

PC-15 proposes requiring cpu_threads used and cpu_threads available in all scalability test frontmatter. For MILP tests (C-4, C-8), both 1-thread and max-thread timings should be reported.

---

## T-16: SCOPF TINY Network Too Radially Connected for Meaningful Contingency Coverage

**Affected tools:** pypsa, powermodels, powersimulations
**Signal level:** Medium | **Dominant factor:** network
**Proposed change:** PC-16

### Pattern

The IEEE 39-bus TINY network is insufficiently meshed for SCOPF evaluation:
- powersimulations (powersimulations-F04): 27 of 34 line contingencies filtered as near-radial (|LODF| >= 0.95). Only 7 non-trivial contingencies remain.
- pypsa (pypsa-F04): Progressive fallback from 35 lines to 19 lines at <50% utilization due to base-case infeasibility of N-1 sets.
- powermodels: Probe-009 (inconclusive) confirmed the network is N-1 infeasible under Modified Tiny load profile at nominal ratings. The Benders mechanism is demonstrated via API (1 iteration, correct infeasibility detection) but multi-iteration convergence is never observed.

The consequence is that A-9 SCOPF results across all tools reflect the network's topological limitations (radial structure, tight base-case loading) rather than the tools' SCOPF formulation quality.

**Probe-009 integration:** The PowerModels A-9 result accurately documents the N-1 infeasibility and 1-iteration behavior. The evaluator's framing ("physical property of the network, not a code limitation") is correct. The qualified_pass for demonstrating the API mechanism is defensible. But the test design gap means no tool demonstrated multi-iteration Benders convergence during this evaluation — not because any tool lacks the capability, but because no feasible SCOPF scenario was provided.

### Protocol implication

PC-16 proposes pre-computing and publishing a feasible N-1 SCOPF configuration for case39 in eval-config.yaml. The pass condition should require either multi-iteration convergence OR explicit demonstration that the joint N-1 problem is infeasible (with the infeasibility correctly detected). This would allow SCOPF mechanism verification to be distinguished from SCOPF convergence verification.

---

## Probe Integration Summary

Eight probes were executed during this sweep. Their outcomes and impact on the themes are:

| Probe | Classification | Theme Impact |
|-------|---------------|-------------|
| probe-001 (pypsa G-FNM-3) | claim_debunked (weak) | T-08: 0.0 is a display artifact; PASS grade is correct; validation report is stale |
| probe-003 (pandapower A-3) | claim_supported | T-04 context: shadow prices are real (min 8.79 $/MWh); sweep concern about artifacts is refuted |
| probe-005 (gridcal A-3) | confirmed_issue | T-10: soft branch constraints confirmed in source code and runtime; A-3 P is misleading |
| probe-007 (gridcal G-FNM-3) | classification_plausible_with_caveats | T-09: formulation_difference classification is defensible but has two design flaws (no magnitude cap, adjacency proxy) |
| probe-009 (powermodels A-9) | inconclusive | T-16: Benders mechanism real; no feasible SCOPF scenario tested; test design gap confirmed |
| probe-010 (powermodels SCIP) | claim_supported (F-3) | T-13: SCIP 8.0.0 = ZIB Academic; Apache 2.0 switch at 8.0.3; F-8 P should be QP |
| probe-013 (powersimulations A-2) | claim_debunked | T-04: iteration count at @info; return type = convergence guarantee; A-2 QP overstates limitation |
| probe-016 (matpower GLPK) | claim_debunked | T-01: GLPK failure is GLP_ETMLIM with status=-1 (no feasible solution); not an exit-flag mapping bug |

---

## GitHub Issues

The github-issues.yaml query (2026-03-14) returned zero issues with the 'protocol' label. No issue integration was performed.
