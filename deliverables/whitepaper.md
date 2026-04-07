# Phase 1 Technology Evaluation White Paper

**Contract FA714626C0006 — SOW Task 1.3**\
**Grid Research Company LLC**\
**April 2026**

> Full test evidence, per-criterion drill-downs, and interactive visualizations are
> available in the [companion report site](https://zgenergy.github.io/grc-tech-evaluation/).
> All evaluation code and raw results are in the accompanying repository under `evaluations/`.

---

## Executive Summary

Under Contract FA714626C0006 with the Naval Research Laboratory, Grid Research Company LLC conducted a structured evaluation of open-source power system modeling tools to identify an optimal technology stack for high-voltage transmission system modeling. The objective was to select a tool capable of supporting substation-fidelity modeling, long-term forecasting, and vulnerability identification at defense-relevant locations including Camp Pendleton, Naval Base San Diego, and the Ports of Long Beach and Los Angeles.

Six tools were evaluated: PyPSA, PowerModels.jl, PowerSimulations.jl, pandapower, GridCal, and MATPOWER. Each tool was assessed against six criteria -- Expressiveness, Extensibility, Scalability, Accessibility, Maturity, and Supply Chain -- using standardized test suites executed on ACTIVSg reference networks at three scales: 39-bus, 2,000-bus, and 10,000-bus. All testing used open-source solvers exclusively (HiGHS, SCIP, Ipopt, GLPK) on a reference workstation with 128 GB RAM and 16 cores. Supply Chain served as a gate criterion: any tool receiving a Weak or Failing grade was disqualified, reflecting the program's requirement for fully inspectable, open-source software deployable in restricted environments.

**PyPSA is the recommended tool for Phase 2 development.** It is the only tool to earn a Strong grade in Expressiveness, the highest-priority criterion, demonstrating native support for security-constrained optimal power flow, PTDF/LODF matrix computation, unit commitment, economic dispatch, and contingency analysis without requiring user-assembled solver code. PyPSA also earned Strong grades in four of the remaining five criteria (Extensibility, Accessibility, Maturity, and Supply Chain), with Adequate in Scalability. Its pure-Python architecture, built on the pandas/numpy/scipy stack, eliminates language-adoption barriers and integrates directly with existing data pipeline and visualization tooling.

PowerModels.jl ranks as the runner-up on the strength of its Strong Extensibility and its JuMP optimization framework, which provides the most flexible constraint-injection API among all evaluated tools. It was not selected because half of its expressiveness tests required user-assembled JuMP code averaging 487 lines per test, its contributor base exhibits a bus factor of one (82.4% of commits from a single author), and Julia adoption would impose workforce ramp-up costs. PowerModels.jl remains a viable fallback should PyPSA's known scalability limitations prove unresolvable.

MATPOWER served as a reference benchmark throughout the evaluation, providing validated numerical baselines against which other tools' results were compared. It is excluded from the primary ranking because the customer requires fully inspectable source code, which precludes MATLAB's compiled runtime environment.

The evaluation identified five risks for Phase 2 development, two rated HIGH severity: PyPSA's Linopy model-building overhead at production scale (302 seconds of model construction versus 6 seconds of solver time on a 10,000-bus DC OPF) and the absence of a native PSS/E RAW file parser, requiring construction of a custom format converter. Mitigation strategies for all identified risks are detailed in the risk register.

## Evaluation Methodology

Each tool was assessed against a gate criterion and five weighted dimensions, evaluated in strict lexicographic priority order. **Supply Chain** serves as the gate: a Weak or Failing grade disqualifies a tool regardless of technical merit, reflecting the non-negotiable requirement for inspectable, open-source components deployable in air-gapped environments. The five remaining criteria are ordered by priority: **Expressiveness** (breadth of native power system analyses) > **Extensibility** (ability to inject custom constraints and extend beyond built-in formulations) > **Scalability** (performance at 10,000+ buses with realistic contingency counts) > **Accessibility** (onboarding friction, documentation quality, error transparency) > **Maturity** (contributor health, institutional funding, operational adoption).

This lexicographic ordering means that a tool with superior Expressiveness is preferred over one with superior Scalability, all else being equal, because the ability to formulate the required analyses is a prerequisite for any downstream performance consideration. Grades use a four-tier scale: **Strong** (ready for Phase 2 as-is), **Adequate** (usable with known workarounds), **Weak** (major gaps requiring significant remediation), and **Failing** (blocking limitations). The full rubric with tier boundary definitions and the complete test protocol are in the repository under `evaluation_guides/`.

Testing used three ACTIVSg synthetic reference networks: IEEE 39-bus (New England) for functional verification, ACTIVSg 2,000-bus for intermediate-scale validation, and ACTIVSg 10,000-bus as the primary scalability benchmark. The 39-bus case was augmented with differentiated generator costs, renewable resources, battery storage, demand response, 24-hour load profiles, and stochastic scenarios to exercise the full range of evaluation sub-questions. The 10,000-bus case was preprocessed to fix zero-impedance branches, set unconstrained thermal ratings, and tighten select branch limits to induce congestion for tests requiring binding constraints and non-uniform locational marginal prices. The progression from 39 to 10,000 buses ensures that tools are tested at a scale representative of real regional transmission networks, not just textbook examples.

Six open-source tools spanning three programming ecosystems were evaluated. The Python tools -- PyPSA (TU Berlin / Open Energy Transition), pandapower (University of Kassel / Fraunhofer IEE), and GridCal (individual developer) -- offer DataFrame-native data models and integration with the scientific Python stack. The Julia tools -- PowerModels.jl (Los Alamos National Laboratory) and PowerSimulations.jl (NREL/DOE) -- are built on the JuMP algebraic modeling layer, providing direct access to the optimization problem structure. MATPOWER (GNU Octave) is the canonical academic power system toolbox with over 25 years of development history; it was excluded from the competitive ranking because MATLAB's compiled runtime does not satisfy the inspectable-source-code requirement, but its results are retained as a calibration baseline.

All evaluations ran within a reproducible devcontainer environment (Ubuntu 24.04, Python 3.12, Julia 1.10, GNU Octave) with dependencies pinned via lockfiles and all solvers (HiGHS, SCIP, Ipopt, GLPK) bundled in the container image. Any reviewer can rebuild the container and independently verify every result without configuring local toolchains. This also validates a key operational requirement: the selected tool can be packaged for deployment in air-gapped networks where internet-dependent installation workflows are unavailable.

## Results

| Tool | Expressiveness | Extensibility | Scalability | Accessibility | Maturity | Supply Chain |
|------|:-:|:-:|:-:|:-:|:-:|:-:|
| **PyPSA** | Strong | Strong | Adequate | Strong | Strong | Strong |
| PowerModels.jl | Adequate | Strong | Adequate | Adequate | Adequate | Adequate |
| PowerSimulations.jl | Adequate | Strong | Adequate | Weak | Adequate | Adequate |
| GridCal | Adequate | Adequate | Adequate | Weak | Weak | Strong |
| pandapower | Weak | Adequate | Weak | Adequate | Strong | Strong |
| MATPOWER\* | Adequate | Strong | Weak | Adequate | Adequate | Strong |

\*Reference benchmark; excluded from ranking (requires MATLAB runtime).

**Expressiveness.** PyPSA earned the sole Strong by passing 8 of 10 tests natively, including SCOPF via BODF-based N-1 contingency constraints (A-9), lossy DC OPF with piecewise-linear loss approximation (A-10), and multi-period storage OPF with cyclic state-of-charge constraints (A-12). Its only blocking gap -- distributed slack OPF (A-11) -- is shared by five of the six evaluated tools (MATPOWER alone achieved a workaround via post-processing PTDF with slack weights). The four Adequate-tier tools present distinct capability profiles: PowerModels excels at OPF formulation rigor with three-component LMP decomposition but lacks unit commitment entirely; PowerSimulations is the only tool with native SCUC formulations (A-5) but is blocked on lossy OPF by a solver-formulation mismatch; GridCal offers broad coverage including native SCOPF but is undermined by a battery energy-balance sign error (A-12). pandapower falls to Weak with four independent blocking failures reflecting a design scope limited to single-period steady-state analysis.

**Extensibility.** The key discriminator is the custom constraint injection API (B-1). PyPSA, PowerModels, PowerSimulations, and MATPOWER all earned Strong by providing documented extension mechanisms requiring 2-4 lines of code for a flow gate constraint with dual extraction. All four also achieved machine-precision PTDF at 10,000 buses (B-9), with errors below 2e-11 p.u. pandapower and GridCal earned Adequate: neither offers a public constraint-injection API, requiring 200+ lines of fragile workarounds dependent on internal naming conventions. Both compensate with excellent graph access via NetworkX and efficient contingency sweep infrastructure.

**Scalability.** No tool achieved Strong -- a notable finding. PyPSA's bottleneck is model construction overhead: 302 seconds building the Linopy model versus 6.2 seconds for the HiGHS solve at 10,000 buses (C-3). GridCal achieved the best SCOPF timing (32s for 50 contingencies). PowerModels delivered the fastest raw DC OPF solve (4.0s) but failed ACPF at 10,000 buses due to MUMPS memory exhaustion. MATPOWER's Weak reflects a cascading GLPK integration bug that blocked all nine 10,000-bus tests. pandapower's SCOPF exhausted 32 GB of memory.

**Accessibility.** PyPSA earned Strong with 6.4-second install-to-first-solve time, good documentation coverage, and meaningful error diagnostics. The most concerning finding among other tools: GridCal's infeasible OPF problems report `converged=True` (D-4), creating a silent-failure trap. PowerSimulations requires ~332 lines per test -- roughly six times the PyPSA equivalent.

**Maturity.** PyPSA and pandapower both earned Strong with diversified contributors and institutional funding (bus factor 2-3). The dominant risk pattern: four of six tools have a bus factor of 1. PowerModels' sole primary author has had zero direct commits in the trailing twelve months, though DOE/LANL backing provides partial mitigation. GridCal earned Weak (bus factor 1, no code review, CI never executes the test suite).

**Supply Chain.** All six tools passed the gate. Python tools and MATPOWER earned Strong through permissive licensing, fully inspectable source code, and clean dependency trees. Julia tools earned Adequate due to larger dependency graphs (114-184 packages). A cross-cutting finding: five of six tools' ecosystems include optional GPL-3.0 GLPK bindings (pandapower, which uses an embedded PYPOWER solver, is the exception) that Phase 2 deployment should explicitly exclude in favor of HiGHS (MIT) or Ipopt (EPL 2.0).

Per-criterion drill-downs with individual test outcomes are on the [report site results pages](https://zgenergy.github.io/grc-tech-evaluation/results).

## Ranking and Sensitivity

The final ranking using lexicographic forced-ranking:

1. **PyPSA** -- sole Strong Expressiveness; Strong in 5 of 6 criteria
2. **PowerModels.jl** -- Strong Extensibility via JuMP; no unit commitment; 487 lines/test average for user-assembled tests
3. **PowerSimulations.jl** -- Strong Extensibility; best UC formulations but Weak Accessibility
4. **GridCal** -- broad but shallow; Weak Maturity undermines otherwise Adequate technical profile
5. **pandapower** -- Strong Maturity and Supply Chain but Weak Expressiveness and Scalability

Three sensitivity scenarios were tested: Scalability First, Extensibility First, and Maturity-Accessibility Swapped. **PyPSA holds the top position in all three scenarios.** The ranking is entirely stable because PyPSA's sole Strong Expressiveness dominates regardless of priority reordering, and tier gaps between adjacent tools are wide enough that no single reordering changes relative positions.

The PyPSA vs. PowerModels trade-off is architectural: PyPSA's high-level API covers SCOPF, UC/ED, and custom constraints natively but incurs model-building overhead at scale. PowerModels exposes JuMP directly for maximum flexibility but requires users to assemble each analysis from scratch. For Phase 2, where the critical-path capabilities are SCOPF, custom constraint injection, and the UC/ED pipeline, PyPSA covers all three natively while PowerModels covers only one. PowerModels should be reconsidered only if R1 (model-building overhead) proves unresolvable. Full sensitivity analysis details are on the [report site head-to-head page](https://zgenergy.github.io/grc-tech-evaluation/results/head-to-head).

## Risk Register

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| R1 | Linopy model-building overhead: 302s build vs. 6s solve at 10k buses | HIGH | Profile early in Phase 2; fall back to direct HiGHS C API for inner loop |
| R2 | No PSS/E RAW parser | HIGH | Build converter via FNM intermediate format; or use MATPOWER `psse2mpc()` as preprocessor |
| R3 | No distributed slack in OPF context | MEDIUM | Implement via `extra_functionality` callback with PTDF formulation |
| R4 | Single-threaded HiGHS limits parallelism | MEDIUM | Process-level parallelism for independent contingency sub-problems |
| R5 | No native SOS2 piecewise-linear costs | LOW | Phase 2 uses linearized costs; gap is irrelevant to planned workflow |

None of these risks are disqualifying. The two HIGH-severity items have concrete mitigation paths with known effort bounds and fallback strategies. If R1 proves unresolvable at production scale, the fallback path is PowerModels.jl, which demonstrated 4.0s DC OPF solve with negligible model-building overhead.

## Phase 2 Outlook

Phase 2 follows a three-stage progression:

**Stage 1 -- Historical Calibration.** Assemble the full network model from available generators, vendor data, sensor flows, and constraint setup information from the ISO. Calibrate distribution factors and learn stochastic scenarios for generation outages and renewable variability. The success criterion is constraints firing as published per ISO market results.

**Stage 2 -- Real-Time Estimation.** Using real-time sensor data, aggregated load and generation figures, and published shadow prices for constraints, produce a real-time state estimation for the entire grid. Shadow prices combined with constraint setup information indicate whether a line is binding, providing at minimum a floor on flow levels. This stage bridges the gap between historical calibration and forward-looking analysis.

**Stage 3 -- Forecasting.** Apply the learned parameters from Stages 1 and 2 (distribution factors, stochastic scenarios for generation outages and renewables) to produce a range of possible power flow and congestion outcomes over a 2-to-3-day horizon. At this stage no prices are available; inputs are limited to load forecasts, renewable forecasts, and known generation and topology. The ultimate deliverable is a forward-looking vulnerability assessment tool capable of producing congestion forecasts at bus-level granularity.

**State Estimation Gap.** A cross-cutting investigation found that none of the six evaluated tools provide production-ready state estimation for transmission-scale grids. pandapower's SE exhibits convergence failures above ~89 buses; GridCal's bad data detection code is entirely commented out. Phase 2 will require dedicated SE tooling work, likely drawing on external open-source frameworks. The full SE investigation is in the repository under `phase2-research/`.

**Recommended next steps.** Begin with the two HIGH-severity risk mitigations: profile Linopy model-building overhead on the target network scale (R1) and build the PSS/E RAW ingestion pipeline (R2). These are on the critical path and will provide early signal on PyPSA viability. Develop ETL pipelines for all data sources in parallel.

---

*This white paper was produced under Contract FA714626C0006, SOW Task 1.3. The [interactive report site](https://zgenergy.github.io/grc-tech-evaluation/) provides full test evidence, per-criterion analysis, and sensitivity visualizations. All evaluation code, test scripts, and raw results are in the accompanying repository.*
