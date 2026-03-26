---
test_id: F-7
tool: powermodels
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: "2026-03-13T23:00:00Z"
protocol_version: v10
skill_version: v1
test_hash: "462a162d"
---

# F-7: Air-gap installability assessment

## Finding

PowerModels.jl and all its dependencies can be installed offline using Julia's built-in depot-caching and package-bundling mechanisms. No runtime network access is required. The devcontainer confirms this: all packages and JLL binaries are pre-downloaded to `/opt/julia-depot/` and the environment resolves from that local cache.

## Evidence

### Julia offline install mechanisms

1. **Local depot cache:** The `JULIA_DEPOT_PATH` environment variable can point to a local directory containing pre-downloaded packages and artifacts. Julia's package manager resolves from the depot without internet access if all required packages are present.

2. **`Pkg.offline(true)` mode:** Julia 1.8+ supports `Pkg.offline(true)` which prevents any network access during package operations and only uses locally available packages.

3. **Tarball bundling:** Custom scripts or `Pkg` utilities can collect all packages from a resolved manifest into an archive for transfer to an air-gapped machine.

4. **JLL artifact caching:** All compiled binary artifacts (`Ipopt_jll`, `HiGHS_jll`, `SCIP_jll`, etc.) are stored as content-addressed archives in the depot's `artifacts/` directory. These can be pre-populated offline.

### Devcontainer verification

The devcontainer at `/opt/julia-depot/` contains all artifact directories and all package sources required for PowerModels 0.21.5 with its full dependency graph. The environment instantiates fully from this local cache.

### Runtime network access

No PowerModels.jl dependency performs runtime network access. JSON parsing, matrix operations, and solver calls are all self-contained. JLL binaries load from local paths via `Libdl.dlopen`.

### Constraints for air-gap transfer

- Must pre-populate both the `packages/` and `artifacts/` subdirectories of the Julia depot
- Must include a Julia General Registry snapshot (or use a local registry mirror)
- Total depot size for this project: approximately 1-2 GB (dominated by compiled solver binaries)
- Julia runtime itself must be available (offline installer available from julialang.org)

## Implications

Air-gap installability is fully supported by Julia's package ecosystem design. Deployment to restricted networks requires transferring the Julia depot (packages + artifacts) alongside the project. This is operationally non-trivial (large transfer size) but architecturally supported, with no fundamental blocking issues. No runtime network dependencies were identified.
