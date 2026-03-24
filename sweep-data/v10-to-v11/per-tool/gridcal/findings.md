# gridcal — Sweep Findings (v10)

## Summary

The gridcal (VeraGridEngine 5.6.28) evaluation is well-documented, code-executed throughout,
and timing measurements are consistently marked as measured rather than estimated. The
primary sweep concerns are: (1) two network insufficiency problems where the test network
is too uncongested or too small to exercise the capability under test (SCOPF on MEDIUM,
SCUC cycling at SMALL); (2) a misleading qualified_pass on lossy DCOPF where the loss
approximation produces results indistinguishable from zero; (3) an unverified
formulation-difference classification for 326 branches with extreme flow deviations in the
FNM DCPF test; and (4) an unverified claim that DCOPF branch limits are enforced as hard
constraints given evidence of soft-constraint behavior. Three extraordinary claims are
flagged for probe: the soft-constraint nature of DCOPF thermal limits, the FNM branch flow
deviation classification, and unverified operational adoption by named utilities.

---

## Finding Details

### gridcal-F01: SCUC pass on TINY masks complete absence of inter-temporal commitment cycling at SMALL

**Category:** network_insufficiency | **Severity:** medium
**Tests:** A-5, C-4

A-5 (SCUC on 10-generator IEEE 39-bus) passes with 6 of 10 generators cycling, demonstrating
genuine unit commitment behavior under differentiated costs. At SMALL scale (C-4, 544
generators, ACTIVSg 2000-bus), no generator cycling is observed across 24 hours under either
solver — all 430 dispatchable generators remain committed for all 24 hours.

Two compounding factors produce this outcome: the TapPhaseControl enum bug forces a
sequential snapshot workaround that structurally cannot enforce inter-temporal constraints
(min up/down times, ramp rates), and the base-case generator costs in the SMALL network are
insufficiently differentiated to drive decommitment even in snapshot mode. The C-4 result
is scored qualified_pass with "stable" workaround classification, but the workaround
eliminates the distinguishing capability of SCUC (inter-temporal commitment decisions).

From C-4: *"No generator cycling observed. The SMALL network's base-case generator costs
are not sufficiently differentiated to drive decommitment... the workaround loses
inter-temporal UC coupling (min up/down times, ramp rates are not enforced across hours)."*

The test demonstrates 24 independent hourly OPF solves at SMALL scale, not scaled SCUC.
This finding is likely cross-tool — other tools' SCUC scale tests may face similar
cost-differentiation gaps in the SMALL network that prevent meaningful UC cycling.

**Cross-tool relevance:** likely
**Proposed action:** redesign_test — Augment SMALL network with differentiated costs
and evaluate whether true multi-period SCUC (with inter-temporal coupling) is tractable
within a time budget, rather than accepting snapshot workarounds as qualified passes.

---

### gridcal-F02: SCOPF on MEDIUM is vacuous — zero binding constraints, zero redispatch

**Category:** network_insufficiency | **Severity:** high
**Tests:** C-8

C-8 SCOPF on the 10,000-bus ACTIVSg network is scored pass with solve time 29.3s. However,
the SCOPF and base-case DCOPF produce results numerically identical to 1.49e-08 $/MWh:
no generators change dispatch above 1 MW, no branches become binding, and the maximum LMP
difference between DCOPF and SCOPF is essentially zero.

From C-8: *"This is consistent with the ACTIVSg10k network being uncongested (max loading
84.72%). Since no branches are near their limits in the base case, N-1 contingencies do not
create post-contingency violations that would require redispatch. The SCOPF correctly
determines that the base-case dispatch is already N-1 secure."*

The test validates that the SCOPF formulation runs to completion on a large network — it
does not measure whether the tool can produce security-driven redispatch at scale. The SMALL
SCOPF (C-8 SMALL) does produce meaningful results (up to 164 MW redispatch, LMP spread
$17–$19/MWh), but is not the scale-stress test. The MEDIUM SCOPF result is effectively a
timing-only measurement for an uncongested network.

This finding is confirmed cross-tool — the ACTIVSg10k network's lack of congestion at
base loading will produce the same vacuous SCOPF results for any tool that implements
SCOPF correctly. The protocol should specify a minimum congestion criterion (e.g., at
least 5 binding branches in base case, or at least one branch >90% loading) for SCOPF
scale tests.

**Cross-tool relevance:** confirmed
**Proposed action:** redesign_test — Add minimum congestion criterion for SCOPF scale
test networks. Apply additional derating (e.g., 50% branch capacity) before running
SCOPF at MEDIUM to ensure security constraints are active.

