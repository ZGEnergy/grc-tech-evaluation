# Phase 1 Test Protocol
## Contract FA714626C0006 | Grid Research Company LLC

---

## Purpose

This document defines the reproducible test suite used to generate grades for the Phase 1 Technology Evaluation Rubric. Every grade in the evaluation report must trace to a specific test result or audit finding documented here. The protocol ensures that tool evaluations are comparable, evidence-based, and defensible.

This is a companion document to the **Phase 1 Technology Evaluation Rubric**, which defines the criteria, sub-questions, and grading standards. The rubric says *what* we evaluate; this protocol says *how*.

---

## Reference Environment

### Hardware Baseline

All performance measurements are recorded on the following reference workstation:

| Spec | Value |
|------|-------|
| RAM | 128 GB |
| CPU | 16 cores |
| GPU | None (not used) |
| OS | Ubuntu 24.04 LTS |

Grades on Scalability are assigned against this baseline. If a tool is additionally tested on other hardware, results are noted for context but do not affect the grade.

### Solver Stack

All tests use open-source solvers exclusively. Commercial solvers (Gurobi, CPLEX) are not used in any test. The following solvers are available:

| Solver | Problem Type | Notes |
|--------|-------------|-------|
| HiGHS | LP, MILP, QP | Primary solver for all linear and mixed-integer problems |
| SCIP | LP, MILP | Secondary MILP solver for comparison |
| Ipopt | NLP (AC PF/OPF) | Primary solver for nonlinear problems |
| GLPK | LP, MILP | Lightweight baseline for comparison |

If a tool cannot interface with any of these solvers, that is recorded as a finding under the Supply Chain criterion (solver dependency lock-in) and the Scalability criterion (solver flexibility).

### Reference Networks

All reference networks used in Phase 1 testing are **completely synthetic**. None represent, derive from, or approximate actual grid topology for any real power system. This is by design — Phase 1 evaluates tool capability, not grid vulnerability. No classified, proprietary, or operationally sensitive grid data is used at any point during Phase 1 testing.

| Label | Network | Buses | Format | Purpose |
|-------|---------|-------|--------|---------|
| TINY | IEEE 39-bus (New England) | 39 | MATPOWER .m | Functional verification — confirm every problem type is expressible. All Suite A and Suite B tests run here first. |
| SMALL | ACTIVSg 2k | ~2,000 | MATPOWER .m / converted | Intermediate scale check — verify that functional results hold beyond toy size. |
| MEDIUM | ACTIVSg 10k | ~10,000 | MATPOWER .m / converted | Scalability benchmark — Suite C grades assessed here. |
| LARGE | FNM Annual S01 | ~30,000 | Intermediate CSV tables (primary); pre-cleaned MATPOWER .m case (fallback) | Data model fidelity — Suite G FNM ingestion tests (FNM_PATH-gated). |

**Why IEEE 39-bus for TINY:** 39 buses, 10 generators, 46 branches. The network is completely synthetic — it does not represent any actual power system. It is meshed, has sufficient generator diversity (varied cost curves, capacity ranges) for unit commitment to be non-trivial, and includes enough branches that graph-distance-2 contingency sweeps produce a meaningful enumeration without hitting the network boundary. Every tool under evaluation either ships with this case or can ingest the MATPOWER .m format trivially. Solves complete in under a second for PF/OPF problems, making it suitable for rapid iteration during tool evaluation. It is also one of the most widely published-against test cases in power systems literature, providing reference results for sanity-checking.

**Why ACTIVSg 2k and 10k:** The ACTIVSg (Activation Synthetic Grid) cases were developed by Texas A&M specifically to provide realistic-looking but entirely fictional test networks. They are synthetic in topology, generation mix, load distribution, and geographic layout. They share statistical properties with real grids (degree distribution, impedance characteristics, generator cost profiles) but do not represent any actual system. The 2k-bus and 10k-bus cases provide scale-appropriate benchmarks without introducing any actual infrastructure data into the evaluation.

### Data Format Notes

The IEEE 39-bus and ACTIVSg cases are distributed in MATPOWER .m format. Each tool's ability to ingest this format — or a standard conversion of it — is tested as part of the evaluation. If a tool requires format conversion (e.g., to PSS/E RAW, PowerModels JSON, or PyPSA CSV), the conversion process and any data loss are documented.

### Data Preparation

Before any tool evaluation begins, reference network data is preprocessed using a standardized script. This ensures all tools operate on identical, well-conditioned data and prevents inconsistent handling of edge cases from confounding tool comparisons.

**ACTIVSg 10k (MEDIUM) preprocessing:**

1. **Zero-reactance transformers:** Set branch reactance to `x = 0.0001 pu` for any branch with `x = 0` (prevents singular admittance matrices).
2. **Zero thermal rating branches:** Set `RATE_A = 9999 MVA` for any branch with `RATE_A = 0` (prevents tools from interpreting zero rating as a zero-capacity constraint).
3. **Congestion induction:** Tighten thermal limits on the 10–20 highest-flow branches to 90% of base-case DCPF flow. This produces binding constraints and non-uniform LMPs, enabling congestion-dependent tests (A-3, A-9, A-10, A-11, B-8, C-3, C-8, C-10) to exercise the features they grade.

**ACTIVSg 2k (SMALL) preprocessing:**

1. Steps (1) and (2) above, applied to SMALL with the same thresholds.

**IEEE 39-bus (TINY) preprocessing:**

The IEEE 39-bus case is used as-is for functional verification. No preprocessing is applied.

The preprocessing script is version-controlled alongside the reference data. Every test result file records which preprocessing version was applied.

### MATPOWER ext2int Conversion

MATPOWER .m case files may contain non-contiguous bus numbering, isolated buses, or out-of-service elements. Tools that use MATPOWER data should apply the equivalent of MATPOWER's `ext2int` conversion (reindexing to internal contiguous numbering and removing out-of-service elements) before constructing admittance matrices. Failure to apply this conversion can produce incorrect results on networks with non-trivial indexing. Document whether the tool handles this conversion automatically or requires manual preprocessing.

---

## Evaluation Scope

Tools are evaluated as their **shipped package plus official companion packages** maintained by the same team or organization. For example:

- **PowerModels.jl** is evaluated together with PowerModelsAnnex.jl and other LANL-ANSI infrastructure packages
- **PowerSimulations.jl** is evaluated together with PowerSystems.jl, InfrastructureSystems.jl, and other NREL Sienna packages
- **PyPSA** is evaluated together with linopy, atlite, powerplantmatching, and other official PyPSA ecosystem packages

Third-party packages that happen to integrate with a tool but are maintained independently are noted but do not contribute to the tool's grade. When an official companion package is used to achieve a passing test result, this is explicitly documented (e.g., "SCUC solved via UnitCommitment.jl, an official LANL-ANSI companion to PowerModels.jl").

Multi-tool stacks are only tested when the integration path is officially supported and documented by the tools themselves (e.g., pandapower with a PowerModels.jl backend, if that is a supported configuration). Hybrid stacks assembled by the evaluator from independently maintained tools are not tested — that is heroics, not a product.

---

## Test Execution Protocol

### General Rules

1. **One test script per tool per test case.** Each test is a self-contained script that can be run independently. No shared state between test cases.

2. **Record everything.** For each test, record:
   - Pass/fail
   - Wall-clock time (for scalability-relevant tests) — must be measured, not estimated (see rule 7)
   - Peak memory usage
   - Lines of code required to express the test
   - Any errors, warnings, or unexpected behavior
   - Version of tool, all companion packages, and solvers used

3. **No heroics.** If a test requires undocumented workarounds, reverse-engineering internals, or patching source code, the test is recorded as a qualified pass with the workaround documented and its durability assessed (see Workaround Durability below).

4. **Document the learning process.** For the Workforce Accessibility criterion, record the wall-clock time from clean install to first successful DCPF solve on TINY as a proxy for learning curve. Note any documentation gaps, broken examples, or misleading guidance encountered during setup.

5. **TINY first, then scale.** Every functional test (Suites A and B) is run on TINY before being attempted on SMALL or MEDIUM. If a tool cannot pass a functional test on a 39-bus network, there is no reason to attempt it at scale. This keeps evaluation velocity high and surfaces tool limitations early.

6. **Workarounds require qualified_pass.** A test requiring any workaround — stable, fragile, or blocking — must be classified as `qualified_pass`, not `pass`. The workaround class affects the grade within the B range but never produces a clean pass. See Workaround Durability Classification below.

