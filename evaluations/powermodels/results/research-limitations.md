# powermodels — Research: Limitations & Ecosystem

## Key Findings

- PowerModels.jl is a single-developer-dominated project: @ccoffrin has 831 of 1,014 commits (82%), with no other contributor above 45 commits. This creates a significant bus-factor risk.
- As of March 2026, the repo has 457 stars, 167 forks, and 87 open issues — modest for a tool positioned as a research framework for power system optimization.
- The package is **research-oriented, single-period OPF only** by design: no unit commitment, no SCUC, no contingency analysis, no multi-period dispatch beyond the manual multi-network replication API.
- Multi-period support exists only through manual `replicate()` + patch-per-timestep workflow; there is no built-in rolling horizon, look-ahead OPF, or BESS cycling dispatch problem.
- The `solve_pf()` function does **not** work with `LPACCPowerModel` (open issue #891, filed Oct 2023, still unresolved as of March 2026).
- The `DCPLL` formulation silently falls back to DCP when used with power flow problems instead of raising an error (open issue #873, filed Aug 2023, unresolved).
- Generators in PQ-type buses are not allowed in power flow (`@assert false` in code), a limitation with no workaround documented (open issue #989, filed Nov 2025).
- PSS/E (PTI) parser has at least 8 open issues dating back to 2020, covering v34 format support, incorrect active-generator bus handling, VSC data, and tolerance for malformed fields. PSS/E support should be considered fragile.
- The ecosystem of extension packages (security-constrained, restoration, distribution, etc.) provides broader coverage but each is a separate package with its own maintenance state; PowerModelsSecurityConstrained.jl explicitly does not support `storage`, `dcline`, or `switch` components.
- Recent commit activity (late 2025 – early 2026) is dominated by dependency bumps and CI updates, not new features — the core package appears to be in maintenance mode.

## Detailed Notes

### Problem Scope and Missing Capabilities

PowerModels is explicitly scoped to **steady-state single-period OPF and power flow** variants. The math-model documentation confirms unit commitment and multi-period problems are out of scope for the core package.

Supported problem types in core PowerModels v0.21:
- AC OPF (polar: ACPPowerModel, rectangular: ACRPowerModel, IVRPowerModel)
- DC OPF (DCPPowerModel, DCMPPowerModel, BFAPowerModel, NFAPowerModel)
- Quadratic approximations (LPACCPowerModel, DCPLLPowerModel)
- SOC/SDP relaxations (SOCWRPowerModel, SOCBFPowerModel, SDPWRMPowerModel, SparseSDPWRMPowerModel, QCRMPowerModel, QCLSPowerModel)
- Transmission network expansion planning (TNEP)
- Optimal transmission switching (OTS)
- Power flow (PF) — but with known gaps (see bugs below)
- Multi-network co-optimization via `solve_mn_opf` (manual setup required)

Not present in core:
- Security-constrained unit commitment (SCUC) — requires PowerModelsSecurityConstrained.jl
- Unit commitment / generation scheduling
- Multi-period economic dispatch
- Contingency analysis (N-1, N-k)
- BESS arbitrage or cycling dispatch as a built-in problem type
- Rolling horizon OPF
- Probabilistic / stochastic OPF (separate StochasticPowerModels.jl)

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/formulation-details/> and <https://lanl-ansi.github.io/PowerModels.jl/stable/math-model/>

### Known Bugs and Open Issues (Evaluation-Relevant)

**Issue #989** — Generators in PQ buses not allowed (filed Nov 2025, unresolved)
`solve_pf()` hits `@assert false` when any generator is on a PQ bus. Affects real-world networks where load buses have distributed generation.
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/989>

**Issue #891** — `solve_pf()` does not work with `LPACCPowerModel` (filed Oct 2023, unresolved)
Raises `MethodError: no method matching expression_branch_power_ohms_yt_from(::LPACCPowerModel, ...)`. A full traceback is in the issue; the formulation is partially implemented for OPF but the PF dispatch is missing.
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/891>

**Issue #873** — DCPLL silently falls back to DCP for power flow (filed Aug 2023, unresolved)
No error is raised; users may not realize they are running a different formulation.
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/873>

**Issue #932** — Incorrect behavior for PSSE active generators at load buses (filed Oct 2024, related fix PR #934 still open)
Generator bus voltage set incorrectly when generator is on a load-type bus in PTI files.
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/932>

**Issue #921** — No support for PSS/E RAW format version 34 (filed Jul 2024, unresolved)
Only PSS/E v33 is officially supported. Many utilities use v33 or v34.
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/921>

**Issue #890** — Problems with non-Float64 types (filed Sep 2023, unresolved)
Cannot use alternative numeric types (ForwardDiff, Dual numbers for sensitivity analysis).
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/890>

**Issue #770** — Parallel power flow computations not supported (filed Mar 2021, unresolved)
Multi-threading is not implemented for batch power flow jobs.
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/770>

**Issue #703** — Switch support for power flow problems (filed Apr 2020, unresolved)
Switches are modeled for OPF but not for PF problem specifications.
Source: <https://github.com/lanl-ansi/PowerModels.jl/issues/703>

### PSS/E Parser Fragility

At least 8 open issues target the PTI/PSS/E parser (label: "File format: PSSE/PTI"):
- #932, #921, #918, #897, #893, #888, #856, #843, #842, #794, #749, #737

Issues range from blank field handling to VSC data, transformer angle offsets >60°, and v34 format support. The parser is described as following PSS/E v33 specification; deviations in real-world files frequently cause parse failures or silent data errors.

### Multi-Period and Storage Limitations

Multi-period OPF is possible via `PowerModels.replicate(data, n)` which clones the single network n times into a multi-network dict; the caller must manually set per-period parameters (load profiles, etc.) before calling `solve_mn_opf`. There is no built-in time-series loading, rolling horizon, or period-linking constraint set for BESS state-of-charge across an arbitrary horizon.

The storage model documents a complementarity constraint `sc_t * sd_t = 0` (no simultaneous charge/discharge), which is a continuous relaxation — the constraint can be violated by interior-point solvers, requiring either a binary variable or a penalty term for strict enforcement. The documentation acknowledges this: "the standard storage model does not use binary variables to prevent simultaneous charging and discharging."
Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/storage/>

### Ecosystem and Dependency Tree

#### Core dependencies (from Project.toml, v0.21):
- JuMP v1 — modeling layer
- Ipopt v1 — nonlinear solver (NLP)
- GLPK v1 — LP/MIP solver
- HiGHS v1 — LP/MIP solver
- SCIP v0.11 — MIP solver
- InfrastructureModels — shared LANL data model library (implicit transitive dep)

All solvers are open-source. For large-scale problems, commercial solvers (Gurobi, CPLEX, MOSEK for SDP) are typically required but are not bundled.

#### First-party extension packages (all LANL-hosted):

| Package | Stars | Description | Last release |
|---|---|---|---|
| PowerModelsDistribution.jl | 156 | Unbalanced distribution networks | Active |
| PowerModelsSecurityConstrained.jl | 41 | SCUC; excludes storage/dcline/switch | v0.12.0 Jan 2024 |
| PowerModelsADA.jl | 37 | Distributed OPF algorithms | Active |
| PowerModelsRestoration.jl | 27 | N-k restoration / MLD | v0.9.0 Jan 2024 |
| PowerModelsAnnex.jl | 25 | Exploratory extensions | Active |
| PowerModelsONM.jl | 20 | Distribution feeder restoration | Active |
| PowerModelsITD.jl | 15 | Integrated T&D optimization | Active |
| PowerModelsGMD.jl | 12 | Geomagnetic disturbance | Active |
| PowerModelsProtection.jl | 10 | Fault study formulations | Active |
| PowerModelsStability.jl | 3 | Stability-constrained PF | Active |

#### Third-party notable:
- PandaModels.jl (13 stars) — bridge from pandapower networks to PowerModels
- StochasticPowerModels.jl (24 stars) — stochastic OPF extension
- PowerModelsDistributionStateEstimation.jl (39 stars) — state estimation for distribution

Source: GitHub API search, March 2026

### Community Size and Activity

- **Stars**: 457 (modest for a 10-year-old research framework)
- **Forks**: 167
- **Open issues**: 87 (several dating back to 2016–2018 with no resolution)
- **Total commits**: 1,014 on master
- **Contributors**: 27 named; @ccoffrin accounts for 831 commits (82%)
- **Second-most active**: @pseudocubic (45), @jd-lara (34), @odow (22)
- **Institutional backing**: Los Alamos National Laboratory (LANL); funded partly through DOE Grid Optimization Competition
- **Discourse**: No dedicated forum; users post on Julia Discourse and GitHub issues

The high concentration of commits in one person represents meaningful key-person risk. The project's pace has slowed noticeably: recent commits (Dec 2025 – Mar 2026) are CI dependency bumps only.

Source: GitHub API, <https://github.com/lanl-ansi/PowerModels.jl>

### Release History and Changelog Quality

| Release | Date | Notes |
|---|---|---|
| v0.21.5 | 2025-08-12 | Relax test conditions, silence logger during precompile |
| v0.21.4 | 2025-05-20 | Numerical fixes in PF, syntax fix in export |
| v0.21.3 | 2024-11-04 | Bug fixes |
| v0.21.2 | 2024-07-05 | Bug fixes |
| v0.21.1 | 2024-03-16 | Bug fixes |
| v0.21.0 | 2024-01-19 | Breaking: new JuMP nonlinear interface |
| v0.20.1 | 2024-01-10 | Bug fixes |
| v0.20.0 | 2024-01-02 | Breaking: two-sided constraints, cost function rewrite, dropped multi-conductor |
| v0.19.10 | 2024-01-01 | Maintenance |
| v0.19.9 | 2023-05-28 | Maintenance |

**Changelog quality**: The CHANGELOG.md exists and is structured, but entries at the patch level are sparse (e.g., "relax test conditions"). Major breaking changes in v0.20 and v0.21 are documented. No pre-release (alpha/beta/RC) process is used.

There have been 80 total releases since 2016. Release cadence is irregular: 5 releases in 2024, 2 in 2025.

Source: GitHub API releases endpoint, CHANGELOG.md

### Documentation Quality

The official docs at <https://lanl-ansi.github.io/PowerModels.jl/stable/> are generated by Documenter.jl and include:
- Manual: network data formats, result structures, math model, storage, switches, multi-network, utilities
- Library: API reference for formulations, problem specs, variables, constraints
- Developer: naming conventions only (not a full extension guide)
- Experiment results: benchmark tables for OPF across PGLib-OPF cases

#### Gaps and weaknesses:
- No troubleshooting guide
- No real-world deployment examples or case studies
- Developer documentation is a style guide, not an architecture guide — adding new formulations requires reading source code
- `solve_pf()` API is not well-documented relative to `solve_opf()`
- Multi-network workflow lacks worked examples showing BESS multi-period dispatch
- Docs do not surface known bugs (issue #891, #873) as warnings

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/>

### Deployment Evidence

PowerModels is primarily used in academic and national-laboratory research. Evidence of production utility/ISO deployment is sparse:
- DOE Grid Optimization (GO) Competition used PowerModels-based solvers (PowerModelsSecurityConstrained.jl was specifically developed for the competition)
- LANL internal use implied by commit history
- No public evidence of use by commercial ISO/RTO operators or energy trading firms

### License

BSD 3-Clause ("Other" per GitHub API, but text confirms BSD). Permissive for commercial and research use. All first-party extension packages share the same license.

Source: <https://github.com/lanl-ansi/PowerModels.jl>

## Sources

1. <https://github.com/lanl-ansi/PowerModels.jl> — Main repository
2. <https://lanl-ansi.github.io/PowerModels.jl/stable/> — Official documentation
3. <https://lanl-ansi.github.io/PowerModels.jl/stable/formulation-details/> — Formulation list
4. <https://lanl-ansi.github.io/PowerModels.jl/stable/math-model/> — Mathematical model scope
5. <https://lanl-ansi.github.io/PowerModels.jl/stable/storage/> — Storage model and limitations
6. <https://lanl-ansi.github.io/PowerModels.jl/stable/multi-networks/> — Multi-network API
7. <https://lanl-ansi.github.io/PowerModels.jl/stable/network-data/> — Supported data formats
8. <https://lanl-ansi.github.io/PowerModels.jl/stable/experiment-results/> — Benchmark tables
9. <https://github.com/lanl-ansi/PowerModels.jl/issues/989> — Generators in PQ buses bug
10. <https://github.com/lanl-ansi/PowerModels.jl/issues/891> — solve_pf LPACCPowerModel bug
11. <https://github.com/lanl-ansi/PowerModels.jl/issues/873> — DCPLL silent fallback
12. <https://github.com/lanl-ansi/PowerModels.jl/issues/932> — PSSE generator at load bus
13. <https://github.com/lanl-ansi/PowerModels.jl/issues/921> — PSS/E v34 support missing
14. <https://github.com/lanl-ansi/PowerModelsSecurityConstrained.jl> — SCUC extension
15. <https://github.com/lanl-ansi/PowerModelsRestoration.jl> — Restoration extension
16. GitHub API: repos/lanl-ansi/PowerModels.jl (stars, forks, releases, contributors)
17. /home/joe/code/zge-workspace/grc-tech-evaluation/evaluations/powermodels/Project.toml — local version pin (v0.21)

## Gaps and Uncertainties

- **Solver compatibility matrix**: It is unclear which formulations (especially SDP variants) require commercial solvers to solve problems of useful size. The benchmark results use HSL ma57 (restricted license, not open-source), not the open-source solvers bundled in Project.toml.
- **Actual multi-period BESS dispatch**: It is unverified whether the `solve_mn_opf` path correctly enforces BESS state-of-charge continuity across timesteps when replicated networks are used, or whether that coupling must be added manually by the user.
- **Simultaneous charge/discharge in practice**: Whether the continuous complementarity constraint `sc_t * sd_t = 0` is enforced tightly enough by Ipopt/HiGHS in practice (vs. requiring explicit binary variables) needs empirical testing.
- **PSS/E v33 vs. v34 gap impact**: The actual severity of PSS/E parsing failures on industry-standard case files (beyond the test cases) is unknown without testing against real utility data.
- **PowerModelsSecurityConstrained.jl maintenance**: v0.12.0 was released Jan 2024 and the last commit was Oct 2025; unclear if it tracks v0.21 of the core package without issues.
- **Performance on large networks (>10k buses)**: Benchmark data covers up to 13,659 buses with QC formulations taking 23–262 seconds (excluding JIT). Behavior at 30k+ buses is not documented.
- **Windows/cross-platform reliability**: Issue #830 (Pluto.jl stream error) and issue #842 (PSSE parser blank field) suggest some platform-specific behavior that was not reproduced on Linux in the benchmarks.