---

### gridcal-F03: Lossy DCOPF qualified_pass obscures a near-nonfunctional loss approximation

**Category:** misleading_result | **Severity:** medium
**Tests:** A-10

A-10 is scored qualified_pass because `add_losses_approximation=True` produces non-zero
losses and a non-zero LMP difference. However, the computed losses (0.055 MW, 0.0009% of
load) are orders of magnitude below the expected 0.5–3% range and far below the ACPF
reference (43.6 MW, 0.7% of load).

From A-10: *"The loss factor formula uses R * rate / V^2 where rate is the branch thermal
rating rather than the actual power flow. For the case39 network, where branch resistances
are very small (0.0002–0.007 pu) and nominal voltages are in the 100s of kV, this produces
negligible loss factors."*

The loss factor formula is structurally broken for the test case: using the thermal rating
rather than actual flow means the approximation systematically underestimates losses by a
factor of ~800x (0.0009% vs ~0.7%). LMP decomposition into energy/congestion/loss components
is also entirely absent. The qualified_pass implies a feature that works with caveats; the
actual situation is a formula producing results indistinguishable from lossless DCOPF for
any standard transmission network. A fail with "feature exists but produces negligible
results" would more accurately represent the finding.

**Cross-tool relevance:** none
**Proposed action:** adjust_scoring — Consider reclassifying A-10 as fail with a note
that the feature exists but the formula is broken for standard transmission parameters.
The 0.5–3% pass criterion should be enforced as a hard threshold.

---

### gridcal-F04: SCUC commitment inferred from dispatch power rather than binary commitment variable

**Category:** missing_verification | **Severity:** medium
**Tests:** A-5

The A-5 SCUC pass is based on a commitment schedule derived by thresholding generator power
output (`gen_power > 0.1` MW) rather than extracting a binary commitment variable from the
MILP solution. The MIP gap is explicitly noted as not directly extractable from the results
object: *"The MIP gap is not directly extractable from the OptimalPowerFlowTimeSeriesResults
object. HiGHS uses a default MIP gap tolerance of 1%."*

This creates an ambiguity: if GridCal is solving an LP relaxation of the MILP (or if the
MILP binary variables are not properly exposed in the results), the dispatch would appear
binary-like for most generators (due to box constraints and load balance), but with no
guarantee of true integrality. The pass condition requires verifying that the formulation
is a genuine MILP with binary commitment variables — this was not confirmed by extracting
binary solution values. A probe should verify whether `OpfDispatchMode.UnitCommitment`
introduces actual binary variables and that the HiGHS solver is invoked in MILP mode.

**Cross-tool relevance:** likely — other Python tools may have similar result object
designs that do not expose MIP integrality certificates.
**Proposed action:** add_verification — Protocol should require reporting at least one
of: (a) MIP gap from solver output, (b) binary variable values from solution, (c) solver
log confirmation of MILP solve.

---

### gridcal-F05: FNM DCPF qualified_pass contains 326 branches with deviations up to 562,955% attributed as formulation difference without independent validation

**Category:** misleading_result | **Severity:** medium
**Tests:** G-FNM-3

G-FNM-3 triggers the hard fail condition (max branch deviation > 50%) but is classified
qualified_pass via a "formulation_difference" classification. The classification rests on
the observation that 88.7% of the 326 failing branches are adjacent to transformer buses,
which is attributed to GridCal's simplified B-matrix omitting transformer tap ratio
corrections.

However, four of the five top-deviating branches are labeled "Line" (not transformer) in
the result table:

| Branch | Type | GridCal (MW) | Reference (MW) | Dev% |
|--------|------|-------------|----------------|------|
| 1668→88630 | Line | 111,582 | -19.82 | 562,955% |
| 21476→84022 | Line | -68,017 | 12.57 | 541,075% |
| 72100→73053 | Line | -13,365 | 3.23 | 413,787% |
| 1635→92191 | Line | -352,878 | 109.50 | 322,365% |

Flows on the order of 100,000–350,000 MW on nominal transmission lines are physically
implausible regardless of formulation differences. The "transformer-adjacent" criterion
classifies a branch as affected if either endpoint appears in the transformer terminal bus
set — but this could make many line branches "adjacent" in a highly-meshed network. The
classification was made by inference, not by comparing B-matrix entries for those specific
branches. If these deviations reflect a data ingestion error (e.g., incorrect per-unit
conversion for tap-adjacent bus admittances), the qualified_pass understates a genuine
correctness failure.

