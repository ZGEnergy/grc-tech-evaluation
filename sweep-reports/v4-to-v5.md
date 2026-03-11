# Evaluation Sweep: v4 → v5

**Date:** 2026-03-09
**Evaluation:** Phase 1 technology assessment
**Tools evaluated:** PyPSA, pandapower, GridCal, PowerModels, PowerSimulations, MATPOWER (6 of 6)
**Protocol version:** v4 (source) → v5 (target)

## Executive Summary

This sweep analyzed all six power-system modeling tools under protocol v4, producing 92 findings across the per-tool evaluations and 18 spot-check probes. Aggregation revealed 13 cross-cutting themes, of which the most impactful concern test network insufficiency: ACTIVSg10k has no binding branch constraints (Theme T01, 5 tools), case39 has uniform generator costs (Theme T02, 5 tools), and case39 SCUC produces no generator cycling (Theme T03, 3 tools). These three themes collectively affect 20+ tests and reduce discriminative signal at the grade-assessment scale. Four probe-debunked claims strengthen the case for protocol changes: PyPSA's false ACPF convergence on 10k-bus (probe-001), pandapower's non-reproducible lambda values (probe-009), PowerSimulations' unit labeling error (probe-021), and PowerSimulations' overstated code coverage (probe-025). The v5 trajectory is toward more rigorous convergence verification, calibrated test networks that produce binding constraints, separation of cascaded from independent failures, and prohibition of estimated timings for scalability grades. Ten protocol changes and two rubric changes are proposed, all meeting the 3+ tool evidence threshold.

## Cross-Tool Comparison Matrices

### Test Outcome Matrix

Legend: P = pass, F = fail, QP = qualified_pass, I = informational, -- = not attempted/blocked

#### Gate Tests

| Test ID | Description | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER |
|---------|-------------|-------|------------|---------|-------------|----------|----------|
| G-1 | TINY ingest | P | P | P | P | P | P |
| G-2 | SMALL ingest | P | P | P | P | P | P |
| G-3 | MEDIUM ingest | P | P | P | P | P | P |

Signal: None. Unanimous pass across all tools. All tools handle MATPOWER .m format.

#### Suite A: Problem Expressiveness

| Test ID | Description | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER | Spread | Signal |
|---------|-------------|-------|------------|---------|-------------|----------|----------|--------|--------|
| A-1 TINY | DCPF | P | P | P | P | P | P | 1 | Low |
| A-1 MED | DCPF at scale | P* | P | P | P | P | P | 2 | Low |
| A-2 TINY | ACPF | P | P | P | P | P | P | 1 | Low |
| A-2 MED | ACPF at scale | P** | P | P | F | F | P | 3 | High |
| A-3 TINY | DCOPF | P | QP | P | P | QP | P | 2 | Low |
| A-3 MED | DCOPF at scale | F | QP | P | P | -- | P | 3 | High |
| A-4 TINY | AC feasibility | P | P | P | P | QP | P | 2 | Low |
| A-4 MED | AC feasibility at scale | F | P | P | QP | -- | P | 3 | High |
| A-5 TINY | SCUC | P | F | F | P | QP | P | 3 | High |
| A-5 SMALL | SCUC at scale | F | F | F | F | -- | P | 2 | Medium |
| A-6 TINY | SCED | P | F | F | QP | QP | P | 3 | High |
| A-6 SMALL | SCED at scale | F | F | F | F | -- | P | 2 | Medium |
| A-7 TINY | N-M contingency sweep | P | P | QP | QP | P | P | 2 | Low |
| A-7 MED | N-M contingency at scale | F | P | QP | F | -- | P | 3 | High |
| A-8 TINY | Stochastic optimization | F | F | F | F | F | P | 2 | Medium |
| A-8 SMALL | Stochastic at scale | F | F | F | F | -- | -- | 1 | Low |
| A-9 TINY | SCOPF | P | F | F | QP | QP | P | 3 | High |
| A-9 SMALL | SCOPF at scale | P | F | F | QP | -- | P | 3 | High |
| A-10 TINY | Lossy DCOPF LMP | P | F | QP | QP | F | QP | 4 | High |
| A-10 SMALL | Lossy DCOPF at scale | P | F | QP | QP | F | QP | 4 | High |
| A-11 TINY | Distributed slack OPF | P | F | F | QP | QP | QP | 4 | High |
| A-11 SMALL | Distributed slack at scale | P | F | F | QP | -- | QP | 3 | High |

Notes:
- *P\** = A-1 MEDIUM PyPSA: all flows NaN due to singular matrix from zero-impedance branches; pass is misleading (probe-001 related).
- *P\*\** = A-2 MEDIUM PyPSA: 0 NR iterations, 83% buses at flat start, converged=False; debunked by probe-001.

#### Suite B: Extensibility

| Test ID | Description | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER | Spread | Signal |
|---------|-------------|-------|------------|---------|-------------|----------|----------|--------|--------|
| B-1 TINY | Custom constraints | P | QP | F | P | P | P | 3 | High |
| B-1 MED | Custom constraints at scale | F | QP | F | P | -- | P | 3 | High |
| B-2 TINY | Callback/hook | P | P | P | QP | QP | P | 2 | Low |
| B-2 MED | Callback at scale | P | P | P | QP | -- | P | 2 | Low |
| B-3 TINY | N-1 contingency loop | P | P | P | P | P | P | 1 | Low |
| B-3 MED | N-1 loop at scale | F | P | P | P | -- | P | 2 | Medium |
| B-4 TINY | Stochastic wrapping | P | QP | QP | P | P | P | 2 | Low |
| B-4 SMALL | Stochastic wrapping at scale | P | QP | QP | P | P | P | 2 | Low |
| B-5 TINY | Interoperability (CSV) | P | P | P | P | P | P | 1 | Low |
| B-5 MED | Interoperability at scale | P | P | P | P | -- | P | 1 | Low |
| B-6 | API stability | I | P | P | P | P | I | 2 | Low |
| B-7 TINY | AC feasibility extension | P | P | P | P | QP | P | 2 | Low |
| B-7 MED | AC feasibility ext. at scale | P | P | P | P | -- | P | 1 | Low |
| B-8 TINY | Reference bus config | P | QP | P | P | P | QP | 2 | Low |
| B-8 SMALL | Reference bus at scale | P | QP | P | P | -- | QP | 2 | Low |
| B-9 TINY | PTDF extraction | P | QP | P | P | P | P | 2 | Low |
| B-9 MED | PTDF at scale | F | QP | QP | P | -- | P | 3 | High |

