---
test_id: D-3
tool: powersimulations
dimension: accessibility
network: N/A
protocol_version: "v10"
skill_version: "v1"
test_hash: "b9d3ff07"
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: null
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: null
solver: null
timestamp: "2026-03-14T00:00:00Z"
---

# D-3: Example Verification

## Result: INFORMATIONAL

## Finding

The PowerSimulations.jl documentation provides **2 tutorials** and **7 how-to guides**.
Both tutorials depend on `PowerSystemCaseBuilder.jl` for test data, which is **not included
in a standard PSI installation** and is not listed as a dependency. Of the tutorials that
could be adapted to run, the core API patterns (build/solve/read results) work correctly,
but the data loading step fails without substitution. The PowerFlows.jl tutorial (1 tutorial)
works with MATPOWER file substitution for the test system.

## Evidence

### Inventory of Official Examples

#### PowerSimulations.jl Tutorials (2)

| # | Tutorial | Runs Unmodified? | Issue |
|---|----------|-----------------|-------|
| 1 | Single-step Decision Problem | **No** | Requires `PowerSystemCaseBuilder` + `HydroPowerSimulations` |
| 2 | Multi-stage PCM Simulation | **No** | Requires `PowerSystemCaseBuilder` + `HydroPowerSimulations` |

**Blocker:** Both tutorials begin with:
```julia
using PowerSystemCaseBuilder
sys = build_system(PSITestSystems, "modified_RTS_GMLC_DA_sys")
```

`PowerSystemCaseBuilder` is a separate package that downloads pre-built test systems from
NREL's data repository. It is not a dependency of PowerSimulations.jl and is not included
in the evaluation environment's `Project.toml`. Installing it would pull additional
dependencies and require network access to download ~100 MB of test system data.

**Adaptation attempt:** Substituting `System("case39.m")` for the test system builder
call would require also removing `HydroPowerSimulations` formulations (hydro generators
exist in RTS-GMLC but not in case39) and adjusting the `ProblemTemplate` device models.
This is not a trivial substitution — it requires understanding which formulations apply
to which generator types.

#### PowerSimulations.jl How-To Guides (7)

| # | Guide | Standalone Runnable? | Notes |
|---|-------|---------------------|-------|
| 1 | Register a variable | No | Conceptual, requires existing model context |
| 2 | Create problem template | No | Conceptual, no complete runnable example |
| 3 | Read simulation results | No | Requires completed simulation |
| 4 | Debug infeasible models | Partially | Shows patterns but needs model context |
| 5 | Configure logging | Yes | Utility guide, not a power system example |
| 6 | Simulation recorder | No | Requires completed simulation |
| 7 | Parallel simulations | No | Requires simulation infrastructure |

The how-to guides are **reference patterns**, not self-contained runnable examples. They
show code snippets in context but do not provide copy-paste-run scripts.

#### PowerFlows.jl Tutorial (1)

| # | Tutorial | Runs Unmodified? | Issue |
|---|----------|-----------------|-------|
| 1 | Solving a Power Flow | **No** (minor fix) | Uses `PowerSystemCaseBuilder`; substituting `System("case39.m")` works |

**Adaptation:** The PowerFlows.jl tutorial uses `build_system(MatpowerTestSystems, "matpower_case5_sys")`.
Replacing this with `System("/path/to/case39.m")` produces a working DCPF and ACPF example.
The tutorial correctly documents:
- DC result type: `Dict{String, Dict{String, DataFrame}}` (nested under time step key)
- AC result type: `Dict{String, DataFrame}` (flat)
- That AC power flow may return `missing` on convergence failure

**Verified working** in devcontainer with MATPOWER file substitution:
```
DC result type: Dict{Union{Char, String}, Dict{String, DataFrames.DataFrame}}
AC result type: Dict{String, DataFrames.DataFrame}
```

### Summary

| Category | Total | Run Unmodified | Run with Fixes | Cannot Run |
|----------|-------|---------------|---------------|------------|
| PSI tutorials | 2 | 0 | 0* | 2 |
| PSI how-to guides | 7 | 0 | 0 | 7 |
| PowerFlows tutorial | 1 | 0 | 1 | 0 |
| **Total** | **10** | **0** | **1** | **9** |

*PSI tutorials could theoretically run with PowerSystemCaseBuilder installed, but this
requires additional package installation and network access for test data download.

### Root Cause

The Sienna ecosystem's tutorial strategy assumes users will install `PowerSystemCaseBuilder`
as a development convenience package. This creates a hard dependency on NREL's data
infrastructure for all getting-started content. Users who want to work with their own
MATPOWER files or CSV data have no tutorial pathway.

The how-to guides provide useful API reference patterns but are not self-contained
examples. A new user cannot copy any how-to guide into a Julia session and run it.

## Implications

**Zero official examples run unmodified** in a standard PSI installation. This is a
significant accessibility barrier. The PowerFlows.jl tutorial is the closest to a working
example and requires only a data source substitution. The PSI tutorials require both
a data source substitution and formulation adjustments (removing hydro models), making
adaptation non-trivial for a newcomer.

For comparison, Python tools (pypsa, pandapower) typically include built-in test networks
(`pypsa.examples.ac_dc_lpf()`, `pp.networks.case39()`) that require no external downloads.
The Julia ecosystem's separation of test data into a dedicated package
(`PowerSystemCaseBuilder`) is architecturally clean but creates a cold-start problem for
new users.
