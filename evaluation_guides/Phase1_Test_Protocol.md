# Phase 1 Test Protocol
## Contract  | Grid Research Company LLC

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

**Why IEEE 39-bus for TINY:** 39 buses, 10 generators, 46 branches. The network is completely synthetic — it does not represent any actual power system. It is meshed, has sufficient generator diversity (varied cost curves, capacity ranges) for unit commitment to be non-trivial, and includes enough branches that graph-distance-2 contingency sweeps produce a meaningful enumeration without hitting the network boundary. Every tool under evaluation either ships with this case or can ingest the MATPOWER .m format trivially. Solves complete in under a second for PF/OPF problems, making it suitable for rapid iteration during tool evaluation. It is also one of the most widely published-against test cases in power systems literature, providing reference results for sanity-checking.

**Why ACTIVSg 2k and 10k:** The ACTIVSg (Activation Synthetic Grid) cases were developed by Texas A&M specifically to provide realistic-looking but entirely fictional test networks. They are synthetic in topology, generation mix, load distribution, and geographic layout. They share statistical properties with real grids (degree distribution, impedance characteristics, generator cost profiles) but do not represent any actual system. The 2k-bus and 10k-bus cases provide scale-appropriate benchmarks without introducing any actual infrastructure data into the evaluation.

### Data Format Notes

The IEEE 39-bus and ACTIVSg cases are distributed in MATPOWER .m format. Each tool's ability to ingest this format — or a standard conversion of it — is tested as part of the evaluation. If a tool requires format conversion (e.g., to PSS/E RAW, PowerModels JSON, or PyPSA CSV), the conversion process and any data loss are documented.

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
   - Wall-clock time (for scalability-relevant tests)
   - Peak memory usage
   - Lines of code required to express the test
   - Any errors, warnings, or unexpected behavior
   - Version of tool, all companion packages, and solvers used

3. **No heroics.** If a test requires undocumented workarounds, reverse-engineering internals, or patching source code, the test is recorded as a qualified pass with the workaround documented and its durability assessed (see Workaround Durability below).

4. **Document the learning process.** For the Workforce Accessibility criterion, record the wall-clock time from clean install to first successful DCPF solve on TINY as a proxy for learning curve. Note any documentation gaps, broken examples, or misleading guidance encountered during setup.