#### Suite C: Scalability

| Test ID | Description | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER | Spread | Signal |
|---------|-------------|-------|------------|---------|-------------|----------|----------|--------|--------|
| C-1 MED | DCPF scale | P | P | P | P | P | P | 1 | Low |
| C-2 MED | ACPF scale | P | P | P | F | F | P | 2 | Medium |
| C-3 MED | DCOPF scale | P | QP | P | P | QP* | P | 3 | Medium |
| C-4 SMALL | SCUC scale | F | F | F | F | QP* | F | 2 | Medium |
| C-5 MED | Contingency sweep scale | QP | P | P | F | QP* | P | 3 | Medium |
| C-6 SMALL | Stochastic scale | P | QP | F | P | QP* | F | 3 | Medium |
| C-7 MED | Solver swap | P | F | P | QP | P | P | 2 | Medium |
| C-8 MED | SCOPF scale | F | F | F | F | F | F | 1 | Low |
| C-9 MED | PTDF scale | QP | P | QP | P | P | P | 2 | Low |
| C-10 MED | Distributed slack scale | P | F | F | QP | F | QP | 3 | Medium |

Notes:
- *QP\** = PowerSimulations C-3/C-4/C-5/C-6: estimated timings only, no actual measurement (probe-020 confirms).

#### Suite D: Workforce Accessibility

| Test ID | Description | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER | Spread | Signal |
|---------|-------------|-------|------------|---------|-------------|----------|----------|--------|--------|
| D-1 | Install to first solve | P | P | QP | QP | QP | I | 3 | Medium |
| D-2 | Documentation audit | QP | QP | I | QP | I | I | 2 | Low |
| D-3 | Tutorial/example verification | P | P | QP | QP | I | I | 3 | Medium |
| D-4 | Error message quality | QP | QP | F | QP | QP | I | 3 | Medium |
| D-5 | Code volume comparison | I | I | I | I | I | I | 1 | Low |

#### Suite E: Maturity & Sustainability

| Test ID | Description | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER | Spread | Signal |
|---------|-------------|-------|------------|---------|-------------|----------|----------|--------|--------|
| E-1 | Release cadence | I | P | P | P | I | I | 2 | Low |
| E-2 | Commit activity | I | P | P | QP | I | I | 2 | Low |
| E-3 | Bus factor | I | P | QP | F | I | I | 3 | Medium |
| E-4 | Funding model | I | P | F | I | I | I | 2 | Low |
| E-5 | Issue responsiveness | I | P | QP | QP | I | I | 2 | Low |
| E-6 | CI/test coverage | I | P | QP | P | I | I | 2 | Low |
| E-7 | Operational adoption | I | P | QP | F | I | I | 3 | Medium |

#### Suite F: Supply Chain

| Test ID | Description | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER | Spread | Signal |
|---------|-------------|-------|------------|---------|-------------|----------|----------|--------|--------|
| F-1 | License compatibility | P | P | QP | P | P | P | 2 | Low |
| F-2 | Dependency tree | QP | P | P | I | I | P | 3 | Low |
| F-3 | Dependency license audit | QP | P | P | QP | I | P | 2 | Low |
| F-4 | Pinned/lockfile | P | P | P | P | P | P | 1 | Low |
| F-5 | Reproducible install | P | P | P | P | P | P | 1 | Low |
| F-6 | Vulnerability scan | P | P | P | P | P | I | 2 | Low |
| F-7 | Binary/native deps | P | P | F | P | P | P | 2 | Low |
| F-8 | Airgap/offline install | P | P | QP | P | P | P | 2 | Low |
| F-9 | SBOM generation | QP | QP | QP | P | I | I | 3 | Low |

#### Phase 2 Readiness

| Test ID | Description | PyPSA | pandapower | GridCal | PowerModels | PowerSim | MATPOWER | Spread | Signal |
|---------|-------------|-------|------------|---------|-------------|----------|----------|--------|--------|
| P2-1 | CIM/CGMES import | I | I | P | I | I | I | 2 | Low |
| P2-2 | Dynamic model formulation | I | I | F | I | I | I | 2 | Low |
| P2-3 | Commitment-injection pipeline | I | I | F | I | I | I | 2 | Low |

### Signal Analysis

#### High-Signal Tests (3+ distinct outcomes)

| Test | Dominant Factor | Notes |
|------|----------------|-------|
| A-2 MED | Tool capability | ACPF convergence at 10k: pandapower/gridcal/matpower pass; PM/PSI fail; PyPSA false convergence (probe-001) |
| A-3 MED | Infrastructure/data | PyPSA fails from zero s_nom; others pass with various approaches |
| A-4 MED | Tool capability + data | ACPF-based feasibility; some tools cannot solve ACPF at scale |
| A-5 TINY | Tool capability | SCUC architecture: built-in (pypsa/matpower) vs manual (PM/PSI) vs absent (pp/gc) |
| A-6 TINY | Tool capability | Same split as A-5 (SCED depends on UC) |
| A-7 MED | Combinatorial + tool | N-M explosion; only pp/gc/matpower complete at MEDIUM |
| A-9 TINY/SMALL | Tool capability | SCOPF: pypsa/matpower native; PM manual; pp/gc absent |
| A-10 | Tool capability | Lossy DCOPF: wide range from native (pypsa) to absent (pp/PSI) |
| A-11 | Tool capability | Distributed slack: wide range from native to absent |
| B-1 | Tool architecture | Custom constraints: JuMP-based (PM/PSI) and linopy (pypsa) vs absent (gc) |
| B-9 MED | Data + tool | PTDF accuracy at scale; phase-shifter correction issue (probe-010) |

#### Low-Signal Tests (unanimous or near-unanimous)

| Test | Outcome | Reason |
|------|---------|--------|
| G-1/G-2/G-3 | All pass | MATPOWER format trivial for all tools |
| A-1 TINY | All pass | DCPF on 39-bus is trivial |
| A-2 TINY | All pass | ACPF on 39-bus is trivial |
| B-3 TINY | All pass | N-1 loop on 39-bus is trivial |
| B-5 TINY/MED | All pass | CSV export trivial for DataFrame-based tools |
| C-1 MED | All pass | DCPF scales well for all tools |
| C-8 MED | All fail | SCOPF at 500 contingencies on 10k-bus is infeasible for all |
| D-5 | All informational | Code volume is informational by design |

