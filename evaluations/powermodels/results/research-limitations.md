# PowerModels.jl -- Research: Limitations & Ecosystem

Research conducted 2026-03-06 against PowerModels.jl v0.21.5 (latest release: 2025-08-12).

## Key Findings

- **Steady-state only**: PowerModels.jl is explicitly a steady-state power network optimization tool. It cannot perform time-series simulation, production cost modeling, unit commitment (SCUC/SCED), or dynamic simulation. These require separate ecosystem packages (UnitCommitment.jl, PowerSimulations.jl).
- **No built-in LODF**: PTDF matrix calculation is supported (`calc_basic_ptdf_matrix`), but LODF (Line Outage Distribution Factor) is not implemented. Open issue [#923](https://github.com/lanl-ansi/PowerModels.jl/issues/923) requests this; a community contributor has offered an implementation but it has not been merged as of March 2026.
- **No distributed slack**: Power flow uses a single-slack-bus model. Generators at PQ buses cause assertion errors (issue [#989](https://github.com/lanl-ansi/PowerModels.jl/issues/989)). No built-in distributed slack bus support.
- **No native contingency analysis**: SCOPF and contingency analysis require the separate package PowerModelsSecurityConstrained.jl (v0.12.0, last pushed 2024-01-19). The core package provides multi-network infrastructure but not contingency problem specifications.
- **MATPOWER parsing bugs**: Several open issues with parsing edge cases -- large cases like case21k fail ([#854](https://github.com/lanl-ansi/PowerModels.jl/issues/854)), Matpower D-Curves unsupported ([#614](https://github.com/lanl-ansi/PowerModels.jl/issues/614)), and load/shunt identification from Matpower format is ambiguous ([#605](https://github.com/lanl-ansi/PowerModels.jl/issues/605)).
- **Moderate community**: 456 stars, 167 forks, 27 contributors, 83 open issues. Active but LANL-led with limited external contribution.
- **Release cadence slowing**: 3 releases in 2024, 2 in 2025 (most recent v0.21.5 on 2025-08-12), none in 2026 so far. Still pre-1.0 after 9+ years.
- **Rich formulation library**: 16+ formulations spanning exact NLP (ACP, ACR, ACT, IVR), linear approximations (DCP, DCMP, BFA, NFA), quadratic (DCPLL, LPACC), conic relaxations (SOCWR, QCRM, QCLS, SOCBF), and SDP relaxations (SDPWRM, SparseSDPWRM).
- **Strong academic pedigree**: Developed at Los Alamos National Laboratory under DOE contract. Foundational paper by Coffrin et al. (2018) is widely cited in power systems optimization literature.
- **BSD-3 license with US Government rights**: Permissive license suitable for government use. Produced under US Government contract DE-AC52-06NA25396.

## Detailed Notes

### Supported Problem Types and Formulations

PowerModels.jl supports five core problem types ([docs](https://lanl-ansi.github.io/PowerModels.jl/stable/specifications/)):

| Problem | Functions | Notes |
|---------|-----------|-------|
| Power Flow (PF) | `build_pf`, `build_pf_bf`, `build_pf_iv` | BIM, BFM, and current-flow variants |
| Optimal Power Flow (OPF) | `build_opf`, `build_opf_bf`, `build_opf_iv`, `build_opf_ptdf` | Includes multi-network and storage variants |
| Optimal Power Balance (OPB) | `build_opb` | Copper-plate approximation |
| Optimal Transmission Switching (OTS) | `build_ots` | Branch status forced to 0 if input is 0 |
| Transmission Network Expansion (TNEP) | `build_tnep` | Candidate branch planning |

Formulations available (from [formulation details](https://lanl-ansi.github.io/PowerModels.jl/stable/formulation-details/)):

**Exact Non-Convex**: ACPPowerModel (polar), ACRPowerModel (rectangular), ACTPowerModel (voltage-angle/magnitude-squared), IVRPowerModel (current-voltage rectangular)

**Linear Approximations**: DCPPowerModel (standard DC), DCMPPowerModel (MATPOWER-compatible DC with tap/shift), BFAPowerModel (branch flow approximation), NFAPowerModel (network flow / transportation)

**Quadratic Approximations**: DCPLLPowerModel, LPACCPowerModel (cold-start LPAC)

**Quadratic Relaxations**: SOCWRPowerModel, SOCWRConicPowerModel, QCRMPowerModel, QCLSPowerModel, SOCBFPowerModel, SOCBFConicPowerModel

**SDP Relaxations**: SDPWRMPowerModel, SparseSDPWRMPowerModel

Source: [formulations docs](https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/), [formulation details](https://lanl-ansi.github.io/PowerModels.jl/stable/formulation-details/)

### Known Limitations Relevant to Evaluation Tests

#### No SCUC / SCED / Unit Commitment
PowerModels.jl is a single-period steady-state optimization tool. It does not model generator commitment decisions, minimum up/down times, start-up costs, or multi-period dispatch. For SCUC, the Julia ecosystem offers [UnitCommitment.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl) (135 stars, actively maintained by Argonne National Lab). PowerModels.jl could provide the network formulation backbone but does not solve UC problems natively.

Source: [PowerSimulations.jl paper](https://arxiv.org/html/2404.03074v1), [UnitCommitment.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl)

#### No Stochastic Optimization (Native)
Stochastic OPF requires [StochasticPowerModels.jl](https://github.com/Electa-Git/StochasticPowerModels.jl) (24 stars, last pushed 2025-10-14), developed externally by KU Leuven (Electa group). Multi-period stochastic dispatch with hydropower is available via [HydroPowerModels.jl](https://github.com/LAMPSPUC/HydroPowerModels.jl) (12 stars).

Source: [StochasticPowerModels.jl](https://github.com/Electa-Git/StochasticPowerModels.jl), [issue #112](https://github.com/lanl-ansi/PowerModels.jl/issues/112)

#### SCOPF / Contingency Analysis
Security-constrained OPF is handled by [PowerModelsSecurityConstrained.jl](https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl) (41 stars, v0.12.0, last pushed 2024-01-19). This was the benchmark algorithm for ARPA-e GOC Challenge 1 (2019). The iterative SCOPF solver adds contingency constraints progressively. Dual value extraction from SCOPF solutions was historically limited but has been improved.

Source: [PowerModelsSecurityConstrained.jl](https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl), [Discourse thread](https://discourse.julialang.org/t/powermodels-jl-multinetwork-for-security-constrained-ac-opf/113511)

#### PTDF and LMP Decomposition
`calc_basic_ptdf_matrix` is available since v0.17.4. Individual row computation via `calc_basic_ptdf_row`. PTDF-based OPF variant available via `solve_opf_ptdf_branch_power_cuts` (currently limited to DCPPowerModel). No native LODF computation ([#923](https://github.com/lanl-ansi/PowerModels.jl/issues/923)). LMP decomposition (congestion + loss components) would need to be manually extracted from dual variables.

Source: [basic data utilities docs](https://lanl-ansi.github.io/PowerModels.jl/stable/basic-data-utilities/), [utilities docs](https://lanl-ansi.github.io/PowerModels.jl/stable/utilities/)

#### Distributed Slack Bus
Not supported. Power flow implementation uses a single reference bus (bus_type=3). Active generators must be at slack (type 3) or PV (type 2) buses; generators at PQ buses cause assertion errors ([#989](https://github.com/lanl-ansi/PowerModels.jl/issues/989)). Issue [#932](https://github.com/lanl-ansi/PowerModels.jl/issues/932) reports incorrect behavior for active generators at load buses in PSSE files.

Source: [issue #989](https://github.com/lanl-ansi/PowerModels.jl/issues/989), [issue #932](https://github.com/lanl-ansi/PowerModels.jl/issues/932)

#### Power Flow Limitations
- `solve_pf()` does not work with LPACCPowerModel ([#891](https://github.com/lanl-ansi/PowerModels.jl/issues/891))
- Power flow does not enforce thermal limits -- this is by design (PF vs OPF distinction), but can surprise users ([Discourse](https://discourse.julialang.org/t/is-there-a-power-flow-formulation-that-considers-branches-power-transfer-limit-in-powermodels-jl/57548))
- Sequential power flow (repeated solves with changing loads) requires using `compute_ac_pf` instead of `solve_pf` for performance ([Discourse](https://discourse.julialang.org/t/sequential-ac-power-flow-using-powermodels-jl/96183))
- DCPLL (DC with losses) support for power flow formulations is an open request ([#873](https://github.com/lanl-ansi/PowerModels.jl/issues/873))

### MATPOWER Format Ingestion Issues

Several open issues affect MATPOWER file parsing:

| Issue | Description | Status |
|-------|-------------|--------|
| [#854](https://github.com/lanl-ansi/PowerModels.jl/issues/854) | case21k parsing fails with `AssertionError: occursin(".", matrix_assignment)` | Open since 2023-02 |
| [#840](https://github.com/lanl-ansi/PowerModels.jl/issues/840) | No auto-extending of data dictionary for loads | Open since 2022-08 |
| [#614](https://github.com/lanl-ansi/PowerModels.jl/issues/614) | No support for Matpower D-Curves | Open since 2019-10 |
| [#605](https://github.com/lanl-ansi/PowerModels.jl/issues/605) | Ambiguous load/shunt identification from Matpower format | Open since 2019-09 |
| [#304](https://github.com/lanl-ansi/PowerModels.jl/issues/304) | Vector data in Matpower Extensions unsupported | Open since 2018-06 |
| [#134](https://github.com/lanl-ansi/PowerModels.jl/issues/134) | Matlab data compatibility issues | Open since 2017-07 |
| [#83](https://github.com/lanl-ansi/PowerModels.jl/issues/83) | Semicolons in strings cause parser failures | Open since 2017-02 |

The MATPOWER parser is part of InfrastructureModels.jl (v0.7.8), not PowerModels itself. There is an open proposal to extract the parser into a separate package ([#894](https://github.com/lanl-ansi/PowerModels.jl/issues/894)).

PSS/E (PTI) format also has multiple open issues (7 open issues labeled "File format: PSSE/PTI"), including lack of v34 support ([#921](https://github.com/lanl-ansi/PowerModels.jl/issues/921)).

### Ecosystem Packages

All LANL packages are under the `lanl-ansi` GitHub organization:

| Package | Stars | Last Push | Purpose |
|---------|-------|-----------|---------|
| [PowerModels.jl](https://github.com/lanl-ansi/PowerModels.jl) | 456 | 2025-12-01 | Core transmission OPF/PF |
| [PowerModelsDistribution.jl](https://github.com/lanl-ansi/PowerModelsDistribution.jl) | 156 | 2025-11-10 | Unbalanced distribution networks |
| [PowerModelsSecurityConstrained.jl](https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl) | 41 | 2024-01-19 | SCOPF / contingency |
| [PowerModelsRestoration.jl](https://github.com/lanl-ansi/PowerModelsRestoration.jl) | 27 | 2025-03-07 | Network restoration optimization |
| [PowerModelsAnnex.jl](https://github.com/lanl-ansi/PowerModelsAnnex.jl) | 25 | 2025-12-03 | Exploratory/experimental extensions |
| [PowerModelsAnalytics.jl](https://github.com/lanl-ansi/PowerModelsAnalytics.jl) | 17 | 2023-12-19 | Visualization |
| [PowerModelsITD.jl](https://github.com/lanl-ansi/PowerModelsITD.jl) | 15 | 2024-10-01 | Integrated transmission-distribution |
| [InfrastructureModels.jl](https://github.com/lanl-ansi/InfrastructureModels.jl) | -- | -- | Shared infrastructure (parsers, etc.) |

External ecosystem packages built on PowerModels:

| Package | Stars | Organization | Purpose |
|---------|-------|--------------|---------|
| [UnitCommitment.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl) | 135 | Argonne National Lab | SCUC |
| [StochasticPowerModels.jl](https://github.com/Electa-Git/StochasticPowerModels.jl) | 24 | KU Leuven (Electa) | Stochastic OPF |
| [PowerModelsACDC.jl](https://github.com/Electa-Git/PowerModelsACDC.jl) | -- | KU Leuven (Electa) | Hybrid AC/DC grids |
| [PowerModelsACDCsecurityconstrained.jl](https://github.com/csiro-energy-systems/PowerModelsACDCsecurityconstrained.jl) | -- | CSIRO | AC/DC SCOPF |
| [HydroPowerModels.jl](https://github.com/LAMPSPUC/HydroPowerModels.jl) | 12 | LAMPSPUC (PUC-Rio) | Hydrothermal dispatch via SDDP |

### Community Size and Activity

- **GitHub**: 456 stars, 167 forks, 27 contributors, 83 open issues (as of 2026-03-06)
- **Subscribers**: 21 watching the repository
- **Created**: 2016-08-01
- **Primary maintainer**: Carleton Coffrin (LANL)
- **Julia Discourse**: Active discussions in the "Optimization (Mathematical)" category; questions typically answered within days
- **Academic impact**: Foundational paper ([arXiv:1711.01728](https://arxiv.org/abs/1711.01728)) by Coffrin, Bent, Sundar, Ng, and Lubin (2017/2018) is widely cited
- **Government connection**: Developed at LANL under DOE contract; ARPA-e GOC competition benchmark

### Documentation Quality

**Strengths**:
- Comprehensive formulation details page listing all 16+ formulations with mathematical descriptions
- Quick start guide with working examples
- Auto-generated API documentation for all public functions
- Network data format documentation
- Tutorial notebooks available ([tutorial-grid-science](https://github.com/lanl-ansi/tutorial-grid-science))

**Weaknesses**:
- Open issue [#705](https://github.com/lanl-ansi/PowerModels.jl/issues/705) "Documentation Improvements" since 2020-04 acknowledges gaps: expressions page missing, modeling components not grouped by type
- Open issue [#272](https://github.com/lanl-ansi/PowerModels.jl/issues/272) "Improved Developer Documentation" since 2018-05
- Open issue [#169](https://github.com/lanl-ansi/PowerModels.jl/issues/169) "Documentation of Multinetwork Features" since 2017-08
- Open issue [#344](https://github.com/lanl-ansi/PowerModels.jl/issues/344) "Docs on Viewing the JuMP Model" since 2018-08
- Sequential/repeated power flow workflows not well documented
- Extension development guide exists but is terse
- No comprehensive examples for LMP extraction or market-oriented workflows

### Release History

| Version | Date | Type | Notable Changes |
|---------|------|------|-----------------|
| v0.21.5 | 2025-08-12 | Patch | Relax tests for INFEASIBLE_POINT, silence Memento during precompilation |
| v0.21.4 | 2025-05-20 | Patch | Fix InexactError in AC PF, PrecompileTools, performance improvements |
| v0.21.3 | 2024-11-04 | Patch | Fix no-buses bug in connected components |
| v0.21.2 | 2024-07-05 | Patch | In-place building, performance improvements, PSSE transformer fix |
| v0.21.1 | 2024-03-16 | Patch | Fix theta delta bounds bug |
| v0.21.0 | 2024-01-19 | Minor (breaking) | Update to new JuMP nonlinear interface |
| v0.20.0 | 2024-01-02 | Minor (breaking) | Mixed PWL/polynomial costs, two-sided constraints, drop multi-conductor support |
| v0.19.10 | 2024-01-01 | Patch | PST variables support for ACP/DCP |
| v0.19.9 | 2023-05-28 | Patch | Fix polynomial costs above quadratic |

**Cadence observation**: v0.20.0 and v0.21.0 were both breaking releases in January 2024, suggesting a consolidation push. Since then, only patch releases. The project remains pre-1.0 (v0.21.x) after 9+ years, indicating the API is still considered unstable.

### Dependency and Licensing

**Direct dependencies**(v0.21.5): InfrastructureModels, JSON, JuMP, LinearAlgebra (stdlib), Memento, NLsolve, PrecompileTools, SparseArrays (stdlib)

**Total dependency count**(with solvers): ~90 packages installed in the evaluation environment including Ipopt, HiGHS, GLPK, SCIP solvers and their JLL binary wrappers.

**License**: BSD-3-Clause with US Government rights clause (DOE contract DE-AC52-06NA25396). All LANL ecosystem packages use the same license. JuMP is MIT-licensed. Solver licenses vary (Ipopt: EPL, HiGHS: MIT, GLPK: GPL-3).

**Note on GLPK**: GLPK is GPL-3 licensed, which is copyleft. If deployed in a context where GPL restrictions matter, HiGHS (MIT) is a suitable alternative for LP/MIP.

### Julia Runtime Considerations

- Julia startup overhead: 5-15 seconds per invocation for package loading even with precompilation
- First-solve latency ("time to first plot" problem): JIT compilation of solver code on first call adds significant one-time cost
- `PrecompileTools` was added in v0.21.4 to mitigate this
- For repeated evaluations, staying in the Julia REPL and using `include()` avoids recompilation

## Sources

1. [PowerModels.jl GitHub repository](https://github.com/lanl-ansi/PowerModels.jl)
2. [PowerModels.jl documentation](https://lanl-ansi.github.io/PowerModels.jl/stable/)
3. [PowerModels.jl CHANGELOG](https://github.com/lanl-ansi/PowerModels.jl/blob/master/CHANGELOG.md)
4. [PowerModels.jl releases](https://github.com/lanl-ansi/PowerModels.jl/releases)
5. [PowerModels.jl formulation details](https://lanl-ansi.github.io/PowerModels.jl/stable/formulation-details/)
6. [PowerModels.jl specifications](https://lanl-ansi.github.io/PowerModels.jl/stable/specifications/)
7. [PowerModels.jl basic data utilities](https://lanl-ansi.github.io/PowerModels.jl/stable/basic-data-utilities/)
8. [PowerModels.jl utilities](https://lanl-ansi.github.io/PowerModels.jl/stable/utilities/)
9. [PowerModels.jl quick guide](https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/)
10. [PowerModels.jl LICENSE](https://github.com/lanl-ansi/PowerModels.jl/blob/master/LICENSE.md)
11. [PowerModels.jl Project.toml](https://github.com/lanl-ansi/PowerModels.jl/blob/master/Project.toml)
12. [PowerModelsSecurityConstrained.jl](https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl)
13. [StochasticPowerModels.jl](https://github.com/Electa-Git/StochasticPowerModels.jl)
14. [UnitCommitment.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl)
15. [HydroPowerModels.jl](https://github.com/LAMPSPUC/HydroPowerModels.jl)
16. [Coffrin et al. (2018) arXiv:1711.01728](https://arxiv.org/abs/1711.01728)
17. [PTDF discussion on Julia Discourse](https://discourse.julialang.org/t/calculating-power-transfer-distribution-factor-ptdf-matrix-using-powermodels-jl/42668)
18. [Sequential PF discussion on Julia Discourse](https://discourse.julialang.org/t/sequential-ac-power-flow-using-powermodels-jl/96183)
19. [SCOPF multinetwork discussion on Julia Discourse](https://discourse.julialang.org/t/powermodels-jl-multinetwork-for-security-constrained-ac-opf/113511)
20. [Issue #923 - LODF utility](https://github.com/lanl-ansi/PowerModels.jl/issues/923)
21. [Issue #989 - Generators in PQ buses](https://github.com/lanl-ansi/PowerModels.jl/issues/989)
22. [Issue #854 - Matpower case21k parsing](https://github.com/lanl-ansi/PowerModels.jl/issues/854)
23. [Issue #705 - Documentation improvements](https://github.com/lanl-ansi/PowerModels.jl/issues/705)

## Gaps and Uncertainties

- **Citation count**: Could not retrieve exact Google Scholar citation count for the foundational paper. It is widely referenced in power systems optimization literature but the exact number needs manual verification.
- **Operational deployment**: No evidence found of PowerModels.jl being used in production by any utility, ISO, or RTO. Usage appears entirely academic and government-research. This is a significant finding for evaluation.
- **LMP decomposition**: While dual variables from OPF can theoretically provide LMPs, there is no documented workflow or utility for decomposing LMPs into energy, congestion, and loss components. Needs testing.
- **Large-scale performance**: No benchmark data found for systems larger than a few thousand buses. The case21k parsing failure ([#854](https://github.com/lanl-ansi/PowerModels.jl/issues/854)) suggests scalability limits that need testing.
- **PowerModelsSecurityConstrained.jl compatibility**: Last pushed January 2024, before PowerModels v0.21.3-v0.21.5. Compatibility with latest PowerModels needs verification.
- **Multi-period OPF**: Multi-network support exists in the core package but documentation is sparse ([#169](https://github.com/lanl-ansi/PowerModels.jl/issues/169)). Unclear how well it handles temporal coupling constraints (ramp rates, storage state of charge across periods).
- **Warm-start support**: Not documented whether PowerModels supports warm-starting solvers from a previous solution. This matters for sequential OPF/market clearing applications.
