---
test_id: F-8
tool: pandapower
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# F-8: Solver Dependency

## Result: PASS

## Finding

pandapower's core power flow and OPF functionality operates entirely on open-source,
bundled solvers with no commercial solver requirements. The DC and AC power flow use
PYPOWER (bundled pure Python) with scipy for linear algebra. The OPF uses PYPOWER's
interior-point solver (PIPS, also bundled). No external solver binary is required for
basic operation.

## Evidence

### Power flow solvers (bundled)

| Algorithm | Implementation | External dependency |
|-----------|---------------|-------------------|
| DC power flow | `pandapower.pypower.dcpf` | scipy.sparse.linalg.spsolve only |
| Newton-Raphson (AC) | `pandapower.pypower.newtonpf` | scipy sparse operations |
| Fast-decoupled (AC) | `pandapower.pypower.fdpf` | scipy sparse operations |
| Gauss-Seidel (AC) | `pandapower.pypower.gausspf` | numpy only |
| Backward/forward sweep | `pandapower.pf.run_bfswpf` | numpy/scipy |

### OPF solver (bundled)

| Solver | Implementation | License |
|--------|---------------|---------|
| PIPS (interior point) | `pandapower.pypower.pips` | BSD (part of PYPOWER) |
| PIPS OPF | `pandapower.pypower.pipsopf_solver` | BSD (part of PYPOWER) |

### Optional alternative backends

| Backend | Solver access | License | Required? |
|---------|--------------|---------|-----------|
| LightSim2Grid | C++ Newton-Raphson | MPL-2.0 | No (performance extra) |
| PowerModels.jl bridge | HiGHS, Ipopt, etc. via Julia | BSD/MIT | No (pandamodels extra) |
| OR-Tools | LP/MILP via Google OR-Tools | Apache-2.0 | No (performance extra) |

### Commercial solver requirements

**None.** pandapower does not require or include bindings to any commercial solver
(CPLEX, Gurobi, MOSEK, etc.). The entire power flow and OPF pipeline runs on bundled
open-source code.

### HiGHS / GLPK availability

HiGHS and GLPK are not directly accessible through pandapower's native Python API. They
are available only through the PowerModels.jl bridge, which requires Julia. For the
evaluation's purposes, the native PYPOWER PIPS solver handles OPF without external
solver dependencies.

## Implications

pandapower achieves full solver independence from commercial software. The bundled PYPOWER
solvers (BSD-licensed, pure Python) cover DC power flow, AC power flow (multiple
algorithms), and OPF (interior point). No external solver binary installation is needed.
This is the strongest possible outcome for solver dependency assessment.
