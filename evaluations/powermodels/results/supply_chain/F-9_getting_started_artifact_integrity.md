---
test_id: F-9
tool: powermodels
dimension: supply_chain
network: N/A
status: qualified_pass
workaround_class: null
timestamp: "2026-03-13T23:00:00Z"
protocol_version: v10
skill_version: v1
test_hash: "0aba8d44"
---

# F-9: Getting-started artifact integrity

## Finding

The official documentation links to the `/stable/` URL path (version-pinned release docs) for the quickguide and API reference. Getting-started code examples reference only local file paths with no external downloads. However, the README contains mutable references: a `/dev/` path for the logo SVG, and CI/coverage badges linked to the `master` branch. Code examples do not include explicit version pins, relying instead on Julia's Manifest.toml for implicit version locking.

## Evidence

### Documentation URL pattern

- README links primary docs to: `https://lanl-ansi.github.io/PowerModels.jl/stable/`
- `/stable/` is Documenter.jl's standard stable-release deployment path, updated only on tagged releases
- Quick start guide at: `https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/`
- All substantive links (network data spec, formulation details, experiment results) point to `/stable/`

### Mutable references in README

1. **Logo asset uses `/dev/` URL:** `https://lanl-ansi.github.io/PowerModels.jl/dev/assets/logo.svg` — mutable reference to development branch (cosmetic only, not functional)
2. **CI badge:** `https://github.com/lanl-ansi/PowerModels.jl/workflows/CI/badge.svg` — mutable, informational only
3. **Codecov badge:** `https://codecov.io/gh/lanl-ansi/PowerModels.jl/branch/master/graph/badge.svg` — references `master` branch, informational only
4. **CONTRIBUTING.md link:** `https://github.com/lanl-ansi/PowerModels.jl/blob/master/CONTRIBUTING.md` — references `master` branch

### Getting-started code examples (from quickguide)

```julia
using PowerModels
using Ipopt

solve_ac_opf("matpower/case3.m", Ipopt.Optimizer)
```

No version pin is included in the example. The documentation does not provide explicit guidance on version pinning.

### Julia ecosystem version management

Julia's `Pkg.add("PowerModels")` records the installed version in `Manifest.toml` with a `git-tree-sha1`. Re-installing from the same manifest always produces the identical version. This provides implicit version locking through the package manager rather than explicit pins in code examples, which is idiomatic for Julia.

### No mutable download URLs in functional examples

All code snippets reference network data files (`.m` or `.raw`) by local path. No external data downloads or unversioned artifact fetches are present in the getting-started examples.

## Implications

The qualified pass reflects: (1) documentation correctly uses `/stable/` links for substantive content, (2) the Julia package manager's Manifest.toml mechanism handles version pinning implicitly, (3) mutable references in the README (logo SVG, CI/coverage badges, CONTRIBUTING.md link) are cosmetic and non-functional, and (4) no guidance is given to users about pinning versions in examples — users must know to commit their Manifest.toml. Evaluators following the getting-started guide who use Julia's standard workflow will get a version-pinned environment, but only if they understand Manifest.toml semantics.
