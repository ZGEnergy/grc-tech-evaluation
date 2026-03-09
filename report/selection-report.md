# Phase 1 Tool Selection Report
## Contract FA714626C0006 | Grid Research Company LLC

**Protocol version:** v4
**Date:** 2026-03-09

---

## Methodology

Six open-source power system modeling tools were evaluated against a six-criterion rubric (Expressiveness, Extensibility, Scalability, Accessibility, Maturity, Supply Chain) using standardized test suites on ACTIVSg 2k-bus and 10k-bus reference networks with open-source solvers only. Supply Chain serves as a gate criterion: any tool graded C+ or below is disqualified. The remaining five criteria are ranked by lexicographic priority — Expressiveness > Extensibility > Scalability > Accessibility > Maturity — with ties broken by the next criterion in sequence.

## Grade Comparison

| Rank | Tool | Expressiveness | Extensibility | Scalability | Accessibility | Maturity | Supply Chain |
|------|------|---------------|---------------|-------------|---------------|----------|--------------|
| 1 | MATPOWER | A- | A- | B- | B | C+ | A |
| 2 | PyPSA | B+ | A- | B- | B+ | A- | A |
| 3 | PowerModels | B- | A- | B- | B- | C+ | A |
| 4 | PowerSimulations | B- | B+ | B- | C+ | B | A- |
| 5 | pandapower | C+ | B | B- | B+ | A- | A |
| 6 | GridCal | C+ | B | B- | C+ | B- | B |

All six tools passed the Supply Chain gate (all >= B). MATPOWER ranks first on Expressiveness (A-). PowerModels and PowerSimulations tie on Expressiveness (B-); PowerModels breaks the tie with Extensibility A- vs B+. pandapower and GridCal tie through Scalability; pandapower wins on Accessibility (B+ vs C+).

**Footnote — MATPOWER/Octave:** All testing used GNU Octave, not MATLAB. Octave lacks HiGHS MEX bindings (limiting MILP solver options) and has no production deployment precedent. This is a real Phase 2 operational consideration.

**Footnote — GridCal:** MPL-2.0 license may require legal review for government deployment.

## Sensitivity Analysis

Three alternative ranking scenarios were proposed by the evaluator and confirmed by the GRC principal to test the robustness of the MATPOWER selection.

**Scenario 1 — Maturity as top priority** (Maturity > Expressiveness > Extensibility > Scalability > Accessibility): #1 changes to PyPSA. MATPOWER drops to #5 on C+ Maturity (bus factor 1, no institutional funding). PyPSA's A- Maturity with active multi-contributor development drives it to the top. Full order: PyPSA, pandapower, PowerSimulations, GridCal, MATPOWER, PowerModels.

**Scenario 2 — Equal-weight scoring** (sum of numeric grade values): #1 changes to PyPSA (35 vs 31). PyPSA's balanced profile outperforms MATPOWER's peak-but-trough distribution. Full order: PyPSA (35), MATPOWER (31), pandapower (30), PowerModels (27), PowerSimulations (27), GridCal (24).

**Scenario 3 — Extensibility over Expressiveness** (Extensibility > Expressiveness > Scalability > Accessibility > Maturity): MATPOWER holds #1. Three tools tie on Extensibility A-; MATPOWER breaks the tie with Expressiveness A-. Full order: MATPOWER, PyPSA, PowerModels, PowerSimulations, pandapower, GridCal.

**Summary:** MATPOWER holds #1 only under lexicographic ranking with Expressiveness on top. PyPSA takes #1 in two of three alternative scenarios.

---

## Recommendation

### Selected Tool: MATPOWER

MATPOWER ranks first because it is the only tool that natively expresses the full suite of problems required for Phase 2 CAISO congestion reproduction. MOST provides native SCUC, SCED, stochastic multi-scenario optimization, and preventive SCOPF (A-5, A-6, A-8, A-9) — capabilities that require hundreds of lines of user-assembled code or are entirely absent in every other evaluated tool. Its `makePTDF()` function with distributed slack weighting (B-9) and native piecewise-linear cost curve support (P2-2) directly address CAISO market clearing primitives. The Expressiveness advantage (A- vs B+ for the runner-up) reflects not just breadth but depth: MATPOWER's formulations are the reference standard against which power systems tools are implicitly measured.

The selection carries real risk. MATPOWER has a bus factor of 1 (E-3, E-4), C+ Maturity, and zero production deployments on Octave. These risks are addressable — see the Risk Register below — but they are not cosmetic.

### Head-to-Head: Critical Phase 2 Capabilities

| Capability | MATPOWER | PyPSA | PowerModels | PowerSimulations |
|------------|----------|-------|-------------|------------------|
| Preventive SCOPF | Native (A-9) | Native (A-9) | Extension (~140 LOC JuMP) | Gap |
| Distributed Slack | Native, `makePTDF` weights (B-9) | Extension | Extension | Gap |
| PWL Cost Curves | Native (P2-2) | Gap; SOS2 via `extra_functionality` ~50-100 LOC | Native (P2-2) | Native (P2-2) |
| PSS/E RAW Parsing | Native `psse2mpc()` Rev 23-33+ (P2-1) | Gap; bridge via grg-psse 1-2 days (P2-1) | Native v33 parser (P2-1) | Native v30/32/33 (P2-1) |
| Custom Constraint Injection | Native via MATPOWER callbacks (B-1) | Native, 2 LOC via Linopy model split (B-1) | Native, two-level JuMP API (B-1) | Extension |
| UC/ED Pipeline | Native MOST (A-5, A-6) | SCUC times out at 2k-bus with HiGHS (A-5) | SCUC requires ~140 LOC JuMP (A-5) | Native rich formulations (A-5, A-6) |
| Stochastic Optimization | Native MOST scenarios (A-8) | Gap (A-8) | Gap (A-8) | Gap (A-8) |

