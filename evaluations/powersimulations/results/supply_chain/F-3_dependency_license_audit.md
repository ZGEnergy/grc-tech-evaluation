---
test_id: F-3
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v11"
skill_version: "v2"
test_hash: "ac2a9361"
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

# F-3: Dependency License Audit

## Result: INFORMATIONAL — Two copyleft flags (GLPK GPL-3.0, JuMP MPL-2.0); one proprietary flag (MKL); no unknown/unresolvable licenses

## Finding

The vast majority of PowerSimulations.jl's dependency tree is permissively licensed (MIT, BSD, Apache-2.0). Three notable exceptions require attention:

1. **GLPK / GLPK_jll** — GPL-3.0 (strong copyleft). Both the Julia wrapper and the native GLPK binary are GPL-3.0.
2. **JuMP.jl** — MPL-2.0 (weak copyleft). JuMP is a core dependency that cannot be removed.
3. **MKL_jll** — Intel proprietary binary (redistributable). Optional; OpenBLAS is the default.

**v11 JLL binary artifact audit:** All 41 JLL packages were audited for wrapper vs. binary license discrepancies. All JLL wrappers use MIT for the Julia source code; the binary artifact license (shipped in `share/licenses/` within the JLL prefix) governs the supply chain classification. Key discrepancies are documented below. SCIP binary is confirmed Apache 2.0 (version 10.0.2, well above the 8.0.3 threshold).

## Evidence

### Direct Dependencies — License Summary

| Package | Version | Wrapper License | Binary License | Category |
|---------|---------|----------------|----------------|----------|
| PowerSimulations.jl | v0.30.2 | BSD-3-Clause | N/A (pure Julia) | Permissive |
| PowerSystems.jl | v4.6.2 | BSD-3-Clause | N/A (pure Julia) | Permissive |
| PowerFlows.jl | v0.9.0 | BSD-3-Clause | N/A (pure Julia) | Permissive |
| PowerNetworkMatrices.jl | v0.12.1 | BSD-3-Clause | N/A (pure Julia) | Permissive |
| InfrastructureSystems.jl | v2.6.0 | BSD-3-Clause | N/A (pure Julia) | Permissive |
| JuMP.jl | v1.29.4 | **MPL-2.0** | N/A (pure Julia) | **Weak copyleft** |
| HiGHS.jl | v1.21.1 | MIT | N/A (wrapper only) | Permissive |
| Ipopt.jl | v1.14.1 | MIT | N/A (wrapper only) | Permissive |
| GLPK.jl | v1.2.1 | **GPL-3.0** | N/A (wrapper only) | **Strong copyleft** |
| SCIP.jl | v0.12.8 | MIT | N/A (wrapper only) | Permissive |
| DataFrames.jl | v1.8.1 | MIT | N/A (pure Julia) | Permissive |
| CSV.jl | v0.10.16 | MIT | N/A (pure Julia) | Permissive |
| JSON.jl | v0.21.4 | MIT | N/A (pure Julia) | Permissive |
| TimeSeries.jl | v0.24.2 | MIT | N/A (pure Julia) | Permissive |
| Combinatorics.jl | v1.1.0 | MIT | N/A (pure Julia) | Permissive |

### JLL Binary Artifact License Audit (v11 requirement)

All 41 JLL packages use MIT for the Julia wrapper source code (`src/` directory). The binary artifact license is distinct and governs deployment. Below is the audit of all JLL packages with non-trivial binary licenses.

#### Solver JLL Packages

| JLL Package | Version | Wrapper License | Binary Artifact License | Discrepancy? | Notes |
|-------------|---------|----------------|------------------------|--------------|-------|
| HiGHS_jll | (latest) | MIT | MIT | No | Clean |
| Ipopt_jll | (pinned) | MIT | **EPL-2.0** | **Yes** | Weak copyleft on binary; no impact for library use |
| GLPK_jll | (latest) | MIT | **GPL-3.0** | **Yes** | Strong copyleft on binary; matches wrapper package GPL |
| SCIP_jll | v1000.0.2+0 | MIT | **Apache-2.0** | **Yes** | SCIP 10.0.2 >= 8.0.3 threshold; Apache 2.0 confirmed |
| SCIP_PaPILO_jll | v1000.0.2+0 | MIT | **Apache-2.0** | **Yes** | Same SCIP version; Apache 2.0 |

**SCIP license verification (v11 critical check):** SCIP_jll v1000.0.2+0 maps to SCIP version 10.0.2. The ZIB Academic License applied to SCIP versions < 8.0.3. Starting with SCIP 8.0.3, the license changed to Apache 2.0. Since 10.0.2 >> 8.0.3, the bundled binary is Apache 2.0. Verified via `gh api repos/scipopt/scip` which reports `Apache-2.0` as the SPDX license.

#### Solver Transitive JLL Packages