## Low-Signal Tests

### G-1, G-2, G-3: Gate Tests (TINY/SMALL/MEDIUM ingest)

**Signal level:** Low -- unanimous pass across 6 tools
**Outcome:** All pass
**Root cause:** All tools have MATPOWER .m parsers. Gate tests serve as a precondition filter but provide zero discriminative signal between tools.
**Proposed action:** Preserve. Gate tests prevent downstream waste if a tool cannot ingest the format.
**v5 replacement:** Unchanged (G-1, G-2, G-3)

### A-1 TINY: DCPF on 39-bus

**Signal level:** Low -- unanimous pass across 6 tools
**Outcome:** All pass
**Root cause:** DCPF on IEEE 39-bus is computationally trivial for any power systems tool.
**Proposed action:** Preserve as functional baseline.
**v5 replacement:** Unchanged (A-1 TINY)

### A-2 TINY: ACPF on 39-bus

**Signal level:** Low -- unanimous pass across 6 tools
**Outcome:** All pass
**Root cause:** ACPF converges for all tools on the well-conditioned 39-bus network. The MEDIUM test has high signal (3 distinct outcome classes).
**Proposed action:** Preserve as baseline; the MEDIUM test is the discriminator.
**v5 replacement:** Unchanged (A-2 TINY)

### A-3 TINY: DCOPF on 39-bus (LMP aspect)

**Signal level:** Low -- near-unanimous pass; LMPs uniform across all tools
**Outcome:** All tools report uniform LMPs (~0.3 or ~13.5 $/MWh depending on cost function). Confirmed by probes 006/007 that ACTIVSg10k also produces uniform LMPs.
**Root cause:** All 10 generators in case39 have identical linear cost (0.3 $/MWh) and no branch constraints bind, producing economically uniform LMPs.
**Proposed action:** Modify case39 data to tighten 3-5 branch limits and perturb generator costs (0.5x-2.0x c1 scaling), enabling LMP extraction verification at TINY scale.
**v5 replacement:** Modified (A-3 TINY, with congested network data)

### A-5 TINY (cycling aspect): SCUC on 39-bus

**Signal level:** Low for cycling verification -- all capable tools report all generators committed 24/24 hours
**Outcome:** 0 startups, 0 cycling generators across pypsa, powersimulations, matpower. Capacity-to-load ratio (7,367 MW vs 6,254 MW peak) makes decommitment uneconomical.
**Root cause:** Network generation fleet is too concentrated around peak load for any generator to be decommitted economically.
**Proposed action:** Augment case39 generator fleet (add peakers or increase PMIN to 30%) to force cycling.
**v5 replacement:** Modified (A-5 TINY, with augmented generator data per PC-04)

### A-9 TINY (cost comparison aspect): SCOPF on 39-bus

**Signal level:** Low for cost comparison -- SCOPF and unconstrained OPF produce identical objectives
**Outcome:** pypsa: $1876.269 both; matpower: identical dispatch. No security cost premium observable.
**Root cause:** Identical marginal costs and no binding constraints produce zero SCOPF cost premium.
**Proposed action:** Use perturbed generator costs on TINY to enable cost comparison even without congestion.
**v5 replacement:** Modified (A-9 TINY, with perturbed costs per PC-01 data changes)

### B-3 TINY: N-1 Contingency Loop on 39-bus

**Signal level:** Low -- unanimous pass across 6 tools
**Outcome:** All pass. N-1 on 39-bus is computationally trivial.
**Root cause:** Small network makes contingency loop cost negligible.
**Proposed action:** Preserve as baseline. MEDIUM test has medium signal.
**v5 replacement:** Unchanged (B-3 TINY)

### B-5 TINY/MED: Interoperability (CSV Export)

**Signal level:** Low -- unanimous pass
**Outcome:** All pass (2 LOC for Python tools, 18 LOC for MATPOWER). CSV export is trivial for any tool using DataFrames or numeric matrices.
**Root cause:** No tool struggles with CSV export.
**Proposed action:** Preserve as interoperability baseline even if non-discriminative.
**v5 replacement:** Unchanged (B-5)

### C-1 MED: DCPF Scale on 10k-bus

**Signal level:** Low -- unanimous pass
**Outcome:** All tools complete DCPF on 10k-bus in under 30s.
**Root cause:** DCPF is linear algebra on a sparse matrix; scales well for all tools.
**Proposed action:** Preserve as timing baseline for cross-tool comparison.
**v5 replacement:** Unchanged (C-1)

### C-8 MED: SCOPF Scale at 500 Contingencies on 10k-bus

**Signal level:** Low -- unanimous fail across all 6 tools
**Outcome:** All fail. Probe-016 confirms even 5 contingencies time out for PowerModels.
**Root cause:** 500-contingency SCOPF on 10k-bus produces a problem (~10M constraints, ~11.5M variables) that exceeds the capacity of any open-source solver within the evaluation time budget. The test produces zero discriminative value.
**Proposed action:** Reduce to 50 contingencies (matching SMALL parameter). Allow iterative screening.
**v5 replacement:** Modified (C-8 MED, reduced from 500 to 50 contingencies per PC-07)

### A-8: Stochastic Optimization

**Signal level:** Medium -- MATPOWER (via MOST) is the only native pass; all others fail
**Outcome:** Near-unanimous fail, but this IS the signal. The A-8/B-4 distinction (native vs wrapping) is protocol-correct. Probe-002 shows PyPSA has partial stochastic API that crashes on realistic networks.
**Proposed action:** Preserve. The near-unanimous fail reveals a genuine architectural gap.
**v5 replacement:** Unchanged (A-8)

### A-11 (on uncongested networks): Distributed Slack OPF

**Signal level:** Low for LMP differentiation -- distributed vs single slack produces identical results on uncongested networks
**Outcome:** Confirmed by probe-023. Both formulations produce identical dispatch (max diff 1.5e-7) and objectives on case39 and ACTIVSg2000.
**Root cause:** Without binding constraints, slack bus choice does not affect LMPs.
**Proposed action:** Use a congested network (tightened branch limits per PC-01) where distributed vs single slack produces demonstrably different LMPs.
**v5 replacement:** Modified (A-11, with congested network data)

