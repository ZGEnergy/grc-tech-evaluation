---
test_id: D-1
tool: powersimulations
dimension: accessibility
network: TINY
protocol_version: "v4"
status: qualified_pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T04:15:00Z"
---

# D-1: Install to First Solve

## Result: QUALIFIED PASS

## Finding

PowerSimulations.jl installs successfully via Julia's package manager with no manual
intervention. However, the install-to-first-solve experience involves significant
time investment due to Julia's JIT compilation overhead and the mandatory time series
boilerplate required before any optimization can run.

## Evidence

### Installation

Installation was performed via `Pkg.instantiate()` from a pre-configured `Project.toml`
in the devcontainer (Julia 1.10, Ubuntu 24.04).

- **Direct dependencies:** PowerSystems.jl, PowerSimulations.jl, PowerFlows.jl,
  PowerNetworkMatrices.jl, HiGHS.jl, GLPK.jl, SCIP.jl, Ipopt.jl, JuMP.jl,
  DataFrames.jl, TimeSeries.jl, JSON.jl, Dates (stdlib)
- **Total manifest dependencies:** 183 packages
- **Installation method:** `julia --project=. -e 'using Pkg; Pkg.instantiate()'`
- **Installation issues:** None. All packages resolved and precompiled successfully.

### First-solve barriers

1. **JIT compilation overhead:** First `using PowerSimulations` takes ~15-30s.
   First `build!()` + `solve!()` cycle triggers additional compilation (~40-60s).
   Subsequent runs in same session are fast (<5s).

2. **Time series boilerplate is mandatory:** Even the simplest single-period DCOPF
   requires ~30 LOC of time series setup:
   - Create `SingleTimeSeries` with multiplier values for every generator and load
   - Call `transform_single_time_series!()` to convert to `Deterministic` forecasts
   - This is not obvious from documentation; examples assume multi-period data

3. **MATPOWER data issues:** case39.m has generators with `active_power > Pmax`
   (gen-2: 6.78 > 6.46). PSI logs warnings but does not auto-fix. User must clamp
   manually.

4. **Device model registration required:** Every component type in the system must
   have an explicit device model in the `ProblemTemplate`. Missing any type causes
   build failure. case39 has Lines, Transformer2W, and TapTransformers — all must
   be registered.

5. **Power flow is a separate package:** Users expecting PSI to do power flow
   (DCPF/ACPF) must discover and install PowerFlows.jl separately. PSI only handles
   optimization problems.

### Time to first successful solve

Based on gate test G-1 and expressiveness test A-1:

| Stage | Time |
|-------|------|
| Package installation | ~5 min (first time, with precompilation) |
| JIT compilation (first `using`) | ~15-30s |
| Understanding time series requirement | Significant (not obvious) |
| First DCPF solve (PowerFlows) | ~16.5s total (A-1) |
| First DCOPF solve (PowerSimulations) | ~70s total (A-3) |

### Documentation quality for first solve

- PowerSystems.jl data model docs: Good (component types, accessors well documented)
- PowerSimulations.jl tutorial: Exists but assumes multi-period workflow with CSV data
- Time series setup for MATPOWER data: Not documented as a standalone recipe
- PowerFlows.jl docs: Minimal but API is simple enough to figure out

## Implications

The install process itself is clean (no compilation failures, no dependency conflicts).
The barrier to first solve is the conceptual overhead: understanding that PSI is a
multi-period simulation framework (not a single-period OPF solver), that time series
are mandatory, and that power flow is in a separate package. A user familiar with
traditional power system tools (MATPOWER, pandapower) would find the paradigm shift
significant.

For the accessibility criterion, this represents moderate friction — the tool works
but requires non-trivial domain knowledge of PSI's architecture before a first solve
is achievable.
