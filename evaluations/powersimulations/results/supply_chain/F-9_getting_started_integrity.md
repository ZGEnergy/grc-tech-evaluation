---
test_id: F-9
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T05:00:00Z"
---

# F-9: Getting-Started Artifact Integrity

## Method

Examined official tutorials and getting-started examples in the PowerSimulations.jl repository for version pinning and artifact integrity.

## Findings

### Tutorial Files Examined

- `docs/src/tutorials/decision_problem.jl` -- primary getting-started tutorial
- `docs/src/tutorials/pcm_simulation.jl` -- production cost modeling tutorial

### Version Pinning in Tutorials

The tutorials use bare `using` statements without version specifications:

```julia
using PowerSystems
using PowerSimulations
using HydroPowerSimulations
using PowerSystemCaseBuilder
using HiGHS
```

**No version pins are specified in tutorial code.** This is standard Julia practice -- version pinning is handled by the `Project.toml`/`Manifest.toml` of the documentation build environment, not in the source code itself.

### Documentation Build Reproducibility

The documentation is built via Documenter.jl, which uses the repo's own `docs/Project.toml` to define dependency versions. Users following tutorials are expected to create their own `Project.toml` with appropriate `[compat]` bounds.

### External Data Dependencies

Tutorials use `PowerSystemCaseBuilder.jl` to download test systems:

```julia
sys = build_system(PSISystems, "modified_RTS_GMLC_DA_sys")
```

This downloads data from GitHub at runtime. The data is versioned (tied to PowerSystemCaseBuilder releases) but requires network access on first use.

### URLs and References

- No unversioned download URLs in tutorials
- No references to `main` branch for installation
- Documentation is versioned by release (stable/dev) on the documentation site

### Comparison to Ideal

| Criterion | Status |
|-----------|--------|
| Examples reference specific release version | Partial -- docs are versioned, code uses `using` without version |
| No unversioned downloads | Yes |
| No mutable URLs | Yes |
| No `main` branch references for install | Yes |
| Reproducible environment specification | Yes -- via Project.toml/Manifest.toml |

## Assessment

Tutorials follow standard Julia conventions. They do not pin versions in source code (relying instead on the package manager's lockfile mechanism), which is appropriate for the ecosystem. The use of `PowerSystemCaseBuilder.jl` for test data introduces a runtime download dependency, but the data is versioned. No unversioned tarballs or mutable URLs are used. **Informational** -- the lack of explicit version pins in tutorial code is a minor documentation gap, mitigated by Julia's lockfile-based reproducibility model.
