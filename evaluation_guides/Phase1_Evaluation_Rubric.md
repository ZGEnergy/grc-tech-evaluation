# Phase 1 Technology Evaluation Rubric
## Contract FA714626C0006 | Grid Research Company LLC

---

## Overview

This rubric defines the evaluation criteria and grading standards used to assess open-source power modeling tools for Phase 1 of contract FA714626C0006. Each tool is graded against six criteria organized into two tiers.

### Gate Criterion

**Supply Chain, Inspectability & Licensing Risk (Criterion 6)** is a gate criterion. A grade of C+ or below is disqualifying regardless of performance on all other criteria. This reflects the contract's primary motivation: the customer cannot recommend a tool for classified network authorization if any component in the execution stack is opaque, uninspectable, or legally encumbered.

### Weighted Criteria

The remaining criteria are evaluated in priority order. When two tools have comparable gate scores, the higher-priority criteria break ties:

1. **Problem Expressiveness** — Can it solve the problems we need?
2. **Extensibility** — Can analysts build beyond the built-in problems?
3. **Scalability** — Does it perform at large regional scale?
4. **Workforce Accessibility** — Can NRL analysts use it productively?
5. **Maturity & Sustainability** — Will it still be maintained in three years? (5a: Demonstrated Maturity; 5b: Sustainability Risk)

### Grading Scale

Each criterion is graded on a 9-point scale:

| Grade | Meaning |
|-------|---------|
| **A** | Strong native support, well-tested at scale, no significant caveats |
| **A-** | Strong overall but with one minor caveat that doesn't affect core workflows |
| **B+** | Mostly strong, one meaningful gap that has a stable workaround |
| **B** | Supported with caveats — requires extensions or workarounds, moderate friction |
| **B-** | Functional but multiple workarounds needed, some fragile |
| **C+** | Significant gaps but not disqualifying — tool is usable with substantial effort |
| **C** | Weak, significant gaps, outside tool's design scope |
| **C-** | Barely functional for the use case, major remediation required |
| **F** | Not achievable or disqualifying |

A, B, and C are defined explicitly in each criterion's grading standards. The +/- modifiers are assigned by evaluator judgment based on proximity to the boundary, justified by test evidence. For the gate criterion, the disqualifying boundary sits between B- and C+.

### Evaluation Scope

Tools are evaluated as their **shipped package plus official companion packages** maintained by the same team or organization. For example, PowerModels.jl is evaluated together with PowerModelsAnnex.jl and other LANL-ANSI infrastructure packages. PowerSimulations.jl is evaluated together with PowerSystems.jl, InfrastructureSystems.jl, and other NREL Sienna packages. PyPSA is evaluated together with linopy, atlite, powerplantmatching, and other official PyPSA ecosystem packages.

Third-party packages that happen to integrate with a tool but are maintained independently are noted but do not contribute to the tool's grade. When an official companion package is used to achieve a test result, this is explicitly documented.

Multi-tool stacks are only evaluated when the integration path is officially supported and documented by the tools themselves (e.g., pandapower with a PowerModels.jl backend, if that is a supported configuration). Hybrid stacks assembled by the evaluator from independently maintained tools are not evaluated — that is heroics, not a product.

### Hardware Baseline

All scalability testing is conducted on a reference workstation: **128 GB RAM, 16 cores, no GPU**. Results on other hardware may be noted for context but grades are assigned against this baseline.

### Solver Stack

All tests use open-source solvers exclusively. Commercial solvers (Gurobi, CPLEX) are not used in any test. The available solvers are HiGHS (LP, MILP, QP), SCIP (LP, MILP), Ipopt (NLP), and GLPK (LP, MILP). If a tool cannot interface with these solvers, that is recorded as a finding under Supply Chain (solver lock-in) and Scalability (solver flexibility).

### Reference Networks

| Label | Network | Buses | Purpose |
|-------|---------|-------|---------|
| SMALL | ACTIVSg 2k | ~2,000 | Smoke test, fast iteration |
| MEDIUM | ACTIVSg 10k | ~10,000 | Primary benchmark — all grades assessed here |
| LARGE | FNM Annual S01 | ~30,000 | Data model fidelity — production-network evidence for Expressiveness and Extensibility (FNM_PATH-gated) |

Reference networks are preprocessed per the test protocol's Data Preparation section before evaluation begins. Key preprocessing steps include fixing zero-impedance branches, setting unconstrained thermal ratings, and tightening select branch limits to induce congestion for tests that depend on binding constraints and non-uniform LMPs.

#### FNM Scope Expansion (v5)

The Full Network Model (FNM) Annual S01 variant is included in Phase 1 testing as a LARGE reference network. The FNM is ingested via a shared intermediate format (not direct PSS/E parsing) and tests data model fidelity: whether each tool can faithfully represent a production-scale ISO network's full parameter space, including record types absent from synthetic MATPOWER cases (3-winding transformers, switched shunt discrete steps, multi-section lines, area interchange data, and market-specific supplemental CSVs).

FNM test results inform Expressiveness and Extensibility grades via grading notes (see Criterion 1 and Criterion 2) but do not override the primary sub-questions or alter A/B/C grade boundaries. This follows the precedent of the v2 amendment, which added SCOPF/LMP sub-questions as Phase 2 readiness indicators that inform grades without automatic override.

All FNM-dependent tests are gated by the `FNM_PATH` environment variable. When `FNM_PATH` is not set, FNM tests skip gracefully and tools receive complete grades based on synthetic-network results alone. FNM results are additive evidence, not gating criteria.

For the full rationale, see `data/fnm/docs/rubric-v4-justification.md`.

### Companion Test Protocol

