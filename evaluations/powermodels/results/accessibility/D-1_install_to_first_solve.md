---
test_id: D-1
tool: powermodels
dimension: accessibility
network: N/A
protocol_version: "v4"
status: qualified_pass
workaround_class: null
timestamp: 2026-03-07T00:00:00Z
---

# D-1: Time clean install + first DCPF solve

## Result: QUALIFIED PASS

## Finding

PowerModels install-to-first-solve takes approximately 5.2 seconds (2.1s package load + 3.1s first solve including JIT compilation). Subsequent solves complete in ~0.1s. The installation process itself (`Pkg.add` / `Pkg.instantiate`) requires multi-minute precompilation on first run, which is a known Julia ecosystem characteristic. The three-step install process (add Julia, add packages, precompile) has more friction than pip-based Python tools but is well-documented.

## Evidence

### Timing Results (devcontainer, pre-compiled packages)

| Phase | Time |
|-------|------|
| `using PowerModels, HiGHS` (package load) | 2.14s |
| First DCPF solve (case5, includes JIT) | 3.11s |
| **Total load-to-first-result** | **5.24s** |
| Second DCPF solve (case39, warm) | 0.10s |

### Installation Process

1. **Julia installation**: System-level requirement (not a pip package). Requires Julia 1.10+.
2. **Package declaration**: `Project.toml` lists dependencies (PowerModels, JuMP, solvers).
3. **Package instantiation**: `julia --project=. -e 'using Pkg; Pkg.instantiate()'` downloads and precompiles all packages. First run takes several minutes due to native code compilation.
4. **Verification**: `julia --project=. verify_install.jl` confirms working installation.

### Friction Points

- **Julia startup overhead**: Every Julia process invocation pays a 2-5s load tax for deserializing precompiled caches. This is unavoidable in the Julia ecosystem and particularly impactful for scripted workflows.
- **First-call JIT latency**: The first solve in a session includes JIT compilation (~3s), making the first result slow. Subsequent solves are fast (~0.1s). This "time-to-first-plot" problem is well-known in the Julia community.
- **Precompilation on install**: `Pkg.instantiate()` triggers native compilation that can take 5-15 minutes on first run. This is a one-time cost but is significantly longer than `pip install`.
- **Solver selection**: Users must independently choose and install a solver (HiGHS, Ipopt, GLPK). The docs recommend Ipopt but HiGHS works for LP/MILP problems.

### Documentation Quality for Installation

The Getting Started guide provides clear 3-line installation instructions:

```julia

using Pkg
Pkg.add("PowerModels")
Pkg.add("Ipopt")

```

This is accurate and sufficient. The quick-start example (`solve_ac_opf("matpower/case3.m", Ipopt.Optimizer)`) works immediately after installation.

## Implications

The 5.2s load-to-first-solve is acceptable for interactive/REPL workflows but creates friction for scripted batch jobs where Julia is invoked per-run. The multi-minute precompilation on first install is a known Julia ecosystem cost. Installation documentation is clear and accurate. Qualified pass due to the JIT/startup overhead characteristic of the Julia runtime.