5. **TINY first, then scale.** Every functional test (Suites A and B) is run on TINY before being attempted on SMALL or MEDIUM. If a tool cannot pass a functional test on a 39-bus network, there is no reason to attempt it at scale. This keeps evaluation velocity high and surfaces tool limitations early.

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
| A-2 | AC Power Flow | Solve ACPF (Newton-Raphson) | yes | MEDIUM | Converges. Bus voltage magnitudes and angles, line P/Q flows, and losses accessible as structured output. |
| A-3 | DC OPF | Solve DC OPF with gen costs and line flow limits | yes | MEDIUM | Converges. Optimal dispatch and LMPs/shadow prices extractable from solution. |
| A-4 | AC Feasibility Check | Take DC OPF dispatch from A-3, run full ACPF on that dispatch | yes | MEDIUM | Achievable within the same model context (no export to file and reimport). Voltage violations and thermal limit violations identifiable from results. |
| A-5 | SCUC | Solve 24-hour unit commitment as MILP with: min up/down times, startup costs, ramp rates, reserve requirements | yes | SMALL | Solves to feasibility (MIP gap ≤ 1%). Commitment schedule extractable as a time-indexed binary matrix. Built-in constraint types vs. user-assembled noted. |
| A-6 | SCED | Fix commitment schedule from A-5, solve economic dispatch as LP/QP | yes | SMALL | Solves. Dispatch schedule extractable. UC and ED are cleanly separable as a two-stage workflow. Ramp rate constraints are demonstrably enforced between consecutive dispatch intervals in the ED stage — not just inherited from the UC formulation. |
| A-7 | N-M Contingency Sweep | From a chosen bus, enumerate all branches within graph distance *x* (e.g. *x*=5). Sweep contingencies with escalating order up to *m* simultaneous outages (e.g. *m*=4). At each order *n*, any branch whose removal at order *n*-1 already produced total load loss is pruned from higher-order combinations — so the sweep does not return obvious, overlapping outage sets. | yes | MEDIUM | Completes without full model reconstruction per contingency case. Load loss per contingency case collected. Pruning logic is expressible without fighting the tool. Combinatorial enumeration and graph-distance scoping are achievable via the tool's API or a clean graph library bridge. |
| A-8 | Stochastic Timeseries | Solve a multi-period (24hr, hourly resolution) DC OPF or SCUC with stochastic load and renewable generation scenarios | yes | SMALL | Tool natively supports scenario-indexed timeseries for load, wind, and solar — the stochastic structure is part of the optimization formulation (e.g., scenario tree, two-stage stochastic program), not just independent deterministic solves in a loop. |
| A-9 | SCOPF | Solve DC OPF with N-1 contingency flow constraints embedded in the optimization. On TINY, use all 46 branches as the contingency set. On SMALL/MEDIUM, use a subset of monitored branches (100 on SMALL, 500 on MEDIUM) with iterative contingency screening allowed. | yes | SMALL | Solves. Base-case dispatch respects all contingency flow limits simultaneously. Dispatch and cost differ from unconstrained DC OPF (A-3) — SCOPF should be more expensive. Contingency constraints are part of the optimization, not checked post-hoc. If achievable only by manually enumerating contingency constraints via B-1's custom constraint API, document the effort and classify the workaround. |
| A-10 | Lossy DC OPF / LMP Decomposition | Solve DC OPF with loss approximation on TINY. Any loss method accepted (iterative loss factors, quadratic terms, penalty factors). Decompose LMPs into energy, congestion, and loss components. | yes | SMALL | Tool produces loss-inclusive LMPs where loss components are non-zero. LMP decomposition extractable as structured output. Validate against MATPOWER reference lossy DC OPF solution on same case (tolerance: 1% on total LMP, directional consistency on loss component signs). |
| A-11 | Distributed Slack OPF | Solve DC OPF on TINY with distributed slack (load-proportional). Compare LMPs to single-slack solution from A-3. | yes | SMALL | Tool supports distributed slack formulation. LMPs differ from single-slack results in a physically consistent manner (SMEC reflects the distributed reference). Distributed slack weights are settable via API (e.g., proportional to load, proportional to generation, or custom weights). |

**Recording for each A-test:** Pass/fail on TINY (with notes), wall-clock time on grade network, lines of code, output format, any workarounds and their durability class.

**Note on TINY verification:** On TINY, the pass condition is purely functional — does the tool express and solve the problem? Performance is not measured. If a tool passes on TINY but fails on the grade network, that is a Scalability finding, not an Expressiveness failure.

