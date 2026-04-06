# Phase 1 Technology Evaluation White Paper

**Contract FA714626C0006 — SOW Task 1.3**\
**Grid Research Company LLC**\
**April 2026**

---

## Executive Summary

Under Contract FA714626C0006 with the Naval Research Laboratory, Grid Research Company LLC conducted a structured evaluation of open-source power system modeling tools to identify an optimal technology stack for high-voltage transmission system modeling of the California grid. This evaluation constitutes SOW Task 1.3 (Produce White Paper), building on the technology identification (Task 1.1) and down-selection (Task 1.2) activities completed in the preceding months. The objective was to select a tool capable of supporting substation-fidelity modeling, long-term forecasting, and vulnerability identification at defense-relevant locations including Camp Pendleton, Naval Base San Diego, and the Ports of Long Beach and Los Angeles.

Six tools were evaluated: PyPSA, PowerModels.jl, PowerSimulations.jl, pandapower, GridCal, and MATPOWER. Each tool was assessed against six criteria -- Expressiveness, Extensibility, Scalability, Accessibility, Maturity, and Supply Chain -- using standardized test suites executed on ACTIVSg reference networks at three scales: 39-bus, 2,000-bus, and 10,000-bus. All testing used open-source solvers exclusively (HiGHS, SCIP, Ipopt, GLPK) on a reference workstation with 128 GB RAM and 16 cores. Supply Chain served as a gate criterion: any tool receiving a Weak or Failing grade was disqualified, reflecting the program's requirement for fully inspectable, open-source software deployable in restricted environments.

**PyPSA is the recommended tool for Phase 2 development.** It is the only tool to earn a Strong grade in Expressiveness, the highest-priority criterion, demonstrating native support for security-constrained optimal power flow, PTDF/LODF matrix computation, unit commitment, economic dispatch, and contingency analysis without requiring user-assembled solver code. PyPSA also earned Strong grades in four of the remaining five criteria (Extensibility, Accessibility, Maturity, and Supply Chain), with Adequate in Scalability. Its pure-Python architecture, built on the pandas/numpy/scipy stack, eliminates language-adoption barriers and integrates directly with existing data pipeline and visualization tooling.

PowerModels.jl ranks as the runner-up on the strength of its Strong Extensibility and its JuMP optimization framework, which provides the most flexible constraint-injection API among all evaluated tools. It was not selected because six of eleven expressiveness tests required user-assembled code averaging 269 lines per test, its contributor base exhibits a bus factor of one (82.4% of commits from a single author), and Julia adoption would impose workforce ramp-up costs. PowerModels.jl remains a viable fallback should PyPSA's known scalability limitations prove unresolvable.

MATPOWER served as a reference benchmark throughout the evaluation, providing validated numerical baselines against which other tools' results were compared. It is excluded from the primary ranking because the customer requires fully inspectable source code, which precludes MATLAB's compiled runtime environment.

The evaluation identified five risks for Phase 2 development, two rated HIGH severity: PyPSA's Linopy model-building overhead at production scale (302 seconds of model construction versus 6 seconds of solver time on a 10,000-bus DC OPF) and the absence of a native PSS/E RAW file parser, requiring construction of a custom format converter. Mitigation strategies for all identified risks are detailed in the risk register.

## Introduction

The Naval Research Laboratory requires a transparent, scalable, and government-controlled grid modeling capability to assess vulnerabilities and pressure points on the California high-voltage transmission system. Proprietary tools that dominate current practice are costly, difficult to extend, and impossible to fully inspect -- constraints that are incompatible with deployment in restricted environments and with the program's goal of building a persistent, reproducible analytical capability under government ownership.

This white paper reports the results of a structured technology evaluation conducted under SOW Task 1, designed to identify the optimal open-source tool for Phase 2 model development. The evaluation examined six candidate tools spanning three programming ecosystems: PyPSA, pandapower, and GridCal (Python); PowerModels.jl and PowerSimulations.jl (Julia); and MATPOWER (MATLAB/Octave). Each tool was assessed against six evaluation criteria derived from the program's operational requirements: Expressiveness, Extensibility, Scalability, Accessibility, Maturity, and Supply Chain. Supply Chain functions as a gate criterion -- tools that cannot be deployed with fully inspectable, open-source components in air-gapped environments are disqualified regardless of technical merit.

