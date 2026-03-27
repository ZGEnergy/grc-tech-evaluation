# Phase 1 Tool Selection Report

**Contract FA714626C0006 | Naval Research Laboratory**
**Grid Research Company LLC**
**Date: 2026-03-26**

---

## Executive Summary

Grid Research Company evaluated six open-source power system modeling tools against a rubric of six criteria: Expressiveness, Extensibility, Scalability, Accessibility, Maturity, and Supply Chain. After structured testing across 39-bus, 2,000-bus, and 10,000-bus networks, we recommend **PyPSA** as the primary tool for Phase 2 model development. PyPSA earned Strong grades in five of six criteria and demonstrated the broadest native capability across the evaluation's core use cases. **PowerModels.jl** is the recommended runner-up, distinguished by its mathematical extensibility and native piecewise-linear cost support. The ranking is completely stable across all three sensitivity scenarios tested, reinforcing confidence in the selection.

MATPOWER was evaluated as a reference benchmark but is excluded from primary ranking because the customer requires inspectable source code, which precludes MATLAB's compiled runtime.

---

## Methodology

Each tool was evaluated against six rubric dimensions using a consistent test suite executed on standardized MATPOWER case files at three network scales (39-bus, 2,000-bus, and 10,000-bus). Grades of Strong, Adequate, Weak, or Failing were assigned per criterion based on test outcomes, with Supply Chain serving as a gate (Weak or Failing disqualifies). The final ranking uses lexicographic ordering on [Expressiveness, Extensibility, Scalability, Accessibility, Maturity], with tier-level evidence traceable to individual test IDs.

---

## Grade Table

| Tool | Expressiveness | Extensibility | Scalability | Accessibility | Maturity | Supply Chain |
|------|---------------|---------------|-------------|---------------|----------|--------------|
| PyPSA | Strong | Strong | Adequate | Strong | Strong | Strong |
| pandapower | Weak | Adequate | Weak | Adequate | Strong | Strong |
| GridCal | Adequate | Adequate | Adequate | Weak | Weak | Strong |
| PowerModels.jl | Adequate | Strong | Adequate | Adequate | Adequate | Adequate |
| PowerSimulations.jl | Adequate | Strong | Adequate | Weak | Adequate | Adequate |
| MATPOWER* | Adequate | Strong | Weak | Adequate | Adequate | Strong |

*\*MATPOWER excluded from ranking; the customer requires inspectable source code, which precludes MATLAB's compiled runtime.*

---

## Recommendation: PyPSA

PyPSA is the strongest candidate for Phase 2 development. It is the only tool to earn Strong on Expressiveness, demonstrating native DCOPF with LMP extraction (A-3), security-constrained OPF with LODF-based contingency constraints solving 50 contingencies on a 10,000-bus network in 30 seconds (A-9, C-8), and native security-constrained unit commitment across 24-hour horizons (A-5). Its extensibility layer, the `extra_functionality` callback, provides full access to the underlying Linopy optimization model and passed all eight extensibility tests (B-1 through B-9, excluding B-7 which is not in scope). Documentation quality and installation reliability earned Strong on both Accessibility and Maturity.

PyPSA's primary gaps are well-characterized. It lacks a PSS/E RAW file parser (P2-1), requires a generator tranche workaround for piecewise-linear cost curves rather than native SOS2 support (P2-2), and its Linopy model-building layer introduces measurable overhead at scale (302 seconds for model construction versus 6 seconds of solver time on a 10,000-bus DCOPF, C-3). These gaps are addressable through targeted Phase 2 engineering; none represents an architectural limitation.

---

## Runner-Up: PowerModels.jl

PowerModels.jl earned Strong on Extensibility through its two-level JuMP API, which enables custom constraint injection in as few as four lines of code with automatic dual extraction (B-1). It provides native SOS2 piecewise-linear cost curves (P2-2) and a PSS/E parser supporting v33 format (P2-1), both capabilities that PyPSA lacks. Its mathematical formulation library covers a broader range of relaxations (SOCP, SDP, QC) than any other evaluated tool.

PowerModels falls behind PyPSA on Expressiveness (Adequate versus Strong) because it has no unit commitment capability (A-5) and its SCOPF implementation requires manual Benders decomposition without demonstrated convergence on a feasible instance (A-9). These gaps reflect the tool's design scope: PowerModels is a mathematical optimization research platform, not an integrated power system simulation environment.

**When to reconsider:** If Phase 2 requirements shift to prioritize advanced OPF relaxations or if PyPSA's Linopy overhead proves prohibitive at full production scale, PowerModels' solver-proximal architecture would provide a more direct path to performance optimization.

---

## Head-to-Head Comparison

| Capability | PyPSA | PowerModels.jl | PowerSimulations.jl | GridCal | pandapower |
|-----------|-------|----------------|---------------------|---------|------------|
| SCOPF | Native (A-9, C-8) | Extension (A-9) | Extension (A-9) | Native (A-9) | Gap (A-9) |
| Distributed Slack OPF | Workaround (A-11) | Workaround (A-11) | Native (A-11) | Gap (A-11) | Gap (A-11) |
| PWL Cost Curves | Workaround (P2-2) | Native (P2-2) | Native (P2-2) | Gap (P2-2) | Native (P2-2) |
| PSS/E RAW Parsing | Gap (P2-1) | Workaround, v33 (P2-1) | Workaround, v33/v35 (P2-1) | Workaround (P2-1) | Gap (P2-1) |
| Custom Constraint Injection | Native (B-1) | Native (B-1) | Native (B-1) | Workaround (B-1) | Workaround (B-1) |
| UC/ED Pipeline | Native (A-5, A-6) | Gap (A-5) | Native (A-5, A-6) | Native (A-5) | Gap (A-5) |

