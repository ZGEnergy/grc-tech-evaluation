# powersimulations — Sweep Findings (v10)

## Summary

The PowerSimulations.jl evaluation is evidence-rich and methodologically sound. All
timing figures are flagged as measured; code outputs are captured with concrete numerical
results. The primary sweep concerns are: (1) two qualified_pass results that mask
fundamentally relaxed or partially failed problems (C-3 loses branch flow limits, A-12
fails its BESS arbitrage behavioral condition); (2) ACPF convergence accepted without
residuals at any scale, including a 10K-bus case where the solver logged a convergence
warning but still returned results; (3) a single-threaded SCUC timing measurement on a
32-core machine that is likely 20-30x slower than production-representative performance.
Three probes are recommended: convergence verification for A-2/C-2, LMP unit-conversion
verification for A-3, and multi-threaded timing for C-4.

---

## Finding Details

### powersimulations-F01: DCOPF qualified_pass on MEDIUM masks a fundamentally relaxed problem

**Category:** misleading_result | **Severity:** high
**Tests:** C-3

The C-3 MEDIUM DCOPF qualified_pass is supported by real solver runs with consistent
objectives across HiGHS ($3,659,662.46) and GLPK ($3,659,662.46). However, workaround 4
of the five stacked workarounds removes all branch flow limit constraints:
`StaticBranchUnbounded replaces StaticBranch` because "branch flow limit constraints
cause numerical infeasibility at 10K scale (basis matrix condition number > 10^15)."
Without flow limits, the problem reduces to unconstrained economic dispatch with DC
network balance constraints — the network is present but congestion is absent. This
is a different problem than a network-constrained DCOPF, which is what C-3 is designed
to assess.

The result file notes that LMP extraction failed with StaticBranchUnbounded, which is
consistent with an unconstrained problem: "LMPs should be uniform on ACTIVSg10k (no
binding branch constraints at ~84% max loading)." This is correct reasoning, but it also
means the tool cannot produce LMPs at MEDIUM scale — a significant capability gap that
the qualified_pass status does not surface.

The grading standard should distinguish between "qualified_pass with minor caveats" and
"qualified_pass where a fundamental constraint class is absent from the problem." The
latter is closer to a fail on the congestion-enforcement criterion.

**Cross-tool relevance:** likely — other tools may face similar numerical conditioning
issues with large LP constraint matrices at 10K bus scale.
**Proposed action:** adjust_scoring

---

### powersimulations-F02: ACPF convergence accepted without residual or iteration count

**Category:** missing_verification | **Severity:** high
**Tests:** A-2, C-2

Neither A-2 (TINY ACPF) nor C-2 (MEDIUM ACPF) can report Newton-Raphson iteration count
or convergence residual — PowerFlows.jl v0.9.0 does not expose these in its public API.
Both results infer convergence from non-flat voltage profiles (100% of buses with non-unity
Vm in A-2; 84% in C-2).

The protocol requires: "Convergence residual must be reported and below the tool's stated
tolerance. Number of NR iterations must be reported." A-2 explicitly qualifies the pass on
these grounds. C-2 does not mention the convergence residual gap in its status.

More seriously, the C-2 MEDIUM result documents: "The warm-start NR solver on the first
call logged a convergence warning (NewtonRaphsonACPowerFlow solver failed to converge) but
still returned results." This is a case where the solver itself flagged non-convergence but
the results were accepted and the second call treated as validated. The possibility that
the 10K-bus ACPF result is a partially-converged solution is not ruled out by voltage
profile inspection alone.

A probe could verify ACPF quality by checking active power balance residual (sum of
mismatches across all buses) and comparing against a reference ACPF solution on case39
from a tool that exposes residuals.

**Cross-tool relevance:** none (PowerFlows.jl-specific API limitation)
**Proposed action:** add_verification

---

### powersimulations-F03: SCOPF 17.7% cost increase claim based on only 7 of 34 contingencies