7. **Measured timings only.** Estimated or projected timings must be clearly labeled with `estimated` in the result frontmatter and cannot support `pass` or `qualified_pass` on scalability tests (Suite C). If a test cannot be executed within the time budget (including JIT/startup overhead for first runs), record `fail` with the projected timing as supplementary context. Wall-clock times must be measured using the system clock during actual test execution.

8. **Distinguish cascaded from independent failures.** When a test fails solely because a prerequisite test failed (e.g., C-4 fails because A-5 failed), record the dependent test with `blocked_by: <prerequisite_test_id>` in the result frontmatter. When tabulating outcomes, report "X independent fails + Y blocked" rather than a single count. Blocked tests do not contribute to the criterion's independent fail count but are listed for completeness.

9. **Separate tool expressiveness from solver performance.** For expressiveness tests (Suite A): if a tool can express the formulation correctly but the open-source solver times out or fails to converge, score as `qualified_pass` with a solver-limitation note — not `fail`. The solver limitation is recorded as a scalability finding (Suite C). For scalability tests (Suite C): retain `fail` classification for solver timeouts but note the tool's expressiveness capability separately.

10. **FNM_PATH gating.** All Suite G (FNM Ingestion) tests require the `FNM_PATH` environment variable to be set and pointing to a valid directory containing the FNM intermediate format output (as produced by the Phase 1 data pipeline). When `FNM_PATH` is not set, all Suite G tests skip with a recorded status of "skipped — FNM_PATH not set." This is an all-or-nothing gate: if `FNM_PATH` is unset, no Suite G tests execute. If `FNM_PATH` is set but the directory is invalid or incomplete (e.g., missing manifest), G-FNM-1 fails and G-FNM-2 through G-FNM-5 are skipped. Suite G results are additive evidence for Expressiveness and Extensibility grades — their absence does not create a gap in tool evaluation.

### Workaround Durability Classification

