# Cross-Tool Comparison Matrices — v10-to-v11 Sweep

**Key:**
- `P` = pass
- `QP` = qualified_pass
- `F` = fail
- `I` = informational (not graded)
- `—` = skipped / not applicable / blocked by gate
- `?` = test not run / unknown

**Dominant factor abbreviations:** capability (C), infrastructure (I), network (N), test_design (TD)

**Signal levels:** High (H), Medium (M), Low (L)

**Outcome spread:** Number of distinct graded outcomes across tools (P/QP/F; excludes —, I, ?)

---

## Suite G — Gate Ingestion Tests

| Test | pypsa | pandapower | gridcal | powermodels | powersimulations | matpower | Spread | Signal | Dom. Factor |
|------|-------|------------|---------|-------------|-----------------|---------|--------|--------|-------------|
| G-1 TINY | P | P | P | P | P | P | 1 | L | — |
| G-2 SMALL | P | P | P | P | P | P | 1 | L | — |
| G-3 MEDIUM | P | P | P | P | P | P | 1 | L | — |

**Notes:** Universal pass across all tools. Low signal by design. See T-14 and PC-14. Retain as gates but exclude from pass rate statistics.

---

## Suite A — Problem Expressiveness

| Test | pypsa | pandapower | gridcal | powermodels | powersimulations | matpower | Spread | Signal | Dom. Factor |
|------|-------|------------|---------|-------------|-----------------|---------|--------|--------|-------------|
| A-1 DCPF | P | P | P | P | P | P | 1 | L | — |
| A-2 ACPF | P | P | P | P | QP | P | 2 | M | C |
| A-3 DCOPF | P | P | P(soft) | P | P | P | 1* | H | TD |
| A-4 ACPF (loaded) | P | P | P | P | P | P | 1 | L | — |
| A-5 SCUC | QP | F | P | QP | P | QP | 3 | H | N/TD |
| A-6 SCED | QP | F | QP | QP | QP | P | 3 | M | N/TD |
| A-7 | — | — | — | — | — | — | — | — | — |
| A-8 | — | — | — | — | — | — | — | — | — |
| A-9 SCOPF | QP | F | QP | QP | QP | F | 3 | M | N/TD |
| A-10 Lossy DCOPF | P | F | QP | F | F | F | 3 | H | C |
| A-11 Dist. Slack OPF | QP(block) | F | QP | QP | P | QP | 3 | M | C |
| A-12 Multi-Period Storage | P | F | P | P | QP | QP | 3 | H | C |

**A-3 note:** gridcal DCOPF uses soft branch flow constraints (probe-005 confirmed_issue). The 'P' for gridcal is misleading — branch 2_3_1 reaches 103.5% loading. If hard-constraint enforcement were required, gridcal A-3 = F. See T-10, PC-10.

**A-5 note:** Spread of 3 is substantive, but cycling evidence is weak across all tools (T-02). SCUC formulation completeness is demonstrated; binding behavioral proof is not (PC-02).

**A-9 note:** All QP/F results reflect network-level N-1 infeasibility or radial-topology limitations rather than tool capability gaps (T-16, PC-16). probe-009: inconclusive (PowerModels Benders).

---

## Suite B — Extensibility

| Test | pypsa | pandapower | gridcal | powermodels | powersimulations | matpower | Spread | Signal | Dom. Factor |
|------|-------|------------|---------|-------------|-----------------|---------|--------|--------|-------------|
| B-1 Custom constraints | QP | QP | QP | P | P | QP | 2 | M | C |
| B-2 Custom cost function | P | P | P | P | P | P | 1 | L | — |
| B-3 Contingency sweep | P | P | P | P | P | P | 1 | L | — |
| B-4 Stochastic scenario | P | P | QP | P | P | P | 2 | L | C |
| B-5 Interoperability | P | P | P | P | P | QP | 2 | L | TD |
| B-6 Architecture audit | P | P | P | P | P | P | 1 | L | — |
| B-7 | — | — | — | — | — | — | — | — | — |
| B-8 Ref. bus config | P | P | P | P | P | P | 1 | L | TD |
| B-9 PTDF extraction | P | P | P | P | P | P | 1 | L | — |