Testing comprised 39 standardized sub-questions organized across the six criteria, executed on ACTIVSg synthetic reference networks at 39-bus, 2,000-bus, and 10,000-bus scales. All evaluations used open-source solvers exclusively and were conducted within a reproducible devcontainer environment, ensuring that every result can be independently verified on commodity hardware. Grades follow a four-tier scale (Strong, Adequate, Weak, Failing) with explicit boundary definitions for each criterion.

The remainder of this document is organized as follows. Section 3 defines the evaluation methodology, including criteria definitions, grading scale, test networks, and the reproducible execution environment. Sections 4 through 9 present detailed findings for each criterion. Section 10 presents the head-to-head ranking and sensitivity analysis. Section 11 provides the risk register and recommended mitigations. Section 12 outlines the Phase 2 development scope.

## Evaluation Methodology

### Criteria and Weighting

Each tool was assessed against six criteria organized into a gate criterion and five weighted dimensions. The gate criterion, **Supply Chain**, evaluates licensing, dependency inspectability, and air-gapped deployment feasibility. A grade of Weak or Failing on Supply Chain is disqualifying regardless of performance on all other criteria. This reflects a non-negotiable program requirement: the evaluation cannot recommend a tool for restricted-environment deployment if any component in the execution stack is opaque, uninspectable, or legally encumbered.

The five remaining criteria are evaluated in strict lexicographic priority order, meaning that when two tools receive comparable grades, the higher-priority criterion breaks the tie:

1. **Expressiveness** measures the breadth and depth of power system analyses the tool can formulate natively, from DC and AC power flow through optimal power flow, security-constrained unit commitment, economic dispatch, contingency analysis, and stochastic optimization. A tool that requires analysts to rebuild core problem formulations from scratch scores poorly regardless of its other qualities.

2. **Extensibility** measures how readily analysts can go beyond built-in problem types: injecting custom constraints, traversing the network graph programmatically, constructing contingency sweep pipelines, and exporting results to external tools. Clean extension APIs and accessible internal architecture are valued over raw capability.

3. **Scalability** measures whether the tool performs at production-relevant scale, defined as 10,000 or more buses with realistic contingency counts and operational time horizons, on the reference workstation using open-source solvers.

4. **Accessibility** measures the learning curve, API design quality, documentation accuracy, and error transparency. A tool that requires weeks of trial and error to produce a first meaningful result imposes costs that compound throughout a program of record.

5. **Maturity** measures long-term sustainability: release engineering discipline, test coverage, contributor concentration (bus factor), institutional funding stability, and operational adoption beyond academia.

This lexicographic ordering means that a tool with superior Expressiveness is preferred over one with superior Scalability, all else being equal, because the ability to formulate the required analyses is a prerequisite for any downstream performance consideration.

### Grading Scale

Each criterion is assessed on a four-tier scale. **Strong** indicates the tool meets or exceeds requirements and is ready for Phase 2 deployment as-is or with minor configuration. **Adequate** indicates the tool meets core requirements with caveats; it is usable for Phase 2 with known workarounds or moderate additional effort. **Weak** indicates significant gaps that would require major remediation or custom development for Phase 2 viability. **Failing** indicates blocking architectural limitations with no feasible path forward. For the gate criterion, both Weak and Failing are disqualifying.

Test outcomes from the evaluation protocol map to grade evidence through five categories: pass (full credit), qualified pass (stable workaround demonstrated), partial pass (fragile or non-trivial workaround), constrained pass (capability demonstrated under limiting conditions), and fail. The distinction between workaround durability classes -- stable, fragile, and blocking -- is critical: a stable workaround produces full capability and is unlikely to break across releases, while a blocking workaround indicates a gap with no viable path to resolution without upstream changes.

### Test Networks

All tools were tested against three standardized networks of increasing complexity, distributed in the MATPOWER case file format:

- **IEEE 39-bus (New England)**: A 39-bus test case used for functional verification. The base topology from the standard MATPOWER case file was augmented with differentiated generator costs, renewable resources, battery storage, demand response, 24-hour load profiles, and stochastic scenarios to exercise the full range of evaluation sub-questions.