**Cross-tool relevance:** none
**Proposed action:** add_verification — A probe should compare the GridCal B-matrix
entries for the top-5 deviating branches against the MATPOWER reference B-matrix to
confirm whether the deviation is formulation-level (different tap handling) or computation-
level (numerical error or incorrect data ingestion for those branches).

---

### gridcal-F06: DCOPF shows 112% branch overload on a test claiming converged=True — soft constraint not disclosed in pass determination

**Category:** extraordinary_claim | **Severity:** high
**Tests:** A-3

A-3 passes DCOPF with 7 binding branches and meaningful LMP spread ($5–$84/MWh), but branch
2_3_1 shows 112% loading against the derated limit. The result notes: *"This may indicate
the PTDF-based formulation uses soft constraints or penalty functions rather than hard limits
on some branches."*

The D-4 error quality test confirms that when all branch ratings are set to zero, GridCal
treats them as soft constraints via overload slack variables and reports converged=True.
This establishes that at least some branch thermal limits are enforced as soft constraints.
If the DCOPF formulation systematically uses soft constraints, then all thermal limit
enforcement in A-3, A-9, C-3, C-8 is approximate — the tool may be solving a penalized
dispatch problem rather than a hard-constrained DCOPF. This has material implications for
market applications where hard thermal limits are a legal requirement.

The pass scoring for A-3 does not address whether the 112% overload is a soft-constraint
design choice (acceptable with disclosure) or a solver infeasibility being suppressed
(unacceptable). The formulation should be audited to determine whether branch limits are
hard inequality constraints or soft penalty terms in GridCal's PTDF-based OPF.

**Cross-tool relevance:** none
**Proposed action:** add_verification — Probe should inspect the `linear_opf_ts.py`
formulation to determine whether branch flow limits are modeled as hard LP constraints
(`flow <= limit`) or soft penalty terms (`flow <= limit + slack; min slack`). If soft,
the penalty coefficient should be reported and the implications for market dispatch
accuracy should be noted in all DCOPF test results.

---

### gridcal-F07: Error quality test design conflates soft-constraint behavior with infeasibility detection failure

**Category:** test_design_gap | **Severity:** medium
**Tests:** D-4

D-4 test (a) sets all branch ratings to zero and expects infeasibility detection. The test
concludes "Error quality grade: Poor" because the tool reports converged=True. However,
GridCal's DCOPF uses overload slack variables — the zero-rated-branch problem has a feasible
LP solution that includes nonzero slacks. From D-4: *"treats zero-rated branches as soft
constraints via the overload slack variables and produces a feasible dispatch that violates
all branch limits."*

A tool using soft constraints is behaving correctly (per its own formulation design) when
it finds a feasible solution to a soft-constrained problem. The test conflates two questions:
(1) does the tool enforce branch limits as hard constraints, and (2) does the tool report
solver-level infeasibility when the LP is genuinely infeasible (no feasible dispatch to
meet load balance). A genuine infeasibility test would set load higher than total generation
capacity, not zero branch ratings which a soft-constraint formulation will always handle.
The "poor" error quality rating may be unfair to a deliberately soft-constraint design.

**Cross-tool relevance:** likely — any tool using soft constraints on branch limits will
fail this test by design.
**Proposed action:** redesign_test — Replace the zero-branch-rating infeasibility test
with a load-exceeds-generation-capacity test that produces genuine LP infeasibility.
Add a separate disclosure test: does the tool document whether branch limits are hard
or soft constraints?

---

### gridcal-F08: FNM ingestion gate failure stems from PSS/e v31 format mismatch — MATPOWER fallback masks the architectural gap

**Category:** infrastructure_friction | **Severity:** medium
**Tests:** G-FNM-1, G-FNM-3, G-FNM-4

G-FNM-1 fails because GridCal's PSS/e parser is hardcoded to v35 field counts and v31
(the FNM format) is absent from the supported versions list. The error is explicit:
*"Exception: PSSe 35 load data came with 1 elements and 18 or 17 were expected."*

However, P2-1 characterizes this as a "medium effort" fix: *"The parser architecture
already threads a version parameter to device-level parsers. The fix requires auditing
each device parser to accept the correct field counts for v29-v34 formats — mechanical
but tedious."*

