# PowerModels.jl Evaluation

[PowerModels.jl](https://lanl-ansi.github.io/PowerModels.jl/) — Julia/JuMP
package for power network optimization. Developed by Los Alamos National
Laboratory (LANL-ANSI group).

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

PowerModels natively reads MATPOWER `.m` files:

```julia
using PowerModels
data = PowerModels.parse_file("../../data/networks/case39.m")
```

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