## Spot-Check Probe Results

### Probe Summary

| Probe ID | Tool | Claim | Classification | Impact |
|----------|------|-------|----------------|--------|
| probe-001 | PyPSA | A-2 ACPF "pass" on MEDIUM | claim_debunked | Reclassify A-2 MED as fail; strengthen convergence verification (PC-02) |
| probe-002 | PyPSA | D-2 stochastic docs vs A-8 fail tension | claim_supported | Stochastic API exists but crashes on realistic networks; A-8 FAIL stands |
| probe-006 | pandapower | C-6 stochastic 2.1% convergence rate | claim_supported | Convergence even worse (0.42%); perturbation methodology is root cause (PC-10) |
| probe-007 | pandapower | A-3 uniform LMPs on MEDIUM | claim_supported | Confirms no binding constraints; max loading 84.9%; artificial congestion works |
| probe-008 | pandapower | B-9 PTDF 7.43 pu error on MEDIUM | claim_supported | Reproduces error exactly; shunt attribution is wrong (shunts are 0 MW) |
| probe-009 | pandapower | P2-3 lambda values 1e25 | claim_debunked | Both methods have identical convergence; no 1e25 lambdas observed |
| probe-010 | pandapower | B-9 PTDF error root cause | claim_supported | Phase-shifter Pbusinj/Pfinj correction eliminates ALL error to 1e-12 (PC-03) |
| probe-012 | GridCal | B-9 PTDF 743 MW divergence | claim_supported | Reproduces exact values; same root cause as pandapower (phase shifters) |
| probe-016 | PowerModels | C-5/C-8 projected infeasibility | claim_supported | BFS scope brackets claim; 5-contingency SCOPF timed out at 567s (PC-07) |
| probe-020 | PowerSim | C-3 timing estimated not measured | claim_supported | First run exceeded 600s timeout; null wall_clock confirmed (PC-05) |
| probe-021 | PowerSim | A-4 100x dispatch/limit mismatch | claim_debunked | Labeling error: dispatch is MW, limits are pu; no actual mismatch |
| probe-022 | PowerSim | B-1 binding dual extraction | claim_supported | Binding dual = -0.1398; mechanism works; B-1 test design was weak |
| probe-023 | PowerSim | A-11 distributed slack on uncongested | claim_supported | Identical results confirmed; test needs congested network (T01) |
| probe-024 | PowerSim | C-2 ACPF silent failure diagnostics | claim_supported | Returns Missing silently; no iteration count, no configurable tolerances |
| probe-025 | PowerSim | E-6 100% code coverage | claim_debunked | Actual coverage is 78% from Codecov badge; misread or stale data |
| probe-028 | MATPOWER | C-10 66-min distributed slack timing | claim_supported | MIPS 141s per iteration on dense PTDF constraints; 400x slower than sparse |
| probe-029 | MATPOWER | C-5 97% Octave overhead | claim_supported | containers.Map timed out at 300s; LODF screening completes in 0.81s |
| probe-032 | MATPOWER | C-4 loadmd() ingestion failure | claim_supported | Exact error reproduced; solver never invoked; ext2int resolves bus issue |

### Probe Details

#### probe-001: PyPSA ACPF convergence on ACTIVSg10k

PyPSA's `n.pf()` on ACTIVSg10k performs zero Newton-Raphson iterations and returns `converged: False`. Of 10,000 buses, 8,274 (83%) remain at flat-start voltage magnitude (1.0 pu). Of 9,726 lines, 8,870 (91%) have zero power flow. The original evaluation classified A-2 MEDIUM as pass despite the solver explicitly reporting non-convergence.

**Classification:** claim_debunked
**Impact on v5:** A-2 pass condition must require convergence residual below tolerance, iteration count reported, and >95% of buses not at flat-start defaults (PC-02). PyPSA A-2 MEDIUM should be reclassified as fail.

#### probe-002: PyPSA stochastic API existence vs functionality

PyPSA v1.1.2 has `set_scenarios()`, `set_risk_preference()`, and CVaR-based stochastic optimization methods. A simple single-bus test runs successfully. However, a two-bus test with scenario-indexed load time series crashes with a pandas dtype mismatch in the constraint builder. The D-2 documentation audit is correct that the API exists and is documented. The A-8 evaluation incorrectly claimed the API is absent; the feature exists but has integration bugs on multi-component networks.

**Classification:** claim_supported (D-2 claim is accurate; A-8 FAIL stands for different reasons)
**Impact on v5:** A-8 finding should distinguish "feature absent" from "feature present but broken."

#### probe-006: pandapower stochastic convergence rate on ACTIVSg2000

Reproduced the perturbed scenario loop with identical RNG seed. The probe found 1 of 240 solves converging (0.42%) vs the claimed 5 of 240 (2.1%). The base case converges, and uniform load scaling (0.7x-1.1x) converges reliably. The combination of load AND generator capacity perturbations causes near-total PYPOWER interior point failure.

**Classification:** claim_supported (convergence even worse than reported)
**Impact on v5:** Perturbation methodology needs calibration (PC-10).

#### probe-007: pandapower uniform LMPs on MEDIUM DCOPF

LMPs are uniform to machine precision (std = 6e-12) at 20.737729 $/MWh. Maximum branch loading is 84.9% (no branch approaches its limit). Artificially reducing 5 line limits to 90% of DCPF flow immediately produces LMP spreads of 16.3-24.4 $/MWh with 4,225 distinct values.

**Classification:** claim_supported
**Impact on v5:** Confirms T01 -- ACTIVSg10k preprocessing must tighten branch limits (PC-01).

#### probe-008: pandapower PTDF 7.43 pu flow error

Reproduced max diff of 7.4346 pu on ACTIVSg10k (original: 7.43 pu). Case39 baseline matches perfectly (0.0 diff). Total shunt MW is 0.0, ruling out the original "shunt elements" attribution.

**Classification:** claim_supported
**Impact on v5:** Feeds into probe-010 root cause analysis.

#### probe-009: pandapower lambda values of 1e25

