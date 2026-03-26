---
test_id: D-1
tool: powersimulations
dimension: accessibility
network: TINY
protocol_version: v11
skill_version: v2
test_hash: ef7694d3
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: 24.15
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T00:00:00Z"
---

# D-1: Install-to-First-Solve

## Result: INFORMATIONAL

## Finding

From a pre-instantiated environment, the first DCPF solve on IEEE 39-bus (TINY) takes
**24.15 seconds** wall-clock. This time is dominated by JIT compilation during MATPOWER
file parsing (18.47s) and first power flow solve (4.55s). Subsequent solves in the same
REPL session take 1.2 ms, a ~20,000x speedup demonstrating that nearly all first-run time
is JIT compilation overhead. A cold `Pkg.instantiate()` on a warm depot takes 3.36s;
a cold install from scratch would require downloading and precompiling 184 resolved
packages (estimated 5-15 minutes depending on network and CPU).

## Evidence

### Installation

**Step 1: Project file setup.** The `Project.toml` lists 16 direct dependencies including
PowerSimulations v0.27-0.33, PowerSystems v4-5, PowerFlows v0.6-0.16, plus solvers (HiGHS,
GLPK, Ipopt, SCIP) and utilities (DataFrames, CSV, JuMP, etc.). These resolve to **184
packages** in the Manifest.toml.

```
julia --project=. -e 'using Pkg; Pkg.instantiate()'
```

- **Warm depot (packages already downloaded/compiled):** 3.36s (measured)
- **Cold install (estimated):** 5-15 minutes for download + native code compilation

**Step 2: Verify install.**

```
julia --project=. verify_install.jl
```

The verification script loads PowerSystems, PowerFlows, PowerNetworkMatrices, ingests
case39.m, and runs a DCPF. On first run after instantiation, this triggers JIT compilation.

### First-Solve Timing Breakdown (Measured)

| Phase | Wall-clock | Notes |
|-------|-----------|-------|
| `using PowerSystems` | 0.82s | Package loading (precompiled cache deserialization) |
| `using PowerFlows` | 0.30s | Package loading |
| `using PowerNetworkMatrices` | 0.00s | Already loaded as dependency |
| `System("case39.m")` | 18.47s | MATPOWER parsing + JIT compilation of parser path |
| `solve_powerflow(DCPowerFlow(), sys)` | 4.55s | First DCPF solve + JIT compilation |
| **Total** | **24.15s** | First invocation in fresh Julia process |

**Second solve in same session:** 0.001164s (measured). The ~20,000x speedup
demonstrates that nearly all first-run time is JIT compilation overhead, not algorithmic cost.

### Issues Encountered

1. **MATPOWER parser warnings (nuisance, not blocking):** All 46 branches emit `angmin`/`angmax`
   tightening warnings (92 warning lines total). These are informational but produce significant
   console noise that obscures actual errors. [tool-specific]

2. **Generator validation warnings:** Two generators (gen-2 at bus-31, gen-8 at bus-37)
   emit `Invalid range` warnings because their initial dispatch exceeds `active_power_limits.max`.
   This is a data quality issue in the MATPOWER case, not a tool bug, but the warnings are
   verbose (~20 lines each with full component printout). [tool-specific]

3. **No "quick start" documentation:** The official PowerSimulations.jl tutorials require
   `PowerSystemCaseBuilder.jl` (not included in standard dependencies) to load test
   systems. There is no documented one-liner for "load a MATPOWER file and run power flow"
   -- users must discover that `System(path)` accepts `.m` files and that `PowerFlows.jl`
   (a separate package) provides `solve_powerflow`. See [api-friction A-1](../observations/api-friction-expressiveness-A-1_dcpf.md) for related friction on inconsistent DC/AC return types.

4. **Julia startup tax is inherent:** Every fresh `julia` invocation pays JIT compilation
   for each code path. The recommended mitigation is to stay in the REPL and use `include()`
   for iterative development. This is documented in the project CLAUDE.md but not in the
   official PSI getting-started guide. [tool-specific: Julia ecosystem property]

5. **184 resolved packages:** The dependency footprint is large. The Sienna ecosystem pulls
   in PowerSystems, PowerFlows, PowerNetworkMatrices, InfrastructureSystems, PowerModels,
   plus four solver bindings (HiGHS, GLPK, Ipopt, SCIP) with their JLL binary wrappers.

### Comparison Context

For Python-based tools (pypsa, pandapower, gridcal), install-to-first-solve is typically:
- `pip install` / `uv sync`: 10-30s
- First DCPF solve: <1s (no JIT)
- Total: ~30s

PowerSimulations.jl's total (including cold install) would be 5-15 minutes, reflecting
Julia's ahead-of-time compilation model. For warm-depot subsequent sessions, the 24s
startup is the primary accessibility cost.

## Implications

Julia's JIT compilation model creates a significant first-use barrier. The 24.15s
time-to-first-solve (warm depot) is acceptable for production workflows but poor for
interactive exploration. A newcomer encountering 92 warning lines and 18s of apparent hang
during system loading may conclude the tool is broken. The lack of a minimal "hello world"
example in official docs (requiring PowerSystemCaseBuilder instead of a simple MATPOWER
load) adds friction. The REPL-based development workflow effectively mitigates the JIT
cost for sustained use but represents a Julia ecosystem pattern rather than a PSI-specific
choice. As noted in the [api-friction A-1 observation](../observations/api-friction-expressiveness-A-1_dcpf.md),
the DC and AC power flow result structures are inconsistent, adding further friction to
the first-use experience.
