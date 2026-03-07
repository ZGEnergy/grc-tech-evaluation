---
test_id: F-2
tool: powermodels
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
timestamp: 2026-03-06T00:00:00Z
---

# F-2: Dependency Tree

## Result: INFORMATIONAL

## Finding

The evaluation environment Manifest.toml contains 114 total packages: 79 third-party packages and 35 JLL binary wrapper packages. PowerModels itself has 8 direct dependencies (6 third-party + 2 stdlib). The evaluation project adds 5 solver packages (GLPK, HiGHS, Ipopt, JuMP, SCIP) as direct dependencies.

## Evidence

**PowerModels direct dependencies**(from PowerModels/Project.toml):
- InfrastructureModels v0.7.8
- JSON v0.21.4
- JuMP v1.29.4
- LinearAlgebra (stdlib)
- Memento v1.4.1
- NLsolve v4.5.1
- PrecompileTools v1.2.1
- SparseArrays (stdlib)

**Full manifest**(`Pkg.status(mode=Pkg.PKGMODE_MANIFEST)`): 114 packages total.

**Dependency depth**: PowerModels -> JuMP -> MathOptInterface -> MutableArithmetics (4 levels typical). Solver JLL chains add depth (e.g., Ipopt_jll -> MUMPS_seq_jll -> METIS_jll).

**JLL packages (35)**: ASL_jll, Bzip2_jll, CompilerSupportLibraries_jll, GLPK_jll, GMP_jll, HiGHS_jll, Hwloc_jll, Ipopt_jll, LibCURL_jll, LibGit2_jll, LibSSH2_jll, Libiconv_jll, METIS_jll, MUMPS_seq_jll, MbedTLS_jll, MozillaCACerts_jll, Ncurses_jll, OpenBLAS32_jll, OpenBLAS_jll, OpenLibm_jll, OpenSpecFun_jll, Readline_jll, SCIP_PaPILO_jll, SCIP_jll, SPRAL_jll, SuiteSparse_jll, XML2_jll, Xorg_libpciaccess_jll, Zlib_jll, bliss_jll, boost_jll, libblastrampoline_jll, nghttp2_jll, oneTBB_jll, p7zip_jll.

**Pinning**: The evaluation project's Project.toml specifies compat bounds (e.g., `PowerModels = "0.21"`, `JuMP = "1"`, `HiGHS = "1"`). The Manifest.toml is a full lockfile with exact versions and git-tree-sha1 hashes. Packages marked with a dagger symbol in `Pkg.status` output are constrained from upgrading by compat restrictions.

**Unpinned deps**: All dependencies have compat entries in their upstream Project.toml files. Julia's Pkg resolver enforces semver-compatible ranges.

## Implications

114 packages is a moderate dependency count. The majority of dependencies come from solver JLL packages (SCIP brings in boost, oneTBB, METIS, MUMPS, etc.). PowerModels core is relatively lean with only 6 non-stdlib direct deps. The Manifest.toml lockfile ensures reproducible builds.