Neither `in_service=False` nor `max_p_mw=0` produces lambda values near 1e25. Both methods have identical convergence patterns: the same 3 of 9 generators converge (gens 0, 6, 7) and the same 6 fail, regardless of decommitment method. When converging, lambda values are in the 13-29 range. The claimed workaround provides no benefit.

**Classification:** claim_debunked
**Impact on v5:** P2-3 finding should be corrected; the decommitment behavior is a network topology issue, not an API issue.

#### probe-010: pandapower PTDF error root cause -- phase-shifter corrections

ACTIVSg10k has 5 phase-shifting transformers with nonzero SHIFT angles. The standard PTDF formula `flow = PTDF @ Pinj` omits bus injection corrections (Pbusinj, max magnitude 733.7 pu) and branch flow corrections (Pfinj, max magnitude 366.8 pu). Applying the full equation `flow = PTDF @ (Pinj - Pbusinj) + Pfinj` eliminates ALL error to machine precision (1e-12). The PTDF matrix itself is mathematically correct.

**Classification:** claim_supported (error real; attribution refined)
**Impact on v5:** B-9/C-9 pass condition must account for phase-shifter correction terms (PC-03). This is the most technically significant probe finding in the sweep.

#### probe-012: GridCal PTDF 743 MW divergence

Reproduced exact values: LA vs DCPF max diff 743.46 MW, PTDF@Sbus vs DCPF max diff 15,139.36 MW. Network has 1 island (ruling out island handling). Tap deviation correlation with error is -0.03 (ruling out general tap effects). Same root cause as pandapower: phase-shifting transformer corrections not applied.

**Classification:** claim_supported
**Impact on v5:** Confirms cross-tool nature of T06 (PC-03).

#### probe-016: PowerModels C-5/C-8 infeasibility projections

BFS depth-5 scope ranged from 29-349 branches (vs claimed 500-2,000), making original estimate conservative. Per-contingency DCPF timing (median 0.40s) matches claimed 0.2-0.5s. A 6-network SCOPF (base + 5 contingencies) timed out at 567s -- confirming 500 contingencies is far beyond practical limits.

**Classification:** claim_supported
**Impact on v5:** C-8 MEDIUM should be reduced to 50 contingencies (PC-07); C-5 should cap at N-2 (PC-08).

#### probe-020: PowerSimulations C-3 timing was estimated

The C-3 result file has `wall_clock_seconds: null` and uses "expected to solve" language. The probe's first run (including JIT) exceeded 600s without completing. The "<60s" estimate may refer to solver-only time but is presented without qualification.

**Classification:** claim_supported
**Impact on v5:** Estimated timings cannot support pass/qualified_pass (PC-05).

#### probe-021: PowerSimulations dispatch/limit unit mismatch

The `read_variables()` API returns dispatch in MW while `get_active_power_limits()` returns limits in system-base pu (100 MVA). The A-4 evaluation mislabeled MW values as "pu", creating a false appearance of 100x mismatch. When compared in the same units: gen-1 dispatch 660.85 MW vs Pmax 1040 MW = 63.5% utilization. The ACPF non-convergence in A-4 was caused by applying MW values via a pu-expecting setter.

**Classification:** claim_debunked
**Impact on v5:** A-4/B-7 template should include explicit unit logging (SC-04).

#### probe-022: PowerSimulations binding dual extraction

Set a tight flow gate limit at 50% of unconstrained flow (guaranteed binding). The constrained objective increased 0.62% and `JuMP.dual()` returned -0.1398 for the binding constraint. B-1 only tested the non-binding case (dual=0); the mechanism works correctly for both cases.

**Classification:** claim_supported
**Impact on v5:** B-1 template should include both binding and non-binding gate limits (SC-02).

#### probe-023: PowerSimulations distributed slack on uncongested network

PTDF has 56 variables vs DCP's 95 (difference of 39 = number of buses), confirming PTDF eliminates angle variables. On the uncongested IEEE 39-bus network, both formulations produce identical dispatch (max diff 1.5e-7 MW) and objectives (diff 3.8e-13). The test cannot discriminate because there is no congestion.

**Classification:** claim_supported
**Impact on v5:** A-11 needs a congested network (T01/PC-01).

#### probe-024: PowerSimulations ACPF silent failure on 10k-bus

ACPF returns `Missing` in 5.5s with zero diagnostic information. The `ACPowerFlow` type exposes no tolerance, max-iteration, or warm-start parameters. No error message is thrown. IEEE 39-bus converges successfully (0.49s), confirming this is scale-dependent.

**Classification:** claim_supported
**Impact on v5:** Strengthens T10 -- A-2 should require diagnostic output (PC-02).

#### probe-025: PowerSimulations 100% code coverage

The Codecov badge for PowerSimulations.jl shows 78% coverage, not 100% as reported in E-6. The 22 percentage-point discrepancy indicates the badge was misread or stale.

**Classification:** claim_debunked
**Impact on v5:** E-6 template should require checking the Codecov detail page, not just the badge (SC-03).

#### probe-028: MATPOWER C-10 distributed slack 66-minute timing

MIPS completed 1 iteration in 141.52s on the 1,937-variable, 20,489-constraint QP. MIPS reported "Numerically Failed" after iteration 1, suggesting poor conditioning from the dense PTDF constraint matrix. The single-slack `rundcopf` completed in 3.62s on the same network. The 65-minute total is consistent with ~27 iterations at ~140s each.

**Classification:** claim_supported
**Impact on v5:** Confirms dense PTDF matrix is the root cause of the 400x slowdown.

#### probe-029: MATPOWER contingency sweep 97% Octave overhead

N-1 screening of all 12,706 branches via LODF completed in 0.81s. PTDF+LODF precompute took 17.5s. The containers.Map adjacency construction for 10,000 buses timed out after 260s. Cell-array-based adjacency for the same network completed in 0.106s (2,500x faster). The 97% overhead fraction is confirmed.

**Classification:** claim_supported
**Impact on v5:** The C-5 timing conflates interpreter overhead with tool capability. Scoring should separate algorithm time from infrastructure time.

#### probe-032: MATPOWER MOST loadmd() ingestion failure

The exact error "buses must be numbered consecutively in MPC.bus matrix" is reproduced on ACTIVSg2000. Source code inspection confirms the check at loadmd.m line 302. `ext2int` resolves the bus numbering issue but reveals further MOST input requirements (contab matrix). Standard MATPOWER functions (rundcpf, rundcopf) handle ext2int transparently.

