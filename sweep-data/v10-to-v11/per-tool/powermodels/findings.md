# powermodels — Sweep Findings (v10)

## Summary

The PowerModels.jl evaluation is well-evidenced and thoroughly executed, with all 37
tests producing result files and measured timings. However, several scoring decisions
warrant review. The most significant issue is that SCUC receives qualified_pass status
at both TINY and SMALL scale despite PowerModels providing zero UC capability: the
entire MILP was assembled by the evaluator from raw JuMP. Two additional misleading
scores affect the scalability grade: C-8 (SCOPF MEDIUM) awards pass to a run that did
not converge within the time budget, and A-12 (multi-period storage) awards outright
pass despite three simultaneous non-obvious workarounds. The FNM DCPF hard-fail may
reflect test design (forcing DCPPowerModel when DCMPPowerModel exists and handles tap
ratios) rather than tool limitation. Two extraordinary claims warrant probe:
SCOPF mechanism is "demonstrated" on an N-1 infeasible network (A-9), and the GLPK
convergence at MEDIUM scale reverses a v9 timeout failure without a confirmed explanation.

## Finding Details

### pm-F01: SCUC qualified_pass awarded when PowerModels provides zero UC capability

**Category:** misleading_result | **Severity:** high
**Tests:** A-5, C-4

A-5 (TINY) and C-4 (SMALL) both receive qualified_pass status. The result files are
unambiguous: "PowerModels used ONLY for data parsing ... Everything else is raw JuMP"
(A-5) and "the entire UC formulation (~300 LOC) was user-assembled" (C-4). The workaround
class is recorded as blocking in both cases. The 250/300 lines of user-assembled JuMP
construct binary commitment variables, min up/down time rolling-sum constraints, startup/
shutdown logic, ramp-rate coupling, nodal power balance with B-theta DCPF, and branch
thermal limits. PowerModels' only contribution is parse_file.

A qualified_pass with a blocking workaround accurately represents "the JuMP foundation
makes this implementable" but conveys a false impression that PowerModels participates in
the UC formulation. The synthesis itself identifies A-5's status as a human spot-check
item: "Verify whether 'qualified_pass with blocking workaround' is the correct
classification vs. 'fail' for the expressiveness sub-question." The result should either
be reclassified as fail (with a note that JuMP enables manual implementation) or the
scoring rubric for "blocking workaround + qualified_pass" needs explicit criteria
distinguishing "tool provides partial capability" from "tool provides a data format only."

**Cross-tool relevance:** likely — this scoring pattern may apply to any tool evaluated
with a blocking workaround on a primary capability.
**Proposed action:** adjust_scoring

---

### pm-F02: SCOPF MEDIUM awarded pass despite not converging within the time budget

**Category:** misleading_result | **Severity:** high
**Tests:** C-8

C-8 records status: pass with convergence_iterations: 1. The result file explicitly
states "Benders converged: No (1 iteration, time budget)." The timing breakdown shows
that 50 post-contingency DCPF checks consumed 416s of the 600s budget at ~8.3s/case,
leaving insufficient time for the second iteration. With 17 binding contingencies
identified and 8 blocks added (out of 17 needed), the resulting "optimal" objective
($2,162,360/h) reflects only partial security constraint coverage.

The protocol's "measurement test" designation is cited to justify pass status regardless
of convergence. However, "measurement test" should mean metrics are recorded even if
performance is poor -- not that incomplete convergence equals a pass. The same algorithm
converged in approximately 110s at SMALL scale (A-9), providing a meaningful
scalability comparison point that the pass designation obscures. A qualified_pass
noting "mechanism demonstrated, not converged within budget" would more accurately
characterize the result.

**Cross-tool relevance:** likely — the "measurement test" designation for SCOPF may
produce similar misleading pass scores for other tools.
**Proposed action:** adjust_scoring

---

### pm-F03: SCOPF TINY qualified_pass on an N-1 infeasible network

**Category:** extraordinary_claim | **Severity:** medium
**Tests:** A-9

A-9 demonstrates the SCOPF two-level API mechanism on the IEEE 39-bus Modified Tiny
network. The test discovers the network is not fully N-1 secure at original ratings
under the Modified Tiny load profile: the full N-1 SCOPF LP (all 46 contingencies
simultaneously) is infeasible, and the iterative Benders algorithm runs exactly 1
iteration before hitting infeasibility at iteration 2.

