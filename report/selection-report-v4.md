# Phase 1 Tool Selection Report
## Contract FA714626C0006 | Grid Research Company LLC

**Protocol version:** v4
**Date:** 2026-03-09

---

## Methodology

Six open-source power system modeling tools were evaluated against a six-criterion rubric (Expressiveness, Extensibility, Scalability, Accessibility, Maturity, Supply Chain) using standardized test suites on ACTIVSg 2k-bus and 10k-bus reference networks with open-source solvers only (HiGHS, SCIP, Ipopt, GLPK). Supply Chain serves as a gate criterion: any tool graded C+ or below is disqualified. The remaining five criteria are ranked by lexicographic priority — Expressiveness > Extensibility > Scalability > Accessibility > Maturity — with ties broken by the next criterion in sequence. MATPOWER is designated reference benchmark only per the rubric: its canonical MATLAB runtime disqualifies it for restricted-network deployment, and it is excluded from primary ranking while retained in the grade table for comparison.

## Grade Comparison

| Rank | Tool | Expressiveness | Extensibility | Scalability | Accessibility | Maturity | Supply Chain |
|------|------|---------------|---------------|-------------|---------------|----------|--------------|
| 1 | PyPSA | B+ | A- | B- | B+ | A- | A |
| 2 | PowerModels | B- | A- | B- | B- | C+ | A |
| 3 | PowerSimulations | B- | B+ | B- | C+ | B | A- |
| 4 | pandapower | C+ | B | B- | B+ | A- | A |
| 5 | GridCal | C+ | B | B- | C+ | B- | B |
| — | MATPOWER* | A- | A- | B- | B | C+ | A |

All six tools passed the Supply Chain gate (all >= B). PyPSA leads on Expressiveness (B+), a full grade step above the B- tie between PowerModels and PowerSimulations. PowerModels breaks that tie with Extensibility A- vs B+. pandapower and GridCal tie through Scalability; pandapower wins on Accessibility (B+ vs C+).

*\*MATPOWER is included as a reference benchmark only. The MATLAB runtime is a proprietary binary incompatible with classified network authorization. All MATPOWER testing used GNU Octave, which lacks HiGHS MEX bindings and has no production deployment precedent. MATPOWER is excluded from primary ranking per rubric designation.*

**Footnote — GridCal:** MPL-2.0 license may require legal review for government deployment.

## Sensitivity Analysis

Three alternative ranking scenarios were proposed by the evaluator and confirmed by the GRC principal, all with MATPOWER excluded per rubric designation.

**Scenario 1 — Maturity as top priority** (Maturity > Expressiveness > Extensibility > Scalability > Accessibility): PyPSA holds #1. PyPSA's A- Maturity ties with pandapower for highest among eligible tools; Expressiveness B+ breaks the tie. Full order: PyPSA, pandapower, PowerSimulations, GridCal, PowerModels.

**Scenario 2 — Equal-weight scoring** (sum of numeric grade values, A=9, A-=8, B+=7, B=6, B-=5, C+=4): PyPSA holds #1 with 35 points. Full order: PyPSA (35), pandapower (30), PowerModels (27), PowerSimulations (27), GridCal (24).

**Scenario 3 — Extensibility over Expressiveness** (Extensibility > Expressiveness > Scalability > Accessibility > Maturity): PyPSA holds #1. PyPSA and PowerModels tie on Extensibility A-; PyPSA breaks the tie with Expressiveness B+ vs B-. Full order: PyPSA, PowerModels, PowerSimulations, pandapower, GridCal.

**Summary:** PyPSA holds #1 in all three alternative scenarios. The recommendation is robust to alternative criterion weightings.

---

## Recommendation

### Selected Tool: PyPSA

PyPSA wins decisively on criterion 1: Expressiveness B+ is a full grade step above the B- shared by the next two eligible tools. Beyond this primary differentiator, PyPSA has the strongest balanced profile among all eligible candidates — no grade below B-, with A- in both Extensibility and Maturity and B+ in Accessibility. It demonstrated first-class preventive SCOPF via `optimize_security_constrained()` (A-9), custom constraint injection in 2 lines of code via Linopy model split (B-1), and a mature multi-contributor development community backed by institutional funding at TU Berlin and KIT. The Python ecosystem ensures NRL analysts can integrate PyPSA into existing workflows without adopting a niche language runtime.

