---
test_id: F-7
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

# F-7: Air-Gap Installability

## Method

Assessed whether PowerSimulations.jl and all dependencies can be installed on an air-gapped (no internet) network.

## Findings

### Julia Offline Installation Support

Julia's package manager (`Pkg.jl`) supports offline installation through several mechanisms:

1. **Manifest.toml vendoring:** A resolved `Manifest.toml` pins every dependency to exact versions and content hashes. The corresponding source tarballs can be pre-downloaded.

2. **Package server cloning:** Julia downloads packages from `pkg.julialang.org` (a caching CDN). The entire package server content for a given Manifest can be mirrored. Julia supports setting `JULIA_PKG_SERVER` to point to a local mirror.

3. **Depot copying:** A fully instantiated Julia depot (`~/.julia/`) can be copied to an air-gapped machine. This includes all source code, precompiled caches, and artifact binaries. The depot is self-contained.

4. **Artifact mirroring:** JLL binary artifacts are downloaded from `github.com/JuliaBinaryWrappers/` releases. These URLs are deterministic and can be pre-fetched. The `Artifacts.toml` in each JLL package lists the exact URLs and SHA-256 hashes.

### Runtime Network Requirements

- **No runtime network access required.** Once installed, PowerSimulations.jl runs entirely offline.
- Data loading (MATPOWER files, PSS/E files) is local file I/O.
- Solver execution is local computation.
- The only network-dependent feature is `PowerSystemCaseBuilder.jl` (test data downloader), which is not a dependency of this evaluation project.

### Practical Air-Gap Procedure

```bash
# On connected machine:
julia --project=. -e 'using Pkg; Pkg.instantiate()'
# Copy entire ~/.julia/ depot and project directory to air-gapped machine
# Set JULIA_DEPOT_PATH to the copied depot location
```

### Challenges

- The Julia depot can be large (several GB) due to precompiled caches and binary artifacts
- Precompilation is platform-specific -- the depot must be built on the same OS/architecture as the target
- First-time precompilation on the air-gapped machine may be needed if architectures differ

## Assessment

Air-gap installation is achievable via depot copying or package server mirroring. No runtime network access is required. The only practical challenge is the size of the depot (multi-GB), which is an operational concern but not a blocking one. **Pass.**