The mechanism verification claim -- that "the PowerModels.jl SCOPF mechanism works
correctly" -- rests on: (a) 46/46 individual single-contingency SCOPFs being OPTIMAL,
and (b) the Benders algorithm correctly adding constraints and producing a higher-cost
dispatch in iteration 1 ($144,663/h vs. $98,091/h base). This is reasonable evidence
for API correctness but does not demonstrate that the algorithm converges to a
security-constrained solution. The rubric criterion for SCOPF presumably requires
demonstrating that the tool produces a feasible security-constrained dispatch; this
test only shows the tool correctly identifies that no such dispatch exists for this
network configuration. A network where N-1 feasibility is achievable (e.g., with
looser thermal limits or a modified load profile) would provide stronger evidence.

Probe recommended: run the same SCOPF algorithm on the 39-bus network with relaxed
thermal limits (e.g., restoring original 100% ratings with a lighter load profile
that allows N-1 feasibility) to verify Benders convergence.

**Cross-tool relevance:** likely — the choice of an N-1 infeasible test network
could affect other tools' SCOPF results similarly.
**Proposed action:** add_verification

---

### pm-F04: DCPF verification test mandates solve_dc_pf (DCPPowerModel) when DCMPPowerModel exists and would likely pass

**Category:** test_design_gap | **Severity:** medium
**Tests:** G-FNM-3

G-FNM-3 hard-fails with a 2.43% bus angle pass rate (threshold 95%) and a mean
deviation of 5.1 degrees. The root cause is explicitly identified: DCPPowerModel uses
a simplified B-matrix (`b = -1/x`) that ignores transformer tap ratios, while the
MATPOWER reference uses the full B-matrix via `makeBdc()` which incorporates taps.
The FNM network has 12,501 transformer-connected buses (45% of all buses).

The evaluator identifies that DCMPPowerModel (which uses the full B-matrix) "would
incorporate taps into the B-matrix but is not available through solve_dc_pf" and
notes "Using solve_pf(data, DCMPPowerModel, optimizer) could potentially produce
results closer to the MATPOWER reference, but this was not tested because the task
specification explicitly requires solve_dc_pf."

The synthesis flags this as a human spot-check item: "Verify whether using
solve_pf(data, DCMPPowerModel, optimizer) would pass the DCPF verification." The test
design is measuring which default function the tool exposes for DCPF rather than the
tool's maximum DCPF fidelity. A production user working with a transformer-heavy network
would select DCMPPowerModel. The failure is a test design decision, not necessarily a
tool capability boundary.

Probe recommended: run solve_pf(data, DCMPPowerModel, optimizer) on the FNM network
and compare bus angles against the reference to determine whether the fail is
attributable to DCPPowerModel's simplified B-matrix choice or to deeper tool limitations.