This rubric is accompanied by a separate **Phase 1 Test Protocol** document that defines the exact test cases, pass conditions, and recording requirements used to produce grades. Every grade in the evaluation report must trace to a specific test result or audit finding in the protocol. The rubric says *what* we evaluate; the protocol says *how*.

### Phase 2 Context — ISO Congestion Readiness

The v2 amendments to this rubric add sub-questions and findings that assess each tool's readiness for Phase 2 ISO congestion pattern reproduction. These amendments were motivated by research into how the ISO market clearing engine actually works, which revealed gaps in the original rubric's coverage of key analytical primitives.

**How the ISO clears its market:** The ISO Day-Ahead Market (DAM) uses a Security-Constrained Unit Commitment (SCUC) formulation — a single large MILP that co-optimizes commitment and dispatch. The optimization is linearized: DC power flow with AC-derived parameters (shift factors from a solved AC power flow, marginal loss factors from an AC loss calculation). Contingency constraints are embedded in the optimization via pre-computed LODFs and PTDFs — the engine does not remove equipment and re-run power flow for each contingency. Instead, post-contingency flows are expressed as linear functions of base-case flows, and the corresponding flow limits become additional constraints in the MILP. This is a *preventive* SCOPF: the base-case dispatch must be feasible under all monitored contingencies simultaneously.

**LMP decomposition:** ISO LMPs decompose into three components: System Marginal Energy Cost (SMEC) + Marginal Cost of Congestion (MCC) + Marginal Cost of Losses (MCL). The SMEC is defined at a distributed load-weighted reference bus, not a single slack bus. A tool that produces only lossless single-slack DC OPF LMPs will systematically misrepresent congestion patterns, particularly on long transmission paths where loss components are material.

**Contingency modeling:** The critical distinction is between *post-hoc* contingency analysis (remove equipment, re-solve, check for violations — tested in the original rubric as A-7) and *preventive SCOPF* (contingency flow limits as constraints inside the optimization). All ISOs use preventive SCOPF for market clearing. The original rubric tested only post-hoc sweeps.

**Phase 2 network data:** The Full Network Model (FNM) is NDA-restricted and distributed in PSS/E RAW format. Phase 2 will require either native PSS/E parsing or a custom converter, plus network imputation and calibration to reproduce published congestion patterns. DAM congestion is the recommended Phase 2 starting point due to data availability (public LMP and binding constraint data from OASIS).

**Impact on Phase 1 grading:** The new sub-questions (Expressiveness 9–11, Extensibility 8–9) are supplementary Phase 2 readiness indicators. They inform the grade narrative but do not automatically override the original sub-questions. See the grading note after Expressiveness sub-question 11.

---

## Cross-Cutting Lens — Software Engineering Quality

Power systems modeling tools span a wide range of software engineering competency. Many projects originate as single-contributor academic thesis work and inherit the architectural choices — and limitations — of their author. Others are built by teams with explicit software design goals and institutional review.

Evaluators should notice engineering quality as a signal that runs through multiple criteria rather than answering sub-questions mechanically. Specifically:

- **Accessibility** is affected by API consistency, naming coherence, and whether the tool feels designed for a user or for the author
- **Extensibility** is directly determined by whether the architecture separates concerns cleanly or is a monolith that grew organically
- **Maturity** is signaled by release engineering practices — versioning discipline, changelog quality, dependency pinning, and test coverage
- **Supply Chain risk** is amplified by poor release practices — unsigned artifacts, unversioned distributions, or unauditable dependency trees

When something feels off — documentation that doesn't match behavior, examples that don't run, interfaces that change without warning — that is engineering quality data and should inform the grades.

---

**Tools under primary evaluation:**
- PyPSA
- pandapower
- GridCal (formerly VeraGrid)
- PowerModels.jl (LANL-ANSI)
- PowerSimulations.jl (NREL Sienna)
- MATPOWER *(reference benchmark only — MATLAB runtime disqualifies for classified deployment)*

---

## Criterion 1 — Problem Expressiveness

**Core question:** How naturally does the tool let you formulate the problems we actually need to solve — without fighting the abstraction or working around missing primitives?

"Naturally" means the code reads like the problem, not like a workaround. A tool that can technically solve DC OPF but requires manual assembly of the constraint matrix is expressing the problem poorly.

### Sub-questions

**1. DC Power Flow** — Can you ingest a network and solve DCPF with minimal boilerplate? Does the tool expose nodal injections, line flows, and voltage angles as first-class outputs?

**2. AC Power Flow** — Full Newton-Raphson AC PF. Does the tool converge reliably on realistic, potentially ill-conditioned networks? Are bus voltage magnitudes and angles, line flows, and losses accessible directly? Can the tool report convergence residuals and iteration counts? Are solved voltage magnitudes demonstrably non-trivial (not flat-start defaults)?

**3. DC OPF** — Can you express a linearized OPF with generation cost minimization, line flow limits, and nodal balance constraints without leaving the tool's native API? Does it expose LMPs and shadow prices natively?

**4. AC PF feasibility check on DC OPF solution** — After solving DC OPF to obtain a generation dispatch, can the tool run a full AC PF on that solution to check voltage feasibility and surface violations (voltage magnitude out of bounds, line thermal limit violations, reactive power infeasibility)? Does it do this cleanly within the same network model, or does it require exporting and re-importing the dispatch result into a separate AC solver context?

**5. SCUC** — Can the tool express unit commitment as a MILP natively? Does it support minimum up/down times, startup costs, ramp rates, and reserve requirements as built-in constraint types — or must the user implement those from scratch? Does the formulation produce demonstrable generator cycling when the test data includes excess capacity and peaking units? This is evaluated against the tool's shipped package plus its official companion packages.

