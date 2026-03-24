# pandapower — Sweep Findings (v10)

## Summary

The pandapower evaluation is thorough, well-evidenced, and self-consistent. All 60 result
files are present, timing measurements are marked as measured rather than estimated
throughout, and fail/pass determinations are accurate. The main quality issues fall into
two categories: protocol-design weaknesses that affect pandapower disproportionately due
to its narrow scope, and a small number of unverified claims in passing tests. The most
significant protocol problem is the C-SMALL gate design, which cascades a feature-absence
failure (SCUC) into 8 MEDIUM-tier scalability skips — for a tool that demonstrably
handles DCPF at 28K buses in 0.4 s. Two probe recommendations are made: one on A-3 branch
shadow prices (all 46 branches claimed binding, inconsistent with loading data) and one on
A-3 DC OPF optimality verification (convergence accepted from boolean flag only, with no
iteration count or residual reported by the PYPOWER solver).

---

## Finding Details

### pandapower-F01: C-SMALL gate design conflates feature absence with scale failure, muting 8 MEDIUM tests

**Category:** test_design_gap | **Severity:** high
**Tests:** C-4, C-1, C-2, C-3, C-5 (MEDIUM), C-7, C-8, C-9, C-10

The protocol's C-SMALL gate requires C-4 (SCUC on SMALL) to pass before unlocking all
MEDIUM-tier scalability tests. For pandapower, C-4 fails because SCUC is architecturally
absent — not because the tool struggles with scale. The result:

> "Skipped because Suite C SMALL gate failed (C-4 failed with blocked_by: A-5). The SMALL gate failure was a cascaded failure from A-5 (SCUC unsupported), not a scale-related failure."
> — C-1, C-2, C-3, C-5 MEDIUM (all)

This skips 8 MEDIUM tests covering DCPF, ACPF, DC OPF, solver swap, SCOPF, PTDF, and
distributed-slack OPF — the entire second layer of scalability evidence. Meanwhile, the
tool has demonstrable scale evidence from FNM Suite G:

> "FNM DCPF solved 28K buses in 0.4s"
> — synthesis.md

The gate design was presumably intended to catch scale failures early, not to penalize
tools that lack a specific optimization formulation. The practical effect is that any tool
without SCUC support has its scalability dimension assessed on at most 2 tests (C-4 fail
+ C-5 SMALL pass), regardless of how well it performs at scale for its supported feature
set.

**Cross-tool relevance:** confirmed — the gate design is in the shared protocol and will
affect any tool without SCUC (e.g., matpower, which also lacks native SCUC).
**Proposed action:** redesign_test — MEDIUM tests that do not depend on SCUC (C-1 DCPF,
C-2 ACPF, C-3 DC OPF, C-9 PTDF) should be independently runnable when C-4 fails due to
feature absence rather than scale failure. The gate should only cascade to SCUC-dependent
scalability tests.

---

### pandapower-F02: ACPF convergence residual not verifiable — protocol pass accepted without residual scalar

**Category:** missing_verification | **Severity:** medium
**Tests:** A-2, C-5

The A-2 pass condition requires the convergence residual to be "reported and below the
tool's stated tolerance." pandapower does not expose the final NR residual:

> "Convergence residual: below 1e-8 (tolerance_mva setting; exact value not extractable)"
> — A-2 result

The iteration count (4) is accessible only via `net._ppc["iterations"]` — a private
underscore-prefixed attribute. The convergence_residual frontmatter field is null in both
A-2 and C-5. The pass is accepted based on 100% of buses differing from the 1.0 pu flat
start, which demonstrates convergence indirectly but does not satisfy the protocol's
explicit residual requirement.