---

## Gap Analysis (Phase 2 Development Scope)

### Tool-Intrinsic Gaps

| Gap | Effort | Detail |
|-----|--------|--------|
| PSS/E RAW parser | Weeks | PyPSA has no PSS/E import (P2-1). Build a RAW-to-PyPSA converter or adapt an external parser as a preprocessing step. |
| Piecewise-linear cost curves | Weeks | No native SOS2 support (P2-2). Implement generator tranche decomposition as a reusable utility; validate against reference PWL solutions. |
| Distributed slack in OPF | Weeks | Available in PF but not OPF context (A-11). Implement via custom Linopy constraint using PTDF formulation with load-proportional weights. |

### Tool-Adjacent Engineering

| Gap | Effort | Detail |
|-----|--------|--------|
| Linopy model-building optimization | Weeks | Model construction overhead (302s vs. 6s solver time on 10,000 buses, C-3). Profile and evaluate direct HiGHS C API for inner-loop solves if overhead is prohibitive. |
| Process-level parallelism for contingency sweeps | Weeks | HiGHS simplex is single-threaded; 0.92x speedup with 32 threads (C-8). Architect process-level parallelism for independent contingency sub-problems. |

### Operational Workflow

| Gap | Effort | Detail |
|-----|--------|--------|
| Full network model ingestion pipeline | Months | End-to-end pipeline from PSS/E RAW through validation to production-ready PyPSA network, including topology verification and impedance normalization. |
| Scenario orchestration framework | Months | Production framework for multi-scenario analysis with forecast uncertainty propagation (B-4), result aggregation, and output validation. |

---

## Sensitivity Analysis

Three alternative criterion priority orderings were tested to assess ranking stability. All scenarios were proposed by the evaluator and confirmed by the GRC principal.

**Scenario 1, Scalability First** (Scalability > Expressiveness > Extensibility > Accessibility > Maturity): PyPSA holds #1. Four tools tie at Adequate Scalability, but PyPSA's Strong Expressiveness breaks the tie immediately. Full ordering unchanged.

**Scenario 2, Extensibility First** (Extensibility > Expressiveness > Scalability > Accessibility > Maturity): PyPSA holds #1. Three tools tie at Strong Extensibility, but PyPSA's Strong Expressiveness again breaks the tie. Full ordering unchanged.

**Scenario 3, Maturity and Accessibility Swapped** (Expressiveness > Extensibility > Scalability > Maturity > Accessibility): PyPSA holds #1 via Strong Expressiveness on Criterion 1. Full ordering unchanged.

The ranking is completely stable across all three scenarios. PyPSA holds the top position in every case because it is the only tool with Strong Expressiveness, which dominates regardless of criterion priority ordering. The full ordering also remains unchanged because tier gaps between adjacent-ranked tools are wide enough that no single priority reordering changes relative positions.

---

## Risk Register

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| R1 | Linopy model-building overhead at production scale: PyPSA's Linopy layer takes 302 seconds to construct the optimization model for a 10,000-bus DC OPF (C-3), compared to 6 seconds of solver time. | HIGH | Profile Linopy model construction during Phase 2. If overhead is prohibitive, evaluate direct solver interface (HiGHS C API) for inner-loop solves, using PyPSA only for network data management and result post-processing. |
| R2 | No native PSS/E RAW file parser: PyPSA has no PSS/E import capability (P2-1). Phase 2 requires ingesting the full network model distributed in PSS/E RAW format. | HIGH | Build a PSS/E RAW-to-PyPSA converter during Phase 2. The intermediate CSV-based format used for Phase 1 FNM testing provides a working reference. Alternatively, use an external parser as a preprocessing step. |
| R3 | Distributed slack OPF not available in optimization context: PyPSA supports distributed slack in power flow but not in OPF formulations (A-11). | MED | Implement distributed slack as a custom Linopy constraint via PyPSA's extra_functionality callback using PTDF formulation with load-proportional weights. Estimated effort: weeks. |
| R4 | Single-threaded HiGHS solver limits parallelism: HiGHS simplex does not parallelize; SCOPF on a 10,000-bus network showed 0.92x speedup with 32 threads (C-8). | MED | Use process-level parallelism for independent contingency sub-problems rather than relying on solver-internal threading. PyPSA's architecture supports independent model instantiation per contingency group. |
| R5 | Piecewise-linear cost curves require tranche workaround: PyPSA does not natively support piecewise-linear cost curves (P2-2). | MED | Implement generator tranche decomposition as a reusable utility during Phase 2. Validate against reference PWL solutions from a tool with native SOS2 support. |

---

## Provenance

- **Synthesis files:**
  - pypsa: `evaluations/pypsa/results/synthesis.md` (71bd9d72)
  - pandapower: `evaluations/pandapower/results/synthesis.md` (f4fdef34)
  - gridcal: `evaluations/gridcal/results/synthesis.md` (7626e710)
  - powermodels: `evaluations/powermodels/results/synthesis.md` (5ac6d33e)
  - powersimulations: `evaluations/powersimulations/results/synthesis.md` (f16fd336)
  - matpower: `evaluations/matpower/results/synthesis.md` (a86ae309)
- **Generated:** 2026-03-26T21:45:00Z
- **Ranking algorithm:** Lexicographic on [Expressiveness, Extensibility, Scalability, Accessibility, Maturity] with Supply Chain gate (Weak or Failing disqualifies)