- **ACTIVSg 2,000-bus**: An intermediate-scale synthetic grid used to verify that functional results hold beyond toy-problem size.

- **ACTIVSg 10,000-bus**: The primary scalability benchmark. All scalability tier assignments were assessed against this network. The network was preprocessed to fix zero-impedance branches, set unconstrained thermal ratings, and tighten select branch limits to induce congestion for tests requiring binding constraints and non-uniform locational marginal prices.

The progression from 39 buses to 10,000 buses ensures that tools are tested at a scale representative of real regional transmission networks, not just textbook examples. All scalability measurements were taken on a reference workstation with 128 GB RAM and 16 cores, using no GPU acceleration.

### Tools Evaluated

Six open-source tools were evaluated against the full rubric. Five are ranked competitively; the sixth, MATPOWER, serves as a reference benchmark.

**PyPSA** (Python) is a DataFrame-native power system modeling framework maintained by TU Berlin and Open Energy Transition, with native support for DC and AC power flow, optimal power flow, unit commitment, and multi-period storage optimization via the Linopy algebraic modeling layer.

**PowerModels.jl** (Julia) is a JuMP-based power network optimization framework from Los Alamos National Laboratory, featuring a clean four-layer dispatch architecture that enables custom constraint injection with minimal code overhead.

**PowerSimulations.jl** (Julia) is an NREL/DOE simulation-oriented optimization framework built on JuMP, distinguished by its built-in unit commitment formulations and five-layer package architecture spanning data modeling through simulation orchestration.

**GridCal** (Python) is a power system simulation tool with native LODF-based security-constrained optimal power flow and parameter-driven solver selection via PuLP, maintained by an individual developer.

**pandapower** (Python) is a mature power flow tool with a DataFrame-centric data model and an embedded PYPOWER solver, maintained jointly by the University of Kassel and Fraunhofer IEE, with confirmed production deployments at European system operators.

**MATPOWER** (MATLAB/GNU Octave) is the canonical open-source power system analysis toolbox with over 25 years of development history. It was excluded from the competitive ranking because the customer requires fully inspectable source code, which precludes the compiled MATLAB runtime. All MATPOWER testing used GNU Octave, and its grades are retained as a calibration baseline.

### Reproducibility

All evaluation results are independently reproducible through a containerized execution environment. The project provides a devcontainer specification built on Ubuntu 24.04 with Python 3.12, Julia 1.10, and GNU Octave pre-installed. Each tool's dependencies are pinned via lockfiles (uv.lock for Python tools, Manifest.toml for Julia tools) and installed during the container build, ensuring identical dependency resolution across machines. All solvers used in the evaluation -- HiGHS, SCIP, Ipopt, and GLPK -- are open-source and bundled within the container image.

This approach ensures that any reviewer can rebuild the container, execute the test protocol against the same standardized networks, and obtain the same results without configuring local toolchains or resolving dependency conflicts. The containerized environment also validates a key operational requirement: that the selected tool can be packaged for deployment in air-gapped networks where internet-dependent installation workflows are unavailable.

## Results by Evaluation Criterion

### Expressiveness

Expressiveness measures the breadth of power system analyses a tool can perform natively or with minimal extension, spanning twelve test protocols (A-1 through A-12) that cover DC and AC power flow, optimal power flow with LMP extraction, security-constrained unit commitment, economic dispatch, contingency analysis, SCOPF, lossy DC OPF, distributed slack, and multi-period storage optimization.

| Tool | Grade |
|------|-------|
| **PyPSA** | Strong |
| PowerModels.jl | Adequate |
| PowerSimulations.jl | Adequate |
| GridCal | Adequate |
| pandapower | Weak |
| MATPOWER | Adequate |