**Note on A-7:** The contingency sweep is an escalating, pruned search — not a flat N-1 loop. The algorithm works as follows: (1) Scope the search space by enumerating all branches within graph distance *x* of a chosen bus. (2) Run all N-1 contingencies within that set. Re-solve DCPF for each and record load loss. (3) Any branch whose N-1 removal already produces total load loss at the bus of interest is pruned — it does not appear in higher-order combinations, because any N-2 set containing that branch would produce a redundant, obvious result. (4) From the surviving branches, enumerate N-2 combinations, re-solve, prune again. (5) Continue escalating through N-3, N-4, ... up to N-*m*. This tests three things: graph-distance scoping (does the tool expose topology for enumeration?), efficient contingency re-solve (can branches be removed and restored without model reconstruction?), and programmability (can the pruning and escalation logic be expressed cleanly in user code on top of the tool's API?). On TINY, use *x*=3, *m*=3 to keep the combinatorial space trivial. On MEDIUM, use *x*=5, *m*=4 as the grade-assessment parameters.

**Note on A-8:** The distinction between "native stochastic support" and "loop over deterministic solves" is critical. A tool that only supports deterministic solves but can be wrapped in a Monte Carlo loop is tested under Extensibility (B-4), not here. A passing grade on A-8 requires that the tool's optimization formulation is aware of multiple scenarios simultaneously — e.g., co-optimizing across scenarios with recourse decisions, or enforcing chance constraints across a scenario set. Random noise applied independently to each interval without temporal correlation or cross-scenario structure does not constitute meaningful stochastic support and does not pass.

**Note on A-9:** The distinction between SCOPF and post-hoc contingency analysis (A-7) is critical. A-7 tests whether a tool can re-solve power flow for each contingency case after an initial OPF. A-9 tests whether the tool can incorporate contingency constraints into the OPF itself — the base-case dispatch is constrained to be feasible under all enumerated contingencies. This is how ISO market clearing engines actually work: they solve a preventive SCOPF where post-contingency flows (computed via LODFs/PTDFs) must not exceed emergency limits. A tool that passes A-7 but fails A-9 can analyze contingencies but cannot formulate the market clearing problem. On SMALL and MEDIUM, iterative contingency screening is permitted: the tool may solve with a subset of contingencies, check for violations, add violated contingencies, and re-solve. This reflects actual ISO practice where only binding/near-binding contingencies are active in any given iteration.

**Note on A-10:** There is no single standard for loss approximation in DC OPF. Common approaches include iterative marginal loss factors (CAISO's method), piecewise-linear branch loss approximation, and quadratic loss terms in the objective. The test accepts any method. The key evaluation points are: (a) can the tool include losses at all in its DC OPF formulation, (b) are the resulting LMPs decomposable into energy, congestion, and loss components, and (c) do the loss components have physically correct sign and magnitude (buses far from generation should show positive marginal losses). Reference validation uses MATPOWER's `rundcopf` with loss option enabled on the same case file.

**Note on A-11:** All ISOs use a distributed slack (distributed reference bus) in their market clearing engines. CAISO uses a load-proportional distributed slack for DAM (weighted by cleared load) and a forecast-weighted distributed slack for RTM. Other ISOs use generation-proportional or custom-weighted distributions. A tool that only supports single-slack DC OPF will produce LMPs where the energy component is defined at a single arbitrary bus, making the congestion and loss decomposition non-comparable to ISO-published values. The test verifies that the tool can formulate the distributed slack and that LMP decomposition responds correctly. On TINY, compare distributed-slack LMPs against single-slack LMPs from A-3 — they should differ, and the differences should be physically explainable (buses near the old single slack see the largest changes).

**Note on generator cost curves (A-3, A-5, A-6):** Real ISO markets clear using piecewise-linear bid curves, and any tool deployed operationally would need to support them. However, we do not have actual bid curves for the ISO of interest, so all cost data used in this evaluation is estimated. We have made a deliberate choice to use linear (single-segment) cost curves throughout Phase 1 testing. This keeps the computational burden lower — which is appropriate for an evaluation focused on tool capability comparison rather than production fidelity — and avoids conflating cost-curve complexity with other scalability findings. That said, each tool's support for piecewise-linear cost curves must be documented as a finding under Expressiveness (Criterion 1), even though the Phase 1 tests do not exercise it. A tool that supports only linear cost curves would face a significant limitation in any operational deployment.

---

### Test Suite B: Extensibility

Each test maps to a sub-question in Rubric Criterion 2. **All tests are first run on TINY for functional verification, then on the indicated scale network for grade assessment.**

| ID | Sub-question | Test | Functional (TINY) | Grade Network | Pass Condition |
|----|-------------|------|-------------------|---------------|---------------|
| B-1 | Custom constraints | Add a flow gate limit (sum of flows on a specified set of lines ≤ threshold) to the DC OPF formulation from A-3 | yes | MEDIUM | Achievable through a documented API or extension mechanism. No source patching or forking required. |
| B-2 | Network graph access | From a chosen bus, run BFS to depth 3. Return all buses and branches within that subgraph. | yes | MEDIUM | Works via native graph primitives or clean, documented export to NetworkX (Python) or Graphs.jl (Julia). |
| B-3 | Contingency loop | Solve N-1 DCPF contingencies. Collect max line loading across all cases. | yes | MEDIUM | Runs in a loop without re-parsing or re-instantiating the base model from file each iteration. Base model is modified in-place or cloned efficiently. |
| B-4 | Stochastic scenario wrapping | Generate 50 scenarios by sampling load and renewable generation timeseries from a distribution (e.g., correlated perturbations drawn from a multivariate normal). Solve a 24hr multi-period DCPF for each scenario. Collect results. | yes | SMALL | Tool accepts timeseries inputs programmatically (not from config files only). Scenario loop is expressible without excessive per-scenario overhead. Results are collectable in a structured format. |
| B-5 | Interoperability | Export DCPF results from A-1 to a pandas DataFrame (Python) or DataFrames.jl DataFrame (Julia) and write to CSV. | yes | MEDIUM | Trivial — fewer than 5 lines of code beyond the solve. No custom serialization logic required. |
| B-6 | Code architecture | Qualitative assessment: read the source code for the DCPF solve path. Trace from API call to solver invocation. | N/A | N/A | Document: number of abstraction layers, whether network model / problem formulation / solver interface / results are separated, whether internal interfaces are documented. |
| B-7 | AC feasibility as extension | If AC feasibility check (A-4) required a workaround, document and classify the workaround here. | yes | MEDIUM | Workaround durability assessed. Effort level documented. |
| B-8 | Reference bus configuration | Solve DC OPF on TINY with three different slack configurations: (a) default single slack, (b) a different single slack bus, (c) custom-weighted distributed slack. Compare LMPs across all three. | yes | SMALL | Reference bus / slack formulation is configurable via API without model reconstruction. LMP values change consistently across configurations. Evaluator documents the API calls required and workaround durability. |
| B-9 | PTDF matrix extraction | Compute the PTDF matrix for TINY (39-bus). Verify dimensions (branches x buses). Verify that PTDF-predicted flows match DCPF-solved flows for a given injection pattern. | yes | MEDIUM | PTDF matrix accessible via native API, internal matrix extraction, or unit-injection computation. Flow predictions match DCPF results within numerical tolerance (1e-6). On MEDIUM, document computation time and method. |

**Recording for each B-test:** Pass/fail on TINY, lines of code, API or method used, workaround durability class, total time on grade network (for B-3, B-4, B-8, and B-9).

**Note on TINY for B-3:** On TINY, the contingency loop test uses all 46 branches (full N-1 on the IEEE 39-bus) rather than the 100-branch subset used on MEDIUM. The purpose is functional — does the loop construct work without model re-instantiation? The count is adjusted for MEDIUM to test at realistic volume.

**Note on B-4:** This tests the effort to *wrap* a tool for stochastic analysis when the tool does not natively support it (as tested in A-8). Key factors: Can timeseries be injected via the API, or must config files be rewritten per scenario? Can the model be re-solved with modified timeseries without full reconstruction? Is results collection across scenarios straightforward? The stochastic inputs should use temporally correlated perturbations (not i.i.d. noise per interval) to test whether the tool's timeseries interface supports realistic scenario structures.

---

### Test Suite C: Scalability

Scalability tests reuse the functional tests from Suites A and B but focus on performance measurement at scale. **TINY is not used for Suite C — these tests run on SMALL and MEDIUM only.** No pre-defined pass/fail time thresholds — results are recorded and compared across tools.

| ID | Test | Network | Solver(s) | Record |
|----|------|---------|-----------|--------|
| C-1 | DCPF | MEDIUM | N/A (direct solve) | Wall-clock time, peak memory |
| C-2 | ACPF | MEDIUM | Ipopt | Wall-clock time, peak memory, iterations |
| C-3 | DC OPF | MEDIUM | HiGHS, GLPK | Wall-clock time per solver, peak memory, objective value (verify consistency across solvers) |
| C-4 | SCUC 24hr | SMALL | HiGHS, SCIP | Wall-clock time per solver, MIP gap at termination, peak memory |
| C-5 | N-M contingency sweep (x=5, m=4) | MEDIUM | N/A | Total time, per-contingency-case average, peak memory, number of cases evaluated per order (N-1, N-2, ...), pruning ratio |
| C-6 | 50-scenario stochastic DCPF | SMALL | HiGHS | Total time, per-scenario average, peak memory |
| C-7 | Solver swap | Repeat C-3 with each available open-source solver | MEDIUM | Whether solver swap requires reformulation or just a parameter change. Time per solver. |
| C-8 | SCOPF (N-1, 500 contingencies) | MEDIUM | HiGHS | Wall-clock time, peak memory, number of iterations (if screening), number of binding contingencies |
| C-9 | PTDF matrix computation | MEDIUM | N/A | Wall-clock time, peak memory, matrix density |
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

### Phase 2 Readiness Findings

These findings are informational and do not affect Phase 1 grades. They are collected during Phase 1 evaluation to inform Phase 2 planning effort estimates.

| ID | Finding | Method | Record |
|----|---------|--------|--------|
| P2-1 | PSS/E RAW parsing capability | Attempt to load a PSS/E RAW v30 or v33 test file (if available) or audit documentation/source code for parser existence | Capability (yes/no), supported RAW versions, estimated effort to add if absent |
| P2-2 | Piecewise-linear cost curve support | Documentation audit + brief functional test if supported | Capability (yes/no), formulation type (SOS2, lambda, incremental), any limitations |

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
│   └── supply_chain/
│       └── ...
```

Each test result file (.md) includes:
- **Test ID and description**
- **Network used** (TINY, SMALL, or MEDIUM)
- **Pass / Fail / Qualified Pass**
- **Workaround durability class** (if applicable: Stable / Fragile / Blocking)
- **Wall-clock time and peak memory** (if applicable)
- **Lines of code** (if applicable)
- **Narrative** — what happened, what worked, what didn't, and what it implies for the grade
- **Link to test script** (.py or .jl)

---

## From Test Results to Grades

The rubric defines grading standards (A/B/C) for each criterion. The evaluator assigns grades by mapping test results to those standards as follows:

1. **Gate criterion (Supply Chain, Inspectability & Licensing):** Any disqualifying finding in Suite F → grade C → tool excluded.
2. **Gate test (Data Ingestion):** Failure on G-1 (TINY) → tool excluded from further evaluation. Failure on G-3 (MEDIUM) after passing G-1 → tool proceeds with functional evaluation but scalability grades are capped.
3. **TINY → Scale progression:** A test that fails on TINY is recorded as a failure on the criterion — there is no need to attempt it at scale. A test that passes on TINY but fails at scale is an Expressiveness pass with a Scalability finding.
4. **Per-criterion grades:** The evaluator reviews all test results relevant to that criterion and assigns A/B/C based on the rubric's grading standards. The test results are evidence; the grade is a judgment call informed by that evidence.
5. **Qualified passes and workarounds:** A test that passes only with a Fragile or Blocking workaround pulls the relevant sub-question toward B or C. The evaluator documents which workarounds influenced the grade.
6. **Cross-tool comparison:** After all tools are graded independently, the evaluator reviews grades side-by-side to ensure consistency. If Tool X and Tool Y both received B on Expressiveness but X required significantly more workarounds, the grades should reflect that difference.

---

## Revision History

| Version | Date | Change | Author |
|---------|------|--------|--------|
| v1 | TBD | Initial draft | GRC |
| v2 | TBD | Added TINY tier (IEEE 39-bus) for functional verification. Added synthetic network assurance statement. Restructured test progression: TINY first for all functional tests, scale networks for grade assessment. Added G-1 gate on TINY. | GRC |
| v3 | 2026-03-05 | Added tests A-9 (SCOPF), A-10 (lossy DC OPF / LMP decomposition), A-11 (distributed slack OPF) with notes. Added tests B-8 (reference bus configuration) and B-9 (PTDF matrix extraction). Added scalability tests C-8 (SCOPF), C-9 (PTDF computation), C-10 (distributed slack OPF). Added Phase 2 Readiness Findings section (P2-1, P2-2). Strengthened A-6 pass condition to require demonstrable ramp rate enforcement in ED stage. Updated companion rubric reference to v2. Motivated by CAISO SCED/SCOPF research revealing gaps in Phase 2 readiness assessment. | GRC |