**Category:** extraordinary_claim | **Severity:** medium
**Tests:** A-9

The A-9 SCOPF result asserts a 17.7% cost premium for N-1 security on the 39-bus network.
The measurement is real — the solve completes optimally, and the dispatch shift from nuclear
to gas CC is economically coherent. However, the contingency set is severely pruned: 27 of
34 line contingencies are eliminated because they produce near-radial redistribution
(|LODF| >= 0.95). The 7 applied contingencies add 288 constraints to the base DCOPF.

The 17.7% cost premium reflects security margins against this specific 7-contingency subset.
If the pass/fail filter were relaxed (e.g., |LODF| < 0.99 instead of 0.95), more
contingencies would bind and the cost premium would likely change. The cost-increase
direction is confirmed but the magnitude is contingency-set dependent, which is not
documented in the result.

This finding has cross-tool relevance because all tools will face the same near-radial
topology issue on case39, producing comparably small effective N-1 sets.

**Cross-tool relevance:** confirmed
**Proposed action:** add_verification

---

### powersimulations-F04: 39-bus network is too radially connected for meaningful SCOPF evaluation

**Category:** network_insufficiency | **Severity:** medium
**Tests:** A-9

The protocol specifies "all 46 branches as contingency set" for SCOPF on TINY. In practice,
79% of branch contingencies (27/34 lines) are immediately infeasible on the 39-bus topology
due to near-radial redistribution. The effective test is N-7 SCOPF, not N-46. A tool that
implements SCOPF through brute-force enumeration (like the manual LODF approach used here)
and a tool with built-in intelligent contingency screening would both appear equivalent on
this network — both would filter to approximately 7 effective contingencies.

A more meshed reference network at the SMALL tier (2K-bus, 3206 branches) would produce
meaningful N-50 or N-100 SCOPF tests where contingency screening methodology matters.
The SCOPF behavioral signal on case39 cannot distinguish between "excellent SCOPF with
screening" and "basic LODF enumeration with the same filter."

**Cross-tool relevance:** confirmed — this affects all tools evaluated on A-9.
**Proposed action:** redesign_test

---

### powersimulations-F05: A-12 qualified_pass masks explicit BESS arbitrage condition failure

**Category:** misleading_result | **Severity:** medium
**Tests:** A-12

The A-12 result explicitly reports: "Condition 2: BESS Arbitrage (FAIL). Discharge LMP is
NOT greater than charge LMP." The protocol pass condition requires: "Mean LMP at the BESS
bus during discharge hours must exceed mean LMP during charge hours." This condition failed.

The qualified_pass is justified in the result on the grounds that multi-period DCOPF itself
works (Conditions 1 and 3 pass), and the BESS arbitrage failure stems from using linear
costs (required because HiGHS fails on multi-period QP). This is a reasonable explanation
of causality but does not change the fact that the behavioral condition failed.

The root cause chain is: HiGHS MIQP limitation → forced linear costs → LP degeneracy →
non-unique LMPs → BESS does not arbitrage. This represents a tool capability limitation
(multi-period QP with HiGHS) that produces a behavioral test failure. The current status
of qualified_pass may over-represent capability.

**Cross-tool relevance:** likely — other tools using HiGHS for multi-period LP face the
same LP degeneracy with linear costs for storage arbitrage tests.
**Proposed action:** adjust_scoring

---

### powersimulations-F06: A-10 fail is solver-ecosystem mismatch, not an absent formulation

**Category:** infrastructure_friction | **Severity:** medium
**Tests:** A-10

A-10 fails because DCPLLPowerModel (the lossy DC OPF formulation in PowerModels.jl,
accessible through PSI) uses `ScalarQuadraticFunction-in-GreaterThan` constraints for its
linearized Ohm's law. HiGHS supports QP objectives but not quadratic constraints. The
protocol specifies HiGHS as the primary solver.