PyPSA earned the sole Strong tier by passing 8 of 11 tests natively, including SCOPF via BODF-based N-1 contingency constraints (A-9), lossy DC OPF with piecewise-linear loss approximation (A-10), and multi-period storage OPF with cyclic state-of-charge constraints (A-12). Its only blocking gap -- distributed slack OPF (A-11) -- is shared by every evaluated tool. The four Adequate-tier tools each present distinct capability profiles. PowerModels excels at OPF formulation rigor, delivering three-component LMP decomposition (energy, congestion, loss) via its `DCPLLPowerModel` (A-10), but lacks unit commitment entirely. PowerSimulations is the only tool with native SCUC formulations (A-5), yet it is blocked on lossy OPF by a solver-formulation mismatch where `DCPLLPowerModel` uses quadratic constraints unsupported by HiGHS, GLPK, and SCIP (A-10). GridCal covers a broad spectrum including native LODF-based SCOPF (A-9) but is undermined by two blocking formulation bugs: a battery energy balance sign error that causes energy to increase during discharge (A-12) and distributed slack being hardcoded off at the source level (A-11). pandapower falls to Weak due to four independent architectural blocking failures in SCUC (A-5), lossy OPF (A-10), distributed slack (A-11), and multi-period storage (A-12), reflecting a design scope that does not extend beyond single-period steady-state analysis.

### Extensibility

Extensibility measures the ability to inject custom constraints, swap solvers, access graph topology, extract PTDF matrices, and integrate with external workflows -- capabilities essential for adapting a tool to novel modeling requirements without patching source code.

| Tool | Grade |
|------|-------|
| **PyPSA** | Strong |
| PowerModels.jl | Strong |
| PowerSimulations.jl | Strong |
| MATPOWER | Strong |
| pandapower | Adequate |
| GridCal | Adequate |

The key discriminator across all tools is the custom constraint injection API (B-1). Three candidate tools earned Strong by providing documented public extension mechanisms: PyPSA's `extra_functionality` callback requires only 2 lines of code for a flow gate constraint with dual extraction; PowerModels' two-level `instantiate_model`/`optimize_model!` API achieves the same in 4 lines; and PowerSimulations exposes the full JuMP model via `get_jump_model()` for arbitrary constraint addition. All three Strong-tier tools also achieved machine-precision PTDF accuracy at 10,000 buses (B-9), with maximum flow prediction errors below 2e-11 p.u. pandapower and GridCal both earned Adequate, sharing the same critical gap: no public API for custom OPF constraint injection. In pandapower, the embedded PYPOWER solver is a closed system requiring monkey-patching of `_optimal_powerflow` (B-1). In GridCal, the monolithic OPF formulation -- a single 3,146-line procedural function -- provides no extension points (B-6). Both tools compensate with excellent graph access via NetworkX (B-2) and efficient contingency sweep infrastructure (B-3), with pandapower processing 3,276 cases at 6.4 milliseconds each and GridCal offering branch toggle via a simple `active` flag.

### Scalability

Scalability measures performance degradation as network size increases from 39 buses through 2,000 buses to 10,000 buses, isolating tool overhead from solver performance by using the same solver (HiGHS) where possible.

| Tool | Grade |
|------|-------|
| **PyPSA** | Adequate |
| PowerModels.jl | Adequate |
| PowerSimulations.jl | Adequate |
| GridCal | Adequate |
| pandapower | Weak |
| MATPOWER | Weak |

No tool achieved a Strong scalability tier -- a notable finding given that all other criteria produced at least one Strong result. The four Adequate-tier tools exhibit distinct bottleneck profiles. GridCal achieved the best combined DC OPF and SCOPF timing at 10,000 buses (8.9 seconds and 32.1 seconds respectively for 50 contingencies, C-3/C-8). PowerModels delivered the fastest raw DC OPF solve at 4.0 seconds (C-3) but failed ACPF at 10,000 buses when both Ipopt and NLsolve diverged with MUMPS memory exhaustion (C-2). PowerSimulations was the only tool where SCUC passed at 2,000-bus scale (404 seconds via HiGHS, C-4), confirming its native unit commitment advantage. PyPSA's primary bottleneck is Linopy model construction: on the 10,000-bus DC OPF, the framework spent 302 seconds building the model versus only 6.2 seconds for the HiGHS solve (C-3), making model-building optimization the highest-impact target for Phase 2. pandapower earned Weak despite having the fastest power flow at 10,000 buses (DCPF in 1.0 seconds, C-1) because its PYPOWER solver is hardcoded with no swap mechanism (C-7 fail) and SCOPF exhausted 32 GB of memory (C-8 fail). MATPOWER's Weak tier reflects a cascading failure: a GLPK exit flag integration bug blocked SCUC result extraction at 2,000-bus scale (C-4), triggering the suite gate and causing all nine 10,000-bus tests to be skipped.

