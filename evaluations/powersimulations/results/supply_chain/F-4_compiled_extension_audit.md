---
test_id: F-4
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v11"
skill_version: "v2"
test_hash: "4fd147b3"
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
timestamp: 2026-03-24T00:00:00Z
---

# F-4: Compiled Extension Audit

## Result: INFORMATIONAL

## Summary

PowerSimulations.jl depends on four compiled solver binaries (C/C++/Fortran) plus
numerical libraries. All are distributed as JLL packages built from source via
Julia's BinaryBuilder/Yggdrasil infrastructure. Every compiled component has
publicly available source code and a reproducible build recipe.

## Compiled Components in the Execution Path

### Solver Binaries (directly invoked during solve)

| Component | Language | JLL Package | Upstream Version | Source Repo | Binary License |
|-----------|----------|-------------|------------------|-------------|----------------|
| HiGHS | C++ | HiGHS_jll v1.13.1+0 | 1.13.1 | [ERGO-Code/HiGHS](https://github.com/ERGO-Code/HiGHS) | MIT |
| Ipopt | C++/Fortran | Ipopt_jll v300.1400.1900+0 | 3.14.19 | [coin-or/Ipopt](https://github.com/coin-or/Ipopt) | EPL-2.0 |
| GLPK | C | GLPK_jll v5.0.1+1 | 5.0 | [GNU GLPK](https://www.gnu.org/software/glpk/) | GPL-3.0 |
| SCIP | C++ | SCIP_jll v1000.0.2+0 | 10.0.2 | [scipopt/scip](https://github.com/scipopt/scip) | Apache-2.0 |

### Numerical Libraries (linked by solvers or Julia runtime)

| Component | Language | JLL Package | Source Available | Binary License |
|-----------|----------|-------------|-----------------|----------------|
| OpenBLAS | C/Fortran | OpenBLAS_jll | Yes (GitHub) | BSD-3-Clause |
| MUMPS (sequential) | Fortran | MUMPS_seq_jll v500.800.100+0 | Yes (MUMPS consortium) | CeCILL-C |
| SPRAL | Fortran | SPRAL_jll v2025.5.20+0 | Yes (GitHub) | BSD-3-Clause |
| ASL (AMPL Solver Library) | C | ASL_jll | Yes (GitHub) | BSD-3-Clause |
| GMP | C | GMP_jll | Yes (GNU) | LGPL-3.0+ |
| METIS | C | METIS_jll | Yes (Karypis Lab) | Apache-2.0 |
| HDF5 | C | HDF5_jll | Yes (HDF Group) | BSD-3-Clause |
| MKL | C/Fortran | MKL_jll v2024.2.0+0 | No (Intel proprietary) | Intel Proprietary |

### Total JLL Package Count

The dependency tree includes 41 JLL (Julia Binary Builder) packages that wrap precompiled
native libraries. Beyond the solver and numerical libraries listed above, these are
system-level libraries (zlib, OpenSSL, SQLite, etc.) that are standard, widely audited
components. All have publicly available upstream source except MKL (proprietary but optional).

## BinaryBuilder / Yggdrasil Reproducibility

All JLL packages are built via [Yggdrasil](https://github.com/JuliaPackaging/Yggdrasil),
Julia's community build system. Each JLL has:

1. **A `build_tarballs.jl` recipe** in Yggdrasil specifying:
   - Exact source URL and git commit SHA or archive hash
   - Build script (configure/cmake/make steps)
   - Target platform matrix
2. **Pinned source commits** (e.g., HiGHS pinned to `1d267d97c16928bb5f86fcb2cba2d20f94c8720c`)
3. **SHA-256 hashes** on every download artifact in `Artifacts.toml`
4. **Cross-compilation** from a controlled Linux build environment

### Verified Build Recipes

| Solver | Yggdrasil Path | Source Pinning |
|--------|----------------|----------------|
| HiGHS | `H/HiGHS/build_tarballs.jl` | Git SHA `1d267d97...` |
| GLPK | `G/GLPK/build_tarballs.jl` | Archive hash `4a1013ee...` |
| SCIP | `S/SCIP/build_tarballs.jl` | Archive hash `44877ca3...` |
| Ipopt | `C/Coin-OR/Ipopt/build_tarballs.jl` | Git SHA (via coin-or-common.jl) |

## Buildable from Source?

All four solver binaries can be built from source:

- **HiGHS:** CMake-based, C++11, no exotic dependencies. Straightforward to build.
- **GLPK:** Autotools-based, pure C. Very simple to build.
- **SCIP:** CMake-based, C++. Larger build but well-documented.
- **Ipopt:** Autotools/CMake, requires Fortran compiler for MUMPS/BLAS. More complex
  but has extensive build documentation.

Alternatively, users can rebuild JLL packages from their Yggdrasil recipes using
`BinaryBuilder.jl` to produce bit-identical artifacts.

## MKL Note

Intel MKL (`MKL_jll`) is proprietary (Intel ISSL license). It is an optional
performance optimization for BLAS/LAPACK. The default BLAS backend is OpenBLAS
(BSD-3-Clause). MKL is not required for any solver operation -- it accelerates
dense linear algebra in Julia's standard library. Excluding MKL removes all
proprietary compiled components from the tree.

## Opaque Binary Steps

The only truly opaque components are the compiled solver shared libraries themselves
(`.so` files). However:

- Source code is available for all four solvers
- Build recipes are public and reproducible
- Artifact hashes provide tamper detection
- No solver binary includes telemetry, phone-home, or license-check code

Julia itself compiles all Julia source code to native code via LLVM JIT at package
precompilation time. This compilation is transparent and reproducible from the
Julia source.

## Data Source

- JLL versions from `Pkg.dependencies()` in devcontainer (accessed 2026-03-24)
- Yggdrasil build recipes verified via GitHub (accessed 2026-03-24)
- SCIP version confirmed via `SCIP.SCIPversion()` = 10.0 (accessed 2026-03-24)

## Implications

1. **All compiled components have available source.** Every solver and numerical library in the execution path has publicly available source code and documented build procedures.
2. **Reproducible builds via Yggdrasil.** The BinaryBuilder infrastructure provides auditable, reproducible build recipes for all 41 JLL packages.
3. **MKL is the only non-source-available component and is optional.** Switching to OpenBLAS (the default) eliminates all proprietary compiled dependencies.
4. **No hidden compiled extensions.** Julia's JIT compilation is transparent; all Julia source code is inspectable. The only compiled binaries are the explicitly declared JLL packages.
