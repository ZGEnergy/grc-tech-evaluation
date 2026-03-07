---
test_id: F-4
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# F-4: Compiled Extension Audit

## Method

Identified all `_jll` (JLL = Julia Library Linking) packages in the Manifest.toml. These are compiled C/C++/Fortran libraries distributed as precompiled binaries via BinaryBuilder.jl.

## Findings

### JLL Packages in Execution Path (51 total)

**Solver libraries (core execution path):**

| JLL Package | Upstream Library | Language | Source Available | Buildable |
|-------------|-----------------|----------|-----------------|-----------|
| HiGHS_jll | HiGHS | C++ | Yes (github.com/ERGO-Code/HiGHS) | Yes |
| GLPK_jll | GLPK | C | Yes (gnu.org/software/glpk) | Yes |
| Ipopt_jll | Ipopt | C++ | Yes (github.com/coin-or/Ipopt) | Yes |
| SCIP_jll | SCIP | C | Yes (github.com/scipopt/scip) | Yes |
| SCIP_PaPILO_jll | PaPILO | C++ | Yes (github.com/scipopt/papilo) | Yes |

**Linear algebra / math libraries:**

| JLL Package | Upstream Library | Language | Source Available | Buildable |
|-------------|-----------------|----------|-----------------|-----------|
| OpenBLAS_jll | OpenBLAS | C/Fortran | Yes | Yes |
| OpenBLAS32_jll | OpenBLAS (32-bit int) | C/Fortran | Yes | Yes |
| SuiteSparse_jll | SuiteSparse | C | Yes | Yes |
| MUMPS_seq_jll | MUMPS | Fortran | Yes | Yes |
| SPRAL_jll | SPRAL | Fortran | Yes | Yes |
| METIS_jll | METIS | C | Yes | Yes |
| GMP_jll | GMP | C | Yes | Yes |
| MPFR_jll | MPFR | C | Yes | Yes |
| MKL_jll | Intel MKL | C/Fortran | No (proprietary) | No |
| IntelOpenMP_jll | Intel OpenMP | C++ | No (proprietary) | No |
| libblastrampoline_jll | libblastrampoline | C | Yes | Yes |
| ASL_jll | AMPL Solver Library | C | Yes | Yes |
| CompilerSupportLibraries_jll | GCC runtime | C/Fortran | Yes | Yes |

**I/O and infrastructure:**

| JLL Package | Upstream Library | Notes |
|-------------|-----------------|-------|
| HDF5_jll | HDF5 | BSD-style, source available |
| SQLite_jll | SQLite | Public domain |
| Blosc_jll | Blosc | BSD-3-Clause |
| XML2_jll | libxml2 | MIT |
| Zlib_jll, Zstd_jll, Lz4_jll, Bzip2_jll | Compression libs | All open-source |
| OpenSSL_jll, MbedTLS_jll | TLS | Apache/Dual |
| LibCURL_jll, LibGit2_jll, LibSSH2_jll | Network/git | All open-source |
| nghttp2_jll | nghttp2 | MIT |

**MPI (not used in this evaluation but pulled transitively):**

MPICH_jll, OpenMPI_jll, MPItrampoline_jll, MicrosoftMPI_jll, Hwloc_jll -- all open-source.

### Proprietary Components

**MKL_jll and IntelOpenMP_jll** are Intel proprietary libraries. They are included as an optional BLAS backend. Julia's `libblastrampoline` dynamically dispatches to the best available BLAS at runtime. On Linux, **OpenBLAS is the default**; MKL is only used if explicitly configured via `MKL.jl`. These packages are pulled as transitive dependencies but do not execute by default.

### BinaryBuilder.jl Build Transparency

All JLL packages are built using BinaryBuilder.jl, which:
- Stores build recipes as Julia scripts in public GitHub repos (e.g., `JuliaBinaryWrappers/`)
- Cross-compiles in a reproducible sandbox environment
- Produces artifacts with content-addressed SHA256 hashes
- Publishes build logs alongside artifacts

Every JLL package can be rebuilt from source using its build recipe.

## Assessment

All compiled components in the core execution path have available source code and are buildable from source. The MKL/IntelOpenMP JLL packages are proprietary but optional (OpenBLAS is the default BLAS backend). **Pass.**
