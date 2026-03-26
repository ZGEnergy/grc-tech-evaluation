---
test_id: F-9
tool: powersimulations
dimension: supply_chain
network: N/A
protocol_version: "v11"
skill_version: "v2"
test_hash: "738f75e3"
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
timestamp: 2026-03-24T00:00:00Z
---

# F-9: Getting-Started Artifact Integrity

## Result: INFORMATIONAL

## Finding

PowerSimulations.jl's official getting-started tutorials reference **no pinned version** of
any Sienna package. Tutorial code depends on `PowerSystemCaseBuilder.jl`, an external
package that downloads test data from NREL's data infrastructure at runtime via mutable
URLs. The documentation is served from the `stable` Documenter.jl alias, which resolves
to the latest tagged release but is itself a mutable URL.

## Evidence

### Tutorial Inventory

Both official PSI tutorials live in `docs/src/tutorials/` and are executed by Literate.jl
during the docs build:

| # | Tutorial | File | PowerSystemCaseBuilder? | Version Pinned? |
|---|----------|------|------------------------|-----------------|
| 1 | Single-step Decision Problem | `decision_problem.jl` | Yes | No |
| 2 | Multi-stage PCM Simulation | `pcm_simulation.jl` | Yes | No |

Both tutorials begin with:
```julia
using PowerSystemCaseBuilder
sys = build_system(PSISystems, "modified_RTS_GMLC_DA_sys")
```

### Version Pinning Analysis

**Package imports (no version constraints):**
- Tutorials `using PowerSimulations` with no version qualifier
- The `docs/Project.toml` specifies `[compat]` only for `Documenter`, `InfrastructureSystems`,
  and `julia` -- not for `PowerSimulations`, `PowerSystems`, `PowerSystemCaseBuilder`, or
  `HydroPowerSimulations`
- Users following the tutorial have no guidance on which PSI version to install

**Documentation URL stability:**
- Docs are served at `https://nrel-sienna.github.io/PowerSimulations.jl/stable/`
- The `/stable/` path is a Documenter.jl convention that resolves to the latest tagged release
- This is a **mutable URL** -- its content changes with each release
- No versioned URL (e.g., `/v0.30.2/`) is referenced in tutorial instructions

**Data source (PowerSystemCaseBuilder):**
- Downloads pre-built test systems from NREL's data repository at runtime
- The `build_system()` call fetches data over the network on first use
- No checksum verification of downloaded test data is documented
- The test system identifier (`"modified_RTS_GMLC_DA_sys"`) is a string key, not a
  versioned artifact reference

### Additional Dependencies Not Declared

Both tutorials also require packages not part of a standard PSI installation:
- `HydroPowerSimulations` (required for hydro device formulations in RTS-GMLC)
- `PowerSystemCaseBuilder` (required for test data)
- `HiGHS` (solver)

None of these are listed as dependencies of `PowerSimulations.jl`. A user following the
tutorial must discover and install them manually.

### Contrast with D-3 Findings

From D-3 (Example Verification): **0 of 10 official examples run unmodified** in a standard
PSI installation. The hard dependency on `PowerSystemCaseBuilder` means that even if version
pinning were added, the tutorials would still require network access and an external package
to function.

### Documentation Build Reproducibility

The docs `Project.toml` does not pin PSI or its ecosystem packages. The Literate.jl-based
tutorial execution during docs build uses whatever versions the Julia resolver selects. This
means:
- Tutorial output in the rendered docs may not match what a user sees with a different
  package version
- There is no `Manifest.toml` in the `docs/` directory to lock the build environment
- The `[compat]` section only constrains `Documenter >= 1.7`, `InfrastructureSystems = 3`,
  and `julia >= 1.6`

## Assessment

| Criterion | Status |
|-----------|--------|
| Tutorial code pins PSI version | No |
| Tutorial code pins data dependency versions | No |
| Documentation URL is immutable | No (uses `/stable/` alias) |
| Test data source is versioned/checksummed | No |
| Tutorial lists all required packages | Partial (imports shown, but no install instructions with versions) |
| Tutorial runs without network access | No (requires PowerSystemCaseBuilder download) |

The getting-started artifacts are **not integrity-hardened**. All tutorial entry points use
mutable references (unversioned package imports, `/stable/` URL, runtime data downloads).
This is standard practice for the Julia ecosystem and NREL-Sienna projects but represents a
supply-chain gap for reproducibility-sensitive deployments.

A user following the tutorials at two different points in time could get different package
versions, different test data, and potentially different results -- with no mechanism to
detect or prevent this divergence.

## Data Source

- PowerSimulations.jl `docs/` directory on GitHub (accessed 2026-03-24)
- PowerSystemCaseBuilder.jl source and data fetching mechanism (accessed 2026-03-24)
- Documenter.jl `/stable/` URL behavior (accessed 2026-03-24)