An additional complication: the tolerance_mva parameter has an unfixed unit bug (issue
\#2750) — documented but not treated as a qualification to the pass:

> "pandapower documents this parameter as MVA but internally compares against per-unit mismatches (known bug \#2750, unfixed in v3.4.0)."
> — A-2 result

**Cross-tool relevance:** likely — other tools with embedded solvers (e.g., matpower with
PYPOWER heritage) may also not expose residual scalars publicly.
**Proposed action:** add_verification — the protocol should explicitly specify that when a
tool does not expose a residual scalar, indirect evidence (voltage profile divergence + NR
iteration count from any accessible interface) is sufficient, with a required documentation
note. The tolerance_mva unit ambiguity should be flagged as a qualification.

---

### pandapower-F03: DC OPF branch shadow prices extracted from internal _ppc — scored as no-workaround

**Category:** misleading_result | **Severity:** medium
**Tests:** A-3

A-3 is a clean pass (workaround_class: null). The LMP extraction via `res_bus.lam_p` is
correctly no-workaround — it is a public, documented API. However, the branch shadow
prices required to demonstrate "at least 2 branches with non-zero shadow prices" are
extracted from:

> "Branch shadow prices: Extracted from net.\_ppc\['branch'\]\[:, 13:15\] (MU\_SF, MU\_ST columns)."
> — A-3 result

The result notes this requires "accessing the internal net._ppc structure" but still
scores the test as no-workaround on the grounds that the pass condition "only requires
LMP/shadow price extractability, which is satisfied by the public API." This interpretation
is technically defensible (LMPs are publicly accessible), but the branch shadow prices —
which are also part of the pass condition — require internal API access. The synthesis
separately documents this as an arch-quality concern (OPF duals discarded during result
extraction), but that finding doesn't feed back into the A-3 score.

**Cross-tool relevance:** none — specific to the PYPOWER-backed dual extraction pattern.
**Proposed action:** adjust_scoring — the A-3 pass condition references both LMPs and
branch shadow prices. If branch shadow prices require internal API access, the test should
be scored as qualified_pass/stable rather than clean pass, or the pass condition should be
amended to specify which dual values must be accessible via public API.

---

### pandapower-F04: Distributed slack tests on 39-bus TINY — A-11 pass condition untestable when feature is absent

**Category:** network_insufficiency | **Severity:** medium
**Tests:** A-11, B-8

A-11 correctly fails because distributed slack OPF is not supported. However, the test's
pass condition requires LMPs to "differ from single-slack results in a physically consistent
manner" — which is impossible to verify when the feature is absent. The test therefore
measures only API transparency (does the tool surface an error or silently absorb the
parameter?), not the LMP behavior the rubric intends.

pandapower's case is particularly instructive because rundcopp() silently absorbs
`distributed_slack=True` with zero effect:

> "LMPs are identical across all 39 buses. The distributed_slack=True kwarg is silently accepted by rundcopp() via **kwargs but has zero effect."
> — A-11 result

For tools that do support distributed slack, the TINY network with a single ext_grid
element is a minimal test case. B-8 (reference bus configuration) tests three slack
configurations on the same network, finding a maximum LMP shift of 8.58 $/MWh — a
meaningful difference, but with only 10 generators and a radial topology, it is unclear
whether the LMP shifts are "physically consistent" in the sense the rubric intends or
simply reflect the arithmetic of rerouting reference.

**Cross-tool relevance:** likely — any tool without distributed slack OPF will have the
same untestable pass condition.
**Proposed action:** add_test — A-11 should have a split pass condition: (a) for tools with
distributed slack, the existing LMP comparison test; (b) for tools without it, a scored
assessment of API transparency (does the tool explicitly indicate the feature is absent vs.
silently fail?).

---

### pandapower-F05: A-3 binding branch count anomalous — all 46 branches reported as shadow-price-nonzero

**Category:** missing_verification | **Severity:** high
**Tests:** A-3, A-9

A-3 reports every branch has a nonzero shadow price under 70% derating:

> "Binding branches: 46 of 46 | Lines > 95% loading: 7"
> — A-3 result

This is internally inconsistent. Only 7 branches are above 95% loading, but 46 of 46
are reported as having nonzero shadow prices. In a correctly solved DC OPF, a shadow price
is nonzero only when a constraint is binding (flow = limit). Having all 46 binding while
only 7 are near their limits suggests either (a) the threshold for "nonzero" was not
applied (interior-point solvers produce numerically small but nonzero duals even for
inactive constraints), or (b) the result is computed from column indices that include both
MU_SF and MU_ST and any nonzero in either direction counts.

No threshold was documented:

> "All 46 branches have non-zero shadow prices, far exceeding the 2-branch minimum threshold."
> — A-3 result

The test passes (minimum threshold is 2), so this discrepancy was not investigated further.
This is a moderate concern for cross-tool comparability: if other tools apply a threshold
(e.g., |dual| > 1e-4) while pandapower counts all numerically nonzero duals, the binding
branch counts will not be comparable.

**Cross-tool relevance:** likely — interior-point solver dual extraction without
magnitude thresholds is a common issue.
**Proposed action:** add_verification

**Probe recommended:** Yes
**Probe type:** convergence_check
**Probe description:** Re-run A-3, extract branch shadow prices, apply an explicit
threshold (|dual| > 1e-4 $/MWh), and compare count against branches with loading_percent
> 99%. Expected: ~7-15 branches binding, consistent with the 7 branches >95% loading.
If the threshold-filtered count drops below 2, the test result should be revised to
qualified_pass.

---

### pandapower-F06: G-FNM-3 failure classification as data_ingestion_error — single ingestion path tested

**Category:** misleading_result | **Severity:** medium
**Tests:** G-FNM-3

G-FNM-3 fails due to a localized cluster of ~101 buses with 14-21 degree angle deviations
and a maximum branch flow deviation of 596.6%. The result classifies this as
`data_ingestion_error` because the failing buses are not adjacent to non-unity-tap
transformers (0% transformer adjacency), ruling out a formulation difference:

> "Classification: data_ingestion_error (not formulation_difference)"
> — G-FNM-3 result

This classification is plausible but not verified. Only one ingestion path was tested
(MATPOWER PPC fallback). The classification confidence is limited — if the localized
anomaly persists across any alternative ingestion of the same network data, it would be
a solver characteristic rather than a path artifact. For pandapower, there is no
alternative path available (no native CSV import), so the single-path limitation is
inherent to the tool.

The practical consequence is that the hard-fail penalizes pandapower for an ingestion-path
limitation rather than a solver deficiency. The aggregate metrics are strong (99.64% buses
pass, 99.67% branches pass), and the failure is concentrated in a physically unusual
sub-region (zero-load zero-gen radial cluster with extreme angle swings).

**Cross-tool relevance:** none — specific to pandapower's MATPOWER-only ingestion path.
**Proposed action:** add_verification — tag FNM test results with path_type
(native_csv | matpower_fallback) so that data-ingestion-path artifacts can be distinguished
from tool capabilities in cross-tool synthesis.

---

### pandapower-F07: Six expressiveness failures are scope-boundary audits, not capability probes

**Category:** test_design_gap | **Severity:** medium
**Tests:** A-5, A-6, A-9, A-10, A-11, A-12

Five of the six expressiveness failures follow the same pattern: the test confirms by
API inspection that a feature (SCUC, SCOPF, lossy OPF, distributed slack OPF, multi-period
OPF) is architecturally absent from pandapower's design scope, documents the absence, and
records a blocking fail. The timing entries confirm no solver work was done:

> "Wall-clock: 0.79 s (import and capability check only — no solve attempted)" — A-5 result
>
> "Wall-clock: 0.78 s (includes lossless baseline OPF solve)" — A-10 result

These tests are accurate and correctly scored — pandapower genuinely cannot express these
formulations. The issue is at the protocol level: 60% of expressiveness tests for pandapower
measure what the tool is not, while 40% measure what it does. For a focused tool like
pandapower, this makes the expressiveness dimension score primarily a scope-boundary
assessment rather than a quality assessment of the expressiveness within scope.

The 4 tests pandapower passes (A-1, A-2, A-3, A-4) all pass cleanly with strong results.
The protocol does not distinguish between "tool is in scope and excellent" and "tool is
out of scope for 60% of tests." A broader tool that implements SCUC poorly would score
higher on expressiveness than pandapower, even if pandapower's AC/DC power flow is
technically superior.

**Cross-tool relevance:** confirmed — any tool with a specialized scope (e.g., matpower)
faces the same protocol imbalance.
**Proposed action:** add_test — add a secondary scoring axis for "expressiveness within
declared scope" to complement the absolute pass/fail count.

---

### pandapower-F08: A-3 DC OPF convergence accepted from boolean flag — no iteration count or residual

**Category:** extraordinary_claim | **Severity:** medium
**Tests:** A-3

A-3 reports DC OPF convergence in 0.10 s with objective $156,929, accepted via:

> "Solver iterations: not reported by PYPOWER DC OPF solver"
> — A-3 result

The PYPOWER interior-point solver does not expose iteration counts for the DC OPF
formulation. Convergence is verified only from the boolean `net.converged = True`. The
known case9 silent failure (D-3: "case9 DC OPF fails silently") demonstrates that this
boolean is not always reliable. However, the A-3 result includes the full dispatch table
and LMP values, which provide meaningful indirect verification: the LMP spread of
$76.05/MWh across a 39-bus network with differentiated costs and 70% branch derating is
physically plausible.

The dispatch table shows ext_grid (slack) dispatching at 1,342 MW — above its nominal
Pmax of 1,040 MW. This is noted in the table without comment. The ext_grid (external grid)
in pandapower is unconstrained by default and acts as a slack bus, so dispatch above Pmax
is the expected behavior when Pmax is a "nominal" rather than a hard limit — but this
interpretation is not verified in the result.

**Cross-tool relevance:** likely — PYPOWER-heritage solvers across multiple tools may
share this convergence-verification limitation.
**Proposed action:** add_verification

**Probe recommended:** Yes
**Probe type:** convergence_check
**Probe description:** For the A-3 result, verify dual feasibility: at each generator bus,
check that LMP approximately equals the generator's marginal cost when unconstrained, and
equals marginal cost ± branch shadow price when at a flow limit. This is a necessary
condition for a true DC OPF optimum and can be checked with 5-10 lines of arithmetic on
the existing result data.

---

### pandapower-F09: Gate tests are near-universal passes — minimal discriminative value

**Category:** low_signal | **Severity:** low
**Tests:** G-1, G-2, G-3

All three gate tests pass for pandapower with the standard MATPOWER .m file loader. The
tests verify bus/branch/gen counts match expected values and that no NaN or infinity values
are present. These are format-compatibility checks, not capability assessments:

> "Result: PASS — Actual counts: 39 buses / 46 branches / 10 generators. Load time: 0.085s."
> — G-1 result

For any tool that supports MATPOWER .m file input (all six evaluated tools do), these tests
are expected to pass. A failure would indicate a fundamental format-parsing bug, not a
meaningful capability gap. The load time (0.085 s for TINY) is measured but not used as a
comparative metric.

**Cross-tool relevance:** confirmed — the gate tests provide essentially no discriminative
information across all evaluated tools.
**Proposed action:** redesign_test — gate tests should verify minimum functional capability
(e.g., DCPF convergence + structured result output) rather than element count matching.

---

### pandapower-F10: B-9 uses internal \_ppc (clean pass) while B-1 uses \_ppc interception (fragile) — consistency gap

**Category:** scoring_inconsistency | **Severity:** medium
**Tests:** B-1, B-9

B-9 accesses `net._ppc` to get PYPOWER bus/branch arrays for PTDF computation and is
scored as a clean pass with no workaround:

> "Access to these arrays requires the internal net._ppc attribute (set after solving DCPF), but this is the standard pandapower pattern for accessing PYPOWER-level data."
> — B-9 result

B-1 accesses the same `_ppc` structure (plus the PYPOWER result dict) but requires
intercepting the solve pipeline and is scored as qualified_pass/fragile:

> "Durability: fragile — The workaround depends on the internal structure of _optimal_powerflow (undocumented private function), the PYPOWER opf_model.add_constraints interface, and the internal result dict structure."
> — B-1 result

The distinction is real (read-only post-solve access vs. mid-solve pipeline intercept), but
it is not made explicit in either result file. The scoring rationale should document where
the line falls between "standard pandapower internal access pattern" and "fragile
workaround." Without this documentation, the same `_ppc` access in a future test could be
scored inconsistently.

**Cross-tool relevance:** likely — any tool with a layered internal/external API distinction
will face this classification question.
**Proposed action:** adjust_scoring — explicitly define in the protocol or per-tool
evaluation notes what constitutes acceptable internal API access (post-solve read-only)
vs. fragile workaround (pipeline intercept or pre-result capture).

---

### pandapower-F11: B-3 100% DCPF convergence rate conflates solver success with topological completeness

**Category:** missing_verification | **Severity:** low
**Tests:** B-3

B-3 reports 3,276 contingency cases with 100% convergence. For DCPF (a direct linear
solve), "convergence" means the linear system was solved without a disconnection error.
With check_connectivity=True, disconnected cases raise an exception rather than producing
a solution. Of the 3,276 cases, 924 (28.2%) had load loss — meaning the network
disconnected in those cases, and the "solution" is for the remaining connected components
only.

> "Converged cases: 3,276 (100%) | Cases with load loss: 924 (28.2%)"
> — B-3 result

The 100% convergence figure is not incorrect, but it encompasses cases where the network
was fully or partially islanded. For ACPF-style solvers where convergence means iterative
NR convergence on the full connected network, the comparison is not direct.

**Cross-tool relevance:** confirmed — DCPF contingency sweep convergence rates are
structurally different from ACPF convergence rates and should not be compared across
tools without this qualification.
**Proposed action:** add_verification — protocol should distinguish DCPF "solve completed"
from ACPF "iterative convergence" in contingency sweep convergence reporting.

---

### pandapower-F12: A-11 FAIL category does not distinguish feature-absent from silent-mismatch

**Category:** test_design_gap | **Severity:** medium
**Tests:** A-11

A-11 fails because `rundcopp()` silently absorbs `distributed_slack=True` and produces
identical LMPs to the single-slack baseline. This is categorically different from a tool
that raises `NotImplementedError` (unambiguous absence) or prints a warning:

> "rundcopp() accepts arbitrary **kwargs and silently ignores distributed_slack=True without raising an error or warning. This could mislead users into thinking the feature is active."
> — A-11 result

The current protocol records a FAIL in both cases. However, the silent-mismatch failure
mode has accessibility implications beyond expressiveness: a user who passes
`distributed_slack=True` will believe the feature is active and may publish incorrect
results. This is arguably a higher-severity failure than "not implemented." The A-11 result
documents this accurately but the scoring does not reflect the severity difference.

**Cross-tool relevance:** likely — **kwargs-style parameter absorption without validation
is a common Python API design pattern that could affect other evaluated tools.
**Proposed action:** adjust_scoring — add a secondary observation category
"silent-mismatch" or flag in the FAIL record when a tool accepts a parameter with zero
effect and no warning. This should feed into the accessibility/error-quality dimension
scoring.

---

### pandapower-F13: FNM tests measure MATPOWER fallback path quality, not pandapower ingestion capability

**Category:** infrastructure_friction | **Severity:** medium
**Tests:** G-FNM-1, G-FNM-3, G-FNM-4

All FNM Suite G tests for pandapower use the MATPOWER PPC fallback path because
pandapower has no native intermediate CSV import capability. The FNM results therefore
reflect a two-stage process: (1) the MATPOWER fallback converts intermediate format to
PPC, and (2) pandapower ingests the PPC. Issues in either stage are attributed to
pandapower, even when they may be in the conversion step.

G-FNM-3's localized failure (101 buses with 14-21 degree deviations) is attributed to
"the MATPOWER PPC import path's handling of specific impedance details." G-FNM-4's ACPF
infeasibility is partly attributed to "PPC import path loses AC-critical transformer data."
Both attributions may be correct, but they cannot be confirmed without an alternative
ingestion path.

> "pandapower has no native CSV import capability. The MATPOWER PPC format is the standard programmatic entry point."
> — G-FNM-3 result

For cross-tool comparison, this means pandapower's FNM results are not directly comparable
to tools that use native CSV import — they are measuring different ingestion stacks.

**Cross-tool relevance:** none — specific to pandapower's lack of native FNM CSV import.
**Proposed action:** add_test — tag FNM results with `input_path` (native_csv |
matpower_fallback) and adjust cross-tool FNM comparisons to account for path differences.

---

## Extraordinary Claims

### A-3: All 46 branches have nonzero shadow prices with only 7 above 95% loading

**Concern:** Interior-point solvers produce numerically small but nonzero duals on
inactive constraints. The result reports 46/46 binding without specifying a magnitude
threshold, while the loading data shows only 7 branches above 95% utilization. These
are inconsistent: if shadow prices reflect binding constraints, at most ~7-15 branches
should have meaningful (threshold-filtered) duals.

**Evidence quality:** moderate — the loading_percent vs shadow-price count discrepancy
is documented in the result but not investigated.

This finding should be verified with a threshold-filtered dual extraction. If the count
drops below 2 with a reasonable threshold (|dual| > 1e-4 $/MWh), the A-3 pass condition
may not be satisfied at the level the rubric intends.

---

### A-3: DC OPF convergence verified by boolean flag only — no iteration count or residual

**Concern:** The PYPOWER DC OPF solver does not report iteration count or residual.
Convergence is accepted from `net.converged = True`. The known case9 silent failure (D-3)
demonstrates this flag is not always reliable. The dispatch table provides meaningful
indirect verification (plausible LMPs and objective), but dual-feasibility is not checked.

**Evidence quality:** moderate — the convergence evidence is indirect (dispatch table
plausibility) rather than direct (residual or optimality conditions).

The probe should check dual feasibility: at unconstrained generator buses, LMP should
equal the generator's marginal cost. This is checkable from the existing A-3 results
without rerunning anything.

---

## Test Outcome Matrix

| Test ID | Status | Workaround | Key Issue |
|---------|--------|------------|-----------|
| G-1 | pass | — | Low signal — format compatibility check only |
| G-2 | pass | — | Low signal — format compatibility check only |
| G-3 | pass | — | Low signal — format compatibility check only |
| A-1 | pass | — | Clean; timing measured |
| A-2 | pass | — | Convergence residual not extractable (null in frontmatter) |
| A-3 | pass | — | Branch shadow prices via internal _ppc; 46/46 binding anomaly |
| A-4 | pass | — | Clean |
| A-5 | fail | blocking | Correct scope-boundary assessment; no solve attempted |
| A-6 | fail | blocking | Cascaded from A-5; also independently infeasible |
| A-9 | fail | blocking | Correct scope-boundary assessment |
| A-10 | fail | blocking | Correct scope-boundary assessment |
| A-11 | fail | blocking | Silent **kwargs absorption — not just feature absent |
| A-12 | fail | blocking | PandaModels.jl bridge noted but requires Julia runtime |
| B-1 | qualified_pass | fragile | Monkey-patch of _optimal_powerflow; fragile classification well-justified |
| B-2 | pass | — | Clean; exemplary NetworkX bridge |
| B-3 | pass | — | 100% "convergence" conflates DCPF solve success with ACPF-style convergence |
| B-4 | pass | — | 240 solves; scenario variation spread is modest (3.6%) |
| B-5 | pass | — | Clean |
| B-6 | pass | — | Clean |
| B-8 | qualified_pass | stable | Verbose but public-API-only approach; classification appropriate |
| B-9 | pass | — | Uses internal _ppc but scored no-workaround; scoring inconsistency vs B-1 |
| C-1 | skip | C-SMALL-gate | Feature-absence cascade, not scale failure |
| C-2 | skip | C-SMALL-gate | Feature-absence cascade, not scale failure |
| C-3 | skip | C-SMALL-gate | Feature-absence cascade, not scale failure |
| C-4 | fail | blocking | Cascaded from A-5; correct |
| C-5 (SMALL) | pass | — | Clean 2K-bus ACPF; good scale evidence within scope |
| C-5 (MEDIUM) | skip | C-SMALL-gate | Feature-absence cascade, not scale failure |
| C-7 | skip | C-SMALL-gate | Feature-absence cascade, not scale failure |
| C-8 | skip | C-SMALL-gate | Feature-absence cascade, not scale failure |
| C-9 | skip | C-SMALL-gate | Feature-absence cascade, not scale failure |
| C-10 | skip | C-SMALL-gate | Feature-absence cascade, not scale failure |
| D-1 | informational | — | Correct use of informational status |
| D-2 | informational | — | 3/10 tests completable from docs; 7 require source inspection |
| D-3 | informational | — | 15/16 examples pass; case9 DC OPF silent failure noted |
| D-4 | informational | — | OPF diagnostics poor; silent **kwargs documented here and A-11 |
| D-5 | informational | — | LOC compact for supported features |
| E-1 | informational | — | 19 releases / 24 months; strong |
| E-2 | informational | — | 838 commits / 30 committers; activity pattern consistent with major release cycle |
| E-3 | informational | — | Bus factor 3; reviewer pool concentration noted |
| E-4 | informational | — | Dual Fraunhofer/Uni Kassel anchor; strong |
| E-5 | informational | — | 100% acknowledgment; 29d median; batch-triage pattern |
| E-6 | informational | — | 72% coverage; 28 CI jobs |
| E-7 | informational | — | Hessen DSO study is genuine production use; Grid2Op caveat appropriate |
| F-1 | informational | — | BSD license; clean |
| F-2 | informational | — | 37 packages; depth 3 |
| F-3 | informational | — | All permissive; 1 optional MPL-2.0 |
| F-4 | informational | — | All source-available |
| F-5 | informational | — | Full Python trace to spsolve |
| F-6 | informational | — | Sigstore provenance; strong |
| F-7 | informational | — | Fully air-gap installable |
| F-8 | informational | — | Self-contained PYPOWER solver |
| F-9 | informational | — | Unversioned install in docs; tutorials not in package |
| G-FNM-1 | pass | stable | MATPOWER fallback + zero RATE_A fix; infrastructure_friction applies |
| G-FNM-2 | pass | — | 100% DCPF-critical fields; 55.8% ACPF-critical |
| G-FNM-3 | fail | stable | 99.6% aggregate pass but 596.6% max deviation triggers hard-fail |
| G-FNM-4 | informational | stable | Infeasible at all relaxation levels; DCPF warm-start angles 536.9 deg max |
| G-FNM-5 | informational | — | 34% native; 43% external; lowest native coverage among evaluated tools |
| P2-1 | informational | — | PSS/E RAW not supported |
| P2-2 | informational | — | Piecewise-linear costs natively supported |
| P2-3 | informational | — | Commitment injection via in_service; low friction |
