---
test_id: F-9
tool: powermodels
dimension: supply_chain
status: qualified_pass
timestamp: 2026-03-05
---

# F-9: Getting Started Integrity

## Finding

The official PowerModels.jl getting started guide does not pin package versions in its examples. Installation instructions use `Pkg.add("PowerModels")` without version constraints, and example code uses unversioned imports. The documentation is auto-generated from source and deployed via CI.

## Evidence

**Official quick start** (<https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/>):

```julia
using PowerModels
using Ipopt

solve_ac_opf("matpower/case3.m", Ipopt.Optimizer)
solve_dc_opf("matpower/case3.m", Ipopt.Optimizer)

```

**Version pinning assessment**:
- No version specifier in `Pkg.add()` instructions
- No `Project.toml` / `Manifest.toml` provided for examples
- Examples reference bundled test data (`matpower/case3.m`) which ships with the package
- Documentation is versioned by release tag (stable vs dev), but example code within each version page is not pinned

**Documentation infrastructure**:
- Built via Documenter.jl
- Deployed via GitHub Actions (`documentation.yml` + `documentation-deploy.yml`)
- Versioned docs available at `/stable/` and `/dev/` paths
- Source: `docs/src/quickguide.md` in repository

**Solver choice**: Examples use `Ipopt.Optimizer` but do not explain solver selection tradeoffs or list alternative solvers in the quick start.

Source: <https://lanl-ansi.github.io/PowerModels.jl/stable/quickguide/,> <https://github.com/lanl-ansi/PowerModels.jl/blob/master/docs/src/quickguide.md>

## Implications

The lack of version pinning in examples is standard for Julia package documentation but means a new user running the quick start may get different results depending on when they install. The versioned documentation URLs partially mitigate this (the "stable" docs correspond to the latest release tag). The bundled test data is a positive -- examples do not depend on external data downloads. For reproducibility-sensitive deployments, users should create their own `Project.toml` with explicit version bounds, as demonstrated in this evaluation's setup.