**Cross-tool relevance:** none (specific to PowerModels' formulation split)
**Proposed action:** redesign_test

---

### pm-F05: ACPF convergence accepted without residual or iteration count due to API gap

**Category:** missing_verification | **Severity:** medium
**Tests:** A-2, A-4, C-5

compute_ac_pf returns only a Bool termination_status with no NR iteration count and no
convergence residual in the result dict. Both convergence_residual and
convergence_iterations are null in the A-2 and C-5 (SMALL) result headers.

The evaluator validates convergence indirectly: termination_status == true, and 100% of
PQ buses have Vm != 1.0 pu (differ from flat start). This indirect check is reasonable
but cannot distinguish genuine convergence from early termination within tolerance. The
protocol requires reporting both iteration count and residual; neither is structurally
available for the compute_ac_pf path due to NLsolve's callback architecture.

This is a documented tool limitation (not an evaluator error) but it means the pass and
qualified_pass results for A-2, A-4, and C-5 SMALL are accepted on weaker evidence
than the protocol intends. The Ipopt path (solve_ac_pf) would expose convergence
diagnostics but was used only for the failing MEDIUM tests.

**Cross-tool relevance:** none
**Proposed action:** add_verification

---

### pm-F06: A-12 awarded pass (not qualified_pass) despite three simultaneous stable workarounds

**Category:** scoring_inconsistency | **Severity:** medium
**Tests:** A-12, A-5

A-12 records status: pass with three simultaneous stable workarounds:
1. Solver switch: must use SCIP (not HiGHS or Ipopt) for MIQP due to ZeroOne constraints
2. Cyclic SoC: manual JuMP constraint injection required (not native to solve_mn_opf_strg)
3. Two-phase LMP extraction: SCIP cannot return LP duals; requires fix-and-price via HiGHS

All three are non-obvious. None are documented in the PowerModels quickguide or
solve_mn_opf_strg documentation. The synthesis calls this out as a human spot-check item.

By contrast, A-5 receives qualified_pass with a single blocking workaround. The
evaluation's workaround taxonomy defines blocking vs. stable but does not specify how
multiple simultaneous stable workarounds should affect status. Three concurrent
non-obvious workarounds on a MIQP storage formulation represent substantially more
friction than a single stable workaround, and the cumulative discovery cost for a new
user would likely exceed the discovery cost for some blocking workarounds on simpler
features.

**Cross-tool relevance:** likely — the treatment of cumulative stable workarounds
vs. single blocking workarounds may be inconsistent across tools.
**Proposed action:** adjust_scoring

---

### pm-F07: FNM ingestion suite tests MATPOWER fallback capability, not PowerModels PSS/E parsing

**Category:** infrastructure_friction | **Severity:** medium
**Tests:** G-FNM-1, G-FNM-2, G-FNM-3, G-FNM-4

The PSS/E v31 RAW parser crashes on the Case Identification header, so the entire FNM
ingestion suite was executed against the MATPOWER fallback file (fnm_main_island.m).
The fallback is a pre-cleaned main-island subset with significant record deficits vs.
the manifest: bus -8.1%, load -42.7%, gen -0.5%, branch -3.6%.

The consequences:
- G-FNM-2's 100% DCPF-critical field coverage measures MATPOWER PPC format coverage
  (5 record types: bus, load, gen, branch, shunt), not PowerModels' data model breadth
- G-FNM-1's qualified_pass measures MATPOWER .m loading, not PSS/E parsing
- The 8% ACPF-critical coverage finding reflects MATPOWER format limitations, not
  PowerModels' architecture
- The -42.7% load count deficit means the FNM power balance test is on a different
  (lighter) network than the reference

The PSS/E failure is estimated at 1-2 days to fix, but the FNM suite conclusions as
written characterize MATPOWER ingestion as the primary PowerModels data path for the
FNM, which may not reflect production use.

**Cross-tool relevance:** none (PowerModels-specific PSS/E parser failure)
**Proposed action:** add_test

---

### pm-F08: SCIP license classification conflict between F-3 (ZIB Academic) and F-8 (Apache 2.0)

**Category:** scoring_inconsistency | **Severity:** low
**Tests:** F-3, F-8

F-3 classifies SCIP_jll v0.2.1 / SCIP 8.0.0 as ZIB Academic License and recommends
excluding SCIP from commercial deployments. F-8 classifies the same artifact as
Apache 2.0 and upgrades its assessment from qualified_pass to pass, explicitly stating
"the prior assessment incorrectly identified SCIP as ZIB Academic."

Both tests reference the same Julia environment. The conflict is material because SCIP
is required for A-12 multi-period storage OPF (the only test requiring MIQP with
ZeroOne constraints). If SCIP carries the ZIB Academic restriction, the A-12 multi-period
storage result is not reproducible in commercial deployment and the supply chain
assessment changes. The synthesis calls this out for human resolution.

The F-8 evidence (SCIPversion() returning 8.0, GitHub confirming Apache-2.0 for SCIP
9.x, note that Apache-2.0 applies since v8.0) is more specific, but F-3's JLL artifact
LICENSE file reading is direct evidence that should take precedence if the artifact
itself carries the ZIB Academic text.

**Cross-tool relevance:** likely — other Julia-based tools may use SCIP via the same
SCIP_jll artifact and face the same ambiguity.
**Proposed action:** add_verification

---

### pm-F09: 39-bus network cycling guardrail is weak: only end-of-horizon shutdowns, no restarts

**Category:** network_insufficiency | **Severity:** low
**Tests:** A-5

The A-5 commitment schedule shows 3 generators decommitting in hours H22-H24 with
0 startup events: "Total shutdowns: 3. Total startups: 0 (generators only decommit
toward end of horizon, no recommitment needed within 24h)." The SCUC protocol requires
>= 2 generators cycling; 3 shutdowns meets the threshold but the cycling is economically
trivial -- generators shed at the end of a 24-hour window when there is no future
commitment obligation.

