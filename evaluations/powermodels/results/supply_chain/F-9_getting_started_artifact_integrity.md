---
test_id: F-9
tool: powermodels
dimension: supply_chain
network: N/A
status: qualified_pass
workaround_class: null
timestamp: "2026-03-11T00:00:00Z"
protocol_version: "v9"
skill_version: v1
test_hash: "738f75e3"
---

# F-9: Examine official getting-started examples for version pinning

## Finding

The official documentation links to the `/stable/` URL path (version-pinned release docs) for quickguide and API reference. However, the README references the `/dev/` path for one asset (the logo SVG) and links CI/coverage badges to the `master` branch. The getting-started code examples themselves do not specify version constraints — users are expected to control versions via `Pkg.add(name="PowerModels", version="...")` or Manifest.toml.

## Evidence

### Documentation URL pattern:
- README links docs to: `https://lanl-ansi.github.io/PowerModels.jl/stable/`
- `/stable/` is Documenter.jl's standard stable-release deployment path, updated on each tagged release
- Quick start guide at: `https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/`

#### README flags:
1. Logo asset uses `/dev/` URL: `https://lanl-ansi.github.io/PowerModels.jl/dev/assets/logo.svg` — this is a mutable reference to the in-development branch (cosmetic only, not functional)
2. CI badge links to `master` branch: `https://github.com/lanl-ansi/PowerModels.jl/actions?query=workflow%3ACI` — mutable, but badges are informational only
3. CodeCov badge references `master` branch: mutable but informational

#### Getting-started code examples (from quickguide.md):

```julia

using PowerModels
using Ipopt

solve_ac_opf("matpower/case3.m", Ipopt.Optimizer)

```

No version pin is included in the example. Julia users are expected to manage versioning via their project's `Project.toml` and `Manifest.toml`, which is idiomatic for the Julia ecosystem.

**Julia package management convention:** Unlike Python (where `pip install foo` may pull the latest), Julia's `Pkg.add("PowerModels")` records the installed version in `Manifest.toml` with a `git-tree-sha1`. Re-installing from the same manifest always produces the identical version. The documentation correctly points to `/stable/` for production guidance.

**No mutable download URLs in functional examples:** All code snippets reference network data files (`.m` or `.raw`) by local path. No external data downloads or unversioned artifact fetches are present in the getting-started examples.

## Implications

The qualified pass reflects: (1) documentation correctly uses `/stable/` links, (2) the Julia package manager's Manifest.toml mechanism handles version pinning implicitly, and (3) the two mutable references in the README (logo SVG, CI/coverage badges) are cosmetic and non-functional. Evaluators following the getting-started guide who use Julia's standard workflow will automatically get a version-pinned, reproducible environment.
