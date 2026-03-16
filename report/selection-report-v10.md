# Phase 1 Tool Selection Report
## Contract FA714626C0006 | Grid Research Company LLC

**Protocol version:** v10
**Date:** 2026-03-15

---

## Methodology

Tools were scored across six rubric dimensions (Expressiveness, Extensibility, Scalability, Accessibility, Maturity, Supply Chain) using a structured test battery administered under protocol v10. The primary ranking applies a lexicographic ordering over [Expressiveness, Extensibility, Scalability, Accessibility, Maturity] with a Supply Chain gate: any tool grading C+ or below on Supply Chain is disqualified before ranking. Ties are broken by the next criterion in the priority order; the full ordered grade tuple determines final placement.

## Grade Comparison

| Rank | Tool | Expressiveness | Extensibility | Scalability | Accessibility | Maturity | Supply Chain |
|------|------|---------------|---------------|-------------|---------------|----------|--------------|
| 1 | PyPSA 1.1.2 | B+ | A- | C+ | A- | A | B+ |
| 2 | PowerModels 0.21.5 | B- | A- | B- | B- | B | A- |
| 3 | PowerSimulations 0.30.2 | B- | A- | B- | C+ | B | B+ |
| 4 | GridCal 5.6.28 | B-* | B- | B | C+ | C | B- |
| 5 | pandapower 3.4.0 | C+ | B | C+ | B+ | A- | A |
| —† | MATPOWER 8.1 | B- | A- | C+ | B | C+ | A |

*GridCal Expressiveness corrected from initial B to B- on GRC principal review — a shipped battery energy balance sign error (A-12) in a tool with zero CI test execution reflects a formulation quality gap, not merely a missing feature.

†MATPOWER is included as a reference benchmark only. The Octave/MATLAB runtime dependency disqualifies it for classified deployment. It is excluded from the primary ranking and all head-to-head comparisons.

## Sensitivity Analysis

Three scenarios were proposed by the evaluator and confirmed by the GRC principal to probe the stability of the primary ranking.

**Scenario 1 — Extensibility as top priority** (Extensibility → Expressiveness → Scalability → Accessibility → Maturity):

PyPSA (A-), PowerModels (A-), and PowerSimulations (A-) tie on Extensibility. Expressiveness breaks the three-way tie: PyPSA's B+ leads (#1 unchanged). PowerModels vs PowerSimulations: both B- on Expressiveness and Scalability; Accessibility breaks the tie — PowerModels B- > PowerSimulations C+ → PowerModels #2, PowerSimulations #3. pandapower (B Extensibility) ranks ahead of GridCal (B- Extensibility) → pandapower #4, GridCal #5.

| Rank | Tool |
|------|------|
| 1 | PyPSA 1.1.2 |
| 2 | PowerModels 0.21.5 |
| 3 | PowerSimulations 0.30.2 |
| 4 | pandapower 3.4.0 |
| 5 | GridCal 5.6.28 |

**#1 does not change.**

**Scenario 2 — Maturity gate at C** (C or below disqualifies):

GridCal's Maturity grade of C triggers disqualification (bus factor 1, zero CI test execution, battery sign error shipped in release). The remaining four tools rank in primary order.

| Rank | Tool |
|------|------|
| 1 | PyPSA 1.1.2 |
| 2 | PowerModels 0.21.5 |
| 3 | PowerSimulations 0.30.2 |
| 4 | pandapower 3.4.0 |
| DQ | GridCal 5.6.28 |

**#1 does not change.**

**Scenario 3 — Scalability as top priority** (Scalability → Expressiveness → Extensibility → Accessibility → Maturity):

GridCal's B Scalability leads the field. PyPSA drops to #4 because its C+ Scalability reflects a HiGHS single-threaded MILP timeout on the SCUC SMALL test (C-4 fail). This grade is solver-bound, not an architectural ceiling: PyPSA ACPF scales to 10K buses (C-5 MEDIUM pass) and FNM DCPF runs exact at 27,862 buses in 31.3s (G-FNM-3 pass). PowerModels vs PowerSimulations: tied on Scalability (B-), Expressiveness (B-), and Extensibility (A-); Accessibility breaks the tie — PowerModels B- > PowerSimulations C+ → PowerModels #2, PowerSimulations #3. PyPSA C+ vs pandapower C+: Expressiveness PyPSA B+ > pandapower C+ → PyPSA #4, pandapower #5.