**6. SCED** — Real-time economic dispatch, typically LP/QP. Can you solve SCED as a warm-started dispatch given a fixed commitment schedule? Does the tool separate UC and ED cleanly as a two-stage workflow?

**Note on cost curve formulation:** The MATPOWER .m reference case files contain polynomial (quadratic) generator cost curves. Phase 1 uses whatever cost curves ship with the reference cases as-is — the evaluator documents which cost model is in effect and any solver implications. Real ISO markets clear using piecewise-linear bid curves. For each tool, the evaluator must document whether the tool supports piecewise-linear cost curves in its OPF and UC formulations (sub-questions 3, 5, and 6). This is recorded as an Expressiveness finding: a tool that supports only linear cost curves faces a meaningful limitation in any operational deployment.

**7. N-M Contingency Sweep (point-outward)** — Can you enumerate network elements radiating outward from a node of interest using graph primitives the tool exposes? Can you then re-solve PF/OPF for each contingency case without re-building the model from scratch?

**8. Stochastic Timeseries Optimization** — Does the tool natively support stochastic or multi-scenario optimization for load, wind, and solar timeseries? "Natively" means the stochastic structure is part of the optimization formulation — e.g., scenario trees, two-stage stochastic programs with recourse, or chance-constrained formulations — not independent deterministic solves in a loop. Perturbations must be independent by resource type (load, wind, solar — classified by cost tier proxy), and price extraction is part of the evaluation. Random noise applied independently to each interval without temporal correlation or cross-scenario structure does not constitute meaningful stochastic support.

**9. Security-Constrained OPF (SCOPF)** — Can the tool solve an OPF where N-1 contingency flow constraints are part of the optimization formulation, not checked post-hoc? Does the tool support preventive security constraints where the base-case dispatch must be feasible under all enumerated contingencies simultaneously? Can it use iterative contingency screening (activate/deactivate contingency constraints based on binding status) to manage problem size?

This is distinct from sub-question 7: sub-question 7 tests post-hoc contingency sweeps (re-solve PF/OPF for each contingency case after an initial solve). SCOPF tests contingency constraints *inside* the optimization — the dispatch is constrained to remain feasible under all enumerated contingencies. This is how all ISOs actually clear markets.

**Note on SCOPF feasibility:** Small test cases (e.g., IEEE 39-bus) may have tight thermal limits that make preventive SCOPF infeasible. Thermal rating relaxation is permitted for functional verification per the test protocol. This is a data finding, not a tool limitation.

**10. Lossy DC OPF and LMP Decomposition** — Can the tool solve a DC OPF with loss approximation (iterative loss factors, quadratic loss terms, or penalty factors — any method acceptable)? Can LMPs be decomposed into energy, congestion, and loss components? Are the loss components internally consistent (physically correct signs, total losses 0.5–3% of load, lossy objective exceeding lossless)? A tool that produces only lossless DC OPF LMPs will systematically misrepresent congestion patterns on long transmission paths.

**11. Distributed Slack OPF** — Can the tool solve DC OPF with a distributed slack bus (load-proportional or generation-proportional) rather than a single slack bus? All ISOs use distributed slack in their market clearing engines — the reference bus is a weighted aggregate across participating loads or generators, not a single bus. This directly affects LMP computation: the System Marginal Energy Cost is defined at the distributed reference, and congestion/loss components are relative to it. A tool that only supports single-slack OPF will produce LMP decompositions that don't match ISO-published values.

**Note on Phase 2 readiness sub-questions (9, 10, 11):** These sub-questions are supplementary Phase 2 readiness indicators. The original sub-questions (1–8) remain the primary drivers of the Expressiveness grade. Sub-questions 9–11 inform whether the tool is ready for ISO congestion pattern reproduction. A tool that scores well on 1–8 but poorly on 9–11 receives a grade note, not an automatic downgrade. However, a tool that cannot express SCOPF at all (not even through its extension API) or cannot support distributed slack faces a meaningful limitation for Phase 2 that should be reflected in the grade narrative.

**Note on FNM data model fidelity (v4):** When FNM test results are available (FNM_PATH set), the tool's ability to ingest and faithfully represent the FNM intermediate format is additional evidence for the Expressiveness grade. Specifically:

- **Record type coverage** — The FNM contains PSS/E record types absent from synthetic MATPOWER cases: 3-winding transformers, switched shunt discrete steps, multi-section lines, HVDC records, and area interchange data. A tool that ingests all record types from the intermediate format without data loss demonstrates broader data model expressiveness than one tested only against synthetic cases. Record type coverage informs sub-questions 1 and 2 (DCPF/ACPF) because correct power flow results depend on faithful topology and parameter representation.
- **Power flow verification** — DCPF and ACPF results on the FNM are compared against reference solutions using pass conditions defined in `data/fnm/reference/pass_conditions.json`. A tool that passes FNM power flow verification demonstrates that its data model fidelity is sufficient for production-scale computation, not just ingestion. This directly informs sub-questions 1 and 2.
- **Grade impact** — FNM results strengthen or weaken the evidence base for the grade assigned by sub-questions 1–11, but do not independently determine the grade. A tool that passes all synthetic-network tests but fails FNM ingestion entirely receives a grade note documenting the gap. A tool that passes both synthetic and FNM tests has stronger evidence for its grade. The A/B/C grade boundaries are unchanged.
- **Scale vs. expressiveness** — If FNM ingestion fails due to scale alone (the tool cannot handle ~30K buses regardless of data model completeness), the finding is attributed to Scalability (Criterion 4), not Expressiveness. If failure is due to missing record type support (e.g., the tool has no representation for 3-winding transformers), the finding is attributed to Expressiveness.

### Grading Standards

