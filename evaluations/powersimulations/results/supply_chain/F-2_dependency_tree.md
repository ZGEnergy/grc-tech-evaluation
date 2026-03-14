---
test_id: F-2
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "8b638f83"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: 2026-03-14T00:00:00Z
---

# F-2: Dependency Tree

## Result: INFORMATIONAL

## Finding

The PowerSimulations.jl project (as configured in our evaluation environment with four solvers) resolves to 184 total packages: 15 direct dependencies and 169 transitive. The tree is deep due to solver bindings (JLL wrappers for native C/C++ libraries) and the JuMP optimization stack. Several packages are pinned below latest due to compatibility constraints (marked with the `⌅` indicator by Pkg).

## Evidence

### Summary

| Metric | Value |
|--------|-------|
| Total resolved packages | 184 |
| Direct dependencies | 15 |
| Transitive dependencies | 169 |
| Packages with newer version available (⌃) | 7 |
| Packages constrained below latest (⌅) | 15 |
| Julia stdlib packages included | ~30 |
| JLL (binary wrapper) packages | ~30 |

### Direct Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PowerSimulations | v0.30.2 | Core evaluation target |
| PowerSystems | v4.6.2 | Power system data model |
| PowerFlows | v0.9.0 | Power flow calculations |
| PowerNetworkMatrices | v0.12.1 | Network matrix computations |
| InfrastructureSystems | v2.6.0 | Shared infrastructure layer |
| JuMP | v1.29.4 | Mathematical optimization modeling |
| HiGHS | v1.21.1 | LP/MIP solver (open-source) |
| Ipopt | v1.14.1 | Nonlinear optimization solver |
| GLPK | v1.2.1 | LP/MIP solver (GNU) |
| SCIP | v0.12.8 | Constraint integer programming solver |
| DataFrames | v1.8.1 | Tabular data manipulation |
| CSV | v0.10.16 | CSV file I/O |
| JSON | v0.21.4 | JSON serialization |
| TimeSeries | v0.24.2 | Time series data structures |
| Combinatorics | v1.1.0 | Combinatorial utilities |

### Key Transitive Dependencies

| Package | Version | Role |
|---------|---------|------|
| MathOptInterface | v1.49.0 | Solver abstraction layer (JuMP backend) |
| InfrastructureModels | v0.7.8 | Shared infrastructure for LANL power packages |
| PowerModels | v0.21.5 | Power network optimization models |
| PowerFlowData | v1.5.0 | Power flow data parsing |
| MutableArithmetics | v1.6.7 | Performance optimization for JuMP |
| ForwardDiff | v1.3.2 | Automatic differentiation |
| NLsolve | v4.5.1 | Nonlinear equation solving |
| HDF5 | v0.17.2 | HDF5 file I/O for results |
| SQLite | v1.8.0 | SQLite database for simulation stores |
| Tables | v1.12.1 | Abstract table interface |

### Constrained Packages (⌅)

These packages cannot be upgraded due to compatibility bounds in the dependency graph:

AppleAccelerate v0.4.5, DataStructures v0.18.22, HDF5_jll v1.14.2+1, InfrastructureSystems v2.6.0, IntelOpenMP_jll v2024.2.1+0, Ipopt_jll v300.1400.1900+0, JSON v0.21.4, MKL v0.7.0, MKL_jll v2024.2.0+0, MUMPS_seq_jll v500.800.100+0, NLSolversBase v7.10.0, OpenBLAS32_jll v0.3.24+0, Pardiso v0.5.7, PowerFlows v0.9.0, PowerNetworkMatrices v0.12.1, PowerSystems v4.6.2, PrecompileTools v1.2.1, PrettyTables v2.4.0, SPRAL_jll v2025.5.20+0, TimeSeries v0.24.2, XML2_jll v2.13.9+0

### JLL Binary Wrappers

The dependency tree includes ~30 JLL (Julia Binary Builder) packages that wrap precompiled native libraries:

- Solver backends: `HiGHS_jll`, `Ipopt_jll`, `GLPK_jll`, `SCIP_jll`, `SCIP_PaPILO_jll`
- Linear algebra: `MKL_jll`, `OpenBLAS_jll`, `OpenBLAS32_jll`, `SuiteSparse_jll`
- I/O: `HDF5_jll`, `SQLite_jll`
- Compression: `Blosc_jll`, `Bzip2_jll`, `Zstd_jll`, `Lz4_jll`
- System: `OpenSSL_jll`, `GMP_jll`, `MPFR_jll`

### Data Source

- `.devcontainer/dc-exec -C /workspace/evaluations/powersimulations julia --project=. -e 'using Pkg; Pkg.status(mode=Pkg.PKGMODE_MANIFEST)'` (accessed 2026-03-14)
- `.devcontainer/dc-exec -C /workspace/evaluations/powersimulations julia --project=. -e 'using Pkg; Pkg.dependencies()'` (accessed 2026-03-14)

## Implications

1. **Large dependency tree:** 184 packages is substantial. This is typical for Julia projects that bundle solver bindings (each solver adds its own JLL chain). Without solvers, the count would be significantly lower.
2. **Version pinning pressure:** 15+ packages are constrained below their latest version, indicating tight compatibility coupling within the Sienna ecosystem. Upgrading any single package may require coordinated updates across PowerSystems, InfrastructureSystems, and PowerSimulations.
3. **Native binary dependencies:** The JLL packages distribute precompiled binaries for solver backends (HiGHS, Ipopt, GLPK, SCIP) and linear algebra (MKL, OpenBLAS). These are built by BinaryBuilder.jl and are platform-specific, adding supply chain surface area.
4. **Solver modularity:** The four solvers (HiGHS, Ipopt, GLPK, SCIP) are direct dependencies of our evaluation project, not of PowerSimulations.jl itself. In production, only the needed solver(s) would be included, reducing the tree.