This is categorically different from A-11 (distributed slack), where no formulation exists
anywhere in the ecosystem. For A-10, the formulation exists; the failure is that the
evaluation's designated solver cannot execute it. Ipopt (an NLP solver also available in
the evaluation environment) would handle DCPLLPowerModel's constraint type. The result
notes this: "Alternatively, Ipopt could be used but it is an NLP solver, not the specified
solver for this test."

The fail correctly captures the HiGHS-constrained evaluation outcome, but cross-tool
comparison should recognize this as a protocol-solver-selection effect, not an absolute
capability gap. A protocol note distinguishing "no formulation" from "formulation present
but solver-incompatible" would improve cross-tool interpretability.

**Cross-tool relevance:** confirmed — PowerModels.jl-based tools (PowerModels.jl itself)
face the same HiGHS incompatibility with DCPLLPowerModel.
**Proposed action:** add_test

---

### powersimulations-F07: LMP values produced with undocumented unit conversion not independently verified

**Category:** missing_verification | **Severity:** medium
**Tests:** A-3, B-1

Both A-3 (DCOPF LMPs) and B-1 (custom constraint dual) require dividing raw dual values
by `base_power` (100 MVA) and negating. The D-2 documentation audit confirms this
conversion is not documented: "Dual unit conversion (divide by base_power, negate): No —
Discovered empirically."

The LMP range reported in A-3 ($7.76-$290.11/MWh) is economically plausible for the cost
structure (hydro $5/MWh to gas CC $40/MWh), which provides informal confirmation. But
the result does not show raw dual values alongside converted LMPs, so an independent
reviewer cannot verify the conversion was applied correctly. A 100x error (missing the
base_power division) would produce $0.078-$2.90/MWh (too low) or $776-$29,011/MWh
(too high) — both easily recognizable as wrong, but only if the reviewer knows the expected
range. Without raw dual capture, the verification chain is incomplete.

**Cross-tool relevance:** none — PSI-specific dual unit convention.
**Proposed action:** add_verification

---

### powersimulations-F08: A-6 SCED ramp enforcement verified by constraint count, not binding evidence

**Category:** test_design_gap | **Severity:** medium
**Tests:** A-6

The A-6 result states: "1 binding ramp constraint observed, confirming ramp limits are
enforced in ED independently of UC." This claim is made in passing without identifying
which generator's ramp is binding, what the before/after dispatch values are, or what
the constraint dual value is. The protocol requires that ramp constraints be "demonstrably
enforced between consecutive dispatch intervals in the ED stage."

One binding constraint out of 460 added (0.2%) is a weak signal. The ramp parameters
are set from gen_temporal_params.csv and may be loose relative to the load profile
changes — most generators may simply not need to ramp near their limits. Demonstrating
enforcement with a single unnamed binding constraint is insufficient to confirm the
protocol's intent.

The LMP extraction failure for the ED stage also reduces confidence: "LMPs from ED stage
returned null values. The initialize_model=false + JuMP.optimize!() bypass prevents PSI's
dual tracking from populating." A test that cannot extract dual values for verification
has limited credibility as an economic dispatch validation.

**Cross-tool relevance:** likely — the ramp enforcement verification gap may affect other
tools' SCED results similarly.
**Proposed action:** add_verification

---

### powersimulations-F09: C-8 SCOPF qualified_pass despite solver crash on grade_network

**Category:** scoring_inconsistency | **Severity:** medium
**Tests:** C-8, A-9

C-8 receives qualified_pass despite HiGHS encountering OTHER_ERROR on the MEDIUM
(10K-bus) network after 438 seconds. The grade_network per eval-config.yaml for C-8 is
MEDIUM. A solver crash that produces no result is a more severe outcome than a timeout
with an incumbent solution (which is what SMALL produced). Neither outcome demonstrates
that SCOPF at scale is achievable.

