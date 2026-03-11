# Cross-Cutting Themes Analysis

## Phase 1 Tool Selection | v4-to-v5 Aggregation

---

## Executive Summary

Analysis of 6 per-tool sweep findings (92 total findings) and 18 probe results reveals 13 cross-cutting themes. The most impactful themes concern test network insufficiency (3 themes affecting 20+ tests), estimated rather than measured scalability data (1 theme affecting 5 tests), and a protocol gap in PTDF validation on networks with phase-shifting transformers (1 theme affecting 3 tools). Four probe-debunked claims strengthen the case for protocol changes: PyPSA's false ACPF convergence (probe-001), pandapower's non-reproducible lambda values (probe-009), PowerSimulations' unit labeling error (probe-021), and PowerSimulations' coverage misreport (probe-025).

---

## Theme 1: ACTIVSg10k Has No Binding Constraints (T01)

**Category:** Network insufficiency | **Evidence:** 5 tools | **Probes:** 006, 007, 023

The MEDIUM grade network (ACTIVSg 10k) produces zero binding branch constraints in DCOPF across all tools that can solve it. Maximum branch loading is 84-85% (pandapower: 84.9%, gridcal: 84.7%). LMPs are perfectly uniform ($20.064-$20.738/MWh depending on cost function treatment).

This finding was confirmed by three independent probes:
- **Probe-007** verified pandapower LMPs are uniform to machine precision (std = 6e-12) and demonstrated that artificial congestion immediately produces meaningful LMP spreads (16.3-24.4 $/MWh).
- **Probe-006** showed the base case DCOPF converges cleanly, confirming uniformity is not a solver issue.
- **Probe-023** confirmed PowerSimulations' PTDF and DCP formulations produce identical results on the uncongested network.

**Impact:** Tests A-3, A-9, A-11, B-8, C-3, and C-10 lose discriminative value at MEDIUM scale for any capability dependent on congestion (LMP decomposition, SCOPF cost premium, distributed slack LMP differences). The grade-assessment network fails to exercise the features being graded.

**Proposed remedy:** Tighten 10-20 branch limits in ACTIVSg 10k to 90% of base-case flow as a protocol-level preprocessing step. This preserves the network's realistic topology while enabling congestion signal.

---

## Theme 2: case39 Uniform Costs and No Congestion (T02)

**Category:** Network insufficiency | **Evidence:** 5 tools

IEEE 39-bus has identical generator cost coefficients (c1 = 0.3 $/MWh) and no binding branch constraints at the base operating point. This produces uniform LMPs across all 39 buses for every tool. Specific impacts:

- **A-3 TINY:** All tools report uniform LMPs. The test verifies OPF convergence but not LMP quality.
- **A-9 TINY:** SCOPF objective equals unconstrained OPF objective (pypsa: $1876.269 both). Cost comparison -- a key verification -- produces zero signal.
- **B-8 TINY:** All three slack configurations produce identical LMPs, providing zero discriminative value for reference bus testing.

The SMALL network (ACTIVSg 2000) has heterogeneous costs and produces meaningful LMP spreads (gridcal B-8 SMALL: 11.1 to 32.9 $/MWh). SMALL is the functional grade network for these tests; TINY serves only as a formulation check.

**Proposed remedy:** Perturb case39 generator costs (scale c1 by 0.5x-2.0x) and tighten 3-5 branch limits.

---

## Theme 3: SCUC Produces No Generator Cycling on case39 (T03)

**Category:** Network insufficiency | **Evidence:** 3 tools (pypsa, powersimulations, matpower)

Every tool capable of SCUC reports all 10 generators committed for all 24 hours with zero startups. The capacity-to-load ratio (7,367 MW capacity vs 6,254 MW peak load) combined with startup costs at 5x PMAX means decommitment is never optimal. This renders A-5 a formulation existence test rather than a UC correctness test. A-6 (SCED) shows zero dispatch difference from A-5 because the commitment schedule is trivially "all on."

MATPOWER even reports uniform ramp utilization (26.7% across all generators), confirming that ramp constraints are never near binding.