The G-FNM-1 fail is therefore format-version support, not architectural incapability.
The tool supports PSS/e ingestion in principle (v35 works). G-FNM-3 and G-FNM-4 then
run on a MATPOWER fallback that loses area/zone metadata and aggregates multiple loads
per bus (8,624 vs 15,062 loads). The FNM suite results characterize a network loaded via
a degraded representation, yet G-FNM-3/4 results are attributed to the tool's power flow
capability rather than the fallback path's limitations. The protocol should distinguish
between format version gaps (engineering effort) and architectural incapability.

**Cross-tool relevance:** likely — other tools may also have PSS/e version-specific
parser gaps that cause FNM ingestion to fall back to MATPOWER.
**Proposed action:** add_test — Add a separate test classifying PSS/e version support
range (which versions does the parser handle?) distinct from the CSV-format ingestion
gate. This would allow the evaluation to credit tools for supporting PSS/e v33+ without
penalizing them as heavily for v31 gaps.

---

### gridcal-F09: ACPF false convergence pathway identified in G-FNM-4 but not tested in the D-4 error quality assessment

**Category:** missing_verification | **Severity:** low
**Tests:** G-FNM-4

G-FNM-4 identifies that `retry_with_other_methods=True` causes false convergence:
*"When retry_with_other_methods=True, the solver reports converged=True after 1 iteration
with a residual of 582. This was diagnosed as false convergence — the retry mechanism
falls back to a method that terminates early without achieving actual convergence."*

The D-4 error quality test does not test this pathway. D-4 uses manually introduced errors
(infeasible OPF, zero costs, no slack bus) but does not test whether the ACPF retry
mechanism correctly reports non-convergence. The false convergence mode (retry reports
success despite residual 582) is a distinct, unscored error quality failure that affects
the accessibility dimension. It should be incorporated into the D-4 error quality rating
or flagged as an untested failure mode.

**Cross-tool relevance:** likely — retry mechanisms in other tools may have similar
premature termination behaviors.
**Proposed action:** add_test — Add a D-4 subtest for ACPF retry false convergence:
set an impossible initial condition and verify that retry_with_other_methods does not
report success without achieving the convergence tolerance.

---

### gridcal-F10: Single TapPhaseControl bug produces two qualified_pass scores for B-4 and C-4

**Category:** scoring_inconsistency | **Severity:** low
**Tests:** B-4, C-4

B-4 (stochastic scenario DCOPF) and C-4 (SCUC at SMALL) both encounter the same
TapPhaseControl enum bug in VeraGridEngine 5.6.28 and both apply the identical sequential
snapshot workaround. The bug is documented identically: *"ValueError: 0 is not a valid
TapPhaseControl"* on networks with transformers when using time-indexed compilation.

The two qualified_pass scores arising from a single bug could be collapsed to a single
finding with two affected test IDs. Currently the scoring implies two distinct capability
limitations with stable workarounds, when in fact a single version-specific bug affects
both. If the bug were fixed (as may be the case in v5.6.34, which was not evaluated),
both tests might pass natively. The evaluation does not flag this correlation, which
could influence how the maturity dimension is scored (a single known bug vs. two
independent capability gaps).

**Cross-tool relevance:** none
**Proposed action:** adjust_scoring — Note in the evaluation that B-4 and C-4
qualified_pass outcomes share the same root cause. Consider whether fixing the
TapPhaseControl bug would make both tests pass, which would elevate the extensibility
and scalability scores.

---

### gridcal-F11: Operational adoption claims by named utilities are unverified

**Category:** extraordinary_claim | **Severity:** medium
**Tests:** E-7

E-7 reports that GridCal claims operational use at Redeia (Spanish TSO), Schneider Electric,
and GE Vernova. These claims appear in the project's own research-context.md documentation.
From E-7: *"direct verification of these claims from public sources is limited — the evidence
comes primarily from the project's own research context documentation and presentations."*