| Rank | Tool |
|------|------|
| 1 | GridCal 5.6.28 |
| 2 | PowerModels 0.21.5 |
| 3 | PowerSimulations 0.30.2 |
| 4 | PyPSA 1.1.2 |
| 5 | pandapower 3.4.0 |

**#1 changes to GridCal** under this scenario. However, GRC does not recommend re-weighting on Scalability given GridCal's C Maturity, blocking battery sign error (A-12), and zero-CI-execution development posture.

---

## Recommendation

### Selected Tool: PyPSA 1.1.2

PyPSA wins on Expressiveness (B+), the primary ranking criterion, by being the only evaluated tool to pass 8 of 10 Suite A tests including all three pivotal capabilities for the target application: native SCOPF via `optimize_security_constrained()` with BODF-based N-1 constraints (A-9), native lossy DC OPF with piecewise-linear loss approximation and LMP decomposition (A-10), and multi-period DCOPF with StorageUnit including cyclic state-of-charge and BESS arbitrage (A-12). Its A- Extensibility — driven by the `extra_functionality` callback, clean 4-layer architecture, and native NetworkX integration — ensures the custom constraint work required in Phase 2 can be built on stable public APIs rather than fragile monkey-patches. EU institutional backing, 33 releases in 24 months, and an MIT core license present no supply chain risk.

### Head-to-Head: Critical Phase 2 Capabilities

