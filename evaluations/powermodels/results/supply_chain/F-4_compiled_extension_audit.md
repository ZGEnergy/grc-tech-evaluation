---
test_id: F-4
tool: powermodels
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: "2026-03-13T23:01:54Z"
protocol_version: v10
skill_version: v1
test_hash: "0697916b"
---

# F-4: Identify compiled components in execution path

## Finding

PowerModels.jl itself is pure Julia with no compiled extensions. All compiled components reside in JLL (Julia Binary Wrapper) packages for solvers and numerical libraries. Source code is publicly available for every compiled component, and all are reproducibly built via the JuliaPackaging/Yggdrasil build system.

## Evidence

**PowerModels.jl:** Pure Julia source code. No `ccall` declarations, no C/Fortran extensions, no binary artifacts in the package itself. Verified by inspecting all `.jl` files under `/opt/julia-depot/packages/PowerModels/VCmhH/src/`.

### Compiled components in execution path (35 JLL packages total):

#### Solver binaries (directly invoked):

| Component | Language | JLL Package | Source Available? | Buildable? |
|-----------|----------|-------------|-------------------|------------|
| libipopt.so | C++ | Ipopt_jll v300.1400.1901 | Yes — [github.com/coin-or/Ipopt](https://github.com/coin-or/Ipopt) | Yes — CMake |
| libhighs.so | C++ | HiGHS_jll v1.13.1 | Yes — [github.com/ERGO-Code/HiGHS](https://github.com/ERGO-Code/HiGHS) | Yes — CMake |
| libglpk.so | C | GLPK_jll v5.0.1 | Yes — [gnu.org/software/glpk](https://www.gnu.org/software/glpk/) | Yes — Autoconf |
| libscip.so | C++ | SCIP_jll v0.2.1 (SCIP 8.0.0) | Yes — [scipopt.org](https://www.scipopt.org) | Yes — CMake |

#### Numerical libraries (solver dependencies):

| Component | Language | JLL Package | Source Available? | Buildable? |
|-----------|----------|-------------|-------------------|------------|
| libmumps_seq.so | Fortran/C | MUMPS_seq_jll v500.800.200 | Yes — mumps-solver.org | Yes — Make/CMake |
| libspral.so | Fortran/C | SPRAL_jll v2025.9.18 | Yes — [github.com/ralna/spral](https://github.com/ralna/spral) | Yes |
| libopenblas.so | Fortran/C | OpenBLAS_jll v0.3.23 | Yes — [github.com/OpenMathLib/OpenBLAS](https://github.com/OpenMathLib/OpenBLAS) | Yes |
| libgmp.so | C | GMP_jll v6.2.1 | Yes — [gmplib.org](https://gmplib.org) | Yes — Autoconf |
| libmetis.so | C | METIS_jll v5.1.3 | Yes — [github.com/KarypisLab/METIS](https://github.com/KarypisLab/METIS) | Yes — CMake |
| SuiteSparse libs | C | SuiteSparse_jll v7.2.1 | Yes — [github.com/DrTimothyAldenDavis/SuiteSparse](https://github.com/DrTimothyAldenDavis/SuiteSparse) | Yes — CMake |

#### Infrastructure libraries:

| Component | Purpose | Source Available? |
|-----------|---------|-------------------|
| libcurl, libssh2, libgit2 | Package management (not in solver path) | Yes |
| libz, libbz2 | Compression | Yes |
| libgcc_s, libgfortran, libstdc++ | Compiler runtime | Yes (GCC) |
| libblastrampoline | BLAS dispatch | Yes (Julia stdlib) |

### Build infrastructure:

All JLL packages are built via the [JuliaPackaging/Yggdrasil](https://github.com/JuliaPackaging/Yggdrasil) repository using standardized, auditable build recipes (BinaryBuilder.jl). Build logs are public. Every artifact in Manifest.toml includes a `git-tree-sha1` hash verified by Julia's package manager on download.

No proprietary or opaque binaries were identified anywhere in the execution path.

## Implications

All 35 compiled components have publicly available source code and standard build toolchains. The JLL packaging system provides reproducible binary builds with integrity verification. No black-box binaries exist in the PowerModels execution path. This is a clean result for compiled extension auditability.