By contrast, A-9 (SCOPF on TINY with manual LODF assembly, which is clearly a workaround
for absent built-in SCOPF) also receives qualified_pass. The scoring system does not
distinguish between: (a) a workaround that produces a correct result, (b) a timeout with
an incumbent, and (c) a solver crash with no result. All receive qualified_pass.

The OTHER_ERROR crash on MEDIUM should arguably be treated as a fail on the grade_network,
with the SMALL partial result noted as additional context. Using the same qualified_pass
for both a 7-contingency manual LODF solution and a solver crash is a scoring pattern
inconsistency.

**Cross-tool relevance:** likely — other tools' SCOPF scale results may show similar
outcome diversity under the same qualified_pass label.
**Proposed action:** adjust_scoring

---

### powersimulations-F10: Machine-precision PTDF claim may not generalize to networks with tap transformers

**Category:** extraordinary_claim | **Severity:** medium
**Tests:** B-9

B-9 reports: "Max error: 1.15e-14 p.u. All 46 branches match to machine precision." This
is verified against DCPF results on the case39 network, which has no phase-shifting
transformers (all SHIFT=0). The B-9 result explicitly notes this precondition.

C-9 (PTDF at MEDIUM scale) documents PTDF values outside [-1,1] for the 10K-bus network
due to 776 non-unity tap transformers, but does not perform a flow accuracy check because
the DCPF on MEDIUM also has the simplified B-matrix issue (see G-FNM-3). The machine-
precision claim on case39 cannot be assumed to generalize to networks with off-nominal
taps — which is precisely the real-world scenario where PTDF accuracy matters for
contingency screening.

This finding also connects to G-FNM-3: if PowerFlows.jl's DCPF uses a simplified B-matrix
that ignores tap ratios, then PTDF-DCPF consistency may hold (both use the same simplified
model) while both diverge from physical reality on real networks.

**Cross-tool relevance:** confirmed — the protocol's B-9 PTDF verification requirement
applies equally to all tools, and the phase-shifter correction gap affects any tool using
a simplified admittance matrix.
**Proposed action:** add_test

---

### powersimulations-F11: G-FNM-3 formulation-difference classification understates practical impact

**Category:** misleading_result | **Severity:** low
**Tests:** G-FNM-3

G-FNM-3 classifies the 86.8% bus angle failure as a formulation-difference. This is
technically accurate — PowerFlows.jl uses `b = -1/x` (simplified B-matrix) while MATPOWER
uses the full B-matrix with tap ratio correction. The classification is appropriate for
academic comparison, but it may understate the practical consequence for operational
workflows.

With 2,340 of 2,358 TapTransformers having off-nominal taps (99.2%), the simplified
B-matrix is not a minor edge case on the FNM network — it affects nearly every transformer.
The mean angle deviation (2.66 degrees) and the absence of any API-level fix
("no configuration option in PowerFlows.jl to switch to a full B-matrix") mean this
is not a correctable limitation but a fundamental architectural choice with real impact
on DCPF accuracy for the target use case.

**Cross-tool relevance:** none — PowerFlows.jl-specific architecture.
**Proposed action:** null

---

### powersimulations-F12: SCUC cycling claim not cross-verified against economic necessity

**Category:** missing_verification | **Severity:** low
**Tests:** A-5

A-5 confirms 3 generators cycle (gen-5 Coal, gen-7 Gas CC, gen-10 Gas CC) over 24 hours,
which satisfies the "at least 2 generators must cycle" protocol requirement. The cycling
pattern is economically coherent (gas CC cycles for peak hours), and MIP gap 0.57% is
within the 1% tolerance.

However, the load amplitude (4,237 MW valley to 6,254 MW peak, a 48% swing) is unusually
large. With such a strong demand signal, cycling is driven as much by capacity necessity
as by cost optimization. The test does not verify whether cycling is driven by cost
differentiation specifically. On a flatter load profile, the same 10 generators with
the same cost structure might not force meaningful cycling. The protocol's intent is to
verify that the tool correctly uses cost signals to drive commitment decisions, not just
that it can handle a large demand swing.

