---
test_id: F-2
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

# F-2: Dependency Tree Enumeration

## Method

Analyzed the resolved `Manifest.toml` (Julia's lockfile equivalent) generated from `Project.toml`.

## Findings

### Direct Dependencies (Project.toml)

10 direct dependencies:

1. GLPK (solver wrapper)
2. HiGHS (solver wrapper)
3. InfrastructureSystems (Sienna core library)
4. Ipopt (solver wrapper)
5. JuMP (optimization modeling language)
6. PowerFlows (power flow algorithms)
7. PowerNetworkMatrices (network matrix computations)
8. PowerSimulations (main package)
9. PowerSystems (power system data model)
10. SCIP (solver wrapper)

### Total Dependency Count

- **183 unique packages** in Manifest.toml
- Of these, 135 have `git-tree-sha1` hashes (registry packages)
- 160 have explicit version numbers
- 23 are Julia stdlib packages (no explicit version, bundled with Julia)
- **51 are `_jll` packages** (precompiled binary wrappers via BinaryBuilder.jl)
- 0 non-registry dependencies (no `path =` or `repo-url =` entries)

### Version Pinning

All dependencies in the Manifest.toml are pinned by:
- Exact version number
- `git-tree-sha1` content hash (immutable, content-addressed)

The `Project.toml` uses semver compat bounds (e.g., `HiGHS = "1"`, `PowerSimulations = "0.27 - 0.33"`), which is standard Julia practice. The Manifest.toml resolves these to exact versions.

### Unpinned Dependencies

None. All 183 dependencies are fully resolved and pinned in the Manifest.toml.

## Assessment

183 total dependencies is a substantial tree, driven largely by 4 solver ecosystems (HiGHS, GLPK, Ipopt, SCIP) each bringing their own binary dependencies. The 51 `_jll` packages are precompiled C/C++/Fortran libraries. This count is high but typical for a Julia optimization project that bundles multiple solver backends. All deps are pinned and reproducible. **Informational** -- the count merits awareness but is not a blocking concern.
