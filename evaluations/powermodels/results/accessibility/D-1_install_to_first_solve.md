---
test_id: D-1
tool: powermodels
dimension: accessibility
network: N/A
status: qualified_pass
workaround_class: null
timestamp: 2026-03-11T00:00:00Z
protocol_version: "v9"
skill_version: v1
test_hash: "78db6dec"
---

# D-1: Install-to-First-Solve

## Summary

PowerModels.jl is installable as a pure Julia package via the standard `Pkg` workflow. The devcontainer pre-installs the environment; from a clean system the full path is: install Julia, clone the repo, run `julia --project=. -e 'using Pkg; Pkg.instantiate()'`. No C extensions, no system libraries beyond what Julia ships with, and no solver-specific system dependencies (HiGHS and Ipopt are vendored as Julia artifacts).

Status is **qualified_pass**: installation itself is frictionless, but the Julia JIT compilation overhead and an undocumented API signature difference impose a meaningful first-use tax.

## Installation Steps

1. **Julia 1.10** — download and install from `https://julialang.org/downloads/`. No system package manager needed; the binary is self-contained.
2. **Clone repo / create project** — any directory with a `Project.toml` and `Manifest.toml` defines the environment.
3. **Instantiate** — `julia --project=. -e 'using Pkg; Pkg.instantiate()'`. On first run this downloads and compiles all packages to native code. Duration: 5–15 minutes on first install (building Ipopt, HiGHS native code); subsequent runs reuse the precompiled cache.
4. **Verify** — `julia --project=. verify_install.jl`

## Measured Timing (cold start, precompile cache warm)

| Measurement | Value |
|---|---|
| Julia process startup to `using PowerModels, HiGHS` ready | ~1.0 s (cache warm) |
| `parse_file` for case39.m | ~0.2 s |
| `solve_dc_opf` first invocation (JIT included) | 1.33 s |
| Total wall-clock from process launch to printed result | 2.96 s |
| Solve-only time (excluding startup/JIT) | 1.33 s |

Note: these timings include loading precompiled package cache but not recompilation. The first `Pkg.instantiate()` from zero takes materially longer (minutes, not seconds) due to native code compilation of Ipopt and HiGHS.

## API Friction on First Use

The official documentation quickstart (and several Stack Overflow examples) show:

```julia

solve_dc_opf(data, DCPPowerModel, optimizer_with_attributes(...))

```

This is **incorrect for v0.21.5**. The actual signature is:

```julia

solve_dc_opf(data, optimizer_with_attributes(...))

```

`solve_dc_opf` is a thin wrapper that hardcodes `DCPPowerModel` internally. The 3-argument form `solve_opf(data, DCPPowerModel, optimizer)` is the generic version. This mismatch is a first-use friction point: the incorrect call produces a `MethodError` that mentions `InitializeInfrastructureModel` rather than pointing directly at the API mismatch.

## Result

`termination_status: OPTIMAL` — first solve succeeds cleanly. Pass conditions met.

## Pass/Fail Rationale

**qualified_pass**: Installation is zero-friction for a Julia user. The JIT overhead and the API signature discovery issue add friction for new users, but neither blocks the first successful solve.
