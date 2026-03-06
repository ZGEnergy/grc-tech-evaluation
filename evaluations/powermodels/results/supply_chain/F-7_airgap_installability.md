---
test_id: F-7
tool: powermodels
dimension: supply_chain
status: qualified_pass
timestamp: 2026-03-05
---

# F-7: Airgap Installability

## Finding

Julia's Pkg.jl supports an offline mode and package environments can be pre-populated on a connected machine then transferred. However, there is no first-class "bundle" or "vendoring" mechanism for airgapped installation. JLL binary packages add complexity because they require platform-matched pre-compiled binaries.

## Evidence

**Julia offline mode**: `Pkg.offline(true)` or `JULIA_PKG_OFFLINE=true` environment variable causes Pkg to only consider already-downloaded packages. This works when packages have been pre-downloaded but does not provide a bundle/export mechanism.

**Practical airgap approaches** (from Julia community discourse and Pkg.jl issues):

1. **Copy depot**: Copy `~/.julia/` (the Julia depot) from a connected machine with matching OS/architecture. This includes compiled packages, JLL binaries, and registry data. Fragile for JLL packages with system library dependencies.

2. **Local registry**: Create a local package registry pointing to vendored package sources. Requires manual setup via LocalRegistry.jl.

3. **Container-based**: Build a Docker/Singularity container with all packages pre-installed. Most reliable approach.

**Known issues**:
- GitHub issue JuliaLang/Pkg.jl#2741 "Installation of Julia packages for fully offline environments" remains open, indicating this is a recognized gap.
- JLL packages download platform-specific binaries from GitHub Releases at install time, which fails in airgapped environments unless the depot is pre-populated.
- No equivalent to Python's `pip download` + `pip install --no-index` workflow.

**Manifest.toml**: The evaluation environment's `Manifest.toml` pins all 114 packages to exact versions, providing reproducibility if the packages can be obtained.

Source: <https://github.com/JuliaLang/Pkg.jl/issues/2741,> <https://discourse.julialang.org/t/offline-installation-of-julia-packages/20083>

## Implications

Airgap installation is achievable but requires non-trivial setup (depot copying or containerization). The lack of a first-class vendoring/bundle command is a gap compared to Python's `pip download` or Go's module vendoring. For government/secure environments, the container approach (Docker image with pre-installed packages) is the most practical path. This is a Julia ecosystem limitation, not specific to PowerModels.jl.