**Classification:** claim_supported
**Impact on v5:** C-4/C-6/C-8 MATPOWER failures are data ingestion bugs, not solver capacity limits. The evaluation should distinguish these.

## Proposed Changes

### Test Redesigns

#### PC-01: Standardize ACTIVSg10k preprocessing to force binding constraints

**Rationale:** ACTIVSg10k DCOPF has no binding branch constraints (max loading 84-85%), producing uniform LMPs across all tools. Tests targeting congestion-driven capabilities (A-3, A-9, A-11, B-8, C-3, C-10) lose discriminative value at grade-assessment scale.
**Evidence:** pypsa-F02, pandapower-F02, gridcal-F05, pm-F01, matpower-F03; probes 006, 007, 023
**Change summary:** Add protocol-level preprocessing: (a) set zero-reactance transformers to x=0.0001 pu, (b) set zero thermal rating branches to RATE_A=9999 MVA, (c) tighten 10-20 highest-flow branch limits to 90% of base-case DCPF flow. Apply uniformly across all test dimensions. Also perturb case39 generator costs (0.5x-2.0x c1 scaling) and tighten 3-5 branch limits.
**Cross-tool evidence count:** 5 tools

#### PC-02: Strengthen ACPF convergence verification requirements

**Rationale:** Probe-001 debunked PyPSA's A-2 MEDIUM pass (0 NR iterations, 83% flat start, converged=False). Multiple tools lack convergence diagnostics. The current pass condition allows tools to claim convergence without demonstrating it.
**Evidence:** pypsa-F05, pandapower-F12, gridcal-F06, pm-F08, psi-F10; probes 001, 024
**Change summary:** A-2 pass condition additions: (a) convergence residual must be reported and below the tool's stated tolerance, (b) number of NR iterations must be reported, (c) voltage magnitudes must differ from flat-start defaults (1.0 pu) on >95% of buses. If the tool cannot report iteration count or residual, document this as a diagnostic quality finding.
**Cross-tool evidence count:** 5 tools

#### PC-03: Account for phase-shifting transformers in PTDF validation

**Rationale:** Probe-010 identified that ACTIVSg10k's 5 phase-shifting transformers create Pbusinj/Pfinj correction terms not included in the standard PTDF formula. This causes 743 MW errors in pandapower and gridcal. Applying the correction eliminates all error to machine precision. The B-9 pass condition (1e-6 tolerance) is unachievable without correction.
**Evidence:** pandapower-F03, gridcal-F04, pypsa-F04; probes 008, 010, 012
**Change summary:** B-9/C-9 pass condition: "If the network contains phase-shifting transformers (nonzero SHIFT column in branch data), the PTDF validation must either (a) apply Pbusinj/Pfinj correction terms, or (b) exclude branches with nonzero shift angles from the accuracy comparison. The 1e-6 tolerance applies to the corrected or filtered comparison."
**Cross-tool evidence count:** 3 tools

#### PC-04: Modify case39 UC parameters to force generator cycling

**Rationale:** All tools capable of SCUC report all generators committed for all 24 hours on case39. The capacity-to-load ratio makes decommitment uneconomical. UC binary variables, min up/down times, and startup costs are never exercised.
**Evidence:** pypsa-F07, psi-F05, matpower-F05
**Change summary:** Either (a) increase PMIN to 30% of PMAX, (b) add 2-3 peaker generators with high startup cost and small capacity, or (c) widen the load range (min load to 40% of peak). Target: at least 2 generators cycling during the 24-hour horizon.
**Cross-tool evidence count:** 3 tools

#### PC-07: Reduce C-8 MEDIUM contingency count from 500 to 50

**Rationale:** 500-contingency SCOPF on 10k-bus is a unanimous fail across all 6 tools. Probe-016 shows even 5 contingencies time out for PowerModels. The test produces zero discriminative value.
**Evidence:** pypsa-F03, pm-F03; probe-016. All 6 tools fail.
**Change summary:** C-8 MEDIUM: reduce from 500 to 50 monitored contingencies (matching SMALL parameter). Allow iterative screening.
**Cross-tool evidence count:** 6 tools

#### PC-08: Cap N-M contingency sweep at N-2 for MEDIUM

**Rationale:** N-4 on 10k-bus produces combinatorial explosion infeasible for all tools. The discriminative signal is at N-1 and N-2 only.
**Evidence:** pypsa-F03, pm-F12, matpower-F02; probes 016, 029
**Change summary:** C-5 MEDIUM: change parameters from x=5/m=4 to x=5/m=2 for graded assessment. N-3 and N-4 are informational only and do not affect pass/fail determination.
**Cross-tool evidence count:** 3 tools

#### PC-09: Replace MATPOWER lossy reference with internal consistency checks

**Rationale:** The A-10 pass condition requires MATPOWER reference validation, but MATPOWER's rundcopf has no loss option producing comparable LMPs. No tool can fulfill this requirement.
**Evidence:** pypsa-F09, gridcal-F08, pm-F06, matpower-F09
**Change summary:** Replace "Validate against MATPOWER reference lossy DC OPF solution" with: "Validate internal consistency: (a) loss components have physically correct signs, (b) total losses are 0.5-3% of total load, (c) lossy objective exceeds lossless objective, (d) loss component LMPs sum with energy and congestion components to total LMP within 1% tolerance."
**Cross-tool evidence count:** 4 tools

### New Tests

No new test IDs are proposed. The changes above modify existing tests.

### Removed Tests

No tests are removed. C-8 MED is modified (reduced contingency count), not removed.

### Scoring Changes

#### PC-05: Require measured wall-clock times for all scalability grades

**Rationale:** PowerSimulations has 4 C-tests with null wall_clock_seconds (estimated only). PowerModels has 2 C-tests scored as fail without execution. Probe-020 confirmed C-3 was never executed.
**Evidence:** psi-F01, pm-F03, gridcal-F13; probes 016, 020
**Before:** Protocol requires measured timings but does not explicitly prohibit grading on estimates.
**After:** "Estimated or projected timings must be clearly labeled with 'estimated' in the frontmatter and cannot support pass or qualified_pass on scalability tests. If a test cannot be executed within the time budget, record fail with the projected timing as supplementary context."
**Cross-tool evidence count:** 3 tools

#### PC-06: Distinguish independent from cascaded failures in scoring

