---
test_id: F-5
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

# F-5: Code Inspectability Trace

## Result: PASS

## Finding

The full execution path from `pp.rundcpp()` to the linear system solve is traceable through
pure Python source code. The only opaque step is the final `scipy.sparse.linalg.spsolve`
call, which delegates to compiled C/Fortran (SuperLU). This is a standard, well-documented
numerical library call.

## Evidence

### Call chain: `pp.rundcpp()` to solver

```
pp.rundcpp(net, ...)                          # pandapower/run.py
  -> _init_rundcpp_options(net, ...)          # pandapower/run.py
  -> _powerflow(net, **kwargs)                # pandapower/powerflow.py
       -> _add_auxiliary_elements(net)        # pandapower/auxiliary.py
       -> init_results(net)                   # pandapower/results.py
       -> _pd2ppc(net, **kwargs)              # pandapower/pd2ppc.py
            [converts pandapower DataFrames to PYPOWER case dict]
       -> _run_pf_algorithm(ppci, options)    # pandapower/powerflow.py
            -> _run_dc_pf(ppci, recycle)      # pandapower/powerflow.py
                 -> _get_pf_variables_from_ppci(ppci)
                 -> makeBdc(baseMVA, bus, branch)  # pandapower/pypower/makeBdc.py
                      [builds B matrix and Bf from branch data]
                 -> makeSbus(baseMVA, bus, gen)     # pandapower/pypower/makeSbus.py
                      [computes bus power injections]
                 -> dcpf(B, Pbus, Va0, ref, pv, pq)  # pandapower/pypower/dcpf.py
                      -> scipy.sparse.linalg.spsolve(B_reduced, P_reduced)
                         [COMPILED: SuperLU sparse direct solve]
       -> _ppci_to_net(result, net)           # pandapower/powerflow.py
            [maps results back to pandapower DataFrames]
```

### Module inventory

| Module | Path | Language | Inspectable |
|--------|------|----------|-------------|
| `pandapower.run` | `pandapower/run.py` | Python | Yes |
| `pandapower.powerflow` | `pandapower/powerflow.py` | Python | Yes |
| `pandapower.pd2ppc` | `pandapower/pd2ppc.py` | Python | Yes |
| `pandapower.pypower.makeBdc` | `pandapower/pypower/makeBdc.py` | Python | Yes |
| `pandapower.pypower.makeSbus` | `pandapower/pypower/makeSbus.py` | Python | Yes |
| `pandapower.pypower.dcpf` | `pandapower/pypower/dcpf.py` | Python | Yes |
| `scipy.sparse.linalg` | `scipy/sparse/linalg/` | C/Fortran | Source available |

### Opaque steps

The only non-Python step is `scipy.sparse.linalg.spsolve`, which calls SuperLU (C) and
OpenBLAS (Fortran/C). These are standard numerical libraries with full source availability:

- SuperLU: BSD-licensed, source at <https://github.com/xiaoyeli/superlu>
- OpenBLAS: BSD-3-Clause, source at <https://github.com/OpenMathLib/OpenBLAS>

### Key solver code (from `pandapower/pypower/dcpf.py`)

```python
pvpq_matrix = B[pvpq.T,:].tocsc()[:,pvpq]
ref_matrix = transpose(Pbus[pvpq] - B[pvpq.T,:].tocsc()[:,ref] * Va0[ref])
Va[pvpq] = real(spsolve(pvpq_matrix, ref_matrix))
```

This is a direct sparse linear solve: `B * Va = P`. The matrix construction and result
extraction are fully visible Python. The solve itself is a single, well-understood
library call.

## Implications

pandapower achieves excellent code inspectability for the DC power flow path. Every step
from user API to mathematical formulation is readable Python. The compiled dependency
(scipy/SuperLU) is a standard numerical primitive with decades of peer review and full
source availability. No proprietary or obfuscated code in the critical path.