The 39-bus network's capacity/load ratio (7,367 MW / 6,254 MW = 1.18x) provides limited
economic incentive for mid-cycle unit commitment decisions. A more discriminating test
would show mid-cycle startups (generators coming online for a peak then returning to
offline status), which would exercise min_up and min_down constraints jointly in a
single run. The current result verifies that binary constraint logic is coded correctly
but does not demonstrate that it produces economically significant commitment decisions.

**Cross-tool relevance:** likely — other tools tested on the same 39-bus network face
the same network insufficiency for SCUC demonstration.
**Proposed action:** redesign_test

---

### pm-F10: GLPK convergence on MEDIUM DCOPF contradicts v9 timeout failure; no confirmed explanation

**Category:** extraordinary_claim | **Severity:** medium
**Tests:** C-3, C-7

C-3 reports GLPK solving the 10k-bus MEDIUM DC OPF in 61.86s. The result file notes
this contradicts the v9 evaluation where GLPK timed out at 300s: "the difference may
be due to JIT warm-up improving the model construction or solver configuration differences."
No definitive explanation is offered.

The most plausible explanation is that v10 linearizes 45.5% of quadratic generator costs
(1,130 of 2,485 generators), reducing the problem from a QP to an LP that GLPK can
handle. GLPK does not support QP (confirmed in F-8); if v9 attempted to solve quadratic
costs with GLPK, GLPK would have rejected the formulation entirely rather than timing
out. The discrepancy may be an artifact of different preprocessing between protocol
versions rather than GLPK performance improvement.

This matters for cross-tool comparisons: if GLPK performance is reported as 61.86s
based on a linearized LP while other tools solve the original QP, the solver comparison
is on different problem formulations.

Probe recommended: verify whether v9 applied the same quadratic cost linearization
before attempting GLPK, or whether v9 submitted a QP that GLPK rejected silently (which
would appear as a timeout rather than an explicit error).

**Cross-tool relevance:** none (PowerModels-specific v9 vs v10 protocol difference)
**Proposed action:** add_verification

---

### pm-F11: Architecture audit (B-6) is documentation-based with no runtime execution

**Category:** low_signal | **Severity:** low
**Tests:** B-6

B-6 records status: pass with wall_clock_seconds: null and loc: null. The test is a
static audit of the source tree structure, identifying the four-layer dispatch
architecture (public API / model lifecycle / formulation build / solver interface).
No code is executed and no runtime behavior is observed.

The finding -- that PowerModels has a clean four-layer architecture with Julia multiple
dispatch as the extension mechanism -- is accurate and useful context. However, the
result is not differentiated from what any evaluator could derive from reading the
source code, and it carries the same evidentiary weight as a documentation reading.
This pattern is likely consistent across all tools evaluated (B-6 is presumably an
identical audit for each tool) and produces confirmed low signal.

**Cross-tool relevance:** confirmed — B-6 is identical methodology for all tools.
**Proposed action:** redesign_test

---

### pm-F12: PTDF timing discrepancy: B-9 MEDIUM (106s) vs C-9 MEDIUM (7.55s) for identical API call

**Category:** extraordinary_claim | **Severity:** low
**Tests:** C-9

B-9 ran at MEDIUM scale (10k-bus, identical API call) in 106.44s total. C-9 ran the
same call in 7.55s total, attributed to JIT warm-up. The reported improvement is 14x
for make_basic_network (15.5s → 1.16s) and 15x for calc_basic_ptdf_matrix (35.5s →
2.37s). These are consistent with Julia's JIT behavior for first-invocation vs.
warm-REPL calls, but the magnitudes are at the upper end of typical JIT overhead.

The result also notes that the synthesis reports the warm PTDF time (2.37s) as the
MEDIUM PTDF benchmark, while the cold-start time (35.5s) would represent the user
experience in a fresh process. For scalability grading purposes, the warm-REPL time
is appropriate for repeated evaluation workflows, but single-invocation workflows
(typical in scripted market operations) would see the 35.5s figure.

