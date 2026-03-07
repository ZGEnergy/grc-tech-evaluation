---
test_id: F-9
tool: powermodels
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-06T00:00:00Z
---

# F-9: Getting Started Integrity

## Result: PASS

## Finding

PowerModels documentation and examples use stable, version-pinned references. No mutable URLs or unpinned remote resources are present in the getting-started materials. Examples reference local test data files bundled with the package.

## Evidence

**Quick Start Guide**(`docs/src/quickguide.md`):

All examples use local file paths for network data:

```julia

using PowerModels
using Ipopt
solve_ac_opf("matpower/case3.m", Ipopt.Optimizer)

```

The data files (`case3.m`, `case3.raw`, `case3_dc.m`) are bundled in the package's `test/data/` directory. No external URLs are fetched at runtime.

**Version pinning in Project.toml**:
PowerModels specifies compat bounds for all dependencies:

```toml

[compat]
InfrastructureModels = "0.6, 0.7"
JSON = "0.21"
JuMP = "1.15"
Memento = "1"
NLsolve = "4"
PrecompileTools = "1"
julia = "1.6"

```

**No mutable URLs**: The quickstart guide, README, and documentation contain no `curl`, `wget`, `download()`, or other network-fetch commands. All references to external resources are:
- GitHub repository URLs (stable, versioned)
- Documentation site (<https://lanl-ansi.github.io/PowerModels.jl/stable/>) -- pinned to "stable" branch
- YouTube presentation links (informational, not required)
- IEEE citation DOI (informational)

**README badge URLs**: Point to CI status (GitHub Actions) and code coverage (Codecov). These are informational badges, not runtime dependencies.

**Installation instructions**: Standard Julia Pkg installation:

```julia

using Pkg
Pkg.add("PowerModels")

```

This resolves via the General Registry with semver constraints. Reproducible via Manifest.toml.

## Implications

The getting-started materials are well-structured for reproducibility. All example data is local. Dependencies are version-bounded. No mutable external resources are required to follow the documentation. A user following the quickstart guide will get reproducible results.
