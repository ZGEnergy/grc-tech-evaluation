---
test_id: F-8
tool: powermodels
dimension: supply_chain
network: N/A
status: qualified_pass
workaround_class: null
timestamp: "2026-03-11T00:00:00Z"
protocol_version: "v9"
skill_version: v1
test_hash: "6a50c823"
---

# F-8: Confirm all target use cases functional on open-source solvers only

## Finding

AC OPF works correctly with Ipopt (open-source, EPL 2.0). DC OPF works correctly with HiGHS (MIT) and SCIP (ZIB Academic — not commercial open-source). GLPK fails on the standard case39 DC OPF due to its lack of quadratic programming support, but works with linear cost approximations. The core use cases (AC OPF, DC OPF) are functional with the two fully permissive solvers — Ipopt and HiGHS.

## Evidence

### Tests executed in devcontainer on IEEE 39-bus (case39.m):

```julia

# AC OPF with Ipopt
result = PowerModels.solve_ac_opf(data, Ipopt.Optimizer)
# → termination_status: LOCALLY_SOLVED, objective: 41864.18

```

```julia

# DC OPF with HiGHS
result = PowerModels.solve_dc_opf(data, HiGHS.Optimizer)
# → termination_status: OPTIMAL, objective: 41263.94

```

```julia

# DC OPF with SCIP
result = PowerModels.solve_dc_opf(data, SCIP.Optimizer)
# → SCIP Status: problem is solved [optimal solution found], objective: 41263.94
# Note: SCIP outputs internal DSYEV warnings (non-fatal) but converges correctly

```

```julia

# DC OPF with GLPK — FAILS
result = PowerModels.solve_dc_opf(data, GLPK.Optimizer)
# → MathOptInterface.UnsupportedAttribute{...ScalarQuadraticFunction}:
#   GLPK does not support quadratic objective functions

```

## Solver assessment summary:

| Solver | License | AC OPF | DC OPF | Notes |
|--------|---------|--------|--------|-------|
| Ipopt | EPL 2.0 | PASS (LOCALLY_SOLVED) | PASS (via AC formulation) | Primary NLP solver |
| HiGHS | MIT | N/A (no NLP) | PASS (OPTIMAL) | Primary LP/MIP/QP solver |
| SCIP | ZIB Academic* | N/A (no NLP) | PASS (OPTIMAL) | Restricted to non-commercial |
| GLPK | GPL v3 | N/A | FAIL (no QP support) | Fails on quadratic costs |

*SCIP binary in this manifest (v0.2.1/SCIP ~8.x) uses the ZIB Academic License, which prohibits commercial use.

**GLPK limitation:** The standard case39.m has quadratic generator cost functions (model=2). GLPK does not support QP objectives. GLPK can be used for DC OPF only if cost curves are linearized (model=1), which is a non-default configuration.

**Commercial solver requirement:** No commercial solver (Gurobi, CPLEX, MOSEK) is required for any standard PowerModels use case. The Ipopt + HiGHS combination covers AC NLP and DC LP/QP formulations with permissive licenses.

## Implications

For commercial deployments, the viable open-source solver set is Ipopt (AC OPF) + HiGHS (DC OPF/LP). SCIP must be excluded due to ZIB Academic License restrictions; GLPK is functionally limited (no QP) and GPL-licensed. The qualified pass reflects that GLPK cannot handle the standard quadratic cost case without preprocessing, and SCIP cannot be used commercially — but neither limitation blocks the primary use cases when Ipopt and HiGHS are available.
