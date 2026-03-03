# PowerSimulations.jl Evaluation

[PowerSimulations.jl](https://nrel-sienna.github.io/PowerSimulations.jl/) —
part of NREL's Sienna ecosystem for power systems modeling and simulation.
Provides production cost modeling, unit commitment, and economic dispatch.

## Setup

```bash
julia --project=. -e 'using Pkg; Pkg.instantiate()'
```

Requires Julia 1.10+. No additional system dependencies — all solvers
(HiGHS, Ipopt, GLPK, SCIP) are installed as Julia packages.

## Verify Installation

```bash
julia --project=. verify_install.jl
```

## Data Loading

PowerSystems.jl (the data layer) reads MATPOWER `.m` files:

```julia
using PowerSystems
sys = System("../../data/networks/case39.m")
```

## Related Packages

The Sienna ecosystem evaluated here includes:

- **PowerSystems.jl** — data model and I/O
- **PowerSimulations.jl** — optimization formulations (UC, ED)
- **PowerFlows.jl** — power flow solvers
- **PowerNetworkMatrices.jl** — network matrix computations (PTDF, LODF)
- **InfrastructureSystems.jl** — base infrastructure types

## Results

Test outputs are organized by rubric dimension:

```
results/
├── gate/            # Pass/fail gate criteria
├── expressiveness/  # Modeling capability tests
├── extensibility/   # Custom component and integration tests
├── scalability/     # Performance benchmarks
├── accessibility/   # Documentation and API quality
├── maturity/        # Community and maintenance metrics
└── supply_chain/    # Dependency and license analysis
```
