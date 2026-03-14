---
test_id: F-8
tool: powermodels
dimension: supply_chain
network: N/A
status: pass
workaround_class: null
timestamp: "2026-03-13T23:00:00Z"
protocol_version: v10
skill_version: v1
test_hash: "9f2d46ba"
---

# F-8: Open-source solver sufficiency assessment

## Finding

All target use cases (AC OPF, DC OPF) are fully functional on open-source solvers with permissive licenses. Ipopt (EPL 2.0) handles nonlinear AC formulations. HiGHS (MIT) handles linear and quadratic DC formulations. SCIP (Apache 2.0 since v8.0) also works for DC OPF. GLPK (GPL v3) cannot handle standard quadratic cost DC OPF but works with linearized costs. No commercial solver is required for any standard PowerModels use case.

## Evidence

### Tests executed in devcontainer on IEEE 39-bus (case39.m)

```julia
# AC OPF with Ipopt
result = PowerModels.solve_ac_opf(data, Ipopt.Optimizer)
# termination_status: LOCALLY_SOLVED, objective: 41864.18
```

```julia
# DC OPF with HiGHS
result = PowerModels.solve_dc_opf(data, HiGHS.Optimizer)
# termination_status: OPTIMAL, objective: 41263.94
```

```julia
# DC OPF with SCIP
result = PowerModels.solve_dc_opf(data, SCIP.Optimizer)
# SCIP Status: problem is solved [optimal solution found], objective: 41263.94
```

```julia
# DC OPF with GLPK — FAILS on quadratic costs
result = PowerModels.solve_dc_opf(data, GLPK.Optimizer)
# MathOptInterface.UnsupportedAttribute: GLPK does not support quadratic objective functions
```

### Solver assessment summary

| Solver | Version | License | AC OPF | DC OPF | Notes |
|--------|---------|---------|--------|--------|-------|
| Ipopt | 1.x (via Ipopt_jll) | EPL 2.0 | PASS (LOCALLY_SOLVED) | PASS (via AC formulation) | Primary NLP solver |
| HiGHS | 1.x (via HiGHS_jll) | MIT | N/A (no NLP) | PASS (OPTIMAL) | Primary LP/MIP/QP solver |
| SCIP | 8.0 (via SCIP_jll 0.2.1) | Apache 2.0 | N/A (no NLP) | PASS (OPTIMAL) | Permissive license since v8.0 |
| GLPK | 1.x (via GLPK_jll) | GPL v3 | N/A | FAIL (no QP support) | Fails on quadratic costs |

### SCIP license correction

SCIP v8.0 (November 2021) switched from the ZIB Academic License to Apache 2.0, making it fully permissive for commercial use. The SCIP_jll v0.2.1 in this manifest wraps SCIP 8.0, confirmed by `SCIP.SCIPversion()` returning `8.0` in the devcontainer. The GitHub repository (`scipopt/scip`) confirms Apache-2.0 as the current license.

### GLPK limitation

The standard case39.m has quadratic generator cost functions (model=2). GLPK does not support QP objectives. GLPK can be used for DC OPF only if cost curves are linearized (model=1), which is a non-default configuration.

### Commercial solver requirement

No commercial solver (Gurobi, CPLEX, MOSEK) is required for any standard PowerModels use case. The Ipopt + HiGHS combination covers AC NLP and DC LP/QP formulations with fully permissive licenses (EPL 2.0 + MIT). SCIP (Apache 2.0) provides an additional option for LP/MIP problems.

## Implications

Upgraded from qualified_pass (v9) to pass. The prior assessment incorrectly identified SCIP as ZIB Academic licensed. With SCIP 8.0 confirmed as Apache 2.0, three of four tested solvers (Ipopt, HiGHS, SCIP) carry permissive licenses suitable for commercial use. GLPK remains limited (no QP support, GPL v3 copyleft) but is not needed — Ipopt and HiGHS cover all standard formulations. No commercial solver dependency exists.