**Proposed remedy:** Augment case39 with 2-3 peakers (high startup cost, small capacity) or increase PMIN to 30% of PMAX to force cycling.

---

## Theme 4: Estimated Timings Without Execution (T04)

**Category:** Extraordinary claim pattern | **Evidence:** 3 tools | **Probes:** 016, 020

PowerSimulations has four scalability tests (C-3, C-4, C-5, C-6) with `wall_clock_seconds: null` and language like "expected to solve" or "estimated." Probe-020 confirmed C-3 was never executed (first attempt exceeded 600s timeout). PowerModels scored C-5 and C-8 as fail without execution based on projected infeasibility; probe-016 confirmed the projections were directionally correct but based on rough extrapolation.

The protocol states: "Record everything. For each test, record: Wall-clock time (for scalability-relevant tests)." Four PowerSimulations and two PowerModels tests violate this requirement. The debunked probe-001 (PyPSA ACPF with 0 NR iterations classified as pass) shows a related pattern: results classified without adequate underlying evidence.

**Proposed remedy:** Unmeasured timings cannot support pass or qualified_pass. If execution is not feasible, record fail with projected timing as context.

---

## Theme 5: Cascaded Failures Inflate Fail Counts (T05)

**Category:** Scoring inconsistency | **Evidence:** 4 tools

Multiple tools have scalability tests (C-series) that fail solely because their prerequisite expressiveness tests (A-series) failed:

| Tool | Cascaded Fails | Independent Fails | Total Fails |
|------|---------------|-------------------|-------------|
| pandapower | C-4, C-8, C-10 (3) | 11 | 14 |
| gridcal | C-4, C-6 (2) | 14 | 16 |
| powersimulations | C-8, C-10 (2) | 4 | 6 |
| powermodels | C-4 (1) | 11 | 12 |

These cascaded failures add no new information but inflate the apparent gap count. A tool with 5 independent fail reasons and 3 cascaded failures appears to have 8 problems when it has 5.

**Proposed remedy:** Add a `blocked_by` field to result frontmatter. Report independent and cascaded failures separately in summary tables.

---

## Theme 6: PTDF Phase-Shifter Correction Gap (T06)

**Category:** Protocol gap | **Evidence:** 3 tools | **Probes:** 008, 010, 012

Probe-010 is the most technically significant finding in the sweep. It identified that ACTIVSg10k has 5 phase-shifting transformers with nonzero SHIFT angles that create Pbusinj (bus injection correction) and Pfinj (branch flow correction) terms. The standard PTDF formula `flow = PTDF @ Pinj` omits these corrections, causing errors up to 743 MW.

The full equation is: `flow = PTDF @ (Pinj - Pbusinj) + Pfinj`

Applying this correction eliminates ALL error to machine precision (1e-12). The PTDF matrix itself is correct in all tools tested.

| Tool | Max Error (uncorrected) | Attribution in eval | Actual cause |
|------|------------------------|--------------------|----|
| pandapower | 7.43 pu (743 MW) | "shunt elements" (wrong) | Phase-shifter Pfinj |
| gridcal | 743.46 MW | "island handling" (wrong) | Phase-shifter Pfinj |
| pypsa | 702 MW | "zero-impedance fix" (partially wrong) | Phase-shifter Pfinj |
| powermodels | < 1e-11 | N/A (correct) | Handles internally |

The original B-9 attributions were incorrect (shunts have zero MW on this network; island count is 1). The protocol's pass condition ("flow predictions match DCPF results within 1e-6") is unachievable on any network with phase-shifting transformers unless correction terms are applied.

**Proposed remedy:** Protocol should specify that PTDF validation must account for phase-shifter correction terms (Pbusinj/Pfinj), or the test should exclude phase-shifting transformer branches from the accuracy check.

---

## Theme 7: ACTIVSg10k Zero-Impedance Branch Inconsistency (T07)

**Category:** Infrastructure friction | **Evidence:** 4 tools

ACTIVSg10k has 2,462 branches with zero thermal rating and 3 transformers with zero reactance. Different tools handle these differently:

| Tool | Treatment of RATE_A=0 | Treatment of x=0 |
|------|-----------------------|-------------------|
| PyPSA | Zero-capacity constraint (infeasible) | Singular B-matrix (NaN flows) |
| pandapower | Unconstrained (no limit) | Passes through PYPOWER |
| gridcal | Unconstrained | Passes through |
| powermodels | Unconstrained (data fix for gencost) | Passes through |
| matpower | Unconstrained | Passes through |

PyPSA's expressiveness tests (A-3 MEDIUM) fail due to these data issues, while scalability tests (C-3 MEDIUM) pass after applying data fixes (s_nom=9999, x=0.0001). This creates contradictory results: the same tool fails expressiveness but passes scalability on the same network for the same analysis.

**Proposed remedy:** Standardize ACTIVSg10k preprocessing as a protocol step: zero-reactance transformers get x=0.0001, zero-rating branches get RATE_A=9999. Applied uniformly across all dimensions.

---

## Theme 8: Stochastic Perturbation Methodology Causes Excessive Infeasibility (T08)

**Category:** Test design gap | **Evidence:** 3 tools | **Probe:** 006

The B-4/C-6 stochastic scenario methodology produces very high infeasibility rates when load and generator capacity perturbations are applied simultaneously:

| Tool | Network | Convergence Rate |
|------|---------|-----------------|
| pandapower | SMALL | 0.42-2.1% (probe-006) |
| gridcal | SMALL | 47% |
| powersimulations | TINY | 60% (3/5) |

Probe-006 showed that uniform load scaling alone (0.7x-1.1x) converges reliably; it is the combination of load AND generator perturbations that breaks the solver. This measures solver robustness to near-infeasible problems rather than the tool's stochastic wrapping capability.

**Proposed remedy:** Calibrate perturbation bounds to produce at most 20% infeasible scenarios, or require OPF formulations with load-shedding slack variables.

---

## Theme 9: Lossy DCOPF MATPOWER Reference Validation Unachievable (T09)

**Category:** Missing verification | **Evidence:** 4 tools

The A-10 pass condition requires "Validate against MATPOWER reference lossy DC OPF solution." No tool performs this validation because MATPOWER's `rundcopf` does not have a loss option producing comparable LMPs. PowerModels notes "MATPOWER used lossless DC OPF with post-hoc loss estimation." MATPOWER's own evaluation performs a post-hoc loss estimate that is explicitly "NOT part of the optimization."

The reference validation is structurally impossible as currently specified.

**Proposed remedy:** Replace MATPOWER reference requirement with internal consistency checks: (a) loss components have physically correct signs, (b) total losses are 0.5-3% of load, (c) lossless-vs-lossy objective difference is positive.

---

## Theme 10: ACPF at 10k-Bus Is a Genuine Discriminator (T10)

**Category:** High-signal test | **Evidence:** 6 tools | **Probes:** 001, 024

A-2 MEDIUM produces three distinct outcome classes with strong discriminative value:

1. **Converges with diagnostics:** pandapower (DC warm start), gridcal (convergence error 2.73e-07), matpower (standard NR)
2. **Fails with minimal diagnostics:** PowerModels (NLsolve fails, no iteration count exposed), PowerSimulations (returns `Missing` silently -- probe-024)
3. **Reports false convergence:** PyPSA (probe-001: 0 NR iterations, 83% flat start, converged: False but originally classified as pass)

Probe-001 is particularly impactful: the PyPSA ACPF "pass" on MEDIUM is invalid. The solver performed zero iterations and left 91% of lines with zero flow.

**Proposed remedy:** Strengthen A-2 pass condition: require convergence residual < tolerance, iteration count reported, and >95% of buses not at flat-start defaults.

---

## Theme 11: SCOPF and N-M Sweep Infeasibility at MEDIUM Scale (T13)

**Category:** Test design gap | **Evidence:** 3+ tools | **Probe:** 016

C-8 MEDIUM (500-contingency SCOPF) is a unanimous fail across all 6 tools. Probe-016 showed that even 5 contingencies time out for PowerModels at MEDIUM scale. The protocol's 500-contingency target on 10k-bus produces zero discriminative value.