| JLL Package | Version | Wrapper License | Binary Artifact License | Notes |
|-------------|---------|----------------|------------------------|-------|
| ASL_jll | (latest) | MIT | BSD-3-Clause | AMPL Solver Library; permissive |
| MUMPS_seq_jll | v500.800.100+0 | MIT | CeCILL-C | French free software license, LGPL-compatible; weak copyleft |
| SPRAL_jll | v2025.5.20+0 | MIT | BSD-3-Clause | STFC Rutherford Appleton; permissive |
| METIS_jll | (latest) | MIT | Apache-2.0 | Graph partitioning; permissive |
| bliss_jll | (latest) | MIT | LGPL-3.0 | Graph automorphism; weak copyleft (dynamic linking OK) |
| boost_jll | (latest) | MIT | BSL-1.0 | Boost Software License; permissive |
| GMP_jll | (latest) | MIT | LGPL-3.0+ / GPL-2.0+ | Dual-licensed; LGPL applies for dynamic linking |
| MPFR_jll | (latest) | MIT | LGPL-3.0+ | Weak copyleft; dynamic linking OK |

#### Linear Algebra JLL Packages

| JLL Package | Version | Wrapper License | Binary Artifact License | Notes |
|-------------|---------|----------------|------------------------|-------|
| MKL_jll | v2024.2.0+0 | MIT | **Intel Proprietary** | Redistribution allowed via JLL; optional, replaceable by OpenBLAS |
| OpenBLAS_jll | (latest) | MIT | BSD-3-Clause | Default BLAS backend; permissive |
| IntelOpenMP_jll | v2024.2.1+0 | MIT | **Intel Proprietary** | Runtime for MKL; same removal path as MKL |
| oneTBB_jll | v2022.0.0+1 | MIT | Apache-2.0 | Threading; permissive |
| SuiteSparse_jll | (latest) | MIT | Various (BSD/LGPL per component) | Mostly BSD; some LGPL components |
| libblastrampoline_jll | (latest) | MIT | MIT | Dispatch layer; permissive |

#### I/O and System JLL Packages

| JLL Package | Wrapper License | Binary Artifact License | Notes |
|-------------|----------------|------------------------|-------|
| HDF5_jll | MIT | BSD-3-Clause | Permissive |
| SQLite_jll | MIT | Public Domain | Permissive |
| OpenSSL_jll | MIT | Apache-2.0 | Permissive |
| Zlib_jll | MIT | Zlib | Permissive |
| Zstd_jll | MIT | BSD-3-Clause | Permissive |
| Blosc_jll | MIT | BSD-3-Clause | Permissive |

All remaining JLL packages (CompilerSupportLibraries_jll, Hwloc_jll, Ncurses_jll, Readline_jll, Libiconv_jll, LibCURL_jll, MozillaCACerts_jll, MbedTLS_jll, LLVMOpenMP_jll, OpenLibm_jll, OpenSpecFun_jll, Xorg_libpciaccess_jll, libaec_jll, MPICH_jll, MPItrampoline_jll, MicrosoftMPI_jll, OpenMPI_jll) have permissive binary licenses (MIT, BSD, or equivalent).

### License Category Summary

| Category | Packages | Removable? |
|----------|----------|------------|
| **Permissive** (MIT, BSD, Apache-2.0, BSL-1.0, Zlib, Public Domain) | ~170 | N/A |
| **Weak copyleft** (MPL-2.0, EPL-2.0, LGPL-3.0, CeCILL-C) | JuMP, Ipopt binary, bliss binary, GMP binary, MPFR binary, MUMPS binary, SuiteSparse components | JuMP: no (core dep). Others: dynamic linking, no source disclosure for callers |
| **Strong copyleft** (GPL-3.0) | GLPK.jl + GLPK binary | **Yes** — drop from Project.toml, use HiGHS instead |
| **Proprietary** (Intel redistributable) | MKL_jll, IntelOpenMP_jll | **Yes** — use OpenBLAS (default) instead |
| **Unknown / problematic** | None | N/A |

### Detailed Assessment of Flagged Licenses

#### GLPK — GPL-3.0 (Strong Copyleft)

- **Scope:** Both the native GLPK library (`GLPK_jll`) and the Julia wrapper (`GLPK.jl`) are GPL-3.0.
- **Impact:** GPL-3.0 requires that derivative works be distributed under GPL-3.0. When GLPK is used as a solver backend, the GPL may apply to the combined work depending on how "derivative work" is interpreted for dynamically linked solver backends.
- **Mitigation:** GLPK is a direct dependency of our evaluation project, not of PowerSimulations.jl itself. It can be replaced with HiGHS (MIT) or another solver without any code changes to PowerSimulations.jl. **Removing GLPK from the project eliminates the GPL obligation entirely.**

#### JuMP — MPL-2.0 (Weak Copyleft)

