---
test_id: F-4
tool: powermodels
dimension: supply_chain
status: qualified_pass
timestamp: 2026-03-05
---

# F-4: Compiled Extension Audit

## Finding

35 JLL (Julia Link Library) packages provide pre-compiled binaries in the dependency tree. All are open-source with publicly available build recipes via Yggdrasil (Julia's binary build system). The solver-critical JLLs (HiGHS, Ipopt, SCIP, GLPK) have source available and are reproducibly built.

## Evidence

**JLL packages in dependency tree** (35 total):

Solver-critical JLLs:

| JLL Package | Version | Upstream Source | License |

|-------------|---------|----------------|---------|

| HiGHS_jll | 1.13.1+0 | github.com/ERGO-Code/HiGHS | MIT |

| Ipopt_jll | 300.1400.1901+0 | github.com/coin-or/Ipopt | EPL-2.0 |

| GLPK_jll | 5.0.1+1 | gnu.org/software/glpk | GPL-3.0 |

| SCIP_jll | 0.2.1+0 | github.com/scipopt/scip | Apache-2.0 |

| SCIP_PaPILO_jll | 0.1.0+3 | SCIP presolve library | Apache-2.0 |

| ASL_jll | 0.1.3+0 | AMPL Solver Library | BSD |

Math/system JLLs:

| JLL Package | Version | Notes |

|-------------|---------|-------|

| OpenBLAS_jll | 0.3.23+4 | BLAS implementation |

| OpenBLAS32_jll | 0.3.24+0 | 32-bit integer BLAS |

| SuiteSparse_jll | 7.2.1+1 | Sparse matrix algorithms |

| GMP_jll | 6.2.1+6 | GNU Multiple Precision |

| MUMPS_seq_jll | 500.800.200+0 | Sparse direct solver |

| SPRAL_jll | 2025.9.18+0 | Sparse parallel algebra |

| METIS_jll | 5.1.3+0 | Graph partitioning |

| bliss_jll | 0.77.0+1 | Graph automorphism |

| boost_jll | 1.76.0+1 | C++ libraries |

| oneTBB_jll | 2021.12.0+0 | Thread Building Blocks |

Infrastructure JLLs:

| JLL Package | Version | Notes |

|-------------|---------|-------|

| XML2_jll | 2.13.9+0 | XML parsing |

| Zlib_jll | 1.2.13+1 | Compression |

| Bzip2_jll | 1.0.9+0 | Compression |

| LibGit2_jll | 1.6.4+0 | Git operations |

| LibSSH2_jll | 1.11.0+1 | SSH |

| LibCURL_jll | 8.4.0+0 | HTTP client |

| MbedTLS_jll | 2.28.2+1 | TLS |

| MozillaCACerts_jll | 2023.1.10 | CA certificates |

| Ncurses_jll | 6.6.0+2 | Terminal |

| Readline_jll | 8.3.3+0 | Line editing |

| nghttp2_jll | 1.52.0+1 | HTTP/2 |

| p7zip_jll | 17.4.0+2 | Archive |

| Hwloc_jll | 2.13.0+0 | Hardware locality |

| Xorg_libpciaccess_jll | 0.18.1+0 | PCI access |

| Libiconv_jll | 1.18.0+0 | Character encoding |

| OpenLibm_jll | 0.8.5+0 | Math library |

| OpenSpecFun_jll | 0.5.6+0 | Special functions |

| CompilerSupportLibraries_jll | 1.1.1+0 | GCC runtime |

| libblastrampoline_jll | 5.11.0+0 | BLAS dispatch |

**Build system**: All JLL packages are built via Yggdrasil (<https://github.com/JuliaPackaging/Yggdrasil>), Julia's centralized binary build system. Each JLL has a `build_tarballs.jl` recipe that compiles from source using BinaryBuilder.jl, producing reproducible cross-platform binaries.

Source: `Pkg.dependencies()` in devcontainer, Yggdrasil repository

## Implications

All 35 JLL binaries have open-source upstream projects and reproducible build recipes. No proprietary or closed-source binaries are present. The large number of infrastructure JLLs (LibCURL, MbedTLS, etc.) are Julia stdlib dependencies, not PowerModels-specific. The solver JLLs are the critical ones for correctness, and all four (HiGHS, Ipopt, GLPK, SCIP) have well-maintained open-source codebases. Qualified pass due to the sheer volume of native code (35 JLLs) which increases the supply chain surface area.
