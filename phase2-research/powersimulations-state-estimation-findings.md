# PowerSimulations.jl State Estimation Investigation

## Summary

PowerSimulations.jl and the broader NREL Sienna (formerly SIIP) ecosystem have **no state
estimation capabilities**. None of the 57 repositories in the NREL-Sienna GitHub organization
address state estimation. No GitHub issues mentioning state estimation exist across
PowerSimulations.jl, PowerSystems.jl, or PowerSimulationsDynamics.jl. No NREL publications
were found combining Sienna tools with state estimation.

State estimation in the Julia power systems world is handled by entirely separate ecosystems:
the PowerModels family (LANL/KU Leuven) and JuliaGrid.jl.

## Native SE Support

**None.** PowerSimulations.jl is scoped to power system *operations simulation* -- production
cost modeling, unit commitment, economic dispatch, and multi-stage scheduling. Its optimization
formulations are forward-looking decision problems (what should generators do?), not inverse
estimation problems (what is the current system state given measurements?).

The full Sienna package suite (57 repos) was enumerated via the GitHub API. Relevant packages
and their scope:

| Package | Scope | SE relevance |
|---------|-------|--------------|
| PowerSimulations.jl | Operations scheduling / PCM | None |
| PowerSimulationsDynamics.jl | Transient/dynamic simulation | None |
| PowerSystems.jl | Data model / system representation | None (data layer only) |
| PowerFlows.jl | Steady-state power flow solvers | None (solves known systems) |
| PowerNetworkMatrices.jl | Network matrix representations | None |
| PowerAnalytics.jl | Post-simulation analytics | None |
| HydroPowerSimulations.jl | Hydro unit modeling | None |
| StorageSystemsSimulations.jl | Storage modeling | None |
| PowerSystemsInvestments.jl | Capacity expansion | None |

## SIIP Ecosystem SE Packages

**None exist.** A targeted search of the NREL-Sienna GitHub organization for "state estimation"
returned zero matching repositories. No issues or PRs across the core repos mention state
estimation.

### Julia SE packages outside Sienna

Two Julia packages provide state estimation, but neither is part of the Sienna/SIIP ecosystem:

1. **PowerModelsDistributionStateEstimation.jl** (Electa-Git / KU Leuven)
   - Extension of PowerModelsDistribution.jl (LANL PowerModels family)
   - Supports WLS, WLAV, and maximum likelihood estimation
   - Distribution-network focused
   - No dependency on or integration with any NREL-Sienna package
   - Repository: https://github.com/Electa-Git/PowerModelsDistributionStateEstimation.jl

2. **JuliaGrid.jl** (mcosovic)
   - Standalone framework for power system state estimation
   - Nonlinear SE, PMU-based linear SE, and DC SE models
   - WLS with conventional, orthogonal, and Peters-Wilkinson methods
   - No connection to Sienna or PowerModels ecosystems
   - Repository: https://github.com/mcosovic/JuliaGrid.jl

## NREL Research Connections

No NREL publications were found that combine Sienna/SIIP tools with state estimation. The
primary PowerSimulations.jl publication (Lara et al., IEEE Trans. Power Systems, 2024;
arXiv:2404.03074) focuses exclusively on operations simulation and does not mention state
estimation.

NREL's Sienna development effort is oriented toward planning and operations optimization
(unit commitment, economic dispatch, capacity expansion, reliability assessment via PRAS),
not grid observability or measurement-based estimation.

## Sources

- [NREL-Sienna GitHub organization](https://github.com/NREL-Sienna) -- 57 repositories, none SE-related
- [PowerSimulations.jl repository](https://github.com/NREL-Sienna/PowerSimulations.jl)
- [PowerSimulations.jl paper (arXiv)](https://arxiv.org/html/2404.03074v1)
- [PowerModelsDistributionStateEstimation.jl](https://github.com/Electa-Git/PowerModelsDistributionStateEstimation.jl)
- [JuliaGrid.jl (arXiv paper)](https://arxiv.org/html/2502.18229v1)
- [JuliaGrid.jl documentation](https://mcosovic.github.io/JuliaGrid.jl/stable/)
- [NREL-Sienna Julia packages listing](https://juliapackages.com/u/nrel-sienna)