### Accessibility

Accessibility measures onboarding friction: install-to-first-solve time, documentation quality, example integrity, error diagnostic transparency, and code volume required for standard tasks.

| Tool | Grade |
|------|-------|
| **PyPSA** | Strong |
| pandapower | Adequate |
| MATPOWER | Adequate |
| PowerModels.jl | Adequate |
| GridCal | Weak |
| PowerSimulations.jl | Weak |

PyPSA earned Strong with a 6.4-second install-to-first-solve time (D-1), 5 of 10 Suite A tests implementable from documentation alone (D-2), all built-in examples loading and solving without modification (D-3), and meaningful diagnostics for all three deliberate error scenarios (D-4). The three Adequate-tier tools each present specific friction points: pandapower's OPF returns only a boolean `converged` flag with no infeasibility information (D-4) and its `**kwargs` passthrough silently absorbs invalid parameters; PowerModels imposes a 5-15 minute JIT compilation barrier on first use (D-1) with only 1 of 12 tests fully documented (D-2); MATPOWER's interactive installer blocks in CI environments and its MOST scheduling extension requires reading source code (D-2). GridCal and PowerSimulations both received Weak. GridCal's most concerning finding is that infeasible OPF problems report `converged=True` (D-4), creating a dangerous silent-failure trap compounded by rebrand naming confusion (PyPI package `veragridengine`, import `VeraGridEngine`, documentation references `GridCal`). PowerSimulations requires knowledge of four interacting packages, zero of ten official examples run without modification (D-3), and median code volume is approximately 332 lines per test -- roughly six times the PyPSA equivalent (D-5).

### Maturity

Maturity evaluates long-term viability through two sub-dimensions: demonstrated maturity (release cadence, contributor activity, issue responsiveness, CI practices, operational adoption) and sustainability risk (contributor concentration, funding stability, governance).

| Tool | Grade |
|------|-------|
| **PyPSA** | Strong |
| pandapower | Strong |
| PowerModels.jl | Adequate |
| PowerSimulations.jl | Adequate |
| MATPOWER | Adequate |
| GridCal | Weak |

PyPSA and pandapower both earned Strong through the combination of active multi-contributor development, diversified institutional funding, and confirmed operational adoption. PyPSA shows 321 commits from 22 contributors in the trailing twelve months, a bus factor of 2-3 with a successful founder-to-maintainer transition (E-3), and five independent funding channels including TU Berlin and venture backing (E-4). pandapower reports 842 commits from 45 contributors, a bus factor of 3, and dual institutional anchoring at the University of Kassel and Fraunhofer IEE (E-3, E-4). The most pervasive risk pattern is contributor concentration: five of six tools have a bus factor of 1. PowerModels' primary author holds 82.9% of lifetime commits and has had zero direct commits in the trailing twelve months (E-3), though DOE/LANL institutional backing and 94% test coverage provide partial mitigation. GridCal earned Weak due to the convergence of three risk factors: bus factor of 1, zero code review across all sampled merged PRs, and a CI pipeline that never executes the test suite (E-6).

### Supply Chain

Supply chain risk assessment evaluates licensing, dependency tree transparency, code inspectability, distribution integrity, air-gap installability, and solver dependency -- serving as the gate criterion where a Weak or Failing grade is disqualifying.

| Tool | Grade |
|------|-------|
| **PyPSA** | Strong |
| pandapower | Strong |
| GridCal | Strong |
| MATPOWER | Strong |
| PowerModels.jl | Adequate |
| PowerSimulations.jl | Adequate |