**Rationale:** 4 tools have scalability tests that fail solely because prerequisite expressiveness tests failed. These cascaded failures inflate fail counts without adding signal.
**Evidence:** pandapower-F11, gridcal-F02, psi-F04, pm-F13
**Before:** All failures counted equally in summary tables.
**After:** Add `blocked_by: <test_id>` field to result frontmatter. Report "X independent fails + Y blocked" rather than a single count. Blocked tests do not contribute to the criterion's fail count but are listed for completeness.
**Cross-tool evidence count:** 4 tools

#### PC-10: Calibrate B-4/C-6 perturbation bounds to limit infeasibility

**Rationale:** Uncalibrated perturbations cause 53-99.6% infeasibility across 3 tools. Probe-006 showed the base case converges and uniform load scaling works; combined perturbations are the issue.
**Evidence:** pandapower-F01, gridcal-F10, psi-F13; probe-006
**Before:** No constraint on infeasibility rate from perturbations.
**After:** "Perturbation bounds should be calibrated to produce at most 20% infeasible scenarios on the target network. If infeasibility exceeds 20%, reduce perturbation sigma until the threshold is met and document the final sigma."
**Cross-tool evidence count:** 3 tools

### Rubric Changes

#### RC-01: Clarify that pass+workaround should be qualified_pass

**Rationale:** Multiple tools have tests scored as pass with workaround_class: stable. The protocol states stable workarounds receive B-range grades, implying qualified_pass, but this is not enforced consistently.
**Evidence:** psi-F04, pypsa-F03, pandapower-F05
**Before:** Implicit convention; stable workarounds receive B-range grades.
**After:** "A test requiring any workaround (stable, fragile, or blocking) must be classified as qualified_pass, not pass. The workaround class affects the grade within the B range but never produces a clean pass."

#### RC-02: Separate tool expressiveness from solver performance in scoring

**Rationale:** A-5/C-4 failures on 2000-bus UC conflate HiGHS single-threaded MIP timeout with tool capability. A tool that expresses SCUC in 140 LOC but cannot solve it receives the same fail as a tool that cannot express it at all.
**Evidence:** pm-F04, pypsa-F07, matpower-F06 (solver-specific)
**Before:** Solver timeouts in Suite A produce fail regardless of formulation expressiveness.
**After:** For expressiveness tests (Suite A): if a tool can express the formulation but the open-source solver times out, score as qualified_pass with solver-limitation note. The solver limitation is recorded as a scalability finding (Suite C).

### Skill Updates

Four changes are proposed to the evaluate-tool skill templates:

- **SC-01:** Add peak memory measurement template per language (Python: tracemalloc; Julia: @allocated; Octave: /proc/self/status). Evidence: pandapower-F08, pm-F14, matpower-F11.
- **SC-02:** Add binding constraint test to B-1 template. Include both a non-binding gate limit (verify dual=0) and a binding gate limit (set at 50% of unconstrained flow, verify dual != 0). Evidence: psi-F03, probe-022.
- **SC-03:** Add E-6 badge verification step. Verify coverage percentage by fetching the badge SVG or checking the Codecov/Coveralls detail page rather than relying on the badge rendering alone. Evidence: psi-F12, probe-025.
- **SC-04:** Add unit consistency check to A-4/B-7 dispatch-to-ACPF transfer template. Print base_power, dispatch units, and limit units before transfer. Evidence: psi-F02, probe-021.

## Test-ID Mapping Table

This table enables cross-version comparability. Every v4 test appears exactly once as source_id.