| Grade | Description |
|-------|-------------|
| **A** | All target problem types (DCPF, ACPF, DC OPF, AC feasibility check, SCUC, SCED, contingency sweep, stochastic optimization) expressible natively within the tool's API or official companion packages. Core constraints are built-in primitives, not user-assembled. ACPF convergence verifiable via residuals and iteration counts. Outputs (LMPs, flows, angles, commitment schedules) accessible as structured objects. SCUC produces demonstrable generator cycling on appropriately parameterized test cases. Contingency re-solve does not require full model reconstruction. Stochastic scenarios are first-class objects in the formulation. SCOPF expressible natively or through documented extension API. Loss-inclusive OPF supported with LMP decomposition into energy, congestion, and loss components, validated via internal consistency checks. Distributed slack OPF supported natively. |
| **B** | Most problem types supported, but one or two require a companion package, a manual modeling layer, or a non-obvious workaround. The tool gets you there but with friction. ACPF convergence may lack full diagnostics (iteration count or residual not directly exposed). Stochastic support may require wrapping in an external loop (tested separately under Extensibility). SCOPF achievable through extension API with moderate effort. Loss approximation possible but may require manual implementation. Distributed slack achievable through configuration or workaround. |
| **C** | A target problem type is outside the tool's design scope entirely, or requires rebuilding core functionality from primitives in a general-purpose modeling language. |

---

## Criterion 2 — Extensibility

**Core question:** Once you have a solved power flow or OPF, how hard is it to go beyond the built-in problem types — adding custom constraints, querying the network graph, generating stochastic scenarios, or building a contingency sweep pipeline — without fighting the tool's internal architecture?

This is distinct from Expressiveness. Expressiveness asks "can the tool solve the standard problems?" Extensibility asks "can an analyst build *on top of* those solutions to do something the tool didn't anticipate?"

### Sub-questions

**1. Custom constraints** — Can a user add constraints to an existing OPF formulation (e.g. a custom reserve requirement, a flow gate limit, a correlated scenario constraint) without forking the codebase or monkey-patching internals? Is there a documented extension API?

**2. Network graph access** — Is the network topology exposed as a traversable graph object? Can you run BFS/DFS from a node of interest to identify N-M neighbors, isolate subnetworks, or compute electrical distance — using either the tool's own primitives or by cleanly exporting to a graph library (e.g. NetworkX, Graphs.jl)?

**3. Contingency loop construction** — Can you programmatically define a set of contingencies, solve each, and collect results without re-parsing or re-instantiating the base model each time? Is there a native contingency analysis workflow, or must you build it in a loop?

**4. Stochastic scenario wrapping** — For tools that do not natively support stochastic optimization (as tested in Criterion 1), can you wrap the tool to run scenario ensembles with stochastic load, wind, and solar timeseries? Key factors: Can timeseries be injected via the API or must config files be rewritten per scenario? Can the model be re-solved with modified timeseries without full reconstruction? The stochastic inputs must use temporally correlated perturbations — not i.i.d. noise per interval — to test whether the tool's timeseries interface supports realistic scenario structures. Perturbation bounds must be calibrated to produce at most 20% infeasible scenarios on the target network.

**5. Interoperability** — Can results be exported to standard formats (DataFrames, JSON, HDF5, CSV) for downstream analysis without custom serialization? Can the tool ingest outputs from other tools in the stack?

**6. Code architecture quality** — Is the codebase structured around clean abstractions with meaningful separation of concerns — network model, problem formulation, solver interface, results — or is it a monolithic script that grew organically? Does the architecture suggest it was designed to be extended, or that extension was never a design goal? Are internal interfaces documented or must an analyst reverse-engineer them to build on top of the tool?

**7. AC feasibility as extension** — If the tool does not natively support running an AC PF feasibility check on a DC OPF dispatch within the same model context (as tested in Criterion 1, sub-question 4), document the effort required to achieve this workflow. This is noted here for tools where the AC check requires a workaround rather than a built-in path.

**8. Reference bus control** — Can the analyst programmatically set or change the reference/slack bus? Does LMP computation respond correctly to reference bus changes? This affects LMP decomposition in ISO markets that use distributed load reference buses.

