# PowerSimulations.jl — Research: Limitations & Ecosystem

## Key Findings

- **No built-in SCOPF**: Security-constrained OPF is an open feature request since March 2023 ([#944](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/944)), with zero comments. Test A-9 will require manual contingency constraint assembly or a workaround via B-1's custom constraint API.
- **No built-in loss approximation for PTDF models**: Open issue [#1537](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1537) explicitly states "Add losses approximations to PTDF models" is planned but requires LHS parameter implementation. Test A-10 (lossy DCOPF with LMP decomposition) may be difficult or impossible.
- **No documented distributed slack formulation**: The network formulation library documents CopperPlate, AreaBalance, PTDF, and AreaPTDF models but makes no mention of distributed slack. Test A-11 will likely require a workaround.
- **Active bugs affect evaluation tests**: Ramp-down inequality may be flipped ([#1530](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1530)), DC power flow initialization bug with renewables ([#1545](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1545)), renewable natural-unit profiles treated as scaling factors ([#1557](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1557)).
- **Very active development**: 1021 commits in last 12 months, 21 releases in last 24 months, but dominated by a single lead developer (jd-lara: ~70% of all-time commits).
- **Large dependency footprint**: 80+ resolved packages in Manifest.toml (1186 lines), including MKL, HDF5, SQLite — far heavier than PowerModels.jl for equivalent tasks.
- **Fragile cross-package compat bounds**: The Sienna ecosystem (5+ tightly coupled packages) requires careful version archaeology to get a satisfiable dependency resolution. Multiple packages pinned below latest.
- **BSD-3-Clause across all Sienna packages**: Permissive licensing with no copyleft concerns.
- **NREL institutional backing**: Federally funded via DOE/NREL with named PI (Clayton Barrows) and development lead (José Daniel Lara). Durable funding but bus-factor risk is high.
- **Post-contingency evaluation is an open issue** ([#1522](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1522)) — no body/description, just a title.

## Detailed Notes

### Known Limitations Relevant to Evaluation Tests

#### SCOPF (Test A-9)
SCOPF has been an open feature request since 2023-03-14 ([#944](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/944)). The issue requests "N-1 (N-k) security constrained optimal power flow (unit commitment, economic dispatch) with PTDF formulation against branch and generator contingencies." It has zero comments and remains unimplemented. The evaluation test A-9 requires DC OPF with N-1 contingency constraints embedded in the optimization. This will need to be accomplished via manual constraint addition using JuMP's API (B-1 custom constraint approach), which is a significant workaround.

#### Lossy DCOPF / LMP Decomposition (Test A-10)
Issue [#1537](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1537) ("Add losses approximations to PTDF models") is open and explicitly states the feature "will require the implementation of LHS parameters" — a prerequisite that is itself an open feature request ([#1150](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1150)). Loss-inclusive LMPs and decomposition may not be achievable without substantial custom formulation work.

#### Distributed Slack (Test A-11)
The documented network formulations (CopperPlatePowerModel, AreaBalancePowerModel, PTDFPowerModel, AreaPTDFPowerModel, plus PowerModels.jl formulations) do not include a distributed slack option. The AreaBalancePowerModel could potentially approximate this behavior but is not equivalent. This test may require a custom formulation.

#### Ramp-Down Constraint Bug (Tests A-5, A-6)
Issue [#1530](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1530) reports that ramp-down constraints may have a flipped inequality sign in `rateofchange_constraints.jl`. The reporter notes "I'm not seeing any tests at all for ramp limits." This could affect SCUC (A-5) and SCED (A-6) results where ramp enforcement is a pass condition.

#### DC Power Flow Initialization Bug (Tests A-1, A-3)
Issue [#1545](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1545) describes a bug where bus active power injections/withdrawals are non-zero (should be zero) when renewables use FixedOutput formulation in the power-flow-in-the-loop simulation context. This affects combined optimization + power flow workflows.

#### Renewable Profile Scaling Bug
Issue [#1557](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1557) reports that renewable profiles defined in natural units (MW) are treated as scaling factors, multiplying by rated capacity and producing values 10x too high. This could affect any test involving renewable dispatch (A-12 multi-period with renewables).

### Open Issues Summary (as of 2026-03-13)

**66 open issues total**. Breakdown by label:
- **Code bugs (open):** 8 — including DC PF init (#1545), renewable scaling (#1557), startup time data (#1558), emulation results (#1474, #1554), MarketBidCost loads (#1299), NonSpinningReserve (#1173), docstring build (#1246)
- **Feature requests (open):** 9 — SCOPF (#944), ShiftablePowerLoad (#1491), storage outages in SCUC (#1461), matrix/reduction interface (#1452), ComponentSelector filter (#1152), RHS parameter (#1150), MOF deserialization (#722), hurdle rates (#1339), device simulation docs (#1353)
- **Documentation (open):** 10 — HVDCTwoTerminalLCC (#1533), invalid RenewableNonDispatch configs (#1357), device simulation extensions (#1353), slack explanation (#1338), 2T HVDC docs (#1277), forced outages docs (#1266), FunctionData corrections (#1262), performance guide (#1252), large simulation guide (#1213), doc reorganization (#1165)

### Ecosystem Packages

The NREL-Sienna GitHub organization contains 50+ repositories. Core packages and their metrics:

| Package | Stars | Forks | Open Issues | License | Last Push |
|---------|-------|-------|-------------|---------|-----------|
| PowerSystems.jl | 359 | 101 | 63 | BSD-3 | 2026-03-11 |
| PowerSimulations.jl | 311 | 78 | 66 | BSD-3 | 2026-03-07 |
| PowerSimulationsDynamics.jl | 215 | — | — | BSD-3 | 2026-02-25 |
| InfrastructureSystems.jl | 41 | 40 | 29 | BSD-3 | 2026-03-11 |
| PowerGraphics.jl | 33 | — | — | BSD-3 | 2026-03-06 |
| PowerFlows.jl | 29 | 23 | 42 | BSD-3 | 2026-03-13 |
| PowerNetworkMatrices.jl | 28 | 20 | 44 | BSD-3 | 2026-03-13 |
| PowerSystemsInvestments.jl | 21 | — | — | BSD-3 | 2026-01-13 |

**Extension packages** (domain-specific formulations):
- StorageSystemsSimulations.jl (7 stars) — battery/storage models
- HydroPowerSimulations.jl (12 stars) — hydro dispatch/commitment
- HybridSystemsSimulations.jl (6 stars) — hybrid resource models
- SiennaPRASInterface.jl (5 stars) — probabilistic reliability
- PowerSystemsInvestmentsPortfolios.jl (14 stars) — capacity expansion

**Sienna branding**: Three application layers:
1. **Sienna\Data** — PowerSystems.jl + InfrastructureSystems.jl (data model, time series)
2. **Sienna\Ops** — PowerSimulations.jl (scheduling, dispatch, production cost modeling)
3. **Sienna\Dyn** — PowerSimulationsDynamics.jl (transient/small-signal stability)

### Community Size

- **311 stars / 78 forks** on PowerSimulations.jl (moderate for a Julia power systems package)
- **359 stars / 101 forks** on PowerSystems.jl (the data model layer)
- Compare to PowerModels.jl: ~400 stars, broader community adoption
- Slack channel exists for community support (mentioned on Sienna landing page)
- No Discourse or dedicated forum

### Contributor Concentration

**All-time top contributors:**

| Contributor | Commits | % of Total (~10,463) |
|-------------|---------|---------------------|
| jd-lara | 7,537 | 72% |
| sourabhdalvi | 680 | 6.5% |
| claytonpbarrows | 577 | 5.5% |
| rodrigomha | 513 | 4.9% |
| daniel-thom | 401 | 3.8% |

**Last 12 months (pages 1-2 sample, 200 commits):**

| Contributor | Commits (sample) |
|-------------|-----------------|
| jd-lara | ~91 |
| luke-kiernan | ~41 |
| rodrigomha | ~20 |
| m-bossart | ~18 |
| kdayday | ~9 |
| GabrielKS | ~9 |
| Copilot (AI) | ~9 |

**Bus factor: 1.** jd-lara accounts for 72% of all-time commits and remains the dominant contributor. The project is heavily dependent on a single developer at NREL.

### Documentation Quality

**Structure**: Follows Diataxis framework (Tutorials, How-To, Explanation, Reference). Well-organized.

**Coverage gaps (from open issues):**
- 10 open documentation issues
- No documentation for HVDC LCC models (#1533)
- Invalid configuration examples listed as valid (#1357)
- FunctionData section has known errors (#1262)
- No performance best practices guide (#1252)
- No guide for large-scale simulation setup (#1213)
- Forced outage capability undocumented (#1266)
- Overall doc reorganization needed (#1165)

**Formulation library**: Documents General, Network, Thermal, Renewable, Load, Branch, Source, Services, Feedforwards, and Piecewise Linear Cost formulations. Good tabular format with constraints and variables listed.

**What's NOT documented**: SCOPF, loss approximations, distributed slack, contingency analysis, dynamic line ratings (DLR — under active development per #1559 but not yet documented).

**Multi-package cognitive overhead**: Users must know which package provides which type (e.g., `DCPowerFlow()` from PowerNetworkMatrices, `System()` from PowerSystems, `solve_powerflow!()` from PowerFlows).

### Release History

**21 releases in last 24 months** (since 2024-03-13):

| Version | Date | Notes |
|---------|------|-------|
| v0.33.1 | 2026-02-24 | Latest |
| v0.33.0 | 2026-02-18 | |
| v0.32.4 | 2025-12-18 | |
| v0.32.3 | 2025-12-13 | |
| v0.32.2 | 2025-12-10 | |
| v0.32.1 | 2025-12-09 | |
| v0.32.0 | 2025-12-08 | |
| v0.31.0 | 2025-11-11 | |
| v0.30.2 | 2025-06-09 | (Version in our Manifest) |
| v0.30.1 | 2025-02-27 | |
| v0.30.0 | 2025-02-06 | |
| v0.29.2 | 2025-01-13 | |
| v0.29.1 | 2024-12-26 | |
| v0.29.0 | 2024-12-12 | |
| v0.28.3 | 2024-07-24 | |

**Cadence**: Approximately monthly releases. Frequent patch releases (4 patches for v0.32 in 10 days) suggest instability at minor version boundaries. Semver used but still pre-1.0 (no stability guarantees).

**Note**: Our evaluation environment has v0.30.2 pinned, which is 5 minor versions behind v0.33.1. The compat bounds (`PowerSimulations = "0.27 - 0.33"`) should allow upgrading.

### CI and Testing

**CI workflows (GitHub Actions):**
- Main - CI (active)
- Test-CI (active)
- CrossPackageTest (active) — tests compatibility with other Sienna packages
- Format Check (active)
- Documentation (active)
- Performance Comparison (active)
- Copilot code review + coding agent (active)

CI infrastructure is comprehensive. CrossPackageTest is notable — it tests the full Sienna stack integration.

### Institutional Backing

- **Primary institution**: National Renewable Energy Laboratory (NREL), U.S. Department of Energy
- **PI**: Clayton Barrows, Ph.D. — Group Manager at NREL
- **Development lead**: José Daniel Lara — Senior Researcher at NREL
- **Funding model**: Federal (DOE) research funding. Durable as long as NREL's grid modeling program continues, but subject to federal budget cycles and administration priorities.
- **First Principles Advisory** mentioned as an industry adopter on the Sienna landing page, but no specific utility/ISO deployment evidence found.

### Dependency and Supply Chain

**Direct dependencies in our Project.toml**: 10 packages (PowerSimulations, PowerSystems, PowerFlows, PowerNetworkMatrices, InfrastructureSystems, JuMP, HiGHS, GLPK, Ipopt, SCIP)

**Resolved dependency count**: ~80+ packages in Manifest.toml (1186 lines), including:
- Heavy numerical libraries: MKL, HDF5, BLAS
- Data infrastructure: SQLite, CSV, DataFrames
- Serialization: JSON3, YAML
- Solver interfaces: MathOptInterface, JuMP

**License audit**: All Sienna packages are BSD-3-Clause. JuMP ecosystem is MIT/BSD. Solvers (HiGHS, GLPK, Ipopt, SCIP) are open-source (MIT, GPL for GLPK, EPL for Ipopt). GLPK is GPL-3.0 — potential copyleft concern if linking applies.

**Compat pin issues**: Multiple packages restricted by compat constraints (marked with ⌅ by Pkg resolver). The ecosystem does not keep pace with its own dependency upgrades.

## Sources

1. GitHub: [NREL-Sienna/PowerSimulations.jl](https://github.com/NREL-Sienna/PowerSimulations.jl) — repo metadata, issues, releases, contributors
2. GitHub: [NREL-Sienna/PowerSystems.jl](https://github.com/NREL-Sienna/PowerSystems.jl)
3. GitHub: [NREL-Sienna/PowerNetworkMatrices.jl](https://github.com/NREL-Sienna/PowerNetworkMatrices.jl)
4. GitHub: [NREL-Sienna/InfrastructureSystems.jl](https://github.com/NREL-Sienna/InfrastructureSystems.jl)
5. GitHub: [NREL-Sienna/PowerFlows.jl](https://github.com/NREL-Sienna/PowerFlows.jl)
6. PowerSimulations.jl documentation: https://nrel-sienna.github.io/PowerSimulations.jl/stable/
7. Sienna landing page: https://nrel-sienna.github.io/Sienna/
8. Issue [#944](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/944) — SCOPF feature request (open since 2023-03)
9. Issue [#1537](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1537) — Losses in PTDF models
10. Issue [#1530](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1530) — Ramp-down inequality flipped
11. Issue [#1545](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1545) — DC PF initialization bug
12. Issue [#1557](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1557) — Renewable scaling bug
13. Issue [#1522](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1522) — Post contingency evaluation
14. Issue [#1559](https://github.com/NREL-Sienna/PowerSimulations.jl/issues/1559) — Dynamic Line Ratings PR
15. Local file: `evaluations/powersimulations/notes/install-findings.md`
16. Local file: `evaluations/powersimulations/Project.toml`
17. Local file: `evaluations/powersimulations/Manifest.toml`

## Gaps and Uncertainties

- **SCOPF workaround feasibility**: Unclear how difficult it is to manually add N-1 contingency constraints via JuMP. Need to test during A-9 / B-1.
- **Lossy DCOPF**: May be achievable via PowerModels.jl's DCPLLPowerModel formulation (documented as available through the PowerModels integration) — needs testing.
- **Distributed slack**: AreaBalancePowerModel might approximate distributed slack with single-bus areas, but this is speculation — needs testing.
- **Ramp-down bug severity**: Reporter says "I don't have code that triggers the bug right now." May not affect our test configurations if they use ThermalGen with AbstractThermalDispatch (which is excluded from the bug scope).
- **v0.30.2 vs v0.33.1**: Our pinned version is 5 minor versions behind. Some bugs may be fixed in newer versions, but upgrading risks breaking the dependency resolution that was already difficult.
- **Operational deployment evidence**: Only one industry reference (First Principles Advisory) found. No utility or ISO deployment evidence. No published case studies with real-world production use. NREL internal use for research is the primary use case.
- **PSS/E RAW parsing**: PowerFlowFileParser.jl exists in the NREL-Sienna org (pushed 2026-03-10) but its capabilities and maturity are unknown — needs investigation for P2-1.
- **Academic citation count**: Google Scholar search did not return results (page rendering issue). Citation impact is unknown.
- **GLPK GPL-3.0 license**: Whether Julia's JLL wrapper for GLPK triggers copyleft obligations needs legal review for F-3.
- **Air-gap installability**: Julia's package manager supports offline registries, but the 80+ dependency footprint makes air-gap bundling non-trivial. Needs testing for F-7.