Probe recommended: verify that the C-9 warm-up sequence (case39 solve before MEDIUM
PTDF) was applied consistently, and confirm whether the synthesis-reported PTDF time
(2.37s) or the cold-start time (35.5s) is the appropriate benchmark for the
scalability grade.

**Cross-tool relevance:** none (Julia JIT specific)
**Proposed action:** add_verification

---

### pm-F13: SCED test bypasses UC stage by design, making it an independent ED test

**Category:** test_design_gap | **Severity:** low
**Tests:** A-6

A-6 skips the SCUC stage and treats all generators as committed, reducing the SCED
test to a multi-period ED LP with ramp constraints. The result correctly documents this
as a "stable scope reduction" and awards qualified_pass. The workaround is clean and
the ED implementation via replicate + build_mn_opf + manual ramp constraint injection
is genuine PowerModels capability.

However, the rubric criterion for SCED includes commitment decisions as part of the
assessed capability. By bypassing the UC stage, the test grades the ED capability only,
which PowerModels handles well. Additionally, the "Security-Constrained" prefix in SCED
implies contingency constraints on dispatch; A-6 includes ramp constraints but not
N-1 contingency constraints on the dispatch schedule. The security component is absent.

This is likely a consistent pattern across tools with UC limitations (the test always
degrades to ED-only when UC is unavailable), reducing A-6's discriminative power to
measuring multi-period LP capability rather than SCED capability specifically.

**Cross-tool relevance:** likely — tools without native UC will all reduce A-6 to ED-only.
**Proposed action:** redesign_test

---

## Extraordinary Claims

### C-8: SCOPF MEDIUM awarded pass on non-converged Benders run

**Concern:** The protocol labels C-8 a "measurement test" to justify pass status
regardless of convergence. The run completed 1 of an unknown number of required
iterations; the contingency screening loop alone consumed 70% of the time budget at
8.3s/case for 50 contingencies. The resulting objective ($2,162,360/h) has only 8 of
17 binding contingency blocks enforced. A pass score implies the tool can do MEDIUM
SCOPF; a qualified_pass with "not converged within budget" better reflects the result.

**Evidence quality:** strong

A convergence check probe would run the same algorithm with a lighter contingency set
(top 10 branches instead of 50) to verify whether the algorithm converges within the
600s budget, and report the convergence iteration count and final security constraint
violation magnitude.

---

### A-9: SCOPF mechanism "demonstrated" on N-1 infeasible network

**Concern:** The qualified_pass rests on showing that the tool correctly reports
infeasibility for a network where no N-1 secure dispatch exists. The key question --
does Benders converge to a security-constrained optimum when one exists? -- is never
answered because the test network selection precludes a positive answer.

**Evidence quality:** moderate

A formulation audit probe would test the same SCOPF algorithm on the 39-bus network
with original (100% rated) thermal limits and a modified load profile that allows N-1
feasibility, documenting the number of Benders iterations to convergence and the
final security-constrained objective.

---

### G-FNM-3: DCPF hard-fail may be a test design constraint, not a tool limitation

**Concern:** The test requires solve_dc_pf (DCPPowerModel, simplified B-matrix) even
though DCMPPowerModel (full B-matrix, tap-aware) exists in PowerModels and the evaluator
specifically identifies it as a candidate fix. The 97.6% bus failure rate measures
the gap between DCPPowerModel's simplified formulation and MATPOWER's full B-matrix,
not PowerModels' maximum DCPF fidelity on transformer-heavy networks.

**Evidence quality:** strong

A formulation audit probe would run solve_pf(data, DCMPPowerModel, highs_opt) on the
FNM network and compare bus angle deviations against the same reference CSV, documenting
whether DCMPPowerModel achieves the 95% bus angle pass threshold that DCPPowerModel fails.

---

## Test Outcome Matrix

