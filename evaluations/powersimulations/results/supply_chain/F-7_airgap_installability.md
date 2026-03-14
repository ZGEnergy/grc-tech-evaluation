---
test_id: F-7
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "462a162d"
status: informational
workaround_class: null
timestamp: "2026-03-14T00:00:00Z"
---

# F-7: Air-Gap Installability

## Result: INFORMATIONAL

## Summary

PowerSimulations.jl and its full dependency tree can be installed in an air-gapped
environment using Julia's built-in offline capabilities. The approach requires
pre-fetching 184 packages (including 52 JLL binary artifacts) and serving them from
a local registry clone. No runtime network access is required after installation.

## Air-Gap Installation Methods

### Method 1: Local Registry Mirror + Artifact Server

Julia's package manager supports the `JULIA_PKG_SERVER` environment variable, which
redirects all package and artifact downloads to a local server.

**Steps:**

1. **Clone the General Registry** on the connected side:
   ```bash
   git clone https://github.com/JuliaRegistries/General.git
   ```

2. **Pre-fetch all packages and artifacts** using the Manifest.toml:
   ```julia
   # On connected machine with identical Manifest.toml
   using Pkg
   Pkg.instantiate()  # downloads everything
   ```

3. **Copy the Julia depot** (`~/.julia/` or `$JULIA_DEPOT_PATH`) to the air-gapped
   machine. The depot contains:
   - `packages/` -- all package source code
   - `artifacts/` -- all JLL binary artifacts
   - `registries/` -- the General Registry clone
   - `compiled/` -- precompiled caches (architecture-specific)

4. **Set environment variables** on the air-gapped machine:
   ```bash
   export JULIA_DEPOT_PATH=/path/to/copied/depot
   export JULIA_PKG_OFFLINE=true  # prevents any network access
   ```

5. **Instantiate from Manifest:**
   ```julia
   cd("evaluations/powersimulations")
   using Pkg
   Pkg.instantiate()  # uses local depot, no network
   ```

### Method 2: Bundled Depot Archive

Package the entire Julia depot as a tarball:

```bash
# On connected machine after Pkg.instantiate()
tar czf julia-depot-powersimulations.tar.gz ~/.julia/
```

Transfer and extract on the air-gapped machine. Set `JULIA_DEPOT_PATH` accordingly.

### Method 3: Container Image

Build a container image with all dependencies pre-installed (as done in this
evaluation's devcontainer). Transfer the image to the air-gapped environment.

```bash
docker save grc-eval-devcontainer:latest | gzip > devcontainer.tar.gz
# Transfer to air-gapped machine
docker load < devcontainer.tar.gz
```

## Dependency Footprint

| Category | Count | Approx. Size |
|----------|-------|--------------|
| Julia packages (source) | 132 | ~200 MB |
| JLL binary packages | 52 | ~500 MB |
| Julia runtime | 1 | ~400 MB |
| **Total depot size** | **184 packages** | **~1.1 GB** |

The 52 JLL packages include binary artifacts for the target platform. Only the
platform-specific artifacts need to be fetched (e.g., Linux x86_64 glibc only).

## Runtime Network Access

**No runtime network access is required.** Verified by scanning PowerSimulations.jl
and PowerSystems.jl source code for HTTP/Downloads module references:

- PowerSimulations source: **No HTTP or Downloads references found**
- PowerSystems source: **No HTTP or Downloads references found**

The tool does not phone home, check for updates, validate licenses, or download
data at runtime. All data is loaded from local files (MATPOWER .m files, CSV, etc.).

## `JULIA_PKG_OFFLINE` Mode

Julia provides a built-in offline mode:

```bash
export JULIA_PKG_OFFLINE=true
```

When set, the package manager will:
- Refuse all network connections
- Use only locally cached packages and artifacts
- Error clearly if a required package is not in the local depot

This provides a hard guarantee against accidental network access during package
operations.

## Challenges and Considerations

### 1. Large Dependency Count (184 packages)

The full transitive dependency tree is large. Missing a single package or artifact
will cause `Pkg.instantiate()` to fail in offline mode. The depot copy must be
complete.

**Mitigation:** Use `Pkg.instantiate()` on a connected machine with the exact
`Manifest.toml`, then copy the entire depot.

### 2. Platform-Specific JLL Artifacts

JLL binary artifacts are platform-specific. The connected machine must download
artifacts for the target platform, not its own platform (if different).

**Mitigation:** Use `Pkg.instantiate()` on a machine with the same OS/architecture
as the target, or use `Pkg.Artifacts.ensure_all_artifacts_installed()` with
platform overrides.

### 3. Julia Version Pinning

The Manifest.toml is tied to a specific Julia version (1.10 in our case). The
air-gapped machine must use the same Julia minor version.

### 4. Precompilation

Julia precompiles packages to native code on first `using`. This is
CPU-architecture-specific and takes significant time (10-30 minutes for the full
stack). Pre-compilation can be done on the connected machine if the architecture
matches, but the compiled cache in `~/.julia/compiled/` may not transfer between
machines with different CPU features.

**Mitigation:** Run precompilation once on the air-gapped machine after depot
transfer. This is a one-time cost.

## Assessment

Air-gap installation is **feasible but operationally heavy**. The 184-package
dependency tree with 52 binary artifacts requires careful depot management. Julia's
`JULIA_PKG_OFFLINE=true` mode and depot-based architecture were designed for this
use case. The container image approach (Method 3) is the most reliable path for
production air-gap deployments.