Similarly, the N-M sweep at x=5, m=4 on MEDIUM is infeasible at N-3+ for all tools. The combinatorial explosion (C(1000,3) = 166M combinations) means no tool can complete the test as specified. The discriminative signal is at N-1 and N-2 only.

**Proposed remedy:** Reduce C-8 MEDIUM to 50 contingencies. Cap N-M sweep at N-2 for MEDIUM with N-3+ as informational.

---

## Theme 12: Solver Capability vs Tool Capability Conflation (T04/T11)

**Category:** Scoring inconsistency | **Evidence:** 4 tools

Multiple tests conflate open-source solver limitations with tool capability:

- **A-5/C-4:** HiGHS single-threaded MIP timeout on 2000-bus UC affects pypsa, PowerModels. MATPOWER passes because MIPS handles the formulation (different solver, same tool capability).
- **C-7:** Solver swap is parameter-only for 4 tools, but qualified_pass given because alternative solvers either fail or are not installed.
- **C-3/C-8:** HiGHS QP failure on ACTIVSg2000 forces Ipopt workarounds for PowerModels.

The protocol mandates single-threaded open-source solvers, creating a ceiling on SCUC scale that is independent of tool capability. A tool that can express the formulation in 140 LOC but cannot solve it receives the same fail as a tool that cannot express it at all.

**Proposed remedy:** Separate "can the tool express the formulation" (expressiveness) from "can the solver complete within the budget" (scalability). Allow multi-threaded or commercial solver results as supplementary evidence.

---

## Theme 13: Maturity Metrics Based on Research Without Verification (T12-proxy)

**Category:** Missing verification | **Evidence:** 6 tools | **Probe:** 025

All E-series metrics are research-based. Probe-025 debunked PowerSimulations' "100% code coverage" claim (actual: 78% from Codecov badge). Other maturity numbers (commit counts, contributor percentages, deployment claims) are plausible but unverified. This is inherent to the audit methodology, but the coverage misread demonstrates the risk of accepting badge-reported metrics without verification.

**Proposed remedy:** For E-6 (CI/test coverage), require the evaluator to check the Codecov/Coveralls detail page, not just the badge. For E-7 (operational adoption), require a linked source for each claimed deployment.

---

## Probe Integration Summary

### Debunked Claims (4)

| Probe | Tool | Claim | Impact |
|-------|------|-------|--------|
| probe-001 | PyPSA | ACPF "pass" on MEDIUM | A-2 MEDIUM should be reclassified as fail; strengthens T10 |
| probe-009 | pandapower | Lambda 1e25 with in_service=False | Both decommitment methods have identical convergence; P2-3 finding weakened |
| probe-021 | PowerSim | 100x dispatch/limit mismatch | Labeling error (MW vs pu); A-4 and B-7 findings need revision |
| probe-025 | PowerSim | 100% code coverage | Actual: 78%; E-6 needs correction |

### Supported Claims with Protocol Implications (10)

| Probe | Finding | Protocol Impact |
|-------|---------|-----------------|
| probe-006/007 | Uniform LMPs on ACTIVSg10k | T01: tighten branch limits |
| probe-010 | Phase-shifter PTDF correction | T06: update B-9 pass condition |
| probe-012 | GridCal 743 MW PTDF divergence | T06: same root cause as pandapower |
| probe-016 | PM C-5/C-8 infeasibility confirmed | T04/T13: reduce scale targets |
| probe-020 | PSI C-3 timing never measured | T04: require measured timings |
| probe-022 | PSI binding dual works | B-1 methodology gap but tool works |
| probe-023 | Distributed slack no-op on uncongested | T01: need congested network |
| probe-024 | PSI ACPF silent failure | T10: require diagnostic output |
| probe-028 | MATPOWER 400x slowdown from dense PTDF | Dense matrix formulation issue |
| probe-029 | 97% Octave overhead in contingency sweep | Interpreter, not algorithm |
| probe-032 | MOST loadmd() fails at ingestion | Data ingestion bug, not solver |