| Test ID | Status | Workaround | Key Issue |
|---------|--------|------------|-----------|
| G-1 | pass | — | — |
| G-2 | pass | — | — |
| G-3 | pass | — | — |
| A-1 | qualified_pass | stable | Branch flows require manual post-processing |
| A-2 | qualified_pass | stable | No NR residual/iterations exposed |
| A-3 | pass | — | — |
| A-4 | pass | — | Branch flows require stable workaround |
| A-5 | qualified_pass (blocking) | blocking | PowerModels not involved in UC formulation (pm-F01) |
| A-6 | qualified_pass | stable | UC stage bypassed; SCED reduces to ED-only (pm-F13) |
| A-9 | qualified_pass | stable | N-1 infeasible network; algorithm completes 1 iteration (pm-F03) |
| A-10 | qualified_pass | stable | Requires Ipopt, not HiGHS |
| A-11 | fail | blocking | No distributed slack formulation exists |
| A-12 | pass | stable (x3) | Three simultaneous non-obvious workarounds (pm-F06) |
| B-1 | pass | — | — |
| B-2 | qualified_pass | stable | No Graphs.jl integration |
| B-3 | pass | — | — |
| B-4 | pass | — | — |
| B-5 | pass | — | — |
| B-6 | pass | — | Documentation-based audit, no runtime (pm-F11) |
| B-8 | qualified_pass | stable | Distributed slack requires ~150 LOC custom OPF |
| B-9 | pass | — | — |
| C-1 | qualified_pass | stable | Branch flows require manual post-processing |
| C-2 | fail | blocking | ACPF diverges at MEDIUM; both NLsolve and Ipopt |
| C-3 | qualified_pass | stable | Cost linearization required; GLPK v9/v10 discrepancy (pm-F10) |
| C-4 | qualified_pass (blocking) | blocking | 300 LOC user-assembled MILP; PowerModels parses only (pm-F01) |
| C-5 (SMALL) | pass | — | — |
| C-5 (MEDIUM) | fail | blocking | Cascaded from C-2 |
| C-7 | qualified_pass | stable | SCIP dual extraction crash; GLPK timing discrepancy |
| C-8 | pass | stable | Non-converged Benders (1 iteration); should be qualified_pass (pm-F02) |
| C-9 | pass | — | Cold vs. warm JIT timing discrepancy (pm-F12) |
| C-10 | fail | blocking | Cascaded from A-11 |
| D-1 | qualified_pass | — | JIT overhead; API signature discovery issue |
| D-2 | qualified_pass | — | Core OPF documented; advanced types absent |
| D-3 | qualified_pass | — | 7/10 examples pass; 2 PSS/E header failures |
| D-4 | qualified_pass | — | INFEASIBLE OK; missing cost key cryptic |
| D-5 | informational | — | Mean 379 NBNCL |
| E-1 | informational | — | 5 releases / 24 months |
| E-2 | informational | — | 24 commits / 12 months |
| E-3 | fail | — | 82.9% single contributor; 100% reviewer concentration |
| E-4 | informational | — | LANL/DOE institutional backing |
| E-5 | informational | — | Median close time ~71.5 days |
| E-6 | informational | — | 93.93% coverage, CI on 3 OS |
| E-7 | informational | — | National-lab/academic adoption; no commercial ISO evidence |
| F-1 | pass | — | BSD 3-Clause (LANL) |
| F-2 | pass | — | 114 packages pinned |
| F-3 | qualified_pass | — | GLPK GPL v3; SCIP ZIB Academic (disputed, pm-F08) |
| F-4 | pass | — | All 35 JLL components have public source |
| F-5 | pass | — | Pure Julia to ccall boundary |
| F-6 | pass | — | Registry SHA verification |
| F-7 | pass | — | Julia depot + offline mode |
| F-8 | pass | — | SCIP license claim Apache 2.0 (contradicts F-3, pm-F08) |
| F-9 | qualified_pass | — | /stable/ links OK; no version pin guidance |
| G-FNM-1 | qualified_pass | — | MATPOWER fallback only; PSS/E parser fails (pm-F07) |
| G-FNM-2 | pass | — | 100% DCPF-critical coverage (MATPOWER format only) |
| G-FNM-3 | fail | — | DCPPowerModel simplified B-matrix; DCMPPowerModel not tested (pm-F04) |
| G-FNM-4 | informational | — | ACPF diverges on 27k-bus FNM |
| G-FNM-5 | informational | — | 39% native supplemental CSV |
| P2-1 | informational | — | PSS/E v33 only; v31 header crash |
| P2-2 | informational | — | PWL convex-only native; SOS2 absent |
| P2-3 | informational | — | Commitment injection ~40 LOC; ramp/reserve need JuMP extension |
