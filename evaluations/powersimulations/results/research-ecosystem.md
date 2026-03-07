# powersimulations -- Research: Limitations & Ecosystem

## Key Findings

- **SCOPF is not natively implemented.** Issue [#944](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/944) (opened Mar 2023, still open) requests N-1/N-k SCOPF with PTDF formulation. The legacy `SecurityConstrainedPTDFPowerModel` was removed in v0.33.0 and replaced with a branch-level N-1 formulation ([#1462](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1462)), but full SCOPF remains incomplete.
- **No stochastic optimization support.** No built-in scenario-based or two-stage stochastic formulations exist. No GitHub issues or documentation reference stochastic capabilities. Users would need to build this manually on top of JuMP.
- **PTDF is well-supported** via `PTDFPowerModel` and `AreaPTDFPowerModel`, but PTDF loss approximations are still in development ([#1537](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1537)) and require LHS parameter support not yet implemented.
- **LMP decomposition is not a built-in feature.** Dual variables can be extracted from solved models via JuMP, but PowerSimulations does not provide direct LMP calculation or decomposition utilities. No documentation or issues address this.
- **Massive dependency footprint.** The resolved Manifest.toml contains 183 package entries, including MKL, HDF5, SQLite, MPI. Compare to ~30 for PowerModels.jl doing the same DCPF task.
- **Very active development** with 15 releases in the last 14 months (v0.28.3 to v0.33.1), but rapid version churn creates fragile compat bounds across the Sienna ecosystem.
- **Small core team.** 39 total contributors, but one developer (jd-lara) has 7,537 commits -- roughly 10x the next contributor. Bus factor risk.
- **311 GitHub stars, 78 forks** (as of March 2026). Moderate community for a domain-specific Julia package.
- **Government-backed but no documented production deployments.** Developed under DOE contract DE-AC36-08GO28308 at NREL. No evidence of utility/ISO production use.
- **AC OPF is available via PowerModels.jl integration** (ACP, ACR, SOCWR, LPAC, etc.), not natively in PowerSimulations.jl itself.

## Detailed Notes

### Ecosystem Architecture

PowerSimulations.jl (branded as Sienna\Ops) is part of the NREL Sienna ecosystem, which comprises three application layers:

| Sienna Module | Julia Package(s) | Function |
|---|---|---|
| Sienna\Data | PowerSystems.jl (359 stars), InfrastructureSystems.jl (41 stars) | Data model, parsing, validation |
| Sienna\Ops | PowerSimulations.jl (311 stars), PowerNetworkMatrices.jl (28 stars), PowerFlows.jl (29 stars) | Scheduling, UC, ED, OPF |
| Sienna\Dyn | PowerSimulationsDynamics.jl (215 stars) | Transient/dynamic simulation |

Additional ecosystem packages under [NREL-Sienna](https://github.com/nrel-sienna) (49 repos total):

- **HydroPowerSimulations.jl** (12 stars) -- hydro device extensions
- **StorageSystemsSimulations.jl** (7 stars) -- battery/storage extensions
- **HybridSystemsSimulations.jl** (6 stars) -- hybrid plant extensions
- **PowerAnalytics.jl** (9 stars) -- results analysis
- **PowerGraphics.jl** (33 stars) -- visualization
- **PowerSystemCaseBuilder.jl** (17 stars) -- test system builder
- **PowerSystemsInvestments.jl** (21 stars) -- capacity expansion
- **PyPSA2PowerSystems.jl** (7 stars) -- PyPSA data converter

Sources: [GitHub org page](https://github.com/nrel-sienna), [Sienna NREL page](https://www.nrel.gov/analysis/sienna)

### Network Formulations Available

PowerSimulations.jl provides four native network formulations:

1. **CopperPlatePowerModel** -- single-node, no network constraints
2. **PTDFPowerModel** -- DC approximation using PTDF matrix, nodal balance
3. **AreaBalancePowerModel** -- inter-area flow, one node per region
4. **AreaPTDFPowerModel** -- PTDF with area-level balancing (does NOT support slack variables)

Additionally, via PowerModels.jl integration:
- Non-convex AC: ACPPowerModel, ACRPowerModel, ACTPowerModel
- Linear: DCPPowerModel, NFAPowerModel
- Quadratic/relaxation: SOCWRPowerModel, LPACCPowerModel, QCRMPowerModel
- SDP: SDPWRMPowerModel

Source: [Network formulation docs](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Network/)

### Evaluation-Relevant Limitations

#### SCOPF / Contingency Analysis (N-1)
- Issue [#944](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/944) (opened 2023-03-14, still open, 0 comments): Requests N-1/N-k SCOPF with PTDF formulation, branch and generator contingencies, corrective actions.
- Issue [#1462](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1462) (closed 2026-01-08): Removed legacy `SecurityConstrainedPTDFPowerModel` and refactored N-1 as a branch formulation. Notes: "N-1 model was refactored as a branch formulation. This opens the opportunity for AC modeling of the network but considering post contingency in DC model."
- Issue [#1522](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1522) (opened 2026-01-20, open, no body/comments): "Post contingency evaluation" -- appears to be tracking post-solve contingency checking.
- Issue [#1461](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1461) (open): G-1 SCUC with storage outages not yet supported.
- Issue [#1458](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1458) (open): Error handling for outages on reduced branches in N-1 SCUC.

**Summary:** N-1 SCUC exists but is undergoing active refactoring. Full SCOPF (with corrective actions, voltage constraints) is not implemented. Post-contingency evaluation is in early stages.

#### Stochastic Optimization
No evidence of built-in stochastic optimization support anywhere in the codebase, documentation, or issue tracker. The only related issue is [#1471](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1471) ("Ensure reproducibility of outage queries") which deals with probabilistic outage sampling, not stochastic programming.

#### PTDF / Network Matrices
- `PTDFPowerModel` is mature and well-documented.
- Distributed slack is supported via `PowerNetworkMatrices.jl` -- PTDF can be computed with a `dist_slack` weight vector. ([PowerNetworkMatrices docs](https://github.com/NREL-Sienna/PowerNetworkMatrices.jl/blob/main/docs/src/tutorials/tutorial_PTDF_matrix.md))
- Loss approximation in PTDF models is not yet available ([#1537](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1537)).
- DC Power Flow in the Loop with network reductions is not yet supported ([#1547](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1547)).

#### LMP Decomposition
No built-in LMP calculation or decomposition. Users must extract dual variables from the JuMP model manually. No issues or documentation address this.

#### MATPOWER Format Ingestion
PowerSystems.jl can parse MATPOWER `.m` files via `System(PowerSystems.PSS_MATPOWER, "file.m")`. During parsing, it performs validation and reports violations (e.g., generators exceeding limits). This works but produces verbose warnings for standard test cases. The multi-package API (`PowerSystems` for data, `PowerFlows` for solving, `PowerNetworkMatrices` for network types) adds cognitive overhead. Source: [install-findings.md](../notes/install-findings.md)

### Community and Governance

| Metric | Value |
|---|---|
| GitHub stars | 311 |
| GitHub forks | 78 |
| Open issues | 66 |
| Total contributors | 39 |
| Top contributor (jd-lara) | 7,537 commits |
| #2 contributor (sourabhdalvi) | 680 commits |
| #3 contributor (claytonpbarrows) | 577 commits |
| License | BSD-3-Clause |
| Created | 2017-11-03 |
| Organization | NREL-Sienna (49 repos) |

The project has a Slack community (referenced on NREL Sienna page). No Discourse forum or Stack Overflow tag with significant activity was found.

Source: [GitHub API](https://github.com/NREL-Sienna/PowerSimulations.jl)

### Release History

Very active release cadence -- 15 releases in the last ~14 months:

| Version | Date | Notable |
|---|---|---|
| v0.33.1 | 2026-02-24 | AC line losses aux variable, renewables timeseries patch |
| v0.33.0 | 2026-02-18 | **Breaking:** renamed power flow loop flows, removed legacy N-1 code, synchronous condenser model, decomposition updates, 17 merged PRs |
| v0.32.4 | 2025-12-18 | Outage events cleanup, precompilation improvements |
| v0.32.3 | 2025-12-13 | Parallel branches with unequal impedances, emulation bugfixes |
| v0.32.0 | 2025-12-08 | (minor version bump) |
| v0.31.0 | 2025-11-11 | (minor version bump) |
| v0.30.2 | 2025-06-09 | |
| v0.30.0 | 2025-02-06 | |
| v0.29.0 | 2024-12-12 | |
| v0.28.3 | 2024-07-24 | |

PowerSystems.jl (the data layer) has also been actively releasing:
- v5.5.0 (2026-02-12), v5.4.0 (2026-01-22), v5.0.0 (2025-11-01)

The v5.0 major version bump in PowerSystems.jl (Nov 2025) required coordinated updates across the ecosystem.

Sources: [PowerSimulations releases](https://github.com/NREL-Sienna/PowerSimulations.jl/releases), [PowerSystems releases](https://github.com/NREL-Sienna/PowerSystems.jl/releases)

### Documentation Quality

Documentation follows the [Diataxis framework](https://diataxis.fr/) with five sections:

1. **Tutorials** (2): Single-step problem, multi-stage production cost simulation
2. **How-to guides** (7): Variable registration, templates, results reading, debugging infeasible models, logging, recording, parallel execution
3. **Explanation** (4): Modeling structure, feedforward, chronologies, sequencing
4. **Reference**: Public API, glossary, developer docs
5. **Formulation Library** (9 sections): Thermal, renewable, load, branch, source, services, feedforwards, network, piecewise linear

**Strengths:**
- Structured according to Diataxis best practices
- Recently updated (Jan 2026 with Documenter.jl 1.16.1)
- Tutorials switched to Literate.jl format in v0.33.0
- Formulation library provides mathematical equations for each device model

**Weaknesses:**
- Only 2 tutorials -- limited onboarding paths
- No troubleshooting/FAQ section
- No performance optimization guide (issue [#1252](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1252) open)
- No case studies or real-world examples
- Multiple documentation issues open: [#1533](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1533), [#1357](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1357), [#1338](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1338), [#1266](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1266), [#1262](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1262), [#1213](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1213), [#1165](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1165)
- Multi-package API requires knowing which type lives in which package

Source: [PowerSimulations.jl docs](https://nrel-sienna.github.io/PowerSimulations.jl/latest/)

### Dependency and Supply Chain Analysis

The project's `Manifest.toml` resolves to **183 package entries**. Key dependency categories:

- **Optimization**: JuMP, MathOptInterface, GLPK, HiGHS, Ipopt, SCIP
- **Data**: DataFrames, CSV, HDF5, SQLite, JSON3, YAML
- **Sienna ecosystem**: PowerSystems, InfrastructureSystems, PowerFlows, PowerNetworkMatrices
- **Numerics**: MKL, LinearAlgebra, SparseArrays
- **System**: MPI (multiple implementations)

All Sienna packages are BSD-3-Clause. JuMP is MPL-2.0. Solver packages have their own licenses (GLPK: GPL-3.0, HiGHS: MIT, Ipopt: EPL-2.0, SCIP: Apache-2.0 wrapper around ZIB academic license).

The Pkg resolver reports multiple packages with compatibility constraint pins (marked with special characters), indicating the ecosystem is not keeping up with upstream upgrades.

Source: [Project.toml](../Project.toml), [install-findings.md](../notes/install-findings.md)

### IEEE Publication

Lara et al. (2024), "PowerSimulations.jl -- A Power Systems Operations Simulation Library," IEEE Transactions in Power Systems. ([arXiv](https://arxiv.org/html/2404.03074v1))

Key claims from the paper:
- Designed for production cost modeling spanning months to years
- Supports unit commitment, economic dispatch, AGC, and nonlinear OPF
- Parameters limited to RHS of linear constraints and linear objective coefficients
- Positioned against PyPSA (focused on expansion planning), FESTIV (MATLAB, commercial), PowerModels.jl (single-period only), and commercial tools (PLEXOS, PROMOD -- lack transparency)
- **No mention of SCOPF, contingency analysis, stochastic optimization, or LMP** in the paper

### Operational Deployment Evidence

- Developed under DOE contract at NREL (now National Laboratory of the Rockies)
- The [PSI-Cambodia](https://github.com/NREL-Sienna/PSI-Cambodia) repo (7 stars) suggests use in a Cambodia power system study
- No documented utility, ISO, or commercial production deployments found
- No evidence of use in real-time or day-ahead market operations

## Sources

1. [PowerSimulations.jl GitHub](https://github.com/NREL-Sienna/PowerSimulations.jl)
2. [PowerSystems.jl GitHub](https://github.com/NREL-Sienna/PowerSystems.jl)
3. [InfrastructureSystems.jl GitHub](https://github.com/NREL-Sienna/InfrastructureSystems.jl)
4. [PowerSimulations.jl docs](https://nrel-sienna.github.io/PowerSimulations.jl/latest/)
5. [Formulation library - Network](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Network/)
6. [Formulation library - Introduction](https://nrel-sienna.github.io/PowerSimulations.jl/stable/formulation_library/Introduction/)
7. [NREL Sienna page](https://www.nrel.gov/analysis/sienna)
8. [NREL-Sienna GitHub org](https://github.com/nrel-sienna)
9. [PowerSimulations.jl releases](https://github.com/NREL-Sienna/PowerSimulations.jl/releases)
10. [PowerSystems.jl releases](https://github.com/NREL-Sienna/PowerSystems.jl/releases)
11. [Lara et al. 2024, arXiv](https://arxiv.org/html/2404.03074v1)
12. [PowerNetworkMatrices PTDF tutorial](https://github.com/NREL-Sienna/PowerNetworkMatrices.jl/blob/main/docs/src/tutorials/tutorial_PTDF_matrix.md)
13. [SCOPF issue #944](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/944)
14. [N-1 refactor #1462](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1462)
15. [Post contingency #1522](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1522)
16. [PTDF losses #1537](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1537)
17. [DC PF in loop + reductions #1547](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1547)
18. Local file: `evaluations/powersimulations/notes/install-findings.md`
19. Local file: `evaluations/powersimulations/Project.toml`

## Gaps and Uncertainties

- **Stochastic optimization**: No evidence found for or against. Could be built manually via JuMP but no PowerSimulations-native support exists. Needs verification during testing.
- **LMP decomposition**: Dual variable extraction via JuMP should work in theory but has not been tested with PowerSimulations network formulations. Needs hands-on verification.
- **Distributed slack in PowerSimulations (not just PowerNetworkMatrices)**: The PTDF matrix supports distributed slack, but it is unclear whether `PTDFPowerModel` in PowerSimulations passes this through. Needs code-level verification.
- **Scalability benchmarks**: No published benchmarks found for large systems (1000+ buses). The docs claim scalability is a goal but provide no numbers.
- **AC OPF via PowerModels integration**: The docs list AC formulations but it is unclear how well-tested the PowerModels translator is in recent versions (issue [#1478](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1478) requests increased test coverage).
- **N-1 SCUC maturity**: The formulation was just refactored in Dec 2025/Jan 2026. Testing is needed to assess stability and correctness of the new implementation.
- **Real-world deployment scale**: No public evidence of system size handled in practice. The Cambodia study and NREL internal use may provide data but are not publicly documented.