### Runner-Up: PyPSA

PyPSA is the strongest alternative and would be the selection under two of three sensitivity scenarios. Its balanced profile (no grade below B-), institutional backing (A- Maturity), and Python ecosystem make it the lowest-risk choice for a team prioritizing sustainability and workforce accessibility. PyPSA demonstrated native SCOPF via `optimize_security_constrained()` (A-9) and clean custom constraint injection in 2 LOC (B-1).

PyPSA was not selected because it lacks three capabilities MATPOWER provides natively: stochastic multi-scenario optimization (A-8, blocking), SCUC at operational scale (A-5, times out at 2k-bus with HiGHS), and piecewise-linear cost curves (P2-2, requires extension). The SCUC limitation is the most consequential — without viable unit commitment, PyPSA cannot serve as the single-tool backbone for the full SCUC-to-DCOPF-to-ACPF pipeline that Phase 2 requires. PyPSA should be reconsidered if MATPOWER's bus-factor risk materializes or if Octave runtime proves unworkable at CAISO FNM scale.

### Risk Register

| Risk | Severity | Mitigation |
|------|----------|-----------|
| **Bus factor 1:** Zimmerman (98.5% of commits) has left Cornell with no announced successor. A health event or career change could halt development indefinitely. | HIGH | Pin to a specific MATPOWER release for Phase 2. Maintain a GRC fork with any Phase 2 patches. Document all extensions independently of upstream. Identify and engage potential community co-maintainers early. |
| **Octave runtime viability at FNM scale:** MOST fails at SMALL/MEDIUM scale in testing (C-4, C-6, C-8). No HiGHS MEX bindings limit MILP solver options to GLPK on Octave. CAISO FNM (~6,000 buses with full topology) may exceed Octave's practical performance envelope. | HIGH | Conduct early Phase 2 spike: load CAISO FNM into MATPOWER on Octave and benchmark DCOPF solve time. If Octave proves unworkable, evaluate Julia bridge via MATPOWER.jl or fallback to PowerModels for optimization with MATPOWER for network analysis only. |
| **No production deployment precedent:** MATPOWER has zero operational deployments (E-6). All adoption is academic. Failure modes in production workflows (long-running processes, error recovery, memory management) are undiscovered. | MED | Design Phase 2 architecture with explicit error boundaries around MATPOWER calls. Implement watchdog timeouts and result validation on every solve. Do not assume solver stability over multi-hour batch runs. |
| **MOST monolithic formulations:** MOST constructs monolithic MILP formulations that do not decompose well. At CAISO scale with 24-hour horizons and contingency constraints, the formulation may exceed solver memory. | MED | Implement temporal decomposition (solve 4-6 hour blocks with overlap) outside MOST. Use MOST for formulation generation and extract the optimization model for manual decomposition if needed. Benchmark memory at FNM scale in the early Phase 2 spike. |

---

## Phase 2 Development Scope

### Tool-Intrinsic Gaps

| Gap | Effort | Notes |
|-----|--------|-------|
| Octave solver ecosystem | weeks | Build or acquire HiGHS MEX bindings for Octave, or validate GLPK adequacy for Phase 2 MILP scale. SCIP MEX as fallback. |
| MOST scalability remediation | weeks | Profile and diagnose MOST failures at SMALL/MEDIUM (C-4, C-6, C-8). May require formulation simplification or problem decomposition wrapper. |
| Result export pipeline | days | MATPOWER returns Octave structs. Build serialization layer to export LMPs, flows, commitment schedules to HDF5/Parquet for downstream analysis. |

### Tool-Adjacent Engineering

| Work Item | Effort | Notes |
|-----------|--------|-------|
| FNM ingestion + imputation | months | CAISO FNM uses legacy PSS/E format. `psse2mpc()` handles Rev 23-33+ natively, but FNM-specific quirks (multi-section lines, switched shunts, area interchange) require validation and imputation of missing data. |
| OASIS data pipeline | weeks | Ingest public CAISO OASIS data (binding constraints, LMPs, generation, load) for validation targets. Build automated refresh and alignment with FNM bus/branch numbering. |
| PTDF calibration + validation | weeks | Compute PTDFs from solved AC base case using `makePTDF()`. Validate against CAISO-published shift factors where available. Calibrate loss factors against published MCL components. |
| Contingency list curation | weeks | Build monitored contingency list from OASIS binding constraint data. Map CAISO constraint names to FNM branch IDs. Prioritize by historical binding frequency. |

### Operational Workflow

| Work Item | Effort | Notes |
|-----------|--------|-------|
| Scenario management framework | weeks | Build scenario definition, execution, and result storage layer around MATPOWER. Support parameter sweeps (load levels, contingency sets, generator outages) with reproducible configuration. |
| LMP validation loop | weeks | Automated comparison of computed LMPs against CAISO-published values. Decompose discrepancies into energy, congestion, and loss components. Flag systematic biases for calibration. |
| Result visualization | weeks | Interactive visualization of LMP heatmaps, binding constraint patterns, and contingency impact on the FNM topology. Likely Python-based (matplotlib/plotly) consuming exported MATPOWER results. |
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
- **Generated:** 2026-03-09T21:15:00Z
- **Ranking algorithm:** Lexicographic on [Expressiveness, Extensibility, Scalability, Accessibility, Maturity] with Supply Chain gate (<=C+ disqualifies)
