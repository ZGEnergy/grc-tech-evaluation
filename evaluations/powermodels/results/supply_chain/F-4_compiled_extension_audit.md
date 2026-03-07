---
test_id: F-4
tool: powermodels
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-06T00:00:00Z
---

# F-4: Compiled Extension Audit

## Result: PASS

## Finding

PowerModels.jl itself is pure Julia with no compiled extensions. All compiled components are in solver JLL packages, which wrap pre-built binaries via Julia's BinaryBuilder infrastructure. Source code for all binaries is publicly available. The JLL build recipes are open-source and reproducible.

## Evidence

**PowerModels source**: 42 pure Julia `.jl` files under `src/` covering IO, formulations, problem specifications, and utilities. No C, C++, or Fortran code. No `ccall` statements in PowerModels source.

**JLL binary wrapper packages (35 total)** provide pre-compiled shared libraries. Key solver binaries in the execution path:

| JLL Package | Binary | Language | Source Available | License |
|-------------|--------|----------|-----------------|---------|
| HiGHS_jll | libhighs.so | C++ | Yes (github.com/ERGO-Code/HiGHS) | MIT |
| Ipopt_jll | libipopt.so | C++ | Yes (github.com/coin-or/Ipopt) | EPL-2.0 |
| GLPK_jll | libglpk.so | C | Yes (gnu.org/software/glpk) | GPL-3.0 |
| SCIP_jll | libscip.so | C | Yes (scipopt.org) | ZIB Academic |
| ASL_jll | libasl.so | C | Yes (github.com/ampl/asl) | BSD |
| MUMPS_seq_jll | libdmumps.so | Fortran/C | Yes (mumps-solver.org) | CeCILL-C |
| METIS_jll | libmetis.so | C | Yes (github.com/KarypisLab/METIS) | Apache-2.0 |
| SPRAL_jll | libspral.so | Fortran | Yes (github.com/ralna/spral) | BSD-3-Clause |
| OpenBLAS32_jll | libopenblas.so | Fortran/C | Yes (github.com/OpenMathLib/OpenBLAS) | BSD-3-Clause |
| bliss_jll | libbliss.so | C++ | Yes (users.aalto.fi/~tjunMDla/bliss) | LGPL |

**BinaryBuilder reproducibility**: All JLL packages are built from open-source recipes in the `Yggdrasil` repository (github.com/JuliaPackaging/Yggdrasil). Each recipe specifies exact source URLs, patches, and build flags. Builds are reproducible and auditable.

**Non-solver system libraries**: Bzip2, Zlib, libxml2, ncurses, readline, hwloc, boost, oneTBB -- all standard open-source C/C++ libraries with publicly available source.

## Implications

No opaque binary blobs. All compiled components trace to open-source projects with available build recipes. The JLL/BinaryBuilder infrastructure provides a transparent, auditable path from source to binary. PowerModels core is pure Julia and fully inspectable. Compiled components are limited to solver backends and system libraries, all with source available.