### Head-to-Head: Critical Phase 2 Capabilities

| Capability | PyPSA | PowerModels | PowerSimulations | MATPOWER* |
|------------|-------|-------------|------------------|-----------|
| Preventive SCOPF | Native `optimize_security_constrained()` (A-9) | Extension, ~140 LOC JuMP | Gap | Native MOST (A-9) |
| Distributed Slack | Extension via reference bus config | Extension via API | Gap | Native `makePTDF` weights (B-9) |
| PWL Cost Curves | Gap; SOS2 via `extra_functionality` ~50-100 LOC | Native (P2-2) | Native (P2-2) | Native (P2-2) |
| PSS/E RAW Parsing | Gap; bridge via grg-psse, 1-2 days (P2-1) | Native v33 parser (P2-1) | Native v30/32/33 (P2-1) | Native `psse2mpc()` Rev 23-33+ (P2-1) |
| Custom Constraints | Native, 2 LOC Linopy model split (B-1) | Native, two-level JuMP API (B-1) | Extension | Native callbacks (B-1) |
| UC/ED Pipeline | SCUC times out at 2k-bus with HiGHS (A-5) | SCUC requires ~140 LOC JuMP (A-5) | Native rich formulations (A-5, A-6) | Native MOST (A-5, A-6) |

*\*MATPOWER included as reference column only — excluded from primary ranking per rubric designation.*

### Runner-Up: PowerModels

PowerModels ranks second on the strength of its Extensibility (A-) and its JuMP foundation, which provides the most flexible constraint injection API among all evaluated tools (B-1). It demonstrated native PSS/E v33 parsing (P2-1), native piecewise-linear cost curves (P2-2), and PTDF computation with sub-1e-11 error at 10k-bus (B-9). PowerModels would pass all three Phase 2 readiness checks where PyPSA fails two.

PowerModels was not selected for three reasons. First, its B- Expressiveness reflects the cost of that flexibility: 6 of 11 Suite A tests required user-assembled JuMP code averaging 269 lines per test — the tool provides primitives, not solutions. Second, C+ Maturity with a bus factor of 1 (ccoffrin, 82.4% of commits) and pre-1.0 status after 9+ years of development signals sustainability risk comparable to MATPOWER. Third, Julia remains a niche language for the government workforce; NRL analysts are far more likely to have Python experience than Julia fluency. PowerModels should be reconsidered if PyPSA's SCUC scalability limitation proves unresolvable or if the JuMP modeling layer becomes critical for Phase 2 custom formulations.

### Risk Register

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **SCUC scalability:** PyPSA SCUC times out at SMALL scale (2k-bus) with HiGHS single-threaded (A-5). The target FNM is ~6,000 buses. | HIGH | Evaluate commercial-grade open-source solver configurations (HiGHS parallel, SCIP). Implement temporal decomposition (4-6 hour blocks). If PyPSA SCUC remains intractable, use PowerModels/JuMP for commitment stage only, feeding dispatch back to PyPSA. |
| **No native stochastic optimization:** PyPSA has no stochastic formulation — scenario trees, two-stage programs, and chance constraints are absent (A-8). This is a blocking gap for multi-scenario congestion analysis. | HIGH | Implement deterministic scenario loop with post-hoc aggregation for Phase 2 MVP. Evaluate Linopy-level stochastic extension feasibility. Accept that stochastic optimization is a Phase 3 capability if native support is not forthcoming. |
| **PWL cost curves require extension:** Production market clearing uses piecewise-linear bid curves. PyPSA supports only linear/quadratic costs natively (P2-2). SOS2 formulation via `extra_functionality` is ~50-100 LOC. | MED | Implement SOS2 PWL extension early in Phase 2. The `extra_functionality` callback API is stable and documented (B-1). Validate against MATPOWER reference solutions with identical cost data. |
| **Linopy post-processing bottleneck:** Shadow-price extraction via linopy creates 10+ minute overhead at 10k-bus scale. This affects LMP computation in operational-speed workflows. | MED | Profile linopy shadow-price path and identify optimization targets. Evaluate direct solver dual extraction bypassing linopy post-processing. If unresolvable, accept longer solve times for planning studies and implement caching for repeated analyses. |