**Cross-tool relevance:** confirmed — the same load profile and network are used for
all tools' A-5 tests.
**Proposed action:** null

---

### powersimulations-F13: 0/10 example pass rate inflated by external dependency design choice

**Category:** infrastructure_friction | **Severity:** low
**Tests:** D-3

D-3 reports 0 of 10 official examples run unmodified. This accurately reflects the
out-of-box experience, but all failures at the PSI tutorial level trace to a single root
cause: tutorials use `PowerSystemCaseBuilder.jl`, a separate package not bundled with PSI.

Python ecosystem tools (PyPSA, pandapower) include built-in test networks that require
no external downloads. The Julia ecosystem chose to separate test data into a dedicated
package for architectural cleanliness. This is a legitimate trade-off, not poor tutorial
quality. The PowerFlows.jl tutorial works correctly with a one-line data source
substitution.

Cross-tool comparison using D-3 "examples run unmodified" will systematically disadvantage
Julia-ecosystem tools relative to Python tools with bundled test networks. The protocol
should either standardize the data source across all tools or note that the 0/10 figure
reflects a packaging convention rather than tutorial quality.

**Cross-tool relevance:** likely — other Julia ecosystem tools (PowerModels.jl, Sienna
ecosystem) will show the same pattern.
**Proposed action:** redesign_test

---

### powersimulations-F14: C-5 progressive relaxation is structurally inapplicable to NR power flow

**Category:** test_design_gap | **Severity:** low
**Tests:** C-5

C-5 applies progressive thermal limit relaxation (0%, 10%, 20%) to diagnose ACPF
convergence difficulty. For PowerSimulations.jl using PowerFlows.jl's built-in NR solver,
all three relaxation levels produce identical voltage profiles with identical solve times
(0.34s after JIT). The result correctly explains: "thermal limit relaxation only affects
OPF branch constraints, not the NR power flow equations."

This is a structural test design issue: progressive relaxation is a meaningful diagnostic
for tools that use OPF-based AC feasibility checks (e.g., Ipopt solving the AC OPF with
relaxed thermal constraints). For NR power flow solvers, thermal limits are not part of
the solve — the NR converges or it does not, independent of thermal ratings. The test
as designed cannot distinguish "tool converges easily at nominal limits" from "tool ignores
thermal limits in NR" — both look identical in the output.

**Cross-tool relevance:** confirmed — this affects all tools that implement ACPF via
direct NR rather than through an OPF-based feasibility formulation.
**Proposed action:** redesign_test

---

### powersimulations-F15: Gate ingest tests produce no cross-tool signal

**Category:** low_signal | **Severity:** low
**Tests:** G-1, G-2, G-3

G-1/G-2/G-3 test MATPOWER ingestion at three network tiers. All tools that reach this
evaluation stage pass these tests — they gate out tools that cannot load MATPOWER files
at all, but do not differentiate among surviving tools. The timing reported (6.44s for
case39) is dominated by Julia JIT compilation, not parser performance, making it
incomparable to Python tool loading times.

These tests are necessary as gates but should not carry comparative weight in scoring.

**Cross-tool relevance:** confirmed — universal across all evaluated tools.
**Proposed action:** null

---

### powersimulations-F16: C-4 SCUC timing measured single-threaded on 32-core machine

**Category:** extraordinary_claim | **Severity:** medium
**Tests:** C-4

C-4 measures HiGHS solving a 22,608-binary MILP in 404 seconds, single-threaded, on a
machine with 32 available cores. The result explicitly notes "CPU cores used: 1 (32
available)" without explaining why multi-threading was not used. Modern MILP solvers
including HiGHS achieve near-linear speedup on branch-and-bound with more threads.
A 32-thread run would plausibly reduce solve time to 15-30 seconds, moving C-4 from
"barely within an acceptable time window" to "efficient."