- **Scope:** JuMP.jl is licensed under Mozilla Public License 2.0.
- **Impact:** MPL-2.0 is a weak copyleft (file-level). Modifications to JuMP source files must be shared under MPL-2.0, but code in other files that merely uses JuMP is not affected. MPL-2.0 is explicitly compatible with Apache-2.0 and is generally considered business-friendly.
- **Mitigation:** No action needed. Using JuMP as a library (without modifying its source) imposes no copyleft obligations on the calling code.

#### Ipopt binary — EPL-2.0 (Weak Copyleft)

- **Scope:** The native Ipopt library is EPL-2.0; the Julia wrapper is MIT.
- **Wrapper/binary discrepancy:** Yes — MIT wrapper, EPL-2.0 binary. The binary license governs.
- **Impact:** EPL-2.0 is similar to MPL-2.0 in scope. It requires source disclosure only for modifications to the EPL-licensed code itself. Using Ipopt as a solver backend does not create a derivative work.
- **Mitigation:** No action needed for standard use.

#### SCIP binary — Apache 2.0 (Permissive, version-dependent)

- **Scope:** SCIP_jll v1000.0.2+0 bundles SCIP 10.0.2.
- **Wrapper/binary discrepancy:** Yes — MIT wrapper, Apache 2.0 binary. The binary license governs.
- **v11 critical check:** SCIP versions < 8.0.3 were licensed under ZIB Academic License (non-commercial use only). Version 10.0.2 is well above this threshold. **Apache 2.0 confirmed — no ZIB Academic restriction.**
- **Mitigation:** None needed. Apache 2.0 is permissive.

#### Intel MKL — Proprietary (Redistributable)

- **Scope:** MKL_jll (v2024.2.0+0) and IntelOpenMP_jll (v2024.2.1+0) are proprietary Intel binaries.
- **Wrapper/binary discrepancy:** Yes — MIT wrappers, Intel Proprietary binaries.
- **Impact:** Intel's license allows redistribution of the runtime binaries. It does not impose source code obligations. However, it is a proprietary license with terms that may change.
- **Mitigation:** MKL is optional; OpenBLAS (BSD-3-Clause) is the default BLAS backend. Excluding MKL_jll and IntelOpenMP_jll from the project removes all proprietary dependencies.

#### MUMPS binary — CeCILL-C

- **Scope:** MUMPS_seq_jll bundles MUMPS 5.8.1 under the CeCILL-C license.
- **Impact:** CeCILL-C is a French free software license compatible with LGPL. It permits dynamic linking without copyleft propagation. Modifications to MUMPS source must be shared.
- **Mitigation:** Standard dynamic linking use; no action needed.

### Data Source

- JLL wrapper LICENSE files checked via `gh api repos/JuliaBinaryWrappers/<pkg>_jll.jl/contents/LICENSE` (accessed 2026-03-24) — all confirm MIT wrapper with binary license in `share/licenses/`
- SCIP upstream license: `gh api repos/scipopt/scip --jq '.license.spdx_id'` = Apache-2.0 (accessed 2026-03-24)
- Binary artifact licenses: verified via upstream project repositories and JuliaBinaryWrappers release READMEs
- Manifest.toml package versions extracted from devcontainer (accessed 2026-03-24)

## Implications

1. **GLPK is the only strong copyleft dependency and it is removable.** GLPK is not required by PowerSimulations.jl. It is one of several interchangeable solver backends. Dropping it from the project's `Project.toml` and using HiGHS (MIT) instead eliminates all GPL exposure.

2. **JuMP's MPL-2.0 is non-concerning for library use.** MPL-2.0 is file-scoped copyleft. Using JuMP as a dependency (without modifying JuMP source files) does not trigger any copyleft obligations on the calling code. This is the standard use case.

3. **SCIP is clean under v11 audit (Apache 2.0).** The bundled SCIP binary (v10.0.2) is well above the 8.0.3 version threshold where the license changed from ZIB Academic to Apache 2.0. No non-commercial restriction applies.

4. **MKL is the only proprietary dependency and it is optional.** Removing MKL_jll and IntelOpenMP_jll (by using the default OpenBLAS backend) eliminates all proprietary licenses from the tree.

5. **Multiple weak copyleft binaries exist but pose no practical risk.** LGPL/CeCILL-C/EPL components (GMP, MPFR, bliss, MUMPS, Ipopt, SuiteSparse) are all used via dynamic linking, which does not trigger copyleft obligations on the calling application.

6. **No unknown or unresolvable licenses.** Every package in the 184-package tree has an identifiable license. All JLL wrapper/binary discrepancies are documented above.

7. **Recommended configuration for license-clean deployment:**
   - Use HiGHS (MIT/MIT) as the primary LP/MIP solver
   - Use Ipopt (MIT wrapper / EPL-2.0 binary) for nonlinear problems
   - Exclude GLPK, MKL, and IntelOpenMP from the project
   - This yields a dependency tree that is entirely MIT/BSD/MPL/EPL/Apache/LGPL/CeCILL-C — all permissive or weak-copyleft with no source disclosure obligations for users who do not modify the dependency source code.