**9. PTDF matrix extraction** — Can the tool expose or compute Power Transfer Distribution Factors as a programmatically accessible matrix or per-element query? This is the fundamental analytical primitive for congestion analysis. PTDFs may be exposed natively (e.g., MATPOWER's `makePTDF()`), extractable from the solved model's internal matrices, or computable via unit injection experiments. On networks with phase-shifting transformers, does the tool correctly account for Pbusinj/Pfinj correction terms in PTDF-based flow predictions? Document the method and effort level.

**Note on FNM supplemental CSV representability (v4):** When FNM test results are available (FNM_PATH set), the tool's ability to represent data from the 7 FNM supplemental CSVs is additional evidence for the Extensibility grade. The supplemental CSVs carry market-specific data — trading hub definitions, generator distribution factors, contingency definitions, interface limits, transmission ratings beyond the base 3-tier, and outage scheduling data — that no tool natively ingests.

For each supplemental CSV field, a representability classification is assigned using the 3-tier system documented in `data/fnm/docs/supplemental-csvs.md`:

- **Natively representable** — The tool has a built-in attribute or data structure for this data. No analyst effort required.
- **Extension-representable** — The tool can carry this data via its documented extension mechanisms (custom attributes, metadata dictionaries, user-defined fields) without forking or patching the codebase. Moderate analyst effort.
- **Tool-external** — No representation path exists within the tool's data model. The data must be carried in an external structure (DataFrame, dictionary, database) alongside the tool's network model. This creates a split-model workflow where some network data lives inside the tool and some outside.

The proportion of supplemental CSV fields in each tier directly indicates how much post-ingestion extension work an analyst faces to use the FNM for production analysis. This maps to Extensibility sub-questions 1 (custom constraints — supplemental data like interface limits and contingency definitions are inputs to custom constraints), 5 (interoperability — tool-external fields require external data structures that must stay synchronized with the tool's network model), and 6 (code architecture quality — a tool whose data model is easily extended to carry supplemental data demonstrates better architectural extensibility than one that forces tool-external workarounds).

**Grade impact:** A tool with predominantly natively-representable or extension-representable supplemental CSV fields has stronger evidence for an A or B Extensibility grade. A tool where most supplemental data is tool-external demonstrates a meaningful limitation that should be noted in the grade narrative. The A/B/C grade boundaries are unchanged. The representability summary in `data/fnm/docs/supplemental-csv-representability.md` provides the cross-tool comparison matrix.

### Workaround Durability

When a sub-question is answered with a workaround, the workaround is classified:

| Class | Definition |
|-------|-----------|
| **Stable** | Uses a documented, public API in a non-obvious way. Unlikely to break on upgrade. |
| **Fragile** | Depends on undocumented internals, private attributes, or behavior not guaranteed by the API. Could break on any minor version bump. |
| **Blocking** | Requires forking the source, patching compiled code, or is simply not achievable. |

A test requiring any workaround (stable, fragile, or blocking) must be classified as `qualified_pass`, not `pass`. The workaround class determines the grade range: stable workarounds support a B-range grade, fragile workarounds pull toward B- or C+, and blocking workarounds result in C or below.

### Grading Standards

| Grade | Description |
|-------|-------------|
| **A** | Documented extension API for custom constraints. Network exposed as a traversable graph. Contingency loops buildable without model reconstruction. Stochastic scenario wrapping straightforward with API-level timeseries injection and calibrated perturbations (≤20% infeasibility). Results export to standard formats is trivial. Clean architecture with separation of concerns — a competent analyst can extend the tool in days, not weeks. Reference bus configurable via API. PTDF matrix accessible as a structured output with correct handling of phase-shifting transformer correction terms. |
| **B** | Extension is possible but requires understanding internals. Graph access works via a workaround or external library bridge. Contingency looping requires some model reconstruction overhead. Stochastic wrapping achievable but requires config file manipulation or per-scenario overhead. Architecture is partially structured but shows signs of organic growth. Reference bus control possible with workaround. PTDF extraction requires manual computation from network data; phase-shifter corrections may require user implementation. |
| **C** | Extension requires forking or patching the core. Network topology not accessible as a graph. Contingency analysis requires full model rebuilds. Stochastic wrapping not feasible without major effort. Monolithic or thesis-project architecture with no meaningful separation of concerns. |

---

## Criterion 3 — Workforce Accessibility

**Core question:** Can a new analyst at NRL pick this tool up, run their own scenarios, and trust what it's doing?

This criterion is purely about usability — the learning curve, API quality, documentation, and error handling. Inspectability and security authorization concerns are evaluated under Criterion 6 (Supply Chain, Inspectability & Licensing Risk).

### Sub-questions

**1. API design** — Is the API intuitive for someone with a power systems background but not necessarily deep software engineering experience? Are common workflows accomplishable without reading source code?

**2. Documentation quality** — Is there substantive documentation beyond an API reference? Are there worked examples on realistic networks, not just toy cases? Is the math behind the formulations documented so an engineer can verify the model is doing what they think? Critically: is the documentation synchronized with the actual implementation — are documented features verifiably implemented and runnable, or are sections aspirational, partially implemented, or silently broken?

**3. Learning curve** — How long does it realistically take a new analyst to go from installation to running a meaningful DC OPF on a real network? Days? Weeks?

**4. Error transparency** — When something goes wrong (infeasibility, convergence failure, data error), does the tool surface meaningful diagnostic information, or does it fail silently or with cryptic solver output?

### Grading Standards

| Grade | Description |
|-------|-------------|
| **A** | Clean, well-documented API with realistic worked examples. A power systems engineer is productive within days. Errors surface meaningfully with actionable diagnostics. |
| **B** | API is learnable but has rough edges. Documentation covers the basics but gaps exist for advanced use cases. Learning curve measured in weeks, not days. Error messages require solver familiarity to interpret. |
| **C** | Steep learning curve requiring deep software expertise beyond power systems. Documentation is sparse, outdated, or aspirationally ahead of implementation. Errors fail silently or surface only cryptic solver output. |

---

## Criterion 4 — Scalability

**Core question:** Does the tool perform at large regional scale — 10k+ buses, realistic contingency counts, operational time horizons — without requiring heroic engineering effort or hardware unavailable to a government analyst?

Note this is not just raw speed. Scale must be evaluated in the context of actual workflows: a tool that solves DC OPF on the ACTIVSg 10k case in 10 minutes is acceptable if it only runs once; a tool requiring 10 minutes per contingency across thousands of contingencies is not.

All scalability measurements are taken on the reference workstation (128 GB RAM, 16 cores, no GPU) using open-source solvers only. No pre-defined time thresholds — results are recorded and compared across tools. All timings must be measured wall-clock times from actual test execution; estimated or projected timings cannot support pass or qualified_pass grades. Solver performance limitations are distinguished from tool capability limitations — a tool that expresses a formulation correctly but whose solver times out receives a scalability finding, not an expressiveness failure.

### Sub-questions

**1. Power flow at scale** — Does DC and AC PF converge reliably on the ACTIVSg 10k-bus test case? What are realistic wall-clock times on the reference workstation?

**2. DC OPF and AC feasibility check at scale** — Can DC OPF be solved on a 10k+ bus network in a timeframe consistent with operational use? After obtaining the DC OPF dispatch, can the tool execute an AC PF feasibility check on the same network without model reconstruction? Are voltage violations and line limit violations surfaced as structured outputs that can be programmatically interrogated?

**3. SCUC/SCED at scale** — Unit commitment is a MILP and scales poorly with problem size. Does the tool expose tuning handles (e.g. MIP gap tolerance, warm starting, problem decomposition) that make operational-scale UC feasible? What are realistic solve times on the test network?

**4. Solver backend flexibility** — Can the tool interface with multiple open-source solvers (HiGHS, SCIP, Ipopt, GLPK) for different problem types? Is the solver interface abstracted so you can swap solvers without reformulating the problem? This matters operationally: different solvers have different strengths, and the ability to swap without changing the model formulation is significant.

**5. Contingency sweep performance** — For an N-M sweep radiating outward from a point of interest, can the tool solve hundreds or thousands of PF re-runs in a tractable time? Does it support warm-starting from a base case to accelerate contingency solves?

**6. Memory and hardware requirements** — What are realistic RAM requirements for 10k+ bus problems on the reference workstation? Can the tool run within the 128 GB baseline, or does it require more? Is there a clear path to HPC deployment if needed?

### Grading Standards

| Grade | Description |
|-------|-------------|
| **A** | Demonstrated performance on 10k+ bus networks on the reference workstation. Solver interface cleanly abstracted — open-source solvers swappable without reformulation. Contingency re-solves support warm-starting. Clear HPC scaling path. Memory requirements workstation-tractable for DC problems. |
| **B** | Performs adequately at 10k buses but with caveats — contingency sweeps require careful batching, or specific solver needed for MILP problems. HPC path exists but is not well-documented. |
| **C** | Performance degrades significantly at 10k+ buses for core workflows. No warm-start support for contingency re-solves. Solver interface tightly coupled — swapping requires reformulation. No clear HPC path. |

---

## Criterion 5 — Maturity & Sustainability

**Core question:** Is this tool going to be here in three years, actively maintained, and moving in a direction that stays relevant to operational power systems analysis — or is it a research project that could stall, pivot, or lose its key maintainer?

This matters because Phase 2 and any follow-on work builds on whatever stack Phase 1 selects. A tool that degrades or goes unmaintained mid-contract is a serious operational risk for NRL.

### 5a — Demonstrated Maturity

Sub-questions under 5a evaluate backward-looking evidence of engineering discipline and operational track record.

**5a E-1. Release engineering discipline** — Does the project practice disciplined release engineering? Versioned releases (semver or equivalent), pinned dependency versions, meaningful changelogs that match what actually shipped, CI passing on the current release. Do published getting-started examples and tutorials actually run on the current release, or are they stale? Documentation that is aspirationally ahead of the implementation is a signal of poor release discipline, not just a documentation gap.

**5a E-2. Test coverage and CI health** — Does a test suite exist? Does it run in CI? What does it cover — happy-path examples, or edge cases and regressions? Is CI green on the current release? A project without automated tests is shipping on faith.

**5a E-3. Issue responsiveness** — How quickly are bugs and issues addressed? Is the issue tracker active and managed, or is it a graveyard of unacknowledged reports? Sample the last 20 closed and 10 open issues.

**5a E-4. Operational adoption** — Has the tool been used in production or near-production settings by utilities, ISOs, or government entities — not just academic research? Operational adoption is a strong signal of maturity that academic citation counts don't capture.

#### 5a Grading Standards

| Grade Band | Standards |
|:---:|---|
| A | Strong release discipline (semantic versioning, changelogs), robust CI with >80% test coverage, responsive issue triage (<7 days median), demonstrated operational adoption |
| B | Regular releases but inconsistent discipline, CI present with moderate coverage (50-80%), reasonable issue responsiveness (<30 days), some evidence of operational use |
| C | Irregular or absent releases, minimal CI/testing, slow or no issue response (>30 days), no evidence of operational adoption beyond the development team |

### 5b — Sustainability Risk

Sub-questions under 5b evaluate forward-looking risk factors that could threaten continued development.

**5b E-1. Contributor concentration and bus factor** — How many active contributors? What percentage of commits come from the top contributor? Is the contributor base growing or concentrated in one or two people whose departure would stall the project? A project with a bus factor of one is a project with an expiration date.

**Reviewer/approval concentration:** Sample the last 50 merged PRs. Record the percentage approved by the top reviewer. High concentration (>80%) indicates single-gatekeeper risk.

**5b E-2. Funding stability** — Is development backed by a durable institution (national lab, university research group, foundation) or dependent on a single grant or individual? Is there a clear funding model going forward?

**5b E-3. Governance model** — Is there a formal governance structure (foundation, steering committee, published roadmap) or is direction set informally by a single maintainer? This is a secondary signal — good governance without engineering discipline is theater; engineering discipline without governance is a risk to be noted, not a disqualifier.

#### 5b Grading Standards

| Grade Band | Standards |
|:---:|---|
| A | Multiple active contributors (bus factor ≥3), low reviewer concentration (<50% by top reviewer), diversified funding or institutional backing, formal governance model |
| B | Small but stable contributor base (bus factor 2), moderate reviewer concentration (50-80%), identifiable funding source, informal but functional governance |
| C | Single dominant contributor (bus factor 1), high reviewer concentration (>80%), no visible funding sustainability, no governance model |

### Criterion 5 Composite Grading

The final Criterion 5 grade is determined by combining the 5a and 5b sub-criterion grades using the following matrix:

| 5a ↓ \ 5b → | **A range** | **B range** | **C range** |
|:---:|:---:|:---:|:---:|
| **A range** | A / A- | B+ / B | B / B- |
| **B range** | B+ / B | B / B- | C+ / C |
| **C range** | B- / C+ | C+ / C | C / C- |

Within each two-grade cell, select the higher grade when the sub-criterion score is near the boundary of its band (e.g., a low-A 5a score with a solid-B 5b score yields B, not B+).

---

## Criterion 6 — Supply Chain, Inspectability & Licensing Risk

**GATE CRITERION — A grade of C+ or below is disqualifying.**

**Core question:** Is every component in the execution stack open-source, inspectable, and legally unencumbered for government use — including deployment on classified networks? Can every line of code that executes during a solve be read, audited, and authorized?

This is the criterion that motivated the entire contract. A tool can score well on every other dimension and still be disqualifying here. The customer cannot recommend a tool for classified network authorization if any component in the dependency tree is a proprietary binary, an opaquely licensed library, or a package with unclear provenance.

### Sub-questions

**1. License of core package** — Is the tool itself licensed under a permissive open-source license (MIT, BSD-3, Apache-2)? Copyleft licenses (GPL, LGPL, MPL) require legal review before government deployment and may create downstream obligations that complicate a government-controlled toolkit.

**2. Dependency tree transparency and stability** — Can the full dependency tree be enumerated completely and unambiguously? Are all dependencies themselves open-source with known, auditable provenance? Are dependency versions pinned in the package's release artifacts, or can a dependency upgrade silently change runtime behavior without a version bump in the tool itself? An unpinned dependency tree means you cannot guarantee that two installs of the same version are running the same code.

**3. Compiled extensions** — Are there compiled binary components (C extensions, Cython, Fortran) in the execution path? If so, is the source code for those components publicly available and buildable from source? A compiled extension with available source is auditable; one without is not.

**4. Distribution integrity** — Are releases versioned, signed, and distributed through a verifiable channel (PyPI with hashes, Julia General Registry, GitHub releases with signed tags)? Are getting-started examples and tutorials pinned to a specific release, or do they point to unversioned tarballs or blob store artifacts that could change or be substituted without notice? Asking a new user to execute an unversioned, unverifiable artifact to get started is a meaningful security concern for classified network deployment and a red flag in any authorization review.

**5. Code inspectability** — Is the full execution path readable Python or Julia source? Are there compiled extensions, Cython modules, or binary dependencies that execute during a solve without readable source? Can every line that touches network data or solves an optimization problem be read and audited by a government analyst? Trace the execution path from the API call to solver invocation and identify every module that executes.

**6. Security authorization path** — Has the tool, or tools like it, been deployed on classified or air-gapped networks before? Is the dependency tree shallow enough to be tractable to audit? Are all components buildable from source for air-gapped installation? Can the full stack be installed offline without network access at runtime?

**7. Solver dependencies** — The tool's core may be clean but the solver it calls may not be. Are the open-source solver options (HiGHS, SCIP, Ipopt, GLPK) sufficient for all target use cases? A tool that requires a commercial solver to be functional for any target use case introduces a proprietary binary into the stack and fails this criterion.

**8. Data pipeline dependencies** — Libraries used to ingest the reference networks or other data sources are also part of the stack. Are those dependencies clean? Less common dependencies need explicit scrutiny.

**9. Supply chain attack surface** — Is the package distributed through a trustworthy channel with verifiable maintainer identity? Has the package had any known security incidents?

### Grading Standards

| Grade | Description |
|-------|-------------|
| **A** | Permissive license (MIT or BSD-3). Full dependency tree is open-source, auditable, and version-pinned in release artifacts. Full execution path is readable source with no opaque binaries. Any compiled extensions have publicly available, buildable source. Functional on open-source solvers alone for all target use cases. Releases versioned, signed, and distributed through standard trustworthy channels. Getting-started examples pinned to a specific release. Dependency tree shallow enough for tractable audit. All components installable offline. |
| **B** | Copyleft license (LGPL, MPL) requiring legal review but not inherently disqualifying. Dependency tree mostly clean with one or two items needing scrutiny. Most execution path is inspectable but one or two compiled extensions exist with readable source available. Security authorization achievable but requires effort. Some unpinned dependencies but behavior is predictable in practice. |
| **C+** | **Disqualifying.** Significant inspectability gaps that may be remediable with substantial effort — e.g., a compiled extension with source available but no build system, or a dependency with an ambiguous license that could potentially be replaced. |
| **C or below** | **Disqualifying.** Proprietary runtime or binary component anywhere in the execution path with no available source. License terms incompatible with government deployment. Dependency tree not fully enumerable or contains opaque dependencies. Full execution path not auditable. Requires commercial solver to be functional for target use cases. |

---

## Phase 2 Readiness Findings

These are informational findings documented during Phase 1 evaluation. They do not affect Phase 1 grades but directly inform Phase 2 planning effort estimates.

**1. PSS/E RAW Format Parsing** — Does the tool have any PSS/E RAW format parsing capability? If so, which RAW versions (v26, v29, v30, v33, v35)? If not, what is the expected effort to build or integrate a parser? The Full Network Model is distributed in PSS/E format; Phase 2 requires either native parsing or a custom converter.

**2. Piecewise-Linear Cost Curves** — Does the tool support piecewise-linear cost curves in its OPF and UC formulations? This finding is cross-referenced from the Expressiveness cost curve note. Real ISO markets clear using piecewise-linear bid curves; a tool that only supports linear cost curves faces a meaningful limitation in any operational deployment. Document the formulation type if supported (SOS2, lambda, incremental) and any limitations.

---

## Addendum — Tools Considered but Ruled Out

The following tools were identified during the landscape survey and considered for inclusion in the primary evaluation. Each was ruled out for the reason noted. They are documented here for traceability and to inform future scope expansions.

| Tool | Reason Excluded |
|------|----------------|
| **MATPOWER** | Included as a reference benchmark only. MATPOWER itself is BSD-3 licensed and open-source, but its canonical runtime is MATLAB — a proprietary binary. This disqualifies it as a primary stack candidate under the supply chain and inspectability criteria that motivate this contract. GNU Octave is a viable open-source substitute but has known performance limitations at 10k-bus regional scale and is not a production-grade path. MATPOWER's case format (.m) and problem formulations remain the reference standard against which all other tools are implicitly compared. |
| **PYPOWER** | Python port of an early MATPOWER version. Functionally superseded by pandapower, which is faster, better maintained, and compatible with PYPOWER's interface. No reason to evaluate both. |
| **GridDyn** | C++ transmission dynamics simulator developed at LLNL. Last substantive activity circa 2019; project appears stalled. Fails Maturity criterion. |
| **PowSyBl** | Production-grade grid analysis framework used by European transmission system operators (RTE, ENTSO-E). Java core with Python bindings. Strong CGMES/CIM format support but European data model focus — PSS/E RAW ingestion is less tested. Architecturally mature but the operational context and data formats are misaligned with US transmission work. Worth revisiting if scope expands to multi-region or international grids. |
| **PowerGridModel** | C++ core with Python API, developed by Alliander under LF Energy. Designed for high-speed batch power flow across many scenarios in parallel — primarily a distribution system tool. Transmission use is possible but not the design target. Potentially relevant in Phase 2 if contingency sweep volume requires batch PF acceleration, but not a primary evaluation candidate for the full use case set. |
| **HELICS** | Co-simulation framework developed by DOE (NREL/PNNL/LLNL). Not a solver — HELICS orchestrates coupling between separate simulation tools across domains (transmission, distribution, communications, transportation). Not directly applicable to Phase 1 tool evaluation. Potentially relevant in later phases if multi-domain scenario coupling becomes a requirement. |
| **GridLAB-D** | Distribution system simulator developed at PNNL. Scope is explicitly distribution-level (feeders, DER, load modeling). Not applicable to high-voltage transmission modeling. |
| **OpenDSS** | Distribution system simulator developed by EPRI. Same exclusion rationale as GridLAB-D — distribution scope, not transmission. |
| **STEPS** | Large-scale AC-DC hybrid power system analysis tool. Actively maintained and handles mixed AC/DC topology. Less established in the US power systems community and documentation is primarily in Chinese. Warrants re-evaluation if HVDC modeling becomes a primary requirement. |

---

## Quick Reference

| Criterion | Type | Core Question |
|-----------|------|--------------|
| 1. Problem Expressiveness | Weighted (priority 1) | Can it formulate the problems we need to solve? |
| 2. Extensibility | Weighted (priority 2) | Can analysts build on top of solved problems? |
| 3. Workforce Accessibility | Weighted (priority 4) | Can NRL analysts use it productively? |
| 4. Scalability | Weighted (priority 3) | Does it perform at large regional scale with open-source solvers? |
| 5. Maturity & Sustainability (5a/5b) | Weighted (priority 5) | Will it still be here and maintained in three years? (5a: Demonstrated Maturity; 5b: Sustainability Risk) |
| 6. Supply Chain, Inspectability & Licensing Risk | **Gate** | Is every component in the stack auditable, inspectable, and legally clean? |

---

## Revision History

| Version | Date | Change | Author |
|---------|------|--------|--------|
| v1 | TBD | Initial rubric | GRC |
| v2 | 2026-03-05 | Added Phase 2 Context section (ISO SCOPF/LMP research). Added Expressiveness sub-questions 9 (SCOPF), 10 (lossy DC OPF / LMP decomposition), 11 (distributed slack OPF) with grading note. Updated Expressiveness grading standards for A and B to reference new sub-questions. Added Extensibility sub-questions 8 (reference bus control) and 9 (PTDF matrix extraction). Updated Extensibility grading standards for A and B. Added Phase 2 Readiness Findings section (PSS/E RAW parsing, piecewise-linear cost curves). | GRC |
| v3 | 2026-03-06 | Cost curve note updated to acknowledge polynomial costs in MATPOWER files (was "linear costs throughout"). Added SCOPF feasibility note for small test cases. Stochastic optimization sub-question clarified: independent perturbations by resource type, price extraction required. Aligned with protocol v4 changes. | GRC |
| v4 | 2026-03-09 | Cross-tool sweep amendments aligned with protocol v5. ACPF sub-question requires convergence residual, iteration count, and non-flat-start verification. SCUC sub-question requires demonstrable cycling. Lossy DCOPF sub-question specifies internal consistency validation. PTDF sub-question addresses phase-shifter correction terms. Stochastic wrapping sub-question adds perturbation calibration requirement. Workaround scoring clarified: any workaround requires qualified_pass classification. Solver/tool separation: expressiveness grading distinguishes formulation capability from solver performance. Scalability grading requires measured wall-clock times. Reference network preprocessing noted. Extensibility grading standards updated for PTDF phase-shifter handling and calibrated stochastic perturbations. | GRC |
| v5 | 2026-03-09 | FNM scope expansion: added FNM Scope Expansion section incorporating FNM Annual S01 as LARGE reference network (~30K buses, PSS/E v31 via intermediate format, FNM_PATH-gated). Added FNM data model fidelity grading note under Expressiveness (record type coverage, power flow verification, scale-vs-expressiveness attribution). Added supplemental CSV representability grading note under Extensibility (3-tier field classification, sub-question mapping). FNM results inform but do not override primary sub-questions or alter grade boundaries. Full justification: `data/fnm/docs/rubric-v4-justification.md`. | GRC |
| v6 | 2026-03-10 | Split Criterion 5 into 5a (Demonstrated Maturity) and 5b (Sustainability Risk). Added 3x3 composite grade matrix. Added reviewer/approval concentration sub-metric under 5b. | GRC |
