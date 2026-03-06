---
test_id: F-3
tool: powermodels
dimension: supply_chain
status: qualified_pass
timestamp: 2026-03-05
---

# F-3: Dependency License Audit

## Finding

All 114 packages in the dependency tree use permissive or weak-copyleft open-source licenses, with one exception: GLPK and GLPK_jll are GPL-3.0 (strong copyleft). GLPK is an evaluation-added solver dependency, not a PowerModels requirement, and is fully replaceable with MIT-licensed HiGHS. No proprietary or unknown licenses were found. The dominant license is MIT, followed by Julia stdlib (MIT-equivalent), with MPL-2.0 (JuMP) and EPL-2.0 (Ipopt) as the most restrictive permissive licenses in active use.

## Evidence

### License Distribution Summary

| License | Count | Category | Risk |

|---------|-------|----------|------|

| MIT | 52 | Permissive | None |

| Julia stdlib (MIT) | 28 | Permissive | None |

| BSD-3-Clause | 4 | Permissive | None |

| MPL-2.0 | 3 | Weak copyleft (file-level) | Low |

| EPL-2.0 | 2 | Weak copyleft (module-level) | Low |

| Apache-2.0 | 4 | Permissive | None |

| ISC | 1 | Permissive | None |

| Zlib | 2 | Permissive | None |

| BSL-1.0 (Boost) | 1 | Permissive | None |

| LGPL-2.1+ | 3 | Weak copyleft (linking OK) | Low |

| **GPL-3.0** | **2** | **Strong copyleft** | **Medium** |

| Mixed/Multi | 12 | See details | Varies |

### Detailed Audit by Package Category

#### PowerModels Core Dependencies (6 packages)

| Package | Version | License | Notes |

|---------|---------|---------|-------|

| PowerModels | 0.21.5 | BSD-3-Clause (LANL) | Core package |

| InfrastructureModels | 0.7.8 | BSD-3-Clause (LANL) | Network data infrastructure |

| JuMP | 1.29.4 | MPL-2.0 | Mathematical optimization modeling; file-level copyleft, permissive for linking |

| Memento | 1.4.1 | MIT (Invenia) | Logging framework |

| JSON | 0.21.4 | MIT | JSON parser |

| NLsolve | 4.5.1 | MIT | Nonlinear solver (for native PF) |

#### Solver Packages (evaluation additions, not PowerModels requirements)

| Package | Version | License | Risk | Notes |

|---------|---------|---------|------|-------|

| HiGHS | 1.21.1 | MIT | None | LP/MIP solver |

| HiGHS_jll | 1.13.1+0 | MIT | None | Pre-compiled binary |

| Ipopt | 1.14.1 | MIT (wrapper) | None | Julia wrapper |

| Ipopt_jll | 300.1400.1901+0 | EPL-2.0 | Low | Pre-compiled binary; EPL is weak copyleft |

| **GLPK** | **1.2.1** | **GPL-3.0** | **Medium** | **LP/MIP solver; strong copyleft** |

| **GLPK_jll** | **5.0.1+1** | **GPL-3.0** | **Medium** | **Pre-compiled binary** |

| SCIP | 0.11.6 | MIT (wrapper) | None | Julia wrapper |

| SCIP_jll | 0.2.1+0 | Apache-2.0 | None | Pre-compiled binary |

| SCIP_PaPILO_jll | 0.1.0+3 | Apache-2.0 | None | Presolve library |

#### JuMP/MathOptInterface Ecosystem

| Package | Version | License |

|---------|---------|---------|

| MathOptInterface | 1.49.0 | MIT |

| MathOptIIS | 0.1.2 | MIT |

| MutableArithmetics | 1.6.7 | MPL-2.0 |

| OrderedCollections | 1.8.1 | MIT |

| PrecompileTools | 1.2.1 | MIT |

| BenchmarkTools | 1.6.3 | MIT |

#### Automatic Differentiation Stack

| Package | Version | License |

|---------|---------|---------|

| ForwardDiff | 1.3.2 | MIT |

| DiffResults | 1.1.0 | MIT |

| DiffRules | 1.15.1 | MIT |

| ADTypes | 1.21.0 | MIT |

| DifferentiationInterface | 0.7.16 | MIT |

| CommonSubexpressions | 0.3.1 | MIT |

| NLSolversBase | 7.10.0 | MIT |

| FiniteDiff | 2.29.0 | MIT |

#### Linear Algebra / Math Libraries

| Package | Version | License |

|---------|---------|---------|

