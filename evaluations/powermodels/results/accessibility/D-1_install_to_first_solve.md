---
test_id: D-1
tool: powermodels
dimension: accessibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: ef7694d3
status: qualified_pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 3.588
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: HiGHS
timestamp: 2026-03-24T18:00:00Z
---

# D-1: Install-to-First-Solve Wall-Clock Time

## Result: QUALIFIED PASS

## Finding

PowerModels.jl install-to-first-solve takes **3.588 seconds** (measured) with a warm precompile
cache, or 5-15 minutes from a clean `Pkg.instantiate()` due to Julia JIT compilation overhead.
The installation is frictionless for Julia users (zero system dependencies beyond Julia itself),
but JIT compilation and an undocumented API signature difference impose a meaningful first-use tax.

## Evidence

### Measured Timing (devcontainer, Julia 1.10, precompile cache warm)

| Phase | Wall-clock (s) |
|-------|---------------|
| Julia process startup + `using PowerModels, HiGHS` | 1.118 |
| `parse_file` (case3.m) | 0.492 |
| `solve_dc_opf` first invocation (incl JIT) | 1.978 |
| **Total wall-clock from process launch to result** | **3.588** |

Timing source: **measured** via Julia `time()` calls in a self-contained script executed
inside the devcontainer on 2026-03-24. The script was:

```julia
t_start = time()
using PowerModels; using HiGHS
t_loaded = time()
data = PowerModels.parse_file(...)
t_parsed = time()
result = solve_dc_opf(data, HiGHS.Optimizer)
t_solved = time()
```

Result: `termination_status: OPTIMAL`, `objective: 5782.032079653238`

### Installation Steps

1. **Julia 1.10** -- download from `https://julialang.org/downloads/`. Self-contained binary.
2. **Project setup** -- directory with `Project.toml` and `Manifest.toml`.
3. **Instantiate** -- `julia --project=. -e 'using Pkg; Pkg.instantiate()'`. First run downloads
   and compiles all packages (5-15 minutes). Subsequent runs use precompile cache.
4. **Verify** -- `julia --project=. verify_install.jl`

### Environment Configuration

| Package | Version | Purpose |
|---------|---------|---------|
| PowerModels | 0.21.x | Core power systems library |
| JuMP | 1.x | Mathematical optimization framework |
| HiGHS | 1.x | LP/QP solver |
| Ipopt | 1.x | NLP solver |
| SCIP | 0.11.x | MILP/MINLP solver |
| GLPK | 1.x | LP/MILP solver |

No C extensions, no system libraries beyond Julia. HiGHS, Ipopt, and SCIP are vendored as
Julia JLL artifacts.

### API Friction on First Use

The official quickstart shows `solve_ac_opf("matpower/case3.m", Ipopt.Optimizer)` (2-argument
convenience wrapper). Some online examples show a 3-argument `solve_dc_opf(data, DCPPowerModel,
optimizer)` which is invalid in v0.21.5 and produces a `MethodError` mentioning
`InitializeInfrastructureModel` rather than pointing at the API mismatch.

### Issues Encountered

| # | Issue | Severity |
|---|-------|----------|
| 1 | JIT compilation delay (~5-15 min first install) | Medium -- one-time cost, Julia design characteristic |
| 2 | API signature mismatch between quickstart and some online examples | Low -- use 2-arg form |
| 3 | `verify_install.jl` uses `OPTIMAL` constant requiring JuMP import | Low |

## Implications

The 3.6s warm-start time is competitive for a Julia tool (JIT overhead is inherent to the
language). The 5-15 minute cold-start for `Pkg.instantiate()` is a significant barrier for
first-time evaluation but is a one-time cost. Status is qualified_pass because neither the
JIT overhead nor the API signature issue blocks a successful first solve.
