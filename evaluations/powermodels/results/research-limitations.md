# PowerModels.jl -- Research: Limitations & Ecosystem

## Key Findings

- **Steady-state only**: PowerModels.jl is explicitly scoped to steady-state power network optimization (PF, OPF). It cannot perform multi-period simulation, unit commitment, or long-range operational scheduling without extension packages.
- **No built-in SCUC or multi-period OPF**: Unit commitment, ramping constraints, and time-series dispatch require separate packages (UnitCommitment.jl, PowerSimulations.jl). Multi-period/stochastic OPF was discussed in Issue #112 but delegated to extensions.
- **SCOPF lives in a separate package**: Security-constrained OPF is not in the core; it requires PowerModelsSecurityConstrained.jl. That package does not support storage, dcline, or switch components.
- **Historical DC OPF bug**: Transformer phase shift was ignored in DC OPF (Issue #422), mirroring a MATPOWER limitation. This was acknowledged as a bug and addressed in later releases.
- **No native distributed slack or LMP decomposition**: PowerModels uses a single reference bus. Distributed slack and LMP congestion/loss decomposition are not built-in features.
- **Large ecosystem but fragmented**: 15+ extension packages exist (distribution, restoration, ACDC, GMD, ITD, stability, protection, etc.), but each is independently maintained with varying maturity levels.
- **Research-focused, not production-focused**: Developed at Los Alamos National Laboratory primarily for research. No evidence of direct operational deployment at utilities or ISOs.
- **Moderate release cadence**: Only two releases in the last 24 months (v0.21.4 in May 2024, v0.21.5 in August 2024). Still on v0.x, signaling the API is not yet considered stable.
- **114 transitive dependencies** in the resolved Manifest.toml (with solvers GLPK, HiGHS, Ipopt, SCIP, JuMP). The dependency tree is substantial but typical for Julia optimization stacks.
- **Strong academic impact**: 456 GitHub stars, 167 forks, 29 contributors, 83 open issues. The foundational 2018 PSCC paper by Coffrin et al. is widely cited (estimated 300+ citations). Used as the ARPA-e GOC Competition benchmark algorithm.

## Detailed Notes

### Scope and Problem Types

PowerModels.jl focuses on steady-state power network optimization. Its design decouples **problem specifications** (Power Flow, Optimal Power Flow) from **formulation details** (AC polar, AC rectangular, DC approximation, SOC relaxation, SDP relaxation, QC relaxation, PTDF, etc.).

Supported formulations include:
- **ACPPowerModel** -- AC power flow (polar coordinates)
- **ACRPowerModel** -- AC power flow (rectangular coordinates)
- **IVRPowerModel** -- Current-voltage rectangular formulation
- **DCPPowerModel** -- Standard DC approximation
- **DCPLLPowerModel** -- DC with piecewise-linear losses
- **SOCWRPowerModel** -- Second-order cone relaxation (W-R space)
- **SOCBFPowerModel** -- Second-order cone (branch flow)
- **QCRMPowerModel** / **QCLSPowerModel** -- Quadratically-constrained relaxations
- **SDPWRMPowerModel** -- Semidefinite programming relaxation
- **NFAPowerModel** -- Network flow approximation

This is a strength for OPF research but means many operational power system problems (UC, economic dispatch over time, contingency screening) are out of scope without extensions.

Source: [PowerModels formulations documentation](https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/)

### Multi-Period and Stochastic OPF (Issue #112)

GitHub Issue #112 (opened June 2017, closed as completed) discussed adding multi-period and stochastic OPF support. The resolution was a "network replicates" abstraction (the `multinetwork` feature) where variables become indexed by replicate ID. However:

- The core package provides the **infrastructure** (multinetwork data model) but not ready-made multi-period or stochastic problem formulations.
- Users must build their own inter-temporal linking constraints (ramp rates, storage state-of-charge, etc.).
- Stochastic programming was deferred to extension packages like [StochasticPowerModels.jl](https://github.com/Electa-Git/StochasticPowerModels.jl) (KU Leuven, not LANL-maintained, explicitly warns about breaking changes).

Source: [Issue #112](https://github.com/lanl-ansi/PowerModels.jl/issues/112)

### DC OPF Transformer Phase Shift Bug (Issue #422)

Issue #422 reported that PowerModels' DC OPF ignored transformer phase shift parameters entirely -- changing the `shift` value produced identical results. The maintainer acknowledged this was a deliberate (but problematic) choice to match MATPOWER's behavior from 2016. The fix required converting transformer parameters to polar form and was addressed in subsequent releases.

This is relevant because DC OPF with phase shifters is fundamental to market operations (PJM, MISO, ERCOT all use DC OPF variants with phase shifter modeling).

Source: [Issue #422](https://github.com/lanl-ansi/PowerModels.jl/issues/422)

### PTDF and Lossy DC Formulations

PowerModels includes:
- `solve_opf_ptdf_branch_power_cuts` -- iterative PTDF-based OPF with lazy constraint generation
- `compute_dc_pf` -- computes voltage angles from bus injections (useful when formulation does not model angles, e.g., PTDF/LODF)
- A lossy DC power flow model based on injections

However, there is no built-in **LMP decomposition** (separating marginal prices into energy, congestion, and loss components) or **distributed slack bus** formulation. These would need to be implemented by the user via JuMP's dual variable access.

Source: [PowerModels utilities documentation](https://lanl-ansi.github.io/PowerModels.jl/stable/utilities/), [PowerModels power flow documentation](https://lanl-ansi.github.io/PowerModels.jl/stable/power-flow/)

### Security-Constrained OPF

SCOPF is handled by [PowerModelsSecurityConstrained.jl](https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl), a separate LANL package. Key details:

- Used as the **benchmark algorithm for ARPA-e GOC Challenge 1** (October 2019)
- Supports iterative cut-based and direct SCOPF formulations
- **Does not support** storage, dcline, or switch components
- The GOC competitions progressed through three challenges (basic SCOPF, multi-period with UC, AC unit commitment), with LANL providing benchmark algorithms for each

Source: [PowerModelsSecurityConstrained docs](https://lanl-ansi.github.io/PowerModelsSecurityConstrained.jl/stable/), [ARPA-e GOC benchmark report (OSTI)](https://www.osti.gov/biblio/1825378)

### Unit Commitment and Scheduling

PowerModels.jl has **no built-in unit commitment** capability. Related packages:

- **UnitCommitment.jl** (ANL-CEEESA, Argonne National Lab) -- dedicated SCUC solver with state-of-the-art MIP formulations, but a separate project, not a PowerModels extension
- **PowerSimulations.jl** (NREL-Sienna) -- operations simulation library that integrates with PowerModels.jl for network formulations. Provides multi-period UC, economic dispatch, and production cost modeling
- **GOC3Benchmark.jl** (LANL) -- AC unit commitment benchmark for GOC Challenge 3

Source: [UnitCommitment.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl), [PowerSimulations.jl paper](https://arxiv.org/html/2404.03074v1), [GOC3Benchmark.jl](https://github.com/lanl-ansi/GOC3Benchmark.jl)

### Ecosystem Packages

The PowerModels ecosystem is extensive. All are Julia/JuMP-based and share the InfrastructureModels.jl foundation:

| Package | Maintainer | Purpose |

|---------|-----------|---------|

| PowerModels.jl | LANL | Core transmission OPF |

| PowerModelsDistribution.jl | LANL | Unbalanced distribution networks |

| PowerModelsSecurityConstrained.jl | LANL | SCOPF |

| PowerModelsRestoration.jl | LANL | Power system restoration, N-k MLD |

| PowerModelsGMD.jl | LANL | Geomagnetic disturbance impacts |

| PowerModelsITD.jl | LANL | Integrated transmission-distribution |

| PowerModelsONM.jl | LANL | Distribution operations & microgrids |

| PowerModelsAnalytics.jl | LANL | Visualization and analysis |

| PowerModelsAnnex.jl | LANL | Experimental/exploratory methods |

| PowerModelsACDC.jl | KU Leuven (Electa) | AC/DC grids with converters |

| PowerModelsACDCsecurityconstrained.jl | CSIRO | SCOPF for AC/DC grids |

| StochasticPowerModels.jl | KU Leuven (Electa) | Stochastic OPF |

| PowerModelsProtection.jl | LANL | Fault studies |

| PowerModelsStability.jl | LANL | Small signal stability |

Source: [LANL-ANSI GitHub organization](https://github.com/lanl-ansi)

### Community Size and Indicators

| Metric | Value |

|--------|-------|

| GitHub stars | 456 |

| GitHub forks | 167 |

| Contributors | 29 |

| Open issues | 83 |

| Primary developer | Carleton Coffrin (LANL) |

| Original paper | PSCC 2018, widely cited (est. 300+ on Google Scholar) |

| Julia package downloads | Not publicly tracked in detail |

The project has a moderate-sized academic community. Most contributors are from LANL or affiliated research groups. The 83 open issues (as of early 2026) suggest some backlog, though many are feature requests rather than bugs.

Source: [GitHub repository](https://github.com/lanl-ansi/PowerModels.jl)

### Release History (Last 24 Months)

| Version | Date | Key Changes |

|---------|------|-------------|

| v0.21.5 | 2024-08-12 | Bug fixes: test relaxation for INFEASIBLE_POINT, silenced Memento logger during precompilation, chordal SDP bounds, shunt sign handling |

| v0.21.4 | 2024-05-20 | 17 PRs merged: PrecompileTools for reduced compilation latency, PSS/E export fixes, performance improvements for incidence matrix and connected components, bus type update logic |

| v0.21.3 | 2023-11-04 | CI updates, connected components fix for networks lacking active buses |

| v0.21.2 | 2023-07-05 | Performance improvements, in-place basic data format conversion, PSS/E three-winding transformer support |

| v0.21.1 | 2023-03-16 | Bug fix for theta delta bounds |

| v0.21.0 | 2023-01-19 | Major: JuMP new nonlinear interface |

Release cadence is approximately 2-4 releases per year, with the most recent (v0.21.5) from August 2024. The project remains on v0.x after 8+ years, which may indicate either caution about API stability guarantees or simply a convention choice.

Source: [GitHub releases](https://github.com/lanl-ansi/PowerModels.jl/releases)

### License and Dependency Licensing

- **PowerModels.jl**: BSD license (part of the MICOT project, LA-CC-15-024)
- **InfrastructureModels.jl**: BSD (LANL)
- **JuMP.jl**: MPL-2.0 (Mozilla Public License)
- **MathOptInterface.jl**: MIT
- **Ipopt**: EPL-2.0 (Eclipse Public License) -- note: links to MUMPS, HSL for linear solvers
- **HiGHS**: MIT
- **GLPK**: GPL-3.0 -- **potential license concern** for proprietary use
- **SCIP**: Apache-2.0 (as of SCIP 8.0)

The GLPK dependency (GPL-3.0) is notable: if included in a distributed application, GPL copyleft obligations apply. For evaluation purposes, GLPK is optional (HiGHS or Ipopt can be used instead).

Source: Manifest.toml analysis, respective GitHub repositories

### Dependency Tree

The project as configured in this evaluation has **114 total resolved dependencies** (including transitive) and **6 direct dependencies**: PowerModels v0.21.5, JuMP v1.29.4, Ipopt v1.14.1, HiGHS v1.21.1, GLPK v1.2.1, SCIP v0.11.6.

PowerModels' own direct dependencies are: InfrastructureModels, JSON, JuMP, LinearAlgebra, Memento, NLsolve, PrecompileTools, SparseArrays.

The dependency tree is large but largely composed of JLL (binary wrapper) packages for native solver libraries (Ipopt, HiGHS, SCIP, GLPK, MUMPS, METIS, etc.).

Source: `/evaluations/powermodels/Manifest.toml`, `/evaluations/powermodels/Project.toml`

### Documentation Quality

**Strengths:**
- Well-structured Documenter.jl-generated docs with separate manual, library reference, and developer sections
- Getting started guide with worked examples using `solve_opf`, `instantiate_model`, `parse_file`
- Mathematical model documentation explaining formulation details
- Network data format documentation for MATPOWER and PTI/PSS(R)E formats
- [Grid science tutorial notebook](https://github.com/lanl-ansi/tutorial-grid-science) for classroom/workshop use

**Weaknesses:**
- Limited end-to-end tutorials for non-trivial use cases (e.g., building custom problems, extracting duals/LMPs, working with multinetwork)
- No cookbook or recipes section for common tasks
- Extension packages have inconsistent documentation quality
- No explicit performance tuning guide for large-scale problems
- API reference is auto-generated from docstrings; some functions lack detailed descriptions

Source: [PowerModels documentation](https://lanl-ansi.github.io/PowerModels.jl/stable/), [Quick guide](https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/)

### Scalability and Performance

- Research papers demonstrate PowerModels on networks up to **30,000 buses** using the pglib-opf benchmark library
- Performance depends heavily on the chosen solver (Ipopt for NLP, HiGHS/Gurobi for LP/MIP) and formulation
- Julia's JIT compilation introduces a **5-15 second startup penalty** per invocation (mitigated by PrecompileTools in v0.21.4+ and by staying in the REPL)
- No built-in warm-starting across sequential solves (would need manual JuMP-level implementation)
- [ExaModelsPower.jl](https://arxiv.org/html/2510.12897v1) is a separate GPU-accelerated alternative for large-scale nonlinear OPF, suggesting PowerModels' CPU-only approach has scaling limits

Source: [PowerModels documentation](https://lanl-ansi.github.io/PowerModels.jl/stable/), [ExaModelsPower.jl paper](https://arxiv.org/html/2510.12897v1)

### Comparison to MATPOWER

| Aspect | PowerModels.jl | MATPOWER |

|--------|---------------|----------|

| Language | Julia | MATLAB/Octave |

| Formulations | 10+ (AC, DC, SOC, SDP, QC, PTDF, ...) | AC, DC, SOC (limited) |

| Solver flexibility | Any JuMP-compatible solver | MIPS, limited external |

| Data formats | MATPOWER .m, PTI .raw, JSON | MATPOWER .m |

| Extensibility | Julia type system, multiple dispatch | MATLAB function overloading |

| UC/SCUC | No (separate packages) | No (separate via MOST) |

| Community | Academic/research | Academic + industry legacy |

| License | BSD | BSD |

| Startup time | 5-15s (Julia JIT) | Instant (interpreted) |

PowerModels reads MATPOWER case files natively, making migration straightforward. The key advantage is formulation flexibility; the key disadvantage is Julia ecosystem friction (startup time, smaller user base, less industry tooling).

Source: [PowerModels README](https://github.com/lanl-ansi/PowerModels.jl), [MATPOWER](https://matpower.org)

### Operational Deployment Evidence

No evidence of direct operational deployment at utilities, ISOs, or RTOs was found. PowerModels.jl is:
- Used extensively in **academic research** (LANL, NREL, university groups)
- Used as **ARPA-e GOC Competition benchmark** (government research)
- Integrated into **PowerSimulations.jl** (NREL) for production cost modeling research
- Referenced by **pandapower** (Python) as an optional backend for OPF

The package documentation explicitly states it "cannot inherently be used to perform long-range simulation (representing months to years of operation) or solve sequences of operational problems," confirming its research orientation.

Source: [PowerSimulations.jl](https://arxiv.org/html/2404.03074v1), [pandapower docs](https://pandapower.readthedocs.io/en/v2.6.0/opf/powermodels.html)

## Sources

1. [PowerModels.jl GitHub repository](https://github.com/lanl-ansi/PowerModels.jl)
2. [PowerModels.jl documentation](https://lanl-ansi.github.io/PowerModels.jl/stable/)
3. [PowerModels.jl releases](https://github.com/lanl-ansi/PowerModels.jl/releases)
4. [Issue #112: Multi-period and stochastic OPF](https://github.com/lanl-ansi/PowerModels.jl/issues/112)
5. [Issue #422: Transformer angle shift in DC OPF](https://github.com/lanl-ansi/PowerModels.jl/issues/422)
6. [PowerModelsSecurityConstrained.jl](https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl)
7. [PowerModelsSecurityConstrained docs](https://lanl-ansi.github.io/PowerModelsSecurityConstrained.jl/stable/)
8. [StochasticPowerModels.jl](https://github.com/Electa-Git/StochasticPowerModels.jl)
9. [UnitCommitment.jl](https://github.com/ANL-CEEESA/UnitCommitment.jl)
10. [PowerSimulations.jl paper (arXiv)](https://arxiv.org/html/2404.03074v1)
11. [GOC3Benchmark.jl](https://github.com/lanl-ansi/GOC3Benchmark.jl)
12. [ARPA-e GOC benchmark report (OSTI)](https://www.osti.gov/biblio/1825378)
13. [Coffrin et al., "PowerModels.jl: An Open-Source Framework for Exploring Power Flow Formulations," PSCC 2018](https://ieeexplore.ieee.org/document/8442948/)
14. [ExaModelsPower.jl paper (arXiv)](https://arxiv.org/html/2510.12897v1)
15. [LANL-ANSI GitHub organization](https://github.com/lanl-ansi)
16. [pandapower PowerModels integration docs](https://pandapower.readthedocs.io/en/v2.6.0/opf/powermodels.html)
17. [PowerModels formulations documentation](https://lanl-ansi.github.io/PowerModels.jl/stable/formulations/)
18. [PowerModels network data documentation](https://lanl-ansi.github.io/PowerModels.jl/stable/network-data/)
19. [Grid science tutorial notebooks](https://github.com/lanl-ansi/tutorial-grid-science)
20. [Julia Discourse: PowerModels multinetwork for SCOPF](https://discourse.julialang.org/t/powermodels-jl-multinetwork-for-security-constrained-ac-opf/113511)
21. Local files: `evaluations/powermodels/Project.toml`, `evaluations/powermodels/Manifest.toml`

## Gaps and Uncertainties

- **Exact citation count**: Could not retrieve the precise Google Scholar citation count for the 2018 PSCC paper (estimated 300+ based on Semantic Scholar metadata patterns).
- **Issue breakdown**: The 83 open issues were not categorized (bugs vs. feature requests vs. questions). A manual review of the GitHub issues page would be needed.
- **Distributed slack implementation**: No issues or documentation explicitly discuss distributed slack bus modeling. It is unclear whether this can be achieved through the multinetwork/custom constraint mechanism without significant custom code.
- **LMP decomposition**: No evidence of built-in or community-contributed LMP decomposition (energy + congestion + loss components). Users would need to extract duals manually from JuMP and compute decomposition.
- **Production use**: No public evidence of utility/ISO operational deployment. Absence of evidence is not evidence of absence -- LANL may have government/industry partnerships not publicly documented.
- **Performance benchmarks**: No standardized wall-clock benchmarks comparing PowerModels to MATPOWER or commercial solvers on identical hardware for identical problems. The 30,000-bus claim comes from research papers, not reproducible benchmarks.
- **Stochastic programming maturity**: StochasticPowerModels.jl (the main stochastic extension) explicitly warns about breaking changes, suggesting pre-production maturity.
- **NREL Sienna ecosystem overlap**: The relationship between PowerModels.jl (LANL) and the NREL Sienna stack (PowerSystems.jl, PowerSimulations.jl, PowerFlows.jl) is collaborative but potentially competing. PowerSimulations.jl uses PowerModels formulations but has its own data model.
