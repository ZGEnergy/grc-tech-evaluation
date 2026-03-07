---
test_id: F-7
tool: powermodels
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-06T00:00:00Z
---

# F-7: Airgap Installability

## Result: PASS

## Finding

PowerModels.jl can be installed offline using Julia's package depot cloning mechanism. All runtime dependencies are bundled in the depot (pure Julia source + pre-compiled JLL artifacts). No runtime network access is required after installation.

## Evidence

**Offline installation mechanism**: Julia's package system supports fully offline operation via depot cloning:

1. On an internet-connected machine, install all packages and run `Pkg.instantiate()`. This populates the Julia depot (`~/.julia/` or custom `JULIA_DEPOT_PATH`) with:
   - Package source code under `packages/`
   - Pre-compiled artifacts (solver binaries) under `artifacts/`
   - Registry metadata under `registries/`
   - Compiled caches under `compiled/`

2. Copy the entire depot directory to the airgapped machine.

3. Set `JULIA_DEPOT_PATH` to point to the copied depot. All packages resolve from local cache.

**Verified in devcontainer**: The evaluation environment uses a pre-populated depot at `/opt/julia-depot/`. The container successfully loads PowerModels, solves problems, and accesses all solver binaries without network access during runtime. The Manifest.toml lockfile ensures the same versions are used.

**Runtime network requirements**: None. PowerModels does not make any network calls during execution. Data files are loaded from local disk. Solver binaries are pre-compiled shared libraries loaded from the depot.

**JLL artifacts**: All 35 JLL packages store their pre-built binaries in the `artifacts/` directory, indexed by content hash. These are downloaded once during `Pkg.instantiate()` and never fetched at runtime.

**Alternative offline method**: Julia also supports creating a "sysimage" via PackageCompiler.jl, which bundles all packages into a single shared library. This eliminates even the depot dependency.

## Implications

Airgap deployment is straightforward using Julia's built-in depot mechanism. The evaluation environment itself demonstrates this pattern -- the devcontainer has a pre-populated depot that works without network access. No additional tooling or workarounds are needed.