| v4 Test | v5 Test | Relationship | Notes |
|---------|---------|-------------|-------|
| G-1 | G-1 | unchanged | -- |
| G-2 | G-2 | unchanged | -- |
| G-3 | G-3 | unchanged | -- |
| A-1 TINY | A-1 TINY | unchanged | -- |
| A-1 MED | A-1 MED | modified | Standardized ACTIVSg10k preprocessing (PC-01) |
| A-2 TINY | A-2 TINY | unchanged | -- |
| A-2 MED | A-2 MED | modified | Strengthened convergence verification (PC-02): require residual, iteration count, >95% non-flat-start |
| A-3 TINY | A-3 TINY | modified | Perturbed case39 costs and tightened branch limits (PC-01) |
| A-3 MED | A-3 MED | modified | Standardized ACTIVSg10k preprocessing (PC-01) |
| A-4 TINY | A-4 TINY | unchanged | -- |
| A-4 MED | A-4 MED | modified | Standardized ACTIVSg10k preprocessing (PC-01) |
| A-5 TINY | A-5 TINY | modified | Augmented case39 generator fleet to force cycling (PC-04) |
| A-5 SMALL | A-5 SMALL | modified | RC-02: solver timeout now scored as qualified_pass with note |
| A-6 TINY | A-6 TINY | modified | Augmented case39 generator data (inherits PC-04) |
| A-6 SMALL | A-6 SMALL | modified | RC-02: solver timeout now scored as qualified_pass with note |
| A-7 TINY | A-7 TINY | unchanged | -- |
| A-7 MED | A-7 MED | modified | C-5/A-7 graded at N-2 max; N-3+ informational (PC-08) |
| A-8 TINY | A-8 TINY | unchanged | -- |
| A-8 SMALL | A-8 SMALL | unchanged | -- |
| A-9 TINY | A-9 TINY | modified | Perturbed case39 costs to enable cost comparison (PC-01) |
| A-9 SMALL | A-9 SMALL | unchanged | -- |
| A-10 TINY | A-10 TINY | modified | Internal consistency checks replace MATPOWER reference validation (PC-09) |
| A-10 SMALL | A-10 SMALL | modified | Internal consistency checks replace MATPOWER reference validation (PC-09) |
| A-11 TINY | A-11 TINY | modified | Congested network data for LMP differentiation (PC-01) |
| A-11 SMALL | A-11 SMALL | modified | Congested network data for LMP differentiation (PC-01) |
| B-1 TINY | B-1 TINY | modified | Template adds binding gate limit test (SC-02) |
| B-1 MED | B-1 MED | modified | Template adds binding gate limit test (SC-02) |
| B-2 TINY | B-2 TINY | unchanged | -- |
| B-2 MED | B-2 MED | unchanged | -- |
| B-3 TINY | B-3 TINY | unchanged | -- |
| B-3 MED | B-3 MED | unchanged | -- |
| B-4 TINY | B-4 TINY | modified | Calibrated perturbation bounds (PC-10) |
| B-4 SMALL | B-4 SMALL | modified | Calibrated perturbation bounds (PC-10) |
| B-5 TINY | B-5 TINY | unchanged | -- |
| B-5 MED | B-5 MED | unchanged | -- |
| B-6 | B-6 | unchanged | -- |
| B-7 TINY | B-7 TINY | modified | Unit consistency check added to template (SC-04) |
| B-7 MED | B-7 MED | modified | Unit consistency check added to template (SC-04) |
| B-8 TINY | B-8 TINY | modified | Congested network data (PC-01) |
| B-8 SMALL | B-8 SMALL | modified | Congested network data (PC-01) |
| B-9 TINY | B-9 TINY | unchanged | -- |
| B-9 MED | B-9 MED | modified | Phase-shifter correction requirement added (PC-03) |
| C-1 MED | C-1 MED | modified | Memory measurement template added (SC-01); standardized preprocessing (PC-01) |
| C-2 MED | C-2 MED | modified | Memory measurement template added (SC-01) |
| C-3 MED | C-3 MED | modified | Standardized preprocessing (PC-01); measured timing required (PC-05) |
| C-4 SMALL | C-4 SMALL | modified | Measured timing required (PC-05); blocked_by field added (PC-06) |
| C-5 MED | C-5 MED | modified | N-M capped at N-2 for grading (PC-08); measured timing required (PC-05) |
| C-6 SMALL | C-6 SMALL | modified | Calibrated perturbations (PC-10); measured timing required (PC-05) |
| C-7 MED | C-7 MED | unchanged | -- |
| C-8 MED | C-8 MED | modified | Reduced from 500 to 50 contingencies (PC-07) |
| C-9 MED | C-9 MED | modified | Phase-shifter correction requirement added (PC-03) |
| C-10 MED | C-10 MED | modified | Congested network data (PC-01); measured timing required (PC-05) |
| D-1 | D-1 | unchanged | -- |
| D-2 | D-2 | unchanged | -- |
| D-3 | D-3 | unchanged | -- |
| D-4 | D-4 | unchanged | -- |
| D-5 | D-5 | unchanged | -- |
| E-1 | E-1 | unchanged | -- |
| E-2 | E-2 | unchanged | -- |
| E-3 | E-3 | unchanged | -- |
| E-4 | E-4 | unchanged | -- |
| E-5 | E-5 | unchanged | -- |
| E-6 | E-6 | modified | Badge verification step added (SC-03) |
| E-7 | E-7 | unchanged | -- |
| F-1 | F-1 | unchanged | -- |
| F-2 | F-2 | unchanged | -- |
| F-3 | F-3 | unchanged | -- |
| F-4 | F-4 | unchanged | -- |
| F-5 | F-5 | unchanged | -- |
| F-6 | F-6 | unchanged | -- |
| F-7 | F-7 | unchanged | -- |
| F-8 | F-8 | unchanged | -- |
| F-9 | F-9 | unchanged | -- |
| P2-1 | P2-1 | unchanged | -- |
| P2-2 | P2-2 | unchanged | -- |
| P2-3 | P2-3 | unchanged | -- |

**Relationship values:**
- `unchanged` -- test passes through to new version without modification
- `modified` -- same test ID, adjusted parameters/conditions/templates
- `redesigned` -- substantially different test under same or new ID
- `split` -- one test became multiple
- `merged` -- multiple tests became one
- `removed` -- test dropped, not replaced
- `new` -- no predecessor in v4

## Deferred Items

The following items were considered but not included in v5:

1. **Removing B-5 (CSV export) for low signal.** B-5 is trivially passed by all tools, but it documents an interoperability baseline that may matter for Phase 2 integration requirements. Deferred to v6 pending Phase 2 scope clarification.

2. **Adding a CIM/CGMES-native gate test.** Currently only GridCal supports CIM import (P2-1). A CIM gate test would be premature until Phase 2 requirements are finalized and at least 2 tools have CIM support.

3. **Requiring commercial solver benchmarks.** RC-02 separates expressiveness from solver performance but does not mandate commercial solver testing. Adding Gurobi/CPLEX benchmarks would improve scalability comparison but introduces licensing and reproducibility concerns for the evaluation environment.

4. **Normalizing D-5 LOC counts.** Cross-tool LOC comparison is confounded by language differences (Octave boilerplate vs Python one-liners). A normalized metric (e.g., McCabe complexity or essential LOC) was considered but deferred due to complexity of defining "essential" consistently across 3 languages.

5. **Splitting C-7 into mechanism + multi-solver comparison.** T11 identified that C-7 conflates solver swap mechanism (binary) with solver performance (continuous). This split was discussed but deferred because it would require ensuring 2+ solvers are installed per tool in the evaluation environment, which is a container configuration change.

6. **Requiring linked sources for E-7 operational adoption claims.** Theme T13 identified that maturity metrics are research-based without verifiable citations. Requiring linked sources for every claim would significantly increase evaluation effort. Instead, SC-03 addresses the most impactful case (E-6 badge verification) while deferring broader citation requirements.

## Methodology

- **Sweep date:** 2026-03-09
- **Tools analyzed:** 6 of 6 (PyPSA, pandapower, GridCal, PowerModels, PowerSimulations, MATPOWER)
- **Per-tool findings:** 92 total (pypsa: 17, pandapower: 13, gridcal: 16, powermodels: 16, powersimulations: 15, matpower: 14)
- **Extraordinary claims flagged:** 19 (pypsa: 3, pandapower: 3, gridcal: 3, powermodels: 3, powersimulations: 6, matpower: 3; note: some overlap with findings)
- **Probes run:** 18 (pypsa: 2, pandapower: 5, gridcal: 1, powermodels: 1, powersimulations: 6, matpower: 3)
- **Probe classifications:** 4 claim_debunked, 14 claim_supported
- **Cross-cutting themes:** 13
- **Proposed protocol changes:** 10 (PC-01 through PC-10)
- **Proposed rubric changes:** 2 (RC-01, RC-02)
- **Proposed skill updates:** 4 (SC-01 through SC-04)
- **Evidence threshold:** Changes require cross-tool evidence from 3+ tools
- **Protocol source:** v4