---

## Phase 2 Development Scope

### Tool-Intrinsic Gaps

| Gap | Effort | Notes |
|-----|--------|-------|
| PSS/E RAW parser integration | days | Bridge via grg-psse Python package. PyPSA has no native parser (P2-1). grg-psse handles v33; FNM version compatibility requires validation. |
| Piecewise-linear cost curves | days | SOS2 formulation via `extra_functionality` callback, ~50-100 LOC (P2-2). Stable API, well-documented extension point. |
| SCUC scalability | weeks | Profile and resolve timeout at 2k-bus (A-5). Solver tuning (MIP gap, parallel threads), formulation tightening, or temporal decomposition. May require hybrid approach with JuMP for commitment stage. |
| Stochastic optimization wrapper | weeks | No native support (A-8). Build scenario loop with correlated timeseries injection via PyPSA's timeseries API. Not a true stochastic program — deterministic solves with post-hoc aggregation. |
| Linopy shadow-price performance | weeks | 10+ min overhead at 10k-bus for dual extraction. Profile and optimize, or implement direct solver dual access. |

### Tool-Adjacent Engineering

| Work Item | Effort | Notes |
|-----------|--------|-------|
| FNM ingestion + imputation | months | Target FNM in legacy PSS/E format. Parse via grg-psse bridge, then validate and impute missing data (multi-section lines, switched shunts, area interchange). FNM-specific topology quirks require manual curation. |
| OASIS data pipeline | weeks | Ingest public ISO OASIS data (binding constraints, LMPs, generation, load) for validation targets. Build automated refresh and alignment with FNM bus/branch numbering. |
| PTDF calibration + validation | weeks | Compute PTDFs from solved AC base case. PyPSA exposes network matrices; validate against published shift factors where available. Calibrate loss factors against published MCL components. |
| Contingency list curation | weeks | Build monitored contingency list from OASIS binding constraint data. Map published constraint names to FNM branch IDs. Prioritize by historical binding frequency. |

### Operational Workflow

| Work Item | Effort | Notes |
|-----------|--------|-------|
| Scenario management framework | weeks | Build scenario definition, execution, and result storage layer around PyPSA. Support parameter sweeps (load levels, contingency sets, generator outages) with reproducible configuration. |
| LMP validation loop | weeks | Automated comparison of computed LMPs against ISO-published values. Decompose discrepancies into energy, congestion, and loss components. Flag systematic biases for calibration. |
| Result visualization | weeks | Interactive visualization of LMP heatmaps, binding constraint patterns, and contingency impact on the FNM topology. Python-native (matplotlib/plotly) within PyPSA's ecosystem. |
| Analyst workflow documentation | days | Runbooks for common Phase 2 workflows: running a day-ahead scenario, interpreting results, modifying contingency lists, adjusting network parameters. |

---

## Provenance

- **Protocol version:** v4
- **Synthesis files:**
  - `worktree-eval/pypsa-v4:evaluations/pypsa/results/synthesis.md` @ 302d44c
  - `worktree-eval/pandapower-v4:evaluations/pandapower/results/synthesis.md` @ e34e3cc
  - `worktree-eval/gridcal-v4:evaluations/gridcal/results/synthesis.md` @ 7fc0686
  - `worktree-eval/powermodels-v4:evaluations/powermodels/results/synthesis.md` @ 10c40c7
  - `worktree-eval/powersimulations-v4:evaluations/powersimulations/results/synthesis.md` @ e413b5d
  - `worktree-eval/matpower-v4:evaluations/matpower/results/synthesis.md` @ d5d90dc
- **Generated:** 2026-03-09T21:45:00Z
- **Ranking algorithm:** Lexicographic on [Expressiveness, Extensibility, Scalability, Accessibility, Maturity] with Supply Chain gate (<=C+ disqualifies). MATPOWER excluded per rubric designation (reference benchmark only).
