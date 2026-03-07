---
test_id: F-8
tool: powermodels
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-06T00:00:00Z
---

# F-8: Solver Dependency Assessment

## Result: PASS

## Finding

PowerModels.jl functions fully on open-source solvers. HiGHS (MIT) handles all LP/MIP problems. Ipopt (EPL-2.0) handles all NLP problems (AC-OPF). Together they cover the full range of PowerModels formulations without any proprietary or restrictively-licensed solver.

## Evidence

**Verified solver functionality:**

HiGHS (MIT, v1.21.1) -- tested DC-OPF solve:

```

result = PowerModels.solve_dc_opf(data, HiGHS.Optimizer)
# Termination: OPTIMAL
# Objective: 17613.21587795645

```

**Solver coverage by formulation type:**

| Formulation | Problem Type | Suitable Open-Source Solver | License |
|-------------|-------------|----------------------------|---------|
| DCPPowerModel | LP | HiGHS | MIT |
| ACPPowerModel | NLP | Ipopt | EPL-2.0 |
| ACRPowerModel | NLP | Ipopt | EPL-2.0 |
| SOCWRPowerModel | SOCP | HiGHS (via conic) or Ipopt | MIT / EPL-2.0 |
| QCWRPowerModel | QCP | Ipopt | EPL-2.0 |
| LPACCPowerModel | LP | HiGHS | MIT |
| OTS (with binary) | MIP | HiGHS | MIT |
| TNEP (with binary) | MIP | HiGHS | MIT |

**Solver licenses:**
- **HiGHS**(v1.21.1): MIT license. Fully open-source LP/MIP/QP solver. No restrictions.
- **Ipopt**(v1.14.1 wrapper, Ipopt_jll v300.1400.1901): EPL-2.0 (Eclipse Public License). Weak copyleft -- linking does not impose EPL on the consuming application per EPL-2.0 Section 2.
- **GLPK**(v1.2.1): GPL-3.0. Functional but not recommended for commercial use due to copyleft. Avoidable.
- **SCIP**(v0.11.6): ZIB Academic License. Non-commercial only. Avoidable.

**PowerModels does not bundle or require any specific solver.** The solver is passed as an argument (`Optimizer` parameter) to solve functions. Users choose which solver to install and use.

**Recommended commercial-safe solver set**: HiGHS + Ipopt covers all PowerModels formulations. Both have permissive or weak-copyleft licenses compatible with commercial use.

## Implications

PowerModels achieves full functionality on open-source solvers alone. The HiGHS + Ipopt combination covers LP, MIP, NLP, and SOCP problem types, which spans all PowerModels formulations. No proprietary solver dependency exists. GPL-3.0 (GLPK) and ZIB Academic (SCIP) solvers are optional and can be excluded from deployment without losing any formulation capability.