**B-1 note:** All QP outcomes arise from different friction points (PyPSA: linopy internals, pandapower: PYPOWER monkey-patch, gridcal: API verbosity, matpower: OPF extension API complexity). The spread=2 is meaningful.

**B-4 note:** gridcal QP reflects TapPhaseControl enum bug (single-version bug, likely fixable).

**B-5 note:** matpower QP is arguably ambiguous — 3 lines meets the <5 LOC criterion for minimal export; 12 lines for production-quality (matpower-F09). See PC-07 for qualified_pass severity discussion.

**B-8 note:** All P outcomes are vacuous for DC OPF — LMP is invariant to slack bus choice. See T-11, PC-11.

---

## Suite C — Scalability

| Test | pypsa | pandapower | gridcal | powermodels | powersimulations | matpower | Spread | Signal | Dom. Factor |
|------|-------|------------|---------|-------------|-----------------|---------|--------|--------|-------------|
| C-1 DCPF MEDIUM | — | — | P | P | P | — | 1 | L | TD |
| C-2 ACPF MEDIUM | — | — | P | P | P | — | 1 | L | TD |
| C-3 DCOPF MEDIUM | — | — | P | P | QP | — | 2 | M | C |
| C-4 SCUC SMALL | F | F | QP | F | P | F | 3 | H | C/N |
| C-5 ACPF SMALL | P | P | P | P | P | P | 1 | L | — |
| C-5 ACPF MEDIUM | P | — | P | P | P | — | 1 | L | — |
| C-7 Solver swap MEDIUM | — | — | P | P | P | — | 1 | L | I |
| C-8 SCOPF SMALL | — | — | P | P | QP | P | 2 | M | C |
| C-8 SCOPF MEDIUM | — | — | P(vac) | P(nc) | QP(crash) | — | 2 | L | N/TD |
| C-9 PTDF MEDIUM | — | — | P | P | P | — | 1 | L | — |
| C-10 Dist. Slack MEDIUM | — | — | P | P | P | — | 1 | L | — |

**C-1, C-2, C-3 note:** pypsa, pandapower, matpower have these skipped by C-SMALL gate despite evidence of MEDIUM-scale capability (e.g., pypsa/pandapower pass G-FNM-3 at 27K buses; pandapower solves DCPF at 28K in 0.4s). Gate design conflates MILP and LP/PF scalability (T-01, PC-01).

**C-3 note:** powersimulations QP because StaticBranchUnbounded removed all branch flow limits — the 'DCOPF' is actually an unconstrained ED (powersimulations-F01). See T-03.

**C-4 note:** Highest spread (3) and highest signal. Genuine capability differentiation. gridcal QP via snapshot workaround (no inter-temporal coupling). powersimulations P at 404s single-threaded (may be much faster multi-threaded; powersimulations-F16).

**C-8 MEDIUM note:** 'vac' = vacuous pass (zero redispatch on uncongested network); 'nc' = non-converged (1 Benders iteration); 'crash' = HiGHS OTHER_ERROR. None represent genuine SCOPF capability evidence. See T-03, PC-03.

---

## Suite D — Accessibility

| Test | pypsa | pandapower | gridcal | powermodels | powersimulations | matpower | Spread | Signal | Dom. Factor |
|------|-------|------------|---------|-------------|-----------------|---------|--------|--------|-------------|
| D-1 Install timing | I | I | I | I | I | I(est) | — | L | — |
| D-2 Documentation | I | I | I | I | I | I | — | M | C |
| D-3 Examples | I | I | I | I | I | I | — | M | C |
| D-4 Error quality | I | I | I | I | I | I | — | H | C |
| D-5 API ergonomics | I | I | I | I | I | I | — | M | C |

**D-4 note:** gridcal D-4 'poor' rating is partially confounded by soft-constraint formulation design (gridcal-F07). The test uses zero-rated branches expecting infeasibility detection, but soft constraints absorb the violation. True LP infeasibility (load > capacity) was not tested.

**D-3 note:** powersimulations 0/10 example pass rate inflated by PowerSystemCaseBuilder dependency gap (powersimulations-F13). Cross-tool comparison on D-3 should account for ecosystem packaging differences between Python and Julia tools.

---

## Suite E — Maturity & Sustainability