SCIP hit TIME_LIMIT (600s) single-threaded; multi-threaded SCIP might solve within
the limit. The timing measurement as recorded is reproducible but unrepresentative of
production deployment on the evaluation hardware. Cross-tool comparison of C-4 times
would be misleading if other tools' SCUC tests used multi-threading.

The protocol does not specify single-threaded measurement for scalability tests. Adding
a multi-threaded measurement as a secondary metric would significantly improve the
interpretability of C-4 results across tools.

**Cross-tool relevance:** confirmed — SCUC timing comparisons across all tools are
affected if threading discipline is inconsistent.
**Proposed action:** add_verification

---

## Extraordinary Claims

### A-9: SCOPF 17.7% cost increase from N-1 contingencies

**Concern:** Only 7 of 34 line contingencies applied after near-radial topology filter.
The cost increase is real but quantified against a minimal effective contingency set on
a topology where 79% of contingencies are infeasible.
**Evidence quality:** moderate

The 17.7% cost increase direction is confirmed by the economic logic (nuclear→gas CC shift)
and by the mathematical correctness of LODF-based constraint injection. However, the
magnitude is highly sensitive to which contingencies survive the |LODF| < 0.95 filter.
A probe is not recommended because the result is correctly bounded as a TINY-network
finding; the SCOPF capability itself is more meaningfully assessed at scale (C-8).

---

### B-9: Machine-precision PTDF (max error 1.15e-14 p.u.)

**Concern:** Verified on case39 which has no phase-shifting transformers. C-9 shows
PTDF values outside [-1,1] on the 10K-bus network due to tap transformers, with no
flow accuracy check. The machine-precision claim cannot be assumed to hold at scale
with off-nominal taps.
**Evidence quality:** moderate

The B-9 measurement itself is credible — the case39 verification is thorough and the
machine-precision result is consistent with known properties of PTDF computation on
lossless networks. The claim should be interpreted as network-specific rather than
as a general characterization of PowerNetworkMatrices.jl's PTDF accuracy.

---

### C-4: 404-second SCUC (single-threaded, 32 cores available)

**Concern:** Single-threaded HiGHS on a 32-core machine. Multi-threaded performance
would likely be 15-30 seconds. The timing as measured is reproducible but does not
represent production capability.
**Evidence quality:** strong

This is a straightforward timing understatement. The fix is to re-run with
`set_optimizer_attribute(optimizer, "threads", 32)` and record both timings. This probe
is recommended because C-4 is the primary SCUC scalability data point and the single-
threaded constraint is not explained in the result file.

---

## Test Outcome Matrix

