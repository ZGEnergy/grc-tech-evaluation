---
test_id: D-1
tool: powermodels
dimension: accessibility
network: N/A
status: qualified_pass
workaround_class: null
timestamp: 2026-03-13T23:00:00Z
protocol_version: v10
skill_version: v1
test_hash: "9be8107b"
---

# D-1: Install-to-First-Solve

## Summary

PowerModels.jl is installable as a pure Julia package via the standard `Pkg` workflow. The devcontainer pre-installs the environment; from a clean system the full path is: install Julia, clone the repo, run `julia --project=. -e 'using Pkg; Pkg.instantiate()'`. No C extensions, no system libraries beyond what Julia ships with, and no solver-specific system dependencies (HiGHS and Ipopt are vendored as Julia artifacts).

Status is **qualified_pass**: installation itself is frictionless, but the Julia JIT compilation overhead and an undocumented API signature difference impose a meaningful first-use tax.

## Installation Steps

1. **Julia 1.10** -- download and install from `https://julialang.org/downloads/`. No system package manager needed; the binary is self-contained.
2. **Clone repo / create project** -- any directory with a `Project.toml` and `Manifest.toml` defines the environment.
3. **Instantiate** -- `julia --project=. -e 'using Pkg; Pkg.instantiate()'`. On first run this downloads and compiles all packages to native code. Duration: 5-15 minutes on first install (building Ipopt, HiGHS, SCIP native code); subsequent runs reuse the precompiled cache.
4. **Verify** -- `julia --project=. verify_install.jl`

## Environment Configuration

The evaluation `Project.toml` declares 8 dependencies:

| Package | Version | Purpose |
|---------|---------|---------|
| PowerModels | 0.21.x | Core power systems library |
| JuMP | 1.x | Mathematical optimization framework |
| HiGHS | 1.x | LP/QP solver |
| Ipopt | 1.x | NLP solver |
| SCIP | 0.11.x | MILP/MINLP solver |
| GLPK | 1.x | LP/MILP solver |
| DataFrames | any | Tabular data |
| CSV | any | File export |

Julia 1.10 is the minimum required version. The `Manifest.toml` pins exact dependency versions for reproducibility.

## Measured Timing (cold start, precompile cache warm)

| Measurement | Value |
|---|---|
| Julia process startup to `using PowerModels, HiGHS` ready | ~1.0 s (cache warm) |
| `parse_file` for case39.m | ~0.2 s |
| `solve_dc_opf` first invocation (JIT included) | 1.33 s |
| Total wall-clock from process launch to printed result | 2.96 s |
| Solve-only time (excluding startup/JIT) | 1.33 s |

Note: these timings include loading precompiled package cache but not recompilation. The first `Pkg.instantiate()` from zero takes materially longer (minutes, not seconds) due to native code compilation of Ipopt, HiGHS, and SCIP.

## API Friction on First Use

The official documentation quickstart shows:

```julia
solve_ac_opf("matpower/case3.m", Ipopt.Optimizer)
solve_dc_opf("matpower/case3.m", Ipopt.Optimizer)
```

These are 2-argument convenience wrappers. The generic 3-argument form is:

```julia
solve_opf(data, ACPPowerModel, Ipopt.Optimizer)
```

Some online examples (and older documentation) show a 3-argument form for `solve_dc_opf` that is invalid in v0.21.5:

```julia
# INVALID -- produces MethodError
solve_dc_opf(data, DCPPowerModel, optimizer)
```

The error message mentions `InitializeInfrastructureModel` rather than pointing at the API mismatch, which is a discoverability gap for new users.

## Issues Encountered

| # | Issue | Severity | Resolution |
|---|-------|----------|------------|
| 1 | JIT compilation delay (~5-15 min first install) | Medium | One-time cost; Julia design characteristic |
| 2 | API signature mismatch between quickstart and some online examples | Low | Use 2-arg form for convenience functions; 3-arg for `solve_opf` |
| 3 | `verify_install.jl` uses `OPTIMAL` constant requiring JuMP import | Low | Add `using JuMP` or compare to string |

## Result

`termination_status: OPTIMAL` -- first solve succeeds cleanly. Pass conditions met.

## Pass/Fail Rationale

**qualified_pass**: Installation is zero-friction for a Julia user. The JIT overhead and the API signature discovery issue add friction for new users, but neither blocks the first successful solve. Total wall-clock from `Pkg.instantiate()` to first successful solve result is under 20 minutes including compilation; under 3 seconds on subsequent runs.