| Test | pypsa | pandapower | gridcal | powermodels | powersimulations | matpower | Spread | Signal | Dom. Factor |
|------|-------|------------|---------|-------------|-----------------|---------|--------|--------|-------------|
| E-1 Release cadence | I | I | I | I | I | I | — | M | — |
| E-2 CI/CD | I | I | I | I | I | I | — | M | — |
| E-3 Test coverage | I | I | I | I | I | I | — | M | — |
| E-4 Issue response | I | I | I | I | I | I | — | M | — |
| E-5 Deprecation policy | I | I | I | I | I | I | — | L | — |
| E-6 Core maintainers | I | I | I | I | I | I | — | H | — |
| E-7 Operational adoption | I | I | I | I | I | I | — | H | — |

**E-7 note:** gridcal's claimed adoption (Redeia, Schneider Electric, GE Vernova) originates primarily from project's own documentation (gridcal-F11). Unverified from public sources.

---

## Suite F — Supply Chain

| Test | pypsa | pandapower | gridcal | powermodels | powersimulations | matpower | Spread | Signal | Dom. Factor |
|------|-------|------------|---------|-------------|-----------------|---------|--------|--------|-------------|
| F-1 Dependency count | P | P | P | P | P | P | 1 | L | — |
| F-2 Transitive deps | P | P | P | P | P | P | 1 | L | — |
| F-3 License audit | P | P | P | QP(ZIB) | P | P | 2 | H | I |
| F-4 CVE history | P | P | P | P | P | P | 1 | L | — |
| F-5 Build reproducibility | P | P | P | P | P | P | 1 | L | — |
| F-6 Source inspectability | P | P | P | P | P | P | 1 | L | — |
| F-7 Native extensions | P | P | P | P | P | P | 1 | L | — |
| F-8 Solver dependency | P | P | P | P(wrong) | P | P | 1 | H | I |
| F-9 Container isolation | P | P | P | P | P | P | 1 | L | — |

**F-3 / F-8 note:** PowerModels F-3 correctly classifies SCIP_jll v0.2.1 as ZIB Academic. F-8 incorrectly claims Apache 2.0 — probe-010 confirmed this is wrong (Apache 2.0 switch was at SCIP 8.0.3, not 8.0.0). F-8 P for powermodels should be QP. See T-13, PC-13.

---

## Suite G-FNM — FNM Ingestion Suite

| Test | pypsa | pandapower | gridcal | powermodels | powersimulations | matpower | Spread | Signal | Dom. Factor |
|------|-------|------------|---------|-------------|-----------------|---------|--------|--------|-------------|
| G-FNM-1 PSS/E ingestion | F | F | F | QP | ? | F | 2 | H | I |
| G-FNM-2 Field coverage | P | ? | QP | P | ? | — | 2 | M | C |
| G-FNM-3 DCPF accuracy | P | F | QP | F | F | P | 3 | H | C/I |
| G-FNM-4 ACPF convergence | ? | F | F | F | ? | I | 2 | H | C/I |
| G-FNM-5 Supplemental data | ? | ? | ? | ? | ? | I | — | M | C |

**G-FNM-1 note:** 4 of 6 tools have no PSS/E v31 ingestion path (pypsa: no importer, pandapower: no CSV import, gridcal: v35-hardcoded parser, powermodels: v31 header crash). matpower ingested directly (native format). All non-matpower tools used MATPOWER fallback. See T-09, PC-09.

**G-FNM-3 note:**
- pypsa P: probe-001 confirmed actual deviations are 1.07e-8 deg (floating-point noise); PASS grade correct.
- gridcal QP: 326 branches with deviations up to 562,955% (transformer-adjacent pattern, probe-007 plausible_with_caveats). Material DCPF limitation for real networks.
- powermodels F: DCPPowerModel ignores transformer taps; 2.43% pass rate. DCMPPowerModel not tested (test design constrained to solve_dc_pf; pm-F04).
- powersimulations F: PowerFlows.jl simplified B-matrix ignores tap ratios; 86.8% bus angles outside 1-deg tolerance.
- matpower P: Self-referential (reference generated by MATPOWER itself; matpower-F02).
- pandapower F: 596.6% max branch flow deviation; 101-bus cluster with 14-21 deg angle bias; classified as data_ingestion_error.