All six tools passed the gate threshold, making supply chain the least differentiating criterion. The Python tools and MATPOWER earned Strong through permissive or file-level-copyleft licensing, fully inspectable source code, and straightforward air-gap installation. PyPSA's MIT license and 17-direct-dependency tree represent the cleanest Python profile, with one replaceable GPL-2.0 dependency (Levenshtein, substitutable with the MIT-licensed `rapidfuzz`). pandapower is the only evaluated tool with Sigstore provenance attestations and Trusted Publishing via GitHub Actions, representing a best-in-class distribution integrity practice. The Julia tools earned Adequate primarily due to larger dependency trees -- 114 packages for PowerModels and 184 for PowerSimulations -- and the presence of optional GPL-licensed GLPK solver wrappers requiring explicit exclusion. A cross-cutting finding applies to all tools: the optional GPL-3.0-licensed GLPK solver bindings appear in every tool's ecosystem, and any Phase 2 deployment configuration should explicitly exclude GLPK in favor of HiGHS (MIT) or Ipopt (EPL 2.0).

## Head-to-Head Comparison and Ranking

### Final Ranking

The evaluation compared five candidate tools across six rubric dimensions using a lexicographic forced-ranking methodology where higher-priority criteria break ties before lower-priority criteria are considered. MATPOWER served as a reference benchmark but was excluded from the primary ranking because the customer requires inspectable source code, a condition that MATLAB's compiled runtime does not satisfy.

The final ranking is as follows:

1. **PyPSA** -- the only tool graded Strong in Expressiveness, the highest-priority criterion. PyPSA also earned Strong in Extensibility, Accessibility, Maturity, and Supply Chain, with Adequate in Scalability. It demonstrated native security-constrained OPF, native unit commitment and economic dispatch, and native custom constraint injection through its `extra_functionality` callback.

2. **PowerModels.jl** -- Strong Extensibility through the JuMP two-level API, Adequate in all other criteria. PowerModels provides the most flexible constraint injection interface among all evaluated tools and demonstrated native piecewise-linear cost curves with sub-1e-11 numerical error at 10,000 buses. However, it lacks unit commitment entirely and required an average of 269 lines of user-assembled code per expressiveness test.

3. **PowerSimulations.jl** -- Strong Extensibility and the cleanest unit commitment formulation hierarchy among all tools. Weak Accessibility (Julia adoption barrier) separates it from PowerModels in the ranking.

4. **GridCal** -- Adequate across most criteria but only Weak in Maturity (82% single-contributor commit share). Native SCOPF and UC are present but hampered by bugs at scale.

5. **pandapower** -- Strong Maturity and Supply Chain, but Weak Expressiveness and Weak Scalability place it last among candidates.

### Sensitivity Analysis

Three alternative weighting scenarios were tested: Scalability First, Extensibility First, and Maturity-Accessibility Swapped. PyPSA holds the top position in all three scenarios. The ranking is entirely stable because PyPSA is the only tool with Strong Expressiveness, which dominates regardless of criterion priority ordering. The tier gaps between adjacent-ranked tools are wide enough that no single priority reordering changes relative positions. This stability provides high confidence that the recommendation is not an artifact of the chosen weighting scheme.

### PyPSA vs. PowerModels.jl

The comparison between the top two tools centers on a fundamental architectural trade-off. PyPSA provides a high-level Python API that covers most standard power system analyses natively, at the cost of a Linopy model-building layer that introduces 302 seconds of overhead on a 10,000-bus DC OPF (versus 6 seconds of solver time). PowerModels.jl exposes the JuMP optimization layer directly, offering maximum flexibility and minimal overhead, but requires users to assemble solver code for each non-standard analysis type. For Phase 2, where the critical-path capabilities are SCOPF, custom constraint injection, and the UC/ED pipeline, PyPSA covers all three natively while PowerModels covers only one (custom constraints). PowerModels should be reconsidered if PyPSA's model-building overhead proves unresolvable at production scale.

## Risk Register

Five risks have been identified that bear directly on the Phase 2 tool selection decision. All risks are specific to PyPSA, the recommended tool, and represent known gaps or limitations that must be managed during Phase 2 development.

**R1: Linopy model-building overhead at production scale (HIGH severity).** PyPSA's Linopy abstraction layer takes 302 seconds to construct the optimization model for a 10,000-bus DC OPF, compared to 6 seconds of actual solver time. At production scale with repeated solves across contingency scenarios, this overhead may dominate wall-clock time. Mitigation: profile Linopy model construction early in Phase 2. If overhead is prohibitive, evaluate a direct solver interface (HiGHS C API) for the inner optimization loop, retaining PyPSA for network data management and result post-processing.

