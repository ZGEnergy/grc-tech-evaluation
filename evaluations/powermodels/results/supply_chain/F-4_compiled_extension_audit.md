---
test_id: F-4
tool: powermodels
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: "2026-03-11T00:00:00Z"
protocol_version: "v9"
skill_version: v1
test_hash: "4fd147b3"
---

# F-4: Identify compiled components in the execution path

## Finding

PowerModels.jl itself is pure Julia with no compiled extensions. All compiled components are in the solver JLL packages (Ipopt, HiGHS, GLPK, SCIP), where native shared libraries are wrapped by Julia bindings. Source code is available for all major compiled components; binaries are reproducibly built from source via the JuliaPackaging/Yggdrasil build recipes.

## Evidence

**PowerModels.jl itself:** Pure Julia source code. No `ccall`, no C extensions, no Fortran code, no binary artifacts. Verified by inspecting `/opt/julia-depot/packages/PowerModels/VCmhH/src/` — all `.jl` files.

### Compiled components in the execution path:

| Component | Type | Location | Source available? | Buildable from source? |
|-----------|------|----------|-------------------|----------------------|
| libipopt.so.3 | C++ NLP solver | `/opt/julia-depot/artifacts/70465b8ab4c5555d0a58aeb9b5069e4a814f3df0/lib/libipopt.so.3` | Yes — <https://github.com/coin-or/Ipopt> | Yes — standard CMake build |
| libmumps_seq.so | Fortran sparse linear solver (Ipopt dependency) | via MUMPS_seq_jll artifact | Yes — <https://github.com/JuliaSparse/MUMPS_seq_jll.jl> + source at mumps-solver.org | Yes — standard Fortran/C build |
| libhighs.so.1.13.1 | C++ LP/MIP/QP solver | `/opt/julia-depot/artifacts/57846bf52e8d91e2d6dfef3b0e474315208dc524/lib/libhighs.so.1.13.1` | Yes — <https://github.com/ERGO-Code/HiGHS> | Yes — CMake build |
| libglpk.so.40 | C LP/MIP solver | `/opt/julia-depot/artifacts/bc64c29f1b72c24f25fad29b5e5fbe3e0d8bf7b0/lib/libglpk.so.40` | Yes — <https://www.gnu.org/software/glpk/> | Yes — Autoconf build |
| libscip.so (SCIP) | C++ MIP solver | via SCIP_jll artifact | Yes — <https://www.scipopt.org> (source tarball registration required) | Yes — CMake build |
| libspral.so (SPRAL) | Fortran/C sparse linear solver | via SPRAL_jll | Yes — <https://github.com/ralna/spral> | Yes |
| OpenBLAS / libblastrampoline | BLAS/LAPACK | stdlib | Yes | Yes |

**JLL build infrastructure:** All JLL packages (e.g., `Ipopt_jll`, `HiGHS_jll`) are built via the [JuliaPackaging/Yggdrasil](https://github.com/JuliaPackaging/Yggdrasil) repository using standardized build recipes. The build logs are public and linked from each JLL package's GitHub repository.

**Artifact verification:** Every artifact in `Manifest.toml` includes a `git-tree-sha1` hash, enabling integrity verification. Julia's package manager verifies this hash on download.

**METIS_jll, Hwloc_jll, XML2_jll, Zlib_jll, Bzip2_jll:** Additional compiled dependencies in the SCIP/HiGHS/Ipopt call chain. All are OSS with available source code.

No opaque proprietary binaries were identified in the execution path.

## Implications

All compiled components have publicly available source code and standard build toolchains. The JLL packaging system provides reproducible binary builds. No black-box or proprietary binaries exist in the standard PowerModels execution path. This is a clean result for supply chain inspectability.