| Capability | PyPSA 1.1.2 | PowerModels 0.21.5 | PowerSimulations 0.30.2 | GridCal 5.6.28 | pandapower 3.4.0 |
|------------|-------------|-------------------|------------------------|----------------|-----------------|
| SCOPF | Native (`optimize_security_constrained()`, A-9) | Workaround (~250 LOC user MILP) | Gap | Native (`consider_contingencies=True`, A-9) | Gap |
| Distributed Slack | Gap (A-11; architecturally blocked in `n.optimize()`) | Gap (A-11 fail) | Gap (A-11 fail) | Gap (hardcoded off in OPF, A-11) | Gap |
| PWL Cost Curves | Gap (issue #1020) | Native (convex PWL, no SOS2) | Native (SOS2, all formulations) | Not tested | Native (`create_pwl_cost()`) |
| PSS/E RAW Parsing | Gap (no ingestion path, G-FNM-1 fail) | Workaround (v33 only; 1–2d fix for v31) | Workaround (v33/35; 3–6wk for v31) | Gap (v35 only; FNM is v31) | Gap (no parser) |
| Custom Constraints | Native (`extra_functionality` callback, B-1) | Native (two-level API, B-1) | Extension (2–3wk, internal APIs) | Workaround (fragile monkey-patch only, B-1) | Workaround (monkey-patch, B-1) |
| UC/ED Pipeline | Gap (SCUC SMALL timeout, C-4 fail) | Workaround (~250 LOC user MILP, A-5) | Native (ThermalStandardUnitCommitment, A-5) | Native (24hr SCUC with min up/down, A-5) | Gap (no UC capability) |

### Runner-Up: PowerModels 0.21.5

PowerModels finishes second on the strength of its A- Extensibility — a clean, documented two-level constraint injection API requiring only 4 lines beyond model instantiation (B-1 pass) — combined with LANL/DOE institutional backing and first-class PTDF support with machine-epsilon accuracy (B-9). It was not chosen for three reasons: native SCUC requires a user-assembled ~250 LOC MILP with no built-in UC API (A-5 blocking workaround); ACPF diverges at MEDIUM scale on both NLsolve and Ipopt (C-2 independent fail); and branch flows are absent from the `compute_*` result dictionaries, producing pervasive post-processing friction across tests A-1, A-2, A-4, B-3, and C-1. GRC would reconsider PowerModels if the deployment environment mandated a Julia runtime and the ACPF convergence failure at 10K buses could be resolved upstream.

### Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| PyPSA has no PSS/E RAW ingestion path; the full network model (FNM) is delivered in v31 format (G-FNM-1 fail). Phase 2 cannot start without a conversion pipeline. | HIGH | Develop a PSS/E v31 → MATPOWER .m converter in Phase 2 pre-work using the shared `matpower_loader` that already passes G-FNM-3. Estimated 1–2 weeks. Validate against the MATPOWER DCPF baseline before any PyPSA optimization run. |
| PyPSA has no native PWL cost curve support (tracked as issue #1020). Accurate LMP decomposition requires convex piecewise-linear heat rates. | HIGH | Implement PWL costs via `extra_functionality` using SOS2 binary variables injected into the HiGHS MILP. Prototype and validate against PowerSimulations' native SOS2 output before committing to the architecture. Estimated 1–2 weeks. |
| SCUC at SMALL scale fails due to HiGHS single-threaded MILP timeout (C-4). Production UC runs at the target scale will be larger. | MED | Evaluate Gurobi or CPLEX as a drop-in HiGHS replacement for MILP workloads — PyPSA's solver interface is a single parameter change. If a commercial solver is unavailable in the classified environment, implement a Lagrangian relaxation pre-solve to warm-start HiGHS. |
| Shadow price assignment bug: `lines_t.mu_upper` and `lines_t.mu_lower` are silently empty after `n.optimize()`. Congestion pricing logic in Phase 2 depends on binding constraint duals. | MED | Use `n.statistics()` to extract shadow prices post-solve and validate against manually computed dual variables on a small reference network before integrating into LMP decomposition. File an upstream bug report. |
| PyPSA's transformer `b` field carries dual semantics (susceptance vs. tap-ratio) that are undocumented. Incorrect FNM parameterization will produce silently wrong power flows. | LOW | Establish a transformer round-trip test: load FNM, run DCPF, compare branch flows to the MATPOWER baseline used in G-FNM-3. Enforce this as a regression gate before any production optimization run. |

---

## Phase 2 Development Scope

### Tool-Intrinsic Gaps

| Gap | Effort | Notes |
|-----|--------|-------|
| PWL cost curve injection via `extra_functionality` (SOS2) | weeks | No native support (issue #1020); must implement and validate against reference LMPs |
| SCUC solver upgrade or warm-start strategy | weeks | HiGHS MILP timeout at SMALL scale (C-4 fail); evaluate Gurobi/CPLEX or Lagrangian relaxation pre-solve |
| Shadow price extraction workaround | days | `lines_t.mu_upper/lower` silent after `n.optimize()`; use `n.statistics()` as interim path |
| Transformer `b` field documentation and validation | days | Dual semantics undocumented; regression test against MATPOWER DCPF baseline required |

### Tool-Adjacent Engineering

| Work Item | Effort | Notes |
|-----------|--------|-------|
| PSS/E v31 → MATPOWER .m converter | weeks | No PyPSA ingestion path (G-FNM-1 fail); extend shared `matpower_loader` used in G-FNM-3 |
| FNM imputation and island resolution | weeks | Large network likely contains radial islands and missing impedance data; must stabilize before any OPF run |
| PTDF calibration against FNM baseline | weeks | PyPSA SubNetwork PTDF API passes B-9; validate at full FNM scale before production use |
| LMP decomposition validation harness | weeks | Compare PyPSA LMP components to MATPOWER reference; confirm energy/congestion/loss split |

### Operational Workflow

| Work Item | Effort | Notes |
|-----------|--------|-------|
| Scenario management framework | weeks | Parameterize contingency sets, load levels, and generator availability across study scenarios |
| LMP validation loop | weeks | Automated comparison of PyPSA LMPs to reference solutions before each production run |
| Solver environment configuration | days | Confirm HiGHS version and thread count in deployment environment; document solver swap path |
| Result archival and reproducibility | weeks | Hash inputs + solver config + PyPSA version to produce reproducible study artifacts |

---

## Provenance

- **Protocol version:** v10
- **Synthesis files:**
  - `evaluations/pypsa/results/synthesis.md` @ `5c5db8c4`
  - `evaluations/pandapower/results/synthesis.md` @ `7e8194ab`
  - `evaluations/gridcal/results/synthesis.md` @ `143aa2db`
  - `evaluations/powermodels/results/synthesis.md` @ `4b0983ff`
  - `evaluations/powersimulations/results/synthesis.md` @ `519bf37b`
  - `evaluations/matpower/results/synthesis.md` @ `09dbb45d`
- **Generated:** 2026-03-15T00:00:00Z
- **Ranking algorithm:** Lexicographic on [Expressiveness, Extensibility, Scalability, Accessibility, Maturity] with Supply Chain gate (<=C+ disqualifies)