---

## P2 Readiness (Informational Only)

| Test | pypsa | pandapower | gridcal | powermodels | powersimulations | matpower |
|------|-------|------------|---------|-------------|-----------------|---------|
| P2-1 PSS/E parsing | I | I | I | I | — | — |
| P2-2 AC OPF feasibility | I | I | I | I | — | — |
| P2-3 Multi-area coordination | I | I | I | I | — | — |

P2 tests are informational only and not graded. Not included in cross-tool comparison statistics.

---

## Summary Table: Graded Outcomes by Test Suite

| Suite | pypsa | pandapower | gridcal | powermodels | powersimulations | matpower |
|-------|-------|------------|---------|-------------|-----------------|---------|
| G (gate) | 3P | 3P | 3P | 3P | 3P | 3P |
| A (express.) | 8P 3QP 0F | 4P 0QP 6F | 6P 4QP 0F | 5P 5QP 2F | 7P 4QP 1F | 7P 2QP 1F |
| B (extend.) | 6P 2QP 0F | 7P 1QP 0F | 7P 1QP 0F | 8P 0QP 0F | 8P 0QP 0F | 7P 1QP 0F |
| C (scale) | 2P 0QP 1F (+7—) | 2P 0QP 0F (+8—) | 9P 2QP 0F | 9P 1QP 1F | 8P 1QP 1F (+1—) | 4P 1QP 1F (+8—) |
| F (supply) | 9P 0QP 0F | 9P 0QP 0F | 9P 0QP 0F | 8P 1QP 0F | 9P 0QP 0F | 9P 0QP 0F |
| G-FNM | 1P 0QP 1F (+3?) | 0P 0QP 2F (+3?) | 1P 1QP 1F (+2?) | 1P 1QP 2F (+1?) | 0P 0QP 1F (+4?) | 2P 0QP 1F (+2I) |

**Footnote:** '—' = skipped by gate; '?' = not run / unknown; 'I' = informational.
D and E suites are all informational across all tools and omitted from this summary.

---

## High-Signal Test Summary

Tests with High signal and spread >= 2 — the tests most likely to produce useful cross-tool differentiation:

| Test | Signal | Spread | Key Pattern |
|------|--------|--------|------------|
| C-4 SCUC SMALL | H | 3 | Genuine capability split: tools with/without native SCUC |
| G-FNM-3 DCPF | H | 3 | B-matrix tap-ratio formulation matters at real-grid scale |
| A-10 Lossy DCOPF | H | 3 | Only pypsa passes; lossy formulation rare in this tool set |
| A-12 Multi-Period Storage | H | 3 | Differentiated by multi-period OPF + storage API |
| F-3 License audit | H | 2 | SCIP ZIB Academic for PowerModels (probe-010 confirmed) |
| A-3 DCOPF (hard constraint) | H | — | GridCal soft constraints confirmed (probe-005); requires protocol fix |
| G-FNM-1 PSS/E ingestion | H | 2 | Universal v31 parser gap; infrastructure finding |

---

## Probe Integration Summary

| Probe | Tool | Test | Classification | Impact on Matrix |
|-------|------|------|---------------|-----------------|
| probe-001 | pypsa | G-FNM-3 | claim_debunked (weak) | P grade confirmed; report precision is display artifact |
| probe-003 | pandapower | A-3 | claim_supported | 46/46 shadow prices are real; sweep concern refuted |
| probe-005 | gridcal | A-3 | confirmed_issue | GridCal A-3 P is misleading; soft constraints confirmed |
| probe-007 | gridcal | G-FNM-3 | classification_plausible_with_caveats | QP defensible but understates severity; no magnitude cap |
| probe-009 | powermodels | A-9 | inconclusive | Benders mechanism real; convergence never demonstrated |
| probe-010 | powermodels | F-3/F-8 | claim_supported (F-3) | SCIP ZIB Academic at pinned version; F-8 P should be QP |
| probe-013 | powersimulations | A-2 | claim_debunked | Iteration count at @info; return type = convergence guarantee; A-2 QP overstates limitation |
| probe-016 | matpower | A-5 | claim_debunked | GLPK failure is genuine (GLP_ETMLIM, status=-1); not an exit-flag mapping bug |