The only independently verifiable external adoption signal is 52 commits from two Navitasoft
developers. The eRoots website does not list clients publicly. These claims materially affect
the maturity narrative: if verified, they would substantially offset the bus-factor-1 and
zero-CI-testing concerns; if unverifiable, the maturity grade may be too lenient. The
synthesis acknowledges this explicitly (Section 5: "Claims of Redeia, Schneider Electric,
GE Vernova usage are unverified from public sources") but the maturity grade rationale does
not account for the unverified status.

**Cross-tool relevance:** none
**Proposed action:** add_verification — Probe should search for public references:
case studies, conference presentations, regulatory filings, or press releases from Redeia,
Schneider Electric, or GE Vernova citing GridCal/VeraGrid. The LF Energy landscape
record (mentioned in E-7) may contain verifiable information.

---

### gridcal-F12: Gate ingestion tests are unanimous pass across all tools — low discriminative value

**Category:** low_signal | **Severity:** low
**Tests:** G-1, G-2, G-3

The three gate tests (G-1/2/3) verify MATPOWER .m file loading at TINY, SMALL, and MEDIUM
scale. All tools in the evaluation passed these tests. The tests measure a table-stakes
prerequisite (MATPOWER file parsing) that does not differentiate tools. Including them in
the total test count inflates the apparent pass rate for all tools equally without adding
insight. The gate status should be recorded as a binary pass/fail gate criterion rather
than scored tests contributing to capability assessment.

**Cross-tool relevance:** confirmed — all tools passed.
**Proposed action:** remove_test — Remove G-1/2/3 from the test outcome count.
Retain them as a binary gate check reported separately from capability test results.

---

### gridcal-F13: SCOPF convergence unverified — no optimality gap or residual reported for A-9 or C-8

**Category:** missing_verification | **Severity:** medium
**Tests:** A-9, C-8

Both A-9 (SCOPF TINY) and C-8 (SCOPF MEDIUM) report pass with no convergence residual or
optimality gap. The YAML frontmatter for both results shows `convergence_residual: null`
and `convergence_iterations: null`. SCOPF is an LP formulation in GridCal — the convergence
check should include LP optimality (dual feasibility, primal feasibility, and duality gap)
rather than just the `converged` flag.

For C-8 specifically, the near-identical results between DCOPF and SCOPF (differences of
~1e-8) are consistent with a correctly solved LP but also consistent with early termination
on a trivially feasible incumbent. The 29.3s solve time for a 10,000-bus LP with 50
contingency constraints is plausible but not benchmarked against theoretical expectations.
An optimality gap < 1e-6 should be confirmed via solver output or residual reporting.

**Cross-tool relevance:** likely — other tools' SCOPF tests may also lack optimality
gap reporting.
**Proposed action:** add_verification — Protocol should require extracting LP dual
feasibility and primal feasibility metrics (or MIP gap for MILP formulations) from
solver output for all OPF-class tests.

---

## Extraordinary Claims

### A-3: DCOPF passes with a branch at 112% loading — soft constraint status unresolved

**Concern:** The DCOPF formulation may use soft constraints (overload slack variables)
rather than hard branch thermal limits. If confirmed, all DCOPF/SCOPF/SCUC results in
the evaluation reflect penalized dispatch that allows thermal violations, which has direct
consequences for market dispatch accuracy. The D-4 test confirms soft-constraint behavior
for zero-rated branches. Whether the base DCOPF formulation enforces any hard thermal
limits is unresolved.
**Evidence quality:** moderate — D-4 confirms soft constraints exist; A-3 observes a
violation in practice. The exact formulation structure requires source code inspection.
**Probe type:** formulation_audit — Inspect `linear_opf_ts.py` branch flow constraint
construction to determine whether `flow[i] <= rating[i]` is a hard inequality or
`flow[i] <= rating[i] + slack[i]` with a penalty.

---

### G-FNM-3: 326 branches with deviations up to 562,955% classified as formulation difference without B-matrix inspection

**Concern:** The top-5 deviating branches include four labeled "Line" with physically
implausible flows (up to 352,878 MW). The "formulation_difference" classification rests
on the transformer-adjacency heuristic, not on direct inspection of the B-matrix entries
for those branches. Flows 3-6 orders of magnitude above reference values on line-type
elements suggest a possible data ingestion error or incorrect per-unit scaling that would
invalidate the qualified_pass.
**Evidence quality:** weak — the result pattern is consistent with the stated hypothesis
but also with alternative explanations involving data ingestion errors.
**Probe type:** formulation_audit — Extract GridCal's B-matrix entries for the top-5
deviating branches and compare against MATPOWER's `makeBdc()` output for the same branches.

---

### E-7: Operational adoption by Redeia, Schneider Electric, GE Vernova — sourced from project's own documentation

**Concern:** These are high-credibility claims for a tool with bus factor 1 and no
automated CI testing. If accurate, they substantially mitigate maturity concerns. If
they cannot be independently verified, the maturity grade narrative may require revision.
**Evidence quality:** weak — claims originate from project's own research-context.md;
no public third-party references found.
**Probe type:** claim_verification — Search for public references: conference presentations,
case studies, press releases, or regulatory documents citing GridCal/VeraGrid by Redeia,
Schneider Electric, or GE Vernova. Check the LF Energy landscape record for corroboration.

---

## Test Outcome Matrix

| Test ID | Status | Workaround | Key Issue |
|---------|--------|------------|-----------|
| G-1 | pass | — | Low signal: all tools pass |
| G-2 | pass | — | Low signal: all tools pass |
| G-3 | pass | — | Low signal: all tools pass |
| A-1 | pass | — | — |
| A-2 | pass | — | — |
| A-3 | pass | — | 112% branch overload; soft constraint status unverified |
| A-4 | pass | — | — |
| A-5 | pass | — | MIP gap not extractable; binary commitment not verified |
| A-6 | pass | stable | Profile manipulation workaround, documented |
| A-9 | pass | — | No optimality gap reported |
| A-10 | qualified_pass | — | Loss approximation produces 0.0009% of load; near-zero signal |
| A-11 | fail | blocking | distributed_slack hardcoded False in OPF formulation |
| A-12 | fail | blocking | Battery energy balance sign error in linear_opf_ts.py |
| B-1 | qualified_pass | fragile | Monkey-patch on internal constraint naming; depends on 3 internal naming conventions |
| B-2 | pass | — | — |
| B-3 | pass | — | — |
| B-4 | qualified_pass | stable | TapPhaseControl enum bug; same root cause as C-4 |
| B-5 | pass | — | — |
| B-6 | informational | — | Monolithic OPF (3146 LOC); no hook points |
| B-8 | pass | — | — |
| B-9 | pass | — | — |
| C-1 | pass | — | — |
| C-2 | pass | — | — |
| C-3 | pass | stable | GLPK absent; SCIP substituted |
| C-4 | qualified_pass | stable | TapPhaseControl bug + monolithic MILP intractable; zero UC cycling |
| C-5 (SMALL) | pass | — | — |
| C-5 (MEDIUM) | pass | — | — |
| C-7 | pass | stable | GLPK absent; SCIP substituted |
| C-8 (SMALL) | pass | — | — |
| C-8 (MEDIUM) | pass | — | Uncongested network; zero SCOPF redispatch; timing measurement only |
| C-9 | pass | — | — |
| C-10 | fail | blocking | Cascaded from A-11 |
| D-1 | informational | — | Fast install; clean first-solve pattern |
| D-2 | informational | — | ReadTheDocs 6 versions behind; 8/10 tests require source reading |
| D-3 | informational | — | All tutorials use deprecated GridCal.Engine imports |
| D-4 | informational | — | OPF reports converged=True on infeasible; test design gap for zero-rate test |
| D-5 | informational | — | Median 183 NBNC LOC |
| E-1 | informational | — | 209 releases/24mo; 28 of 209 with GitHub tags |
| E-2 | informational | — | ~2,357 commits; 8 named contributors in last 12mo |
| E-3 | informational | — | Bus factor 1; 0 of 30 PRs had reviewers |
| E-4 | informational | — | eRoots commercial backing |
| E-5 | informational | — | Median 115 days to close issues; batch-closing pattern |
| E-6 | informational | — | 125 test files; zero run in CI; pylint targets Python 3.8-3.10 |
| E-7 | informational | — | Adoption claims unverified from public sources |
| F-1 | pass | — | MPL-2.0 core |
| F-2 | pass | — | 62 deps; heavy but within gate threshold |
| F-3 | pass | — | 2 LGPL transitive deps (chardet, moocore) |
| F-4 | pass | — | Pure Python core |
| F-5 | pass | — | DCPF path fully traceable |
| F-6 | pass | — | No signing; 28/66 PyPI releases have GitHub tags |
| F-7 | pass | — | ~500-700 MB air-gap bundle |
| F-8 | pass | — | HiGHS bundled; no commercial solver required |
| F-9 | pass | — | Unpinned deps in eval project; no lock file |
| G-FNM-1 | fail | — | PSS/e v31 unsupported; no CSV network import |
| G-FNM-2 | informational | — | Skipped (blocked by G-FNM-1) |
| G-FNM-3 | qualified_pass | — | 326 branches at up to 562,955% deviation; formulation_difference classification unverified |
| G-FNM-4 | informational | — | ACPF infeasible on 27,862-bus FNM; false convergence identified in retry mode |
| G-FNM-5 | informational | — | 83% native contingency; 0% native interface/flowgate model |
| P2-1 | informational | — | PSS/e v31 gap: medium effort to fix |
| P2-2 | informational | — | Piecewise linear costs: not assessed in this sweep |
| P2-3 | informational | — | Commitment injection: not assessed in this sweep |