When a test requires a workaround (anything beyond the tool's documented API), classify it:

| Class | Definition | Example |
|-------|-----------|---------|
| **Stable** | Uses a documented, public API in a non-obvious way. Unlikely to break on upgrade. | Exporting network to NetworkX via a documented converter function |
| **Fragile** | Depends on undocumented internals, private attributes, or behavior not guaranteed by the API. Could break on any minor version bump. | Accessing `network._adjacency` to get graph structure, monkey-patching a solver callback |
| **Blocking** | Requires forking the source, patching compiled code, or is simply not achievable. | Modifying core constraint assembly to add a custom constraint type |

Stable workarounds receive a B on the relevant sub-question. Fragile workarounds receive a B- or C depending on severity. Blocking workarounds receive a C.

---

## Test Suite

### Gate Test: Data Ingestion

Before any criterion-specific testing, each tool must pass this gate:

| ID | Test | Network | Pass Condition |
|----|------|---------|---------------|
| G-1 | Ingest reference network | TINY | Tool loads IEEE 39-bus without error. Bus count, branch count, and generator count match expected values (39 buses, 46 branches, 10 generators). |
| G-2 | Ingest reference network | SMALL | Same verification on ACTIVSg 2k. |
| G-3 | Ingest reference network | MEDIUM | Same verification on ACTIVSg 10k. |

If a tool requires format conversion from MATPOWER .m, the conversion pipeline is documented and the converted file is verified against the original (bus/branch/gen counts, no data loss on critical fields: Pd, Qd, Pg, Qg, rateA, bus type, voltage setpoints).

A tool that cannot pass G-1 is excluded from further evaluation. A tool that passes G-1 but fails G-2 or G-3 proceeds with functional evaluation on TINY but receives reduced scalability grades.

---

### Test Suite A: Problem Expressiveness

Each test maps to a sub-question in Rubric Criterion 1. **All tests are first run on TINY for functional verification, then on the indicated scale network for grade assessment.**

| ID | Sub-question | Test | Functional (TINY) | Grade Network | Pass Condition |
|----|-------------|------|-------------------|---------------|---------------|
| A-1 | DC Power Flow | Solve DCPF | yes | MEDIUM | Converges. Nodal injections, line flows, and voltage angles accessible as structured output (DataFrame, dict, or named array — not raw solver vector). |
| A-2 | AC Power Flow | Solve ACPF (Newton-Raphson) | yes | MEDIUM | Converges. Convergence residual must be reported and below the tool's stated tolerance. Number of NR iterations must be reported. Voltage magnitudes must differ from flat-start defaults (1.0 pu) on >95% of buses. Bus voltage magnitudes and angles, line P/Q flows, and losses accessible as structured output. If the tool cannot report iteration count or residual, document this as a diagnostic quality finding. |
| A-3 | DC OPF | Solve DC OPF with gen costs and line flow limits | yes | MEDIUM | Converges. Optimal dispatch and LMPs/shadow prices extractable from solution. |
| A-4 | AC Feasibility Check | Take DC OPF dispatch from A-3, run full ACPF on that dispatch | yes | MEDIUM | Achievable within the same model context (no export to file and reimport). Voltage violations and thermal limit violations identifiable from results. |
| A-5 | SCUC | Solve 24-hour unit commitment as MILP with: min up/down times, startup costs, ramp rates, reserve requirements. Generator fleet must produce demonstrable cycling (see note below). | yes | SMALL | Solves to feasibility (MIP gap ≤ 1% on TINY, ≤ 10% on SMALL). At least 2 generators must cycle (commit/decommit) during the 24-hour horizon. Commitment schedule extractable as a time-indexed binary matrix. Built-in constraint types vs. user-assembled noted. |
| A-6 | SCED | Fix commitment schedule from A-5, solve economic dispatch as LP/QP | yes | SMALL | Solves. Dispatch schedule extractable. UC and ED are cleanly separable as a two-stage workflow. Ramp rate constraints are demonstrably enforced between consecutive dispatch intervals in the ED stage — not just inherited from the UC formulation. |
| A-7 | N-M Contingency Sweep | From a chosen bus, enumerate all branches within graph distance *x* (e.g. *x*=5). Sweep contingencies with escalating order up to *m* simultaneous outages (e.g. *m*=2 on MEDIUM, *m*=3 on TINY). At each order *n*, any branch whose removal at order *n*-1 already produced total load loss is pruned from higher-order combinations — so the sweep does not return obvious, overlapping outage sets. | yes | MEDIUM | Completes without full model reconstruction per contingency case. Load loss per contingency case collected. Pruning logic is expressible without fighting the tool. Combinatorial enumeration and graph-distance scoping are achievable via the tool's API or a clean graph library bridge. |
| A-8 | Stochastic Timeseries | Solve a multi-period (12hr, hourly resolution) DCOPF with stochastic load and renewable generation scenarios. Perturbations must be independent by resource type (load, wind, solar — classified by cost tier proxy). Extract prices. | yes | SMALL | Tool natively supports scenario-indexed timeseries for load, wind, and solar — the stochastic structure is part of the optimization formulation (e.g., scenario tree, two-stage stochastic program), not just independent deterministic solves in a loop. Perturbations are independent by resource type. Prices extractable from solution. |
| A-9 | SCOPF | Solve DC OPF with N-1 contingency flow constraints embedded in the optimization. On TINY, use all 46 branches as the contingency set. On SMALL, use 50 monitored branches. On MEDIUM, use 50 monitored branches. Iterative contingency screening allowed. | yes | SMALL | Solves. Base-case dispatch respects all contingency flow limits simultaneously. Dispatch and cost differ from unconstrained DC OPF (A-3) — SCOPF should be more expensive. Contingency constraints are part of the optimization, not checked post-hoc. If achievable only by manually enumerating contingency constraints via B-1's custom constraint API, document the effort and classify the workaround. |
| A-10 | Lossy DC OPF / LMP Decomposition | Solve DC OPF with loss approximation on TINY. Any loss method accepted (iterative loss factors, quadratic terms, penalty factors). Decompose LMPs into energy, congestion, and loss components. Compute per-line congestion rent (flow x LMP difference across endpoints). Validate via LMP reconciliation (sum of congestion rents ~ sum of congestion LMP components, 5% tolerance). | yes | SMALL | Tool produces loss-inclusive LMPs where loss components are non-zero. LMP decomposition extractable as structured output. Per-line congestion rent computed and reconciled against congestion LMP components. Validate internal consistency: (a) loss components have physically correct signs (positive marginal loss at load buses far from generation), (b) total losses are 0.5–3% of total load, (c) lossy objective exceeds lossless objective, (d) loss component LMPs sum with energy and congestion components to total LMP within 1% tolerance. |
| A-11 | Distributed Slack OPF | Solve DC OPF on TINY with distributed slack (load-proportional). Compare LMPs to single-slack solution from A-3. | yes | SMALL | Tool supports distributed slack formulation. LMPs differ from single-slack results in a physically consistent manner (SMEC reflects the distributed reference). Distributed slack weights are settable via API (e.g., proportional to load, proportional to generation, or custom weights). |

**Recording for each A-test:** Pass/fail on TINY (with notes), wall-clock time on grade network, lines of code, output format, any workarounds and their durability class.

**Note on TINY verification:** On TINY, the pass condition is purely functional — does the tool express and solve the problem? Performance is not measured. If a tool passes on TINY but fails on the grade network, that is a Scalability finding, not an Expressiveness failure.

**Note on A-7:** The contingency sweep is an escalating, pruned search — not a flat N-1 loop. The algorithm works as follows: (1) Scope the search space by enumerating all branches within graph distance *x* of a chosen bus. (2) Run all N-1 contingencies within that set. Re-solve DCPF for each and record load loss. (3) Any branch whose N-1 removal already produces total load loss at the bus of interest is pruned — it does not appear in higher-order combinations, because any N-2 set containing that branch would produce a redundant, obvious result. (4) From the surviving branches, enumerate N-2 combinations, re-solve, prune again. (5) Continue escalating through N-3, N-4, ... up to N-*m*. This tests three things: graph-distance scoping (does the tool expose topology for enumeration?), efficient contingency re-solve (can branches be removed and restored without model reconstruction?), and programmability (can the pruning and escalation logic be expressed cleanly in user code on top of the tool's API?). On TINY, use *x*=3, *m*=3 to keep the combinatorial space trivial. On MEDIUM, use *x*=5, *m*=2 as the grade-assessment parameters. N-3 and N-4 results on MEDIUM are informational only and do not affect the pass/fail determination — the combinatorial explosion at higher orders is infeasible for all tools at 10k-bus scale.

**Note on A-5 cycling requirement:** The IEEE 39-bus case has a capacity-to-load ratio (~7,367 MW capacity vs ~6,254 MW peak load) that makes decommitment uneconomical with the default parameters. To ensure UC cycling is exercised, augment the generator fleet using one of: (a) increase PMIN to 30% of PMAX for all generators (forcing higher minimum output that makes some generators uneconomical at low load), (b) add 2–3 peaker generators with high startup cost (5x PMAX) and small capacity, or (c) widen the load profile range so minimum load is 40% of peak. The augmentation must produce at least 2 generators cycling (committing and decommitting) during the 24-hour horizon. Document the augmentation applied.

**Note on A-8:** The distinction between "native stochastic support" and "loop over deterministic solves" is critical. A tool that only supports deterministic solves but can be wrapped in a Monte Carlo loop is tested under Extensibility (B-4), not here. A passing grade on A-8 requires that the tool's optimization formulation is aware of multiple scenarios simultaneously — e.g., co-optimizing across scenarios with recourse decisions, or enforcing chance constraints across a scenario set. Random noise applied independently to each interval without temporal correlation or cross-scenario structure does not constitute meaningful stochastic support and does not pass.

**Note on A-9:** The distinction between SCOPF and post-hoc contingency analysis (A-7) is critical. A-7 tests whether a tool can re-solve power flow for each contingency case after an initial OPF. A-9 tests whether the tool can incorporate contingency constraints into the OPF itself — the base-case dispatch is constrained to be feasible under all enumerated contingencies. This is how ISO market clearing engines actually work: they solve a preventive SCOPF where post-contingency flows (computed via LODFs/PTDFs) must not exceed emergency limits. A tool that passes A-7 but fails A-9 can analyze contingencies but cannot formulate the market clearing problem. On SMALL and MEDIUM, iterative contingency screening is permitted: the tool may solve with a subset of contingencies, check for violations, add violated contingencies, and re-solve. This reflects actual ISO practice where only binding/near-binding contingencies are active in any given iteration.

**Note on A-10:** There is no single standard for loss approximation in DC OPF. Common approaches include iterative marginal loss factors (CAISO's method), piecewise-linear branch loss approximation, and quadratic loss terms in the objective. The test accepts any method. The key evaluation points are: (a) can the tool include losses at all in its DC OPF formulation, (b) are the resulting LMPs decomposable into energy, congestion, and loss components, and (c) do the loss components have physically correct sign and magnitude (buses far from generation should show positive marginal losses). Validation uses internal consistency checks rather than cross-tool reference comparison: loss components must have physically correct signs, total losses must be 0.5–3% of total load, the lossy objective must exceed the lossless objective, and decomposed LMP components must sum to the total LMP within 1% tolerance.

**Note on A-11:** All ISOs use a distributed slack (distributed reference bus) in their market clearing engines. ISOs typically use a load-proportional distributed slack for DAM (weighted by cleared load) and a forecast-weighted distributed slack for RTM, or generation-proportional or custom-weighted distributions. A tool that only supports single-slack DC OPF will produce LMPs where the energy component is defined at a single arbitrary bus, making the congestion and loss decomposition non-comparable to ISO-published values. The test verifies that the tool can formulate the distributed slack and that LMP decomposition responds correctly. On TINY, compare distributed-slack LMPs against single-slack LMPs from A-3 — they should differ, and the differences should be physically explainable (buses near the old single slack see the largest changes).

**Note on A-9 feasibility on case39:** The IEEE 39-bus case has tight thermal limits that may make preventive SCOPF infeasible on TINY. If infeasibility occurs, apply thermal rating relaxation (scale rateA to 150%, escalate to 200% if insufficient). Document the relaxation factor applied. This is a data finding reflecting the test case's characteristics, not a tool limitation.

**Note on resource type classification (A-8, B-4):** Generators are classified by resource type using cost curve slope as a proxy (low marginal cost = baseload, mid = intermediate, high = peaker). Wind and solar generators, if present, are identified by zero or near-zero marginal cost with capacity factor patterns. This classification is used for independent stochastic perturbations — each resource type receives its own perturbation distribution rather than a uniform scaling factor applied to all generators.

**Note on performance loops:** For any test involving repeated solves (scenarios, contingencies), clone the base network object rather than reloading from file. Record per-unit metrics (time per scenario, time per contingency) alongside totals.

**Note on generator cost curves (A-3, A-5, A-6):** The MATPOWER .m reference case files contain polynomial (quadratic) generator cost curves. Phase 1 uses whatever cost curves ship with the reference cases as-is — the evaluator documents which cost model is in effect (linear, quadratic, piecewise-linear) and any solver implications. Each tool's support for piecewise-linear cost curves must be documented as a finding under Expressiveness (Criterion 1), even though the Phase 1 tests do not specifically exercise piecewise-linear formulations. A tool that supports only linear cost curves would face a significant limitation in any operational deployment.

---

### Test Suite B: Extensibility

Each test maps to a sub-question in Rubric Criterion 2. **All tests are first run on TINY for functional verification, then on the indicated scale network for grade assessment.**

| ID | Sub-question | Test | Functional (TINY) | Grade Network | Pass Condition |
|----|-------------|------|-------------------|---------------|---------------|
| B-1 | Custom constraints | Add a flow gate limit (sum of flows on a specified set of lines ≤ threshold) to the DC OPF formulation from A-3. Read and assert on the custom constraint's dual value (non-zero when binding, zero when not). Produce a binding constraint report listing all constraints, binding status, and dual values. | yes | MEDIUM | Achievable through a documented API or extension mechanism. No source patching or forking required. Dual value of custom constraint extractable and correctly reflects binding status. |
| B-2 | Network graph access | From a chosen bus, run BFS to depth 3. Return all buses and branches within that subgraph. | yes | MEDIUM | Works via native graph primitives or clean, documented export to NetworkX (Python) or Graphs.jl (Julia). |
| B-3 | Contingency loop | Solve N-1 DCPF contingencies. Collect max line loading across all cases. | yes | MEDIUM | Runs in a loop without re-parsing or re-instantiating the base model from file each iteration. Base model is modified in-place or cloned efficiently. |
| B-4 | Stochastic scenario wrapping | Generate 20 scenarios by sampling load and renewable generation timeseries from a distribution (e.g., correlated perturbations drawn from a multivariate normal) with independent perturbations by resource type. Solve a 12hr multi-period DCOPF for each scenario. Collect prices and dispatch. | yes | SMALL | Tool accepts timeseries inputs programmatically (not from config files only). Scenario loop is expressible without excessive per-scenario overhead. Results (prices, dispatch) are collectable in a structured format. |
| B-5 | Interoperability | Export DCPF results from A-1 to a pandas DataFrame (Python) or DataFrames.jl DataFrame (Julia) and write to CSV. | yes | MEDIUM | Trivial — fewer than 5 lines of code beyond the solve. No custom serialization logic required. |
| B-6 | Code architecture | Qualitative assessment: read the source code for the DCPF solve path. Trace from API call to solver invocation. | N/A | N/A | Document: number of abstraction layers, whether network model / problem formulation / solver interface / results are separated, whether internal interfaces are documented. |
| B-7 | AC feasibility as extension | If AC feasibility check (A-4) required a workaround, document and classify the workaround here. | yes | MEDIUM | Workaround durability assessed. Effort level documented. |
| B-8 | Reference bus configuration | Solve DC OPF on TINY with three different slack configurations: (a) default single slack, (b) a different single slack bus, (c) custom-weighted distributed slack. Compare LMPs across all three. | yes | SMALL | Reference bus / slack formulation is configurable via API without model reconstruction. LMP values change consistently across configurations. Evaluator documents the API calls required and workaround durability. |
| B-9 | PTDF matrix extraction | Compute the PTDF matrix for TINY (39-bus). Verify dimensions (branches x buses). Verify that PTDF-predicted flows match DCPF-solved flows for a given injection pattern. | yes | MEDIUM | PTDF matrix accessible via native API, internal matrix extraction, or unit-injection computation. Flow predictions match DCPF results within numerical tolerance (1e-6). If the network contains phase-shifting transformers (nonzero SHIFT column in branch data), the PTDF validation must either (a) apply Pbusinj/Pfinj correction terms from the admittance matrix construction (`corrected_flow = PTDF @ (Pinj - Pbusinj) + Pfinj`), or (b) exclude branches with nonzero shift angles from the accuracy comparison. The 1e-6 tolerance applies to the corrected or filtered comparison. On MEDIUM, document computation time and method. |

**Recording for each B-test:** Pass/fail on TINY, lines of code, API or method used, workaround durability class, total time on grade network (for B-3, B-4, B-8, and B-9).

**Note on TINY for B-3:** On TINY, the contingency loop test uses all 46 branches (full N-1 on the IEEE 39-bus) rather than the 50-branch subset used on MEDIUM. The purpose is functional — does the loop construct work without model re-instantiation? The count is adjusted for MEDIUM to test at realistic volume.

**Note on B-4:** This tests the effort to *wrap* a tool for stochastic analysis when the tool does not natively support it (as tested in A-8). Key factors: Can timeseries be injected via the API, or must config files be rewritten per scenario? Can the model be re-solved with modified timeseries without full reconstruction? Is results collection across scenarios straightforward? The stochastic inputs should use temporally correlated perturbations (not i.i.d. noise per interval) to test whether the tool's timeseries interface supports realistic scenario structures. Perturbation bounds must be calibrated to produce at most 20% infeasible scenarios on the target network. If infeasibility exceeds 20%, reduce perturbation sigma until the threshold is met and document the final sigma used. Alternatively, OPF formulations may include slack variables for load shedding to prevent infeasibility — document if this approach is used.

---

### Test Suite C: Scalability

Scalability tests reuse the functional tests from Suites A and B but focus on performance measurement at scale. **TINY is not used for Suite C — these tests run on SMALL and MEDIUM only.** No pre-defined pass/fail time thresholds — results are recorded and compared across tools.

| ID | Test | Network | Solver(s) | Record |
|----|------|---------|-----------|--------|
| C-1 | DCPF | MEDIUM | N/A (direct solve) | Wall-clock time, peak memory |
| C-2 | ACPF | MEDIUM | Ipopt | Wall-clock time, peak memory, iterations |
| C-3 | DC OPF | MEDIUM | HiGHS, GLPK | Wall-clock time per solver, peak memory, objective value (verify consistency across solvers) |
| C-4 | SCUC 24hr | SMALL | HiGHS, SCIP | Wall-clock time per solver, MIP gap at termination, peak memory |
| C-5 | N-M contingency sweep (x=5, m=2) | MEDIUM | N/A | Total time, per-contingency-case average, peak memory, number of cases evaluated per order (N-1, N-2), pruning ratio. N-3 and N-4 results are informational only and do not affect the grade. |
| C-6 | 20-scenario stochastic DCOPF (12hr, independent perturbations by resource type, ≤20% infeasibility) | SMALL | HiGHS | Total time, per-scenario average, peak memory, price extraction. Perturbation bounds calibrated per B-4 note. |
| C-7 | Solver swap | Repeat C-3 with each available open-source solver | MEDIUM | Whether solver swap requires reformulation or just a parameter change. Time per solver. |
| C-8 | SCOPF (N-1, 50 contingencies on SMALL, 50 on MEDIUM) | MEDIUM | HiGHS | Wall-clock time, peak memory, number of iterations (if screening), number of binding contingencies. Iterative contingency screening permitted. |
| C-9 | PTDF matrix computation | MEDIUM | N/A | Wall-clock time, peak memory, matrix density. Phase-shifter correction terms (Pbusinj/Pfinj) must be applied per B-9 requirements. |
| C-10 | Distributed slack DC OPF | MEDIUM | HiGHS | Wall-clock time, peak memory, LMP comparison vs single-slack |

**Additional recording for all C-tests:**
- CPU utilization (is the tool using multiple cores, or is it single-threaded?)
- Whether the tool exposes parallelism controls (number of threads, batch dispatch)
- Any out-of-memory events or swap usage

---

### Test Suite D: Workforce Accessibility

Structured qualitative tests.

| ID | Test | Method | Record |
|----|------|--------|--------|
| D-1 | Install-to-first-solve | Start from a clean environment. Install the tool and all dependencies. Run DCPF on TINY. | Wall-clock time from start to successful solve. Number and severity of issues encountered. |
| D-2 | Documentation audit | For each test in Suite A, attempt to complete the test using only official documentation (no source code reading, no GitHub issues, no Stack Overflow). | Which tests were completable from docs alone. Where did the evaluator have to read source, search issues, or guess? |
| D-3 | Example verification | Run every getting-started example and tutorial from the official documentation on the current release. | How many run without modification? How many require fixes? How many are silently broken? |
| D-4 | Error quality | Introduce three deliberate errors: (a) an infeasible OPF (set a line limit to 0), (b) a missing generator cost curve, (c) an invalid bus type. | For each: does the tool surface a meaningful diagnostic, a cryptic solver error, or fail silently? |
| D-5 | Code volume comparison | Count lines of code required for each test in Suite A across all tools. | LOC comparison table. Lower is better for accessibility, all else equal. |

---

### Test Suite E: Maturity & Sustainability

Audit-based. No runtime tests.

| ID | Check | Method | Record |
|----|-------|--------|--------|
| E-1 | Release cadence | Examine release history for last 24 months. | Number of releases, date of last release, whether releases are versioned (semver or equivalent). |
| E-2 | Commit activity | Examine commit history for last 12 months. | Total commits, number of unique committers, ratio of substantive commits (features, fixes) to maintenance (dependency bumps, CI). |
| E-3 | Contributor concentration | Identify top 3 contributors by commit volume over project lifetime. | Percentage of total commits from top contributor. Bus factor assessment. |
| E-4 | Funding model | Research institutional backing. | Funding source(s), grant dependency, institutional affiliation. Assess durability. |
| E-5 | Issue tracker health | Sample last 20 closed issues and last 10 open issues. | Median time-to-close, ratio of acknowledged to ignored issues, quality of responses. |
| E-6 | CI/CD and test coverage | Examine CI configuration and test suite. | CI exists (yes/no), test suite exists (yes/no), approximate coverage if measurable, whether tests pass on current release. |
| E-7 | Operational adoption | Search for evidence of use by utilities, ISOs, government entities, or in production contexts. | Documented deployments, case studies, or credible references. Distinguish from academic-only citation. |

---

### Test Suite F: Supply Chain, Inspectability & Licensing Risk

Audit-based. This is the **gate criterion** — a C grade here is disqualifying.

| ID | Check | Method | Record |
|----|-------|--------|--------|
| F-1 | Core license | Identify license of the main package. | License type. Flag if copyleft (requires legal review) or proprietary (disqualifying). |
| F-2 | Dependency tree enumeration | Generate full dependency tree (`pip freeze` / `Pkg.status` with full manifest). | Total dependency count, tree depth, any unresolvable or unpinned dependencies. |
| F-3 | Dependency license audit | Check license of every direct dependency and all transitive dependencies that execute at runtime. | Any proprietary, unknown, or problematic licenses flagged. |
| F-4 | Compiled extension audit | Identify any compiled components (C extensions, Cython, Fortran, shared libraries) in the execution path. | For each: is source available? Is it buildable from source? |
| F-5 | Code inspectability trace | Trace the execution path from API call (e.g., `solve_dc_opf()`) to solver invocation. Identify every module that executes. | Full module list. Any opaque steps flagged. |
| F-6 | Distribution integrity | Check how releases are distributed. | Versioned releases (yes/no), signed artifacts (yes/no), distribution channel (PyPI, Julia Registry, GitHub). Flag unversioned tarballs or blob store artifacts. |
| F-7 | Air-gap installability | Assess whether the tool and all dependencies can be installed on an air-gapped network. | Can all packages be downloaded as files and installed offline? Any dependencies that require network access at runtime? |
| F-8 | Solver dependency assessment | Confirm that all target use cases are functional on open-source solvers alone. | Which solvers tested (HiGHS, SCIP, Ipopt, GLPK). Any use cases that fail or degrade unacceptably without a commercial solver. |
| F-9 | Getting-started artifact integrity | Examine official getting-started examples and tutorials. | Are examples pinned to a specific release version? Or do they reference unversioned downloads, `main` branch, or mutable URLs? |

---

### Test Suite G: FNM Ingestion

Suite G tests whether each tool can faithfully ingest and represent the Full Network Model (FNM) Annual S01 variant from the shared intermediate format. Unlike Suites A-F, which test problem expressiveness and extensibility on synthetic networks, Suite G tests **data model fidelity** on a production-scale ISO network — can the tool hold all the data, and does the data produce correct power flow results?

**FNM_PATH gating:** All Suite G tests require the `FNM_PATH` environment variable (see General Rule 6). When `FNM_PATH` is not set, all Suite G tests are skipped. When set, `FNM_PATH` must point to a directory containing the intermediate format output as described in `data/fnm/docs/intermediate-schema.md`.

**Suite G gate:** G-FNM-1 is the gate test. If G-FNM-1 fails (the tool cannot ingest the intermediate format to the required record-count fidelity), G-FNM-2 through G-FNM-5 are skipped. This mirrors the relationship between G-1 (TINY ingestion) and Suites A-F.

**No TINY progression:** Suite G does not follow the "TINY first, then scale" pattern. The FNM is a single ~30K-bus network with no smaller equivalent. Tools are tested directly on the LARGE network.

**Reference documents:** Suite G test cases reference the following documents. Evaluate-tool agents must load these at runtime:
- Intermediate format schema: `data/fnm/docs/intermediate-schema.md`
- Field criticality matrix: `data/fnm/docs/field-criticality-matrix.md`
- Pass conditions: `data/fnm/reference/pass_conditions.json`
- Cleaned MATPOWER case: `data/fnm/reference/cleaned/fnm_main_island.mat` (for G-FNM-3/4 power flow)
- Cleaning manifest: `data/fnm/reference/cleaned/summary_cleaning.json`
- DCPF reference solution: `data/fnm/reference/dcpf/`
- ACPF failure analysis: `data/fnm/reference/acpf/summary_acpf.json`
- Supplemental CSV reference: `data/fnm/docs/supplemental-csvs.md`
- Bus exclusion registry: `data/fnm/reference/excluded_buses.json`

| ID | Test | Inputs | Procedure | Pass Condition | References |
|----|------|--------|-----------|----------------|------------|
| G-FNM-1 | Intermediate format ingestion (gate) | Intermediate format tables at `FNM_PATH`, manifest file | Load every intermediate format table listed in the manifest. For each table, count the ingested records (buses, branches, generators, loads, transformers, shunts, etc.). Compare counts against the manifest's expected record counts per table. | All record counts match the manifest exactly. Zero records missing, zero extra records. If the tool's data model merges record types (e.g., branches and transformers into a single table), the merged count must equal the sum of the constituent intermediate format table counts. If any table fails the count check, the tool fails G-FNM-1 and G-FNM-2 through G-FNM-5 are skipped. | `data/fnm/docs/intermediate-schema.md` (table definitions), manifest file at `FNM_PATH` |
| G-FNM-2 | Field coverage audit | Ingested FNM model from G-FNM-1, field criticality matrix | For each intermediate format table: enumerate the fields that the tool's data model actually contains after ingestion. Compare against the field criticality matrix to compute coverage percentage by criticality tier. Report four percentages per table: % of DCPF-critical fields present, % of ACPF-critical fields present, % of Informational fields present, % of Discardable fields present. | 100% of DCPF-critical fields must be present across all tables. This is a hard requirement — any missing DCPF-critical field is a finding that directly impacts the Expressiveness grade. ACPF-critical field coverage is reported but not gated — tools that omit some ACPF-critical fields (e.g., switched shunt discrete steps) receive a documented finding. Informational and Discardable field omissions are noted but carry no grade impact. The coverage report must identify each missing field by name, table, and criticality tier. | `data/fnm/docs/field-criticality-matrix.md` (tier assignments per field per table) |
| G-FNM-3 | DCPF verification | **Primary:** Intermediate CSV tables at `data/fnm/reference/cleaned/intermediate/`. **Fallback:** Cleaned MATPOWER case (`data/fnm/reference/cleaned/fnm_main_island.mat`). DCPF reference solution at `data/fnm/reference/dcpf/`. | **Primary path (CSV):** Load the intermediate CSV tables from `data/fnm/reference/cleaned/intermediate/` into the tool's data model. **Fallback path (MATPOWER):** If the tool lacks CSV ingestion capability, load the pre-cleaned MATPOWER case (27,862-bus main island with all data fixes pre-applied per `summary_cleaning.json`). Record which input path was used in result frontmatter as `input_path: "csv"` or `input_path: "matpower"`. Solve DCPF. Extract bus voltage angles and branch active power flows. Load the DCPF reference solution from `data/fnm/reference/dcpf/`. Compute aggregate deviation metrics as defined in `pass_conditions.json` under the `dcpf` key: (a) fraction of buses with VA deviation within tolerance, (b) fraction of in-service branches with P deviation within tolerance. Check against aggregate pass thresholds and hard-fail thresholds. | Pass if all aggregate thresholds are met and no hard-fail condition is triggered, per the `dcpf` section of `data/fnm/reference/pass_conditions.json`. Buses and branches that exceed the aggregate tolerance but are classified as known outlier causes (per the outlier classification rules in pass_conditions.json) are reported as classified outliers, not unqualified failures. If the tool cannot solve DCPF on the FNM at all (solver failure, out of memory, or timeout after 10 minutes), record the failure mode. If failure is due to scale (tool works on MEDIUM but not LARGE), attribute to Scalability. If failure is due to data model issues (missing topology, incorrect parameters), attribute to Expressiveness. | `data/fnm/reference/cleaned/intermediate/` (CSV tables), `data/fnm/reference/cleaned/fnm_main_island.mat` (MATPOWER fallback), `data/fnm/reference/pass_conditions.json` (thresholds), `data/fnm/reference/dcpf/` (reference angles and flows) |
| G-FNM-4 | ACPF convergence | **Primary:** Intermediate CSV tables at `data/fnm/reference/cleaned/intermediate/`. **Fallback:** Cleaned MATPOWER case (`data/fnm/reference/cleaned/fnm_main_island.mat`). ACPF failure analysis at `data/fnm/reference/acpf/summary_acpf.json`. | **Primary path (CSV):** Load the intermediate CSV tables from `data/fnm/reference/cleaned/intermediate/` into the tool's data model. **Fallback path (MATPOWER):** If the tool lacks CSV ingestion capability, load the pre-cleaned MATPOWER case. Record which input path was used in result frontmatter as `input_path: "csv"` or `input_path: "matpower"`. Attempt ACPF solve. **No reference solution exists** -- MATPOWER 8.1 fails on all solver variants (voltage collapse at ~30% load; see `data/fnm/reference/acpf/summary_acpf.json`). This test assesses **solver robustness**: can the tool converge where MATPOWER cannot? Record: (a) whether ACPF converges, (b) solver algorithm used, (c) convergence residual and iteration count, (d) if converged, VM/VA statistics (min, max, mean) and total losses. If two or more tools converge, compare their solutions cross-tool to verify consistency (cross-tool deviations within `pass_conditions.json` ACPF thresholds). | **Convergence is a positive finding, not a requirement.** If the tool converges, record it as a discriminating strength in solver robustness (Expressiveness narrative). If the tool fails to converge, record the failure mode but do not penalize -- MATPOWER itself cannot solve this case. The test is informational evidence, not a gate. If multiple tools converge, cross-tool consistency checks apply using the `acpf` thresholds in `pass_conditions.json`. | `data/fnm/reference/cleaned/intermediate/` (CSV tables), `data/fnm/reference/cleaned/fnm_main_island.mat` (MATPOWER fallback), `data/fnm/reference/acpf/summary_acpf.json` (MATPOWER failure analysis), `data/fnm/reference/pass_conditions.json` (cross-tool thresholds) |
| G-FNM-5 | Supplemental CSV representability | Ingested FNM model from G-FNM-1, 7 supplemental CSVs at `FNM_PATH`, supplemental CSV reference documentation | For each of the 7 supplemental CSVs (`LINE_AND_TRANSFORMER.csv`, `TRADING_HUB.csv`, `GEN_DISTRIBUTION_FACTOR.csv`, `CONTINGENCY.csv`, `INTERFACE.csv`, `INTERFACE_ELEMENT.csv`, `OUTAGE.csv`): (a) attempt to attach each field's data to the tool's network model using native attributes or the tool's documented extension mechanisms, (b) for each field, record whether attachment succeeded as natively-representable (N), extension-representable (E), or tool-external (X), (c) compare the achieved representability against the analytical classification in `data/fnm/docs/supplemental-csvs.md` and note any discrepancies (e.g., a field classified as E that turns out to be N in practice, or classified as E but actually X due to an undocumented limitation). | No hard pass/fail gate. This is an evidence-collection test. For each CSV, report: total fields, count and percentage by achieved representability tier (N/E/X), and per-field comparison against the analytical classification. The results feed into the Extensibility grade narrative per rubric v5's supplemental CSV representability grading note. Key findings to highlight: (a) fields where achieved representability differs from analytical classification, (b) the tool's overall supplemental data burden (percentage of fields requiring tool-external handling), (c) which supplemental CSV concepts are entirely tool-external (no native or extension path). | `data/fnm/docs/supplemental-csvs.md` (per-field analytical classifications and representability matrices), `data/fnm/docs/supplemental-csv-representability.md` (cross-tool summary) |

**Recording for each G-test:** Pass/fail/skip status, wall-clock time, peak memory (for G-FNM-3 and G-FNM-4), per-table record counts (G-FNM-1), per-table per-tier field coverage percentages (G-FNM-2), aggregate metrics and outlier classification breakdown (G-FNM-3, G-FNM-4), per-CSV per-field representability achieved vs. classified (G-FNM-5). All results include `protocol_version: "v8"` in YAML frontmatter. G-FNM-3 and G-FNM-4 results must additionally include `input_path: "csv"` or `input_path: "matpower"` to record which input path was used.

**Note on G-FNM-1 (record count verification):** The manifest file at `FNM_PATH` lists every intermediate format table with its expected record count. This is the output of the Phase 1 data pipeline's canonical parser. The manifest is the source of truth for record counts — it is not the PSS/E header record count (which may differ due to parser handling of multi-section lines, 3-winding transformer expansion, or record type merging). If a tool's data model combines what the intermediate format stores as separate tables (e.g., 2-winding and 3-winding transformers in a single collection), the tool's combined count must equal the sum of the constituent manifest counts.

**Note on G-FNM-2 (field coverage):** The field criticality matrix assigns every intermediate format field to exactly one of four tiers: DCPF-critical, ACPF-critical, Informational, or Discardable. A "present" field is one where the tool's data model has a corresponding attribute or data element after ingestion — it does not require that the value is numerically identical to the source (value fidelity is tested in G-FNM-3 and G-FNM-4). The key distinction: G-FNM-2 tests structural completeness (are the right fields present?); G-FNM-3/G-FNM-4 test numerical fidelity (are the values correct?). Fields carried via extension mechanisms (custom attributes, metadata dictionaries) count as present. Fields that exist only in an external data structure alongside the tool's network model do not count as present for G-FNM-2 — they are assessed in G-FNM-5's representability framework instead.

**Note on G-FNM-3 and G-FNM-4 (power flow verification):** G-FNM-3 and G-FNM-4 use the cleaned network data, not the raw intermediate format. The **primary input path** is intermediate CSV tables at `data/fnm/reference/cleaned/intermediate/`, which contain the cleaned network in tabular form. The **fallback input path** is the pre-cleaned MATPOWER case (`data/fnm/reference/cleaned/fnm_main_island.mat`), available for tools that lack CSV ingestion capability. Both input paths represent the same cleaned network with all data fixes pre-applied (negative-X coercion, zero-impedance fixes, zero-RATE_A fixes, main island extraction, single-slack reduction) per `summary_cleaning.json`. This ensures all tools solve on identical input data -- cleaning is not part of the test. The result file must record which path was used via the `input_path` frontmatter field. G-FNM-1 and G-FNM-2 still use the raw intermediate format (testing ingestion fidelity). G-FNM-3 and G-FNM-4 use the cleaned data (testing solver accuracy on known-good input).

G-FNM-4 is reframed as a convergence capability test because MATPOWER 8.1 cannot produce an ACPF reference solution (voltage collapse at ~30% load on this flat-start planning model). Tools with more robust initialization (homotopy, voltage regulation heuristics) may succeed where MATPOWER fails -- this is a discriminating test of solver robustness.

The pass conditions are parameterized in `data/fnm/reference/pass_conditions.json` -- the evaluate-tool agent loads the JSON at runtime and applies the thresholds programmatically. The protocol does not hardcode threshold values to avoid duplication and version drift with the pass condition specification. If a tool's DCPF or ACPF solve takes longer than 10 minutes wall-clock time on the reference hardware, record a timeout finding. Timeout is not an automatic failure -- it is recorded and the evaluator determines whether it reflects a scale limitation (Scalability) or a data model issue (Expressiveness) based on whether the tool succeeds on MEDIUM-scale networks.

**Note on G-FNM-5 (supplemental CSV representability):** This test bridges data model assessment and extensibility assessment. It is the only Suite G test that evaluates the tool's extension mechanisms rather than its core data model. The 7 supplemental CSVs carry market-specific data (trading hub definitions, generator distribution factors, contingency definitions, interface limits, thermal rating tiers, outage schedules) that no tool natively ingests. The test measures how much of this data a tool can absorb into its network model versus how much must remain in external data structures. The analytical classifications in `data/fnm/docs/supplemental-csvs.md` are pre-evaluation estimates — G-FNM-5 empirically validates or corrects them. Discrepancies between analytical and empirical classifications are valuable findings.

**Note on failure attribution:** Suite G tests can fail for two distinct reasons: scale and data model. Scale failures (the tool works on smaller networks but cannot handle ~30K buses) are attributed to Scalability (Criterion 4). Data model failures (the tool lacks representation for required record types, or incorrect parameter mapping causes power flow deviation) are attributed to Expressiveness (Criterion 1). The evaluate-tool agent makes this attribution based on whether the tool passes the corresponding Suite A/B tests on MEDIUM. If a tool passes A-1 (DCPF) on MEDIUM but fails G-FNM-3, and the failure is due to a record type the tool does not support (e.g., 3-winding transformers), the attribution is Expressiveness. If the failure is a solver timeout or out-of-memory at 30K-bus scale, the attribution is Scalability.

### `formulation_difference` Tag

The `formulation_difference` tag may be applied to G-FNM-3 and G-FNM-4 deviations when the deviation is attributable to a legitimate formulation difference between the tool under evaluation and the reference solver. Formulation differences arise from different mathematical representations of the same physical network element — for example, different transformer tap models, different phase-shifter angle conventions, or different treatment of zero-impedance branches. These differences produce systematic deviations that are deterministic and explainable, not random solver variation.

**Decision procedure** — the following 6-step procedure determines whether the `formulation_difference` tag applies to a set of unclassified failing buses:

1. **Compute unclassified set.** After applying all existing outlier classification rules (switched_shunt, q_limit, slack_distribution, tap_position, island_boundary), compute the set of buses that still fail the aggregate tolerance but are not classified by any existing rule. These are the candidate buses for `formulation_difference` classification.
2. **Test correlation with transformer/phase-shifter branches.** For each candidate bus, determine whether it is electrically adjacent to (connected by) a transformer or phase-shifter branch. Compute `correlation_fraction` = count(candidate buses adjacent to transformer/phase-shifter branches) / count(all candidate buses).
3. **Correlation gate.** If `correlation_fraction` < 0.80, STOP — the `formulation_difference` tag does NOT apply. The deviation pattern is not sufficiently correlated with transformer/phase-shifter branches to support a formulation-difference explanation.
4. **Boundedness gate.** Compute the maximum absolute deviation among all candidate buses. For DCPF (G-FNM-3), compare against `formulation_difference_max_abs.threshold_deg` in the `dcpf` section of `pass_conditions.json`. For ACPF (G-FNM-4), compare against `formulation_difference_max_abs.threshold_pu` in the `acpf` section. If the maximum absolute deviation exceeds the threshold (and the threshold is not null), STOP — the `formulation_difference` tag does NOT apply. Deviations beyond this bound are too large to attribute to formulation differences.
5. **Apply tag.** If both gates pass, apply the `formulation_difference` tag to all candidate buses that are adjacent to transformer/phase-shifter branches. Populate the `formulation_difference_detail` block in the result file's YAML frontmatter (see schema below).
6. **Recalculate pass/fail.** Recompute aggregate pass metrics with `formulation_difference`-tagged buses treated as classified outliers (same treatment as switched_shunt, q_limit, etc.). **Hard-fail conditions are NOT relaxed** — if any hard-fail threshold is exceeded (excessive_failing_fraction, extreme deviation), the test still fails regardless of `formulation_difference` classification.

**`formulation_difference_detail` frontmatter schema** — when the `formulation_difference` tag is applied, the result file's YAML frontmatter must include the following block:

```yaml
formulation_difference_detail:
  correlated_branch_type: "transformer"  # or "phase_shifter" or "transformer_and_phase_shifter"
  max_abs_deviation_pu: 0.0032           # for ACPF; use max_abs_deviation_deg for DCPF
  affected_bus_count: 47
  affected_bus_fraction: 0.0017          # affected_bus_count / non_excluded_buses
  explanation: "Brief description of the formulation difference and why it produces the observed deviation pattern."
```

The fields are:
- **`correlated_branch_type`**: The type of branch most correlated with the deviation pattern (`"transformer"`, `"phase_shifter"`, or `"transformer_and_phase_shifter"`).
- **`max_abs_deviation_pu`** (ACPF) or **`max_abs_deviation_deg`** (DCPF): The maximum absolute deviation among the `formulation_difference`-tagged buses.
- **`affected_bus_count`**: Number of buses tagged with `formulation_difference`.
- **`affected_bus_fraction`**: `affected_bus_count / count(non_excluded_buses)`.
- **`explanation`**: Human-readable explanation of the identified formulation difference and its mechanism.

---

### Phase 2 Readiness Findings

These findings are informational and do not affect Phase 1 grades. They are collected during Phase 1 evaluation to inform Phase 2 planning effort estimates.

| ID | Finding | Method | Record |
|----|---------|--------|--------|
| P2-1 | PSS/E RAW parsing capability | Attempt to load a PSS/E RAW v30 or v33 test file (if available) or audit documentation/source code for parser existence | Capability (yes/no), supported RAW versions, estimated effort to add if absent |
| P2-2 | Piecewise-linear cost curve support | Documentation audit + functional probe on TINY: define 3-segment piecewise-linear cost curve for one generator, solve DCOPF. Also test quadratic cost if supported separately. | Capability (yes/no), formulation type (SOS2, lambda, incremental), solver compatibility, any limitations |
| P2-3 | Commitment injection workflow | On TINY: obtain SCUC schedule from A-5, lock commitments, solve DCOPF, run AC PF feasibility check | Capability per step, effort level, API friction |

---

## Results Recording

All test results are collected in a structured format:

```
results/
├── {tool_name}/
│   ├── environment.yaml       # Tool version, solver versions, OS, hardware
│   ├── gate/
│   │   ├── G-1.md             # Ingestion test TINY
│   │   ├── G-2.md             # Ingestion test SMALL
│   │   └── G-3.md             # Ingestion test MEDIUM
│   ├── expressiveness/
│   │   ├── A-1_tiny.md        # DCPF functional verification on TINY
│   │   ├── A-1_tiny.py or .jl # Test script (TINY)
│   │   ├── A-1.md             # DCPF grade assessment on scale network
│   │   ├── A-1.py or A-1.jl   # Test script (scale)
│   │   └── ...
│   ├── extensibility/
│   │   └── ...
│   ├── scalability/
│   │   └── ...
│   ├── accessibility/
│   │   └── ...
│   ├── maturity/
│   │   └── ...
│   ├── supply_chain/
│   │   └── ...
│   ├── fnm_ingestion/
│   │   ├── G-FNM-1.md          # Intermediate format ingestion
│   │   ├── G-FNM-1.py or .jl   # Ingestion test script
│   │   ├── G-FNM-2.md          # Field coverage audit
│   │   ├── G-FNM-2.py or .jl   # Coverage audit script
│   │   ├── G-FNM-3.md          # DCPF verification
│   │   ├── G-FNM-3.py or .jl   # DCPF test script
│   │   ├── G-FNM-4.md          # ACPF verification
│   │   ├── G-FNM-4.py or .jl   # ACPF test script
│   │   ├── G-FNM-5.md          # Supplemental CSV representability
│   │   └── G-FNM-5.py or .jl   # Supplemental data test script
```

Each test result file (.md) includes YAML frontmatter with at minimum:
- **`protocol_version`** — the version of this protocol used (currently `"v8"`)
- For Suite G results, use `protocol_version: "v8"`. Existing Suite A-F results produced under v5 remain valid — Suite G is additive and does not alter any v5 test definitions. Mixed-version result sets (v5 for Suites A-F, v8 for Suite G) are expected and do not require re-evaluation of existing results. Results produced under v6 (before cleaned case export and G-FNM-4 reframing) should be re-evaluated under v8. G-FNM-3 and G-FNM-4 results must include `input_path: "csv"` or `input_path: "matpower"` in frontmatter.
- **Test ID and description**
- **Network used** (TINY, SMALL, or MEDIUM)
- **Pass / Fail / Qualified Pass**
- **Workaround durability class** (if applicable: Stable / Fragile / Blocking)
- **`blocked_by`** (if applicable) — the prerequisite test ID that caused this test to be blocked
- **Wall-clock time and peak memory** (if applicable — must be measured, not estimated, for Suite C)
- **Lines of code** (if applicable)
- **Narrative** — what happened, what worked, what didn't, and what it implies for the grade
- **Link to test script** (.py or .jl)

Results produced under different protocol versions should be compared with caution. If re-evaluation is not feasible, document the version mismatch and note any tests where the version difference materially affects comparability (e.g., changed pass conditions, adjusted parameters).

---

## From Test Results to Grades

The rubric defines grading standards (A/B/C) for each criterion. The evaluator assigns grades by mapping test results to those standards as follows:

1. **Gate criterion (Supply Chain, Inspectability & Licensing):** Any disqualifying finding in Suite F → grade C → tool excluded.
2. **Gate test (Data Ingestion):** Failure on G-1 (TINY) → tool excluded from further evaluation. Failure on G-3 (MEDIUM) after passing G-1 → tool proceeds with functional evaluation but scalability grades are capped.
3. **TINY → Scale progression:** A test that fails on TINY is recorded as a failure on the criterion — there is no need to attempt it at scale. A test that passes on TINY but fails at scale is an Expressiveness pass with a Scalability finding.
4. **Per-criterion grades:** The evaluator reviews all test results relevant to that criterion and assigns A/B/C based on the rubric's grading standards. The test results are evidence; the grade is a judgment call informed by that evidence.
5. **Qualified passes and workarounds:** A test that passes only with a Fragile or Blocking workaround pulls the relevant sub-question toward B or C. The evaluator documents which workarounds influenced the grade. Specific grade impact by workaround class:
   - **Stable workaround:** B range. A single stable workaround on one sub-question does not prevent B+.
   - **Fragile workaround:** B- to C+ range. The grade depends on how critical the affected sub-question is.
   - **Blocking workaround:** Effective fail for the sub-question — treated as C on that item.
   - **Multiple stable workarounds:** Compounds toward B-. Three or more stable workarounds on a single criterion suggest systematic friction, not isolated gaps.
6. **Cross-tool comparison:** After all tools are graded independently, the evaluator reviews grades side-by-side to ensure consistency. If Tool X and Tool Y both received B on Expressiveness but X required significantly more workarounds, the grades should reflect that difference.
7. **FNM Ingestion (Suite G) — when FNM_PATH is set:** Suite G results provide additional evidence for Expressiveness and Extensibility grades, as specified in rubric v5 grading notes. The mapping is:
   - **G-FNM-1 (Ingestion) and G-FNM-2 (Field Coverage):** Inform Expressiveness. Record type coverage and field-level fidelity demonstrate data model breadth beyond what synthetic cases can test. G-FNM-2's per-tier coverage percentages (DCPF-critical, ACPF-critical, Informational) provide granular evidence: 100% DCPF-critical coverage is the minimum for a credible Expressiveness grade; gaps in ACPF-critical fields are noted findings. Discardable field omissions are not penalized.
   - **G-FNM-3 (DCPF Verification) and G-FNM-4 (ACPF Verification):** Inform Expressiveness sub-questions 1 and 2 (DC and AC power flow). Passing these tests demonstrates that the tool's data model fidelity is sufficient for production-scale computation. If failure is due to scale (the tool cannot handle ~30K buses), the finding is attributed to Scalability (Criterion 4), not Expressiveness. If failure is due to missing record type support or incorrect parameter mapping, the finding is attributed to Expressiveness.
   - **G-FNM-5 (Supplemental CSV Representability):** Informs Extensibility. The proportion of supplemental CSV fields that are natively-representable, extension-representable, or tool-external directly indicates the post-ingestion extension burden. This maps to Extensibility sub-questions 1 (custom constraints — supplemental data like interface limits feed custom constraints), 5 (interoperability — tool-external fields require synchronized external data structures), and 6 (code architecture — ease of data model extension).
   - **Grade impact:** Suite G results strengthen or weaken the evidence base for the grade assigned by Suites A-F, but do not independently determine the grade. A tool that passes all synthetic-network tests but fails FNM ingestion entirely receives a grade note documenting the gap. The A/B/C grade boundaries defined in the rubric are unchanged. See rubric v5 grading notes under Criterion 1 ("Note on FNM data model fidelity") and Criterion 2 ("Note on FNM supplemental CSV representability") for the authoritative grade impact specification.

---

## Revision History

| Version | Date | Change | Author |
|---------|------|--------|--------|
| v1 | TBD | Initial draft | GRC |
| v2 | TBD | Added TINY tier (IEEE 39-bus) for functional verification. Added synthetic network assurance statement. Restructured test progression: TINY first for all functional tests, scale networks for grade assessment. Added G-1 gate on TINY. | GRC |
| v3 | 2026-03-05 | Added tests A-9 (SCOPF), A-10 (lossy DC OPF / LMP decomposition), A-11 (distributed slack OPF) with notes. Added tests B-8 (reference bus configuration) and B-9 (PTDF matrix extraction). Added scalability tests C-8 (SCOPF), C-9 (PTDF computation), C-10 (distributed slack OPF). Added Phase 2 Readiness Findings section (P2-1, P2-2). Strengthened A-6 pass condition to require demonstrable ramp rate enforcement in ED stage. Updated companion rubric reference to v2. Motivated by ISO SCED/SCOPF research revealing gaps in Phase 2 readiness assessment. | GRC |
| v4 | 2026-03-06 | Stochastic test methodology: A-8/B-4 require DCOPF (not DCPF), 12hr horizon (was 24hr), independent perturbations by resource type (cost tier proxy), price extraction. C-6 reduced to 20 scenarios (was 50). Shadow price/dual tests: A-10 adds congestion rent computation and LMP reconciliation. B-1 adds dual value assertion and binding constraint report. Performance reductions: A-5 SMALL MIP gap 10% (TINY retains 1%), B-3 MEDIUM contingencies 50 (was 100), A-9 SMALL contingencies 50 (was 100). SCOPF feasibility note for case39 thermal limits. Added P2-3 (commitment injection workflow). Extended P2-2 with TINY functional probe. Qualified pass grade impact made explicit. Added protocol_version to result frontmatter. Cost curve note corrected to acknowledge polynomial costs in MATPOWER files. Added resource type classification note and performance loop guidance. | GRC |
| v5 | 2026-03-09 | Cross-tool sweep amendments. Data preparation: added standardized ACTIVSg preprocessing (zero-impedance fixes, congestion induction via tightened branch limits) and ext2int conversion guidance (PC-01). ACPF verification: A-2 pass condition now requires convergence residual, iteration count, and non-flat-start voltage check (PC-02). PTDF validation: B-9/C-9 require phase-shifter correction terms (Pbusinj/Pfinj) or exclusion of phase-shifting branches (PC-03). SCUC cycling: A-5 requires demonstrable generator cycling with fleet augmentation guidance (PC-04). Timing discipline: estimated timings cannot support pass/qualified_pass on scalability tests (PC-05). Cascaded failures: added blocked_by field to distinguish inherited from independent failures (PC-06). Scale reductions: C-8 MEDIUM reduced from 500 to 50 contingencies (PC-07); C-5 MEDIUM capped at N-2 with N-3+ informational only (PC-08). Lossy DCOPF: A-10 validation changed from MATPOWER reference to internal consistency checks (PC-09). Stochastic calibration: B-4/C-6 perturbation bounds capped at ≤20% infeasibility (PC-10). Scoring rules: workarounds require qualified_pass (RC-01); tool expressiveness separated from solver performance (RC-02). | GRC |
| v6 | 2026-03-09 | FNM ingestion expansion: added Test Suite G (FNM Ingestion) with 5 test cases — G-FNM-1 (intermediate format ingestion gate), G-FNM-2 (field coverage audit vs. criticality matrix), G-FNM-3 (DCPF verification vs. reference), G-FNM-4 (ACPF verification vs. reference), G-FNM-5 (supplemental CSV representability). All Suite G tests gated by FNM_PATH. Added FNM_PATH gating rule to General Rules. Added LARGE reference network (FNM Annual S01, ~30K buses). Added Suite G to "From Test Results to Grades" with Expressiveness and Extensibility mapping. Added fnm_ingestion results directory. Mixed-version result sets (v5 + v6) explicitly permitted. Aligned with rubric v5 grading notes. | GRC |
| v7 | 2026-03-09 | FNM cleaned case export: G-FNM-3 and G-FNM-4 now load from pre-cleaned MATPOWER case (`data/fnm/reference/cleaned/fnm_main_island.mat`) with all 6 data fixes pre-applied (negative-X coercion, zero-X/R/RATE_A, island extraction, single-slack). G-FNM-4 reframed as convergence capability test — no ACPF reference exists (MATPOWER 8.1 fails at ~30% load). Tools that converge score a discriminating strength; failure is not penalized. Added cleaned case and cleaning manifest to reference documents. G-FNM-1/2 unchanged (still use raw intermediate format). | GRC |
| v8 | 2026-03-10 | Intermediate CSV tables as primary G-FNM-3/4 input path with MATPOWER `.m` as fallback. Added `input_path` frontmatter field (csv or matpower) for G-FNM-3 and G-FNM-4 results. Added `formulation_difference` tag definition with 6-step decision procedure (correlation gate at 0.80, boundedness gate against `formulation_difference_max_abs` from pass_conditions.json). Added `formulation_difference_max_abs` key to both `dcpf` and `acpf` sections of `pass_conditions.json`. Added `formulation_difference_detail` frontmatter schema. Hard-fail conditions are not relaxed by the tag. **Backward compatibility:** v7 results for G-FNM-1, G-FNM-2, and G-FNM-5 remain valid under v8. Only G-FNM-3 and G-FNM-4 results should be re-evaluated if produced under v7 without the `input_path` field. | GRC |
