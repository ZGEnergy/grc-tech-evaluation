# PowerModels.jl — Install & Smoke-Test Findings

**Date:** 2026-03-03
**Version resolved:** PowerModels 0.21.x, HiGHS 1.13.1, JuMP 1.29.4
**Script:** [`../verify_install.jl`](../verify_install.jl)

## Summary

DCPF on IEEE 39-bus completed successfully. OPTIMAL status, 30 simplex
iterations, 0.0005s solve time via HiGHS. Cleanest install of all six tools.

## Findings

### [maturity] Clean dependency resolution, no conflicts

`Pkg.instantiate()` resolved all dependencies on the first attempt with no
version conflicts, no UUID issues, no compat workarounds needed. The
`Project.toml` [compat] bounds are well-maintained upstream. This is the
only tool where the initial declared dependencies resolved without any
corrections.

**Rubric relevance:** Maturity (dependency hygiene), Supply Chain (clean
resolution).

### [accessibility] Native .m file reader, clean API

```julia
data = PowerModels.parse_file("case39.m")
result = PowerModels.solve_dc_pf(data, HiGHS.Optimizer)
```

Two lines: parse file, solve. The solver is an explicit argument (no global
state). The result is a dictionary with clear keys (`termination_status`,
`solve_time`, etc.). No extra packages needed for .m file I/O.

### [maturity] Informative warnings about data tightening

The tool emits warnings about tightening angle limits on all 46 branches:

```
this code only supports angmin values in -90 deg. to 90 deg.,
tightening the value on branch 32 from -360.0 to -60.0 deg.
```

This is good engineering practice — the tool tells you exactly what it
changed and why rather than silently modifying input data. Every branch
modification is logged with the branch ID and the old/new values.

### [expressiveness] DCPF formulated as optimization problem

PowerModels solves DCPF as an LP via JuMP/HiGHS (30 simplex iterations),
not as a direct linear solve. This is architecturally different from
pandapower/MATPOWER which use direct matrix solves. The optimization
formulation is more general (same interface works for OPF, DCPF, ACOPF)
but potentially slower for simple power flow.

### [supply_chain] All solvers are Julia packages — no system dependencies

HiGHS, Ipopt, GLPK, and SCIP are all installed as Julia packages with
precompiled binaries via JLL wrappers. No `apt install`, no `brew`, no
system library dependencies. This is a significant advantage for
reproducibility and air-gapped deployment.

### [gate] DCPF passes

39 buses, 46 branches, OPTIMAL status. Full branch count preserved.