**R2: No native PSS/E RAW file parser (HIGH severity).** PyPSA has no PSS/E import capability of any kind. Phase 2 requires ingesting the full network model, which is distributed in PSS/E RAW format. Mitigation: build a PSS/E RAW-to-PyPSA converter during Phase 2, leveraging the CSV-based FNM intermediate format already developed during Phase 1 testing. Alternatively, use MATPOWER's `psse2mpc()` as a preprocessing step and ingest via PyPSA's existing MATPOWER .m importer.

**R3: Distributed slack OPF unavailable in optimization context (MEDIUM severity).** PyPSA supports distributed slack in power flow but not in OPF formulations. LMP decomposition without distributed slack produces systematically biased congestion pricing that diverges from published ISO data. Mitigation: implement distributed slack as a custom Linopy constraint via the `extra_functionality` callback using a PTDF formulation with load-proportional weights.

**R4: Single-threaded HiGHS solver limits parallelism (MEDIUM severity).** HiGHS simplex does not parallelize internally; testing showed 0.92x speedup with 32 threads on a 10,000-bus SCOPF problem. Mitigation: use process-level parallelism for independent contingency sub-problems rather than relying on solver-internal threading.

**R5: Piecewise-linear cost curves require tranche workaround (LOW severity).** PyPSA lacks native SOS2 support for piecewise-linear cost curves. Mitigation: Phase 2 will use linearized cost curves, rendering this gap irrelevant to the planned workflow.

None of these risks are judged to be disqualifying. The two HIGH-severity items (R1, R2) have concrete mitigation paths with known effort bounds and fallback strategies.

## Phase 2 Outlook

### Three-Stage Approach

Phase 2 follows a three-stage progression from historical calibration through real-time estimation to forward-looking forecasting.

**Stage 1 -- Historical Calibration.** Assemble the full network model and supporting data to establish grid topology, including available generators, third-party vendor data, flow data from sensors, and constraint setup and binding information from the ISO. The goal is to calibrate a state estimate -- effectively rebuilding state estimation from observable data since the ISO does not publish its internal SE results -- and to calibrate distribution factors and learn stochastic scenarios for generation outages and renewable variability. The success criterion is constraints firing as published per ISO market results.

**Stage 2 -- Real-Time Estimation.** Using real-time sensor data, aggregated load and generation figures, and published shadow prices for constraints, produce a real-time state estimation for the entire grid. Shadow prices combined with constraint setup information indicate whether a line is binding, providing at minimum a floor on flow levels. This stage bridges the gap between historical calibration and forward-looking analysis.

**Stage 3 -- Forecasting.** Apply the learned parameters from Stages 1 and 2 (distribution factors, stochastic scenarios for generation outages and renewables) to produce a range of possible power flow and congestion outcomes over a 2-to-3-day horizon. At this stage no prices are available; inputs are limited to load forecasts, renewable forecasts, and known generation and topology.

### The State Estimation Gap

A cross-cutting investigation found that none of the six evaluated tools provide production-ready state estimation for transmission-scale grids. Two tools (pandapower and GridCal) have native SE implementations, but both have critical limitations: pandapower's SE exhibits convergence failures above approximately 89 buses, and GridCal's bad data detection code is entirely commented out. Phase 2 will therefore require building a custom SE capability, likely drawing on external open-source frameworks as a foundation rather than relying on any of the six evaluated tools.

### Recommended Next Steps

Phase 2 development should begin with the two HIGH-severity risk mitigations: profiling Linopy model-building overhead on the target network scale (R1) and building the PSS/E RAW ingestion pipeline (R2). These are on the critical path and will provide early signal on whether PyPSA's architecture can sustain the production workflow or whether the PowerModels.jl fallback must be activated. ETL pipelines for all data sources across all three stages should be developed in parallel. The ultimate deliverable is a forward-looking vulnerability assessment tool capable of producing congestion forecasts at bus-level granularity over a multi-day horizon.

---

*This white paper was produced under Contract FA714626C0006, SOW Task 1.3. The interactive report site with full test evidence is available at the repository's GitHub Pages deployment.*