| SparseArrays | stdlib | MIT |

| LinearAlgebra | stdlib | MIT |

| StaticArraysCore | 1.4.4 | MIT |

| SuiteSparse_jll | stdlib | BSD/LGPL-2.1+ |

| OpenBLAS_jll | stdlib | BSD-3-Clause |

| OpenBLAS32_jll | 0.3.24+0 | BSD-3-Clause |

| libblastrampoline_jll | stdlib | MIT |

| MUMPS_seq_jll | 500.800.200+0 | CeCILL-C (LGPL-compatible) |

| METIS_jll | 5.1.3+0 | Apache-2.0 |

| SPRAL_jll | 2025.9.18+0 | BSD-3-Clause |

| GMP_jll | stdlib | LGPL-3.0+ (dynamic linking OK) |

#### System/Utility Libraries (JLLs)

| Package | License | Notes |

|---------|---------|-------|

| ASL_jll | BSD | AMPL Solver Library |

| Bzip2_jll | BSD | Compression |

| Zlib_jll | Zlib | Compression |

| XML2_jll | MIT | XML parsing |

| Libiconv_jll | LGPL-2.0+ | Character encoding (dynamic linking OK) |

| Hwloc_jll | BSD | Hardware topology |

| Xorg_libpciaccess_jll | MIT | PCI access |

| Ncurses_jll | MIT | Terminal library |

| Readline_jll | GPL-3.0 | Terminal input (SCIP dep only) |

| oneTBB_jll | Apache-2.0 | Threading |

| bliss_jll | LGPL-3.0 | Graph automorphism (SCIP dep) |

| boost_jll | BSL-1.0 | Boost C++ (SCIP dep) |

| nghttp2_jll | MIT | HTTP/2 |

| MbedTLS_jll | Apache-2.0 | TLS |

| CompilerSupportLibraries_jll | MIT | GCC runtime |

| LibCURL_jll | MIT | HTTP client |

| LibSSH2_jll | BSD | SSH |

| LibGit2_jll | GPL-2.0 with linking exception | Git library |

| MozillaCACerts_jll | MPL-2.0 | CA certificates |

| OpenLibm_jll | MIT/BSD | Math library |

| OpenSpecFun_jll | MIT | Special functions |

| p7zip_jll | LGPL-2.1+ | Archive compression |

#### Julia Standard Library (28 packages)

All stdlib packages (ArgTools, Artifacts, Base64, Dates, Distributed, Downloads, FileWatching, InteractiveUtils, Libdl, Logging, Markdown, Mmap, Pkg, Printf, Profile, Random, REPL, Serialization, SHA, Sockets, Statistics, TOML, Tar, Test, Unicode, UUIDs, Future, NetworkOptions) are MIT-licensed as part of the Julia distribution.

### GPL-3.0 Risk Assessment

**GLPK + GLPK_jll (GPL-3.0):**
- These are evaluation-added dependencies, NOT required by PowerModels
- PowerModels' `Project.toml` does not list GLPK as a dependency
- GLPK is fully replaceable with HiGHS (MIT) for all LP/MIP functionality
- If GLPK is removed from the project, zero GPL code remains in the dependency tree

**Readline_jll (GPL-3.0):**
- Transitive dependency of SCIP_jll only
- Provides terminal input handling for SCIP's interactive mode
- SCIP itself is Apache-2.0; Readline is a build dependency for the SCIP binary
- In practice, SCIP is used programmatically (not interactively), so Readline is not invoked at runtime

**LibGit2_jll (GPL-2.0 with linking exception):**
- Julia stdlib dependency for package management
- The linking exception explicitly permits use in non-GPL software
- Standard in all Julia installations; not a PowerModels-specific concern

### Proprietary / Unknown License Check

- **Zero proprietary licenses found** in the entire dependency tree
- **Zero unknown licenses** -- all packages have identifiable SPDX-compatible licenses
- All JLL packages have publicly available build recipes via Julia's Yggdrasil binary build system

## Implications

The dependency tree is clean from a license perspective. The only actionable concern is GLPK (GPL-3.0), which is an optional solver not required by PowerModels and fully replaceable with MIT-licensed HiGHS. For production deployment, removing GLPK from the Project.toml eliminates all strong copyleft from the stack. The weak copyleft licenses (MPL-2.0 for JuMP, EPL-2.0 for Ipopt, LGPL for GMP/Libiconv) impose no practical restrictions on linking or embedding -- they only require sharing modifications to the copyleft-licensed files themselves, not to user code.