| Test ID | Status | Workaround | Key Issue |
|---------|--------|------------|-----------|
| G-1 | pass | — | Low signal (gate only) |
| G-2 | pass | — | Low signal (gate only) |
| G-3 | pass | — | Low signal (gate only) |
| A-1 | pass | — | DC/AC result type inconsistency noted |
| A-2 | qualified_pass | stable | No NR residual or iteration count exposed |
| A-3 | pass | stable | LMP unit conversion undocumented; not independently verified |
| A-4 | pass | — | Clean DCOPF→ACPF workflow |
| A-5 | qualified_pass | fragile | PSI initialization bypass; internal API for result extraction |
| A-6 | qualified_pass | fragile | ED LMP extraction fails; 1 binding ramp constraint asserted but not shown |
| A-9 | qualified_pass | stable | Only 7/34 contingencies applied; network too radial for SCOPF signal |
| A-10 | fail | blocking | Formulation exists (DCPLLPowerModel) but HiGHS cannot solve its constraint type |
| A-11 | fail | blocking | No formulation exists at any level in PSI or PowerModels |
| A-12 | qualified_pass | fragile | BESS arbitrage condition explicitly fails; masked by qualified_pass |
| B-1 | pass | — | JuMP model access works cleanly |
| B-2 | qualified_pass | stable | Manual BFS over adjacency matrix |
| B-3 | qualified_pass | stable | LODF superposition approximate for M>1 |
| B-4 | pass | stable | System reconstruction per scenario; linear costs produce degenerate LMPs |
| B-5 | pass | — | 2-LOC export |
| B-6 | pass | — | 5-layer architecture documented |
| B-8 | pass | — | Reference bus config works; LMP invariance confirmed |
| B-9 | pass | — | Machine precision on case39 (no phase shifters); claim limited to simple networks |
| C-1 | pass | — | 0.275s; no workarounds |
| C-2 | pass | — | Convergence warning on first call; residual not verified |
| C-3 | qualified_pass | fragile | Branch flow limits removed; effectively unconstrained economic dispatch |
| C-4 | qualified_pass | fragile | 404s single-threaded; 32 cores available; SCIP times out |
| C-5 SMALL | pass | — | Progressive relaxation inapplicable to NR; all levels identical |
| C-5 MEDIUM | pass | — | Same structural issue as SMALL |
| C-7 | pass | fragile | Inherits all 5 C-3 workarounds; solver swap is 1-LOC |
| C-8 | qualified_pass | fragile | SMALL timeout with incumbent; MEDIUM OTHER_ERROR crash |
| C-9 | pass | — | 1.6s; 68.6% dense matrix; orientation is buses×branches (transposed vs convention) |
| C-10 | fail | blocking | Cascaded from A-11 |
| D-1 | informational | — | 19s first-solve; JIT dominant; 92 warning lines on load |
| D-2 | informational | — | 3/10 tests doable from docs; dual unit conversion undocumented |
| D-3 | informational | — | 0/10 unmodified; root cause is PowerSystemCaseBuilder dependency |
| D-4 | informational | — | Infeasibility: best-in-class; zero-cost silent success: concerning |
| D-5 | informational | — | Median 332 LOC; ~6x Python tools |
| E-1 | informational | — | 21 releases/24mo; strong cadence |
| E-2 | informational | — | 1019 commits/12mo; 12 contributors |
| E-3 | informational | — | Bus factor = 1; jd-lara 70.5% commits, 78% reviews |
| E-4 | informational | — | NREL/DOE backing; strongest funding model |
| E-5 | informational | — | Median 19.8 day TTC |
| E-6 | informational | — | 78% test coverage; 8 CI workflows |
| E-7 | informational | — | No utility/ISO production deployment confirmed |
| F-1 | pass | — | BSD-3-Clause core |
| F-2 | pass | — | 184 packages; large but standard for Julia |
| F-3 | pass | — | GLPK GPL-3.0 removable flag |
| F-4 | pass | — | Solver binaries source-available; Yggdrasil SHA-256 |
| F-5 | pass | — | Full execution path inspectable |
| F-6 | pass | — | No GPG signatures; git-tree-sha1 |
| F-7 | pass | — | Air-gap feasible via depot copy |
| F-8 | pass | — | All use cases on open-source solvers |
| F-9 | pass | — | Tutorials use mutable URLs and external downloads |
| G-FNM-1 | fail | blocking | PSS/E v31 parser fails at line 1; MATPOWER fallback used |
| G-FNM-2 | blocked | — | Blocked by G-FNM-1 PSS/E failure |
| G-FNM-3 | fail | — | Simplified B-matrix; 86.8% bus angles outside tolerance |
| G-FNM-4 | informational | — | ACPF non-convergent at all relaxation levels on 28K-bus FNM |
| G-FNM-5 | informational | — | 50% N / 30% E / 20% X across 44 fields |
| P2-1 | informational | — | v33/v35 only; v31 needs 3-6 weeks effort |
| P2-2 | informational | — | Piecewise linear: SOS2 fully supported |
| P2-3 | informational | — | Commitment injection: 5/9 ops need internal APIs |
