---
test_id: F-5
tool: pandapower
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: "v10"
skill_version: "v1"
test_hash: "708f9e05"
---

# F-5: Code Inspectability -- Execution Path Trace

## Entry Point: `pandapower.rundcpp(net)`

Traced the full execution path from the user-facing API call to the numerical solver.

## Call Chain

```
pandapower.rundcpp(net)                              # pandapower/run.py
  -> _init_rundcpp_options(net, ...)                 # pandapower/run.py
       Sets ac=False, mode="dc", algorithm=None
  -> _powerflow(net)                                 # pandapower/powerflow.py
       -> _add_auxiliary_elements(net)               # Add dcline gen elements
       -> verify_results(net, mode='dc')             # Initialize result tables
       -> _pd2ppc(net)                               # pandapower/pd2ppc.py
            Converts pandapower DataFrame model to PYPOWER-style
            numpy arrays (ppc/ppci dicts with bus, branch, gen matrices)
       -> _run_pf_algorithm(ppci, options)           # pandapower/powerflow.py
            Dispatches based on ac=False:
            -> _run_dc_pf(ppci)                      # pandapower/pf/run_dc_pf.py
                 -> _get_pf_variables_from_ppci()    # Extract bus/branch/gen arrays
                 -> makeBdc(bus, branch, ...)         # pandapower/pypower/makeBdc.py
                      Builds sparse B matrix (susceptance) and
                      phase shift injection vectors (Pbusinj, Pfinj)
                      using branch reactances, tap ratios, and shift angles
                 -> makeSbus(baseMVA, bus, gen)       # pandapower/pypower/makeSbus.py
                      Computes net bus power injections (gen - load)
                 -> dcpf(B, Pbus, Va0, ref, pv, pq)  # pandapower/pypower/dcpf.py
                      THE SOLVER: Solves Va = B^{-1} * P via
                      scipy.sparse.linalg.spsolve()
                      (SuperLU sparse LU factorization)
                 -> _store_results_from_pf_in_ppci() # Store angles back
       -> _ppci_to_net(result, net)                  # pandapower/powerflow.py
            Converts PYPOWER results back to pandapower DataFrames
```

## Solver Detail: `dcpf()` (pandapower/pypower/dcpf.py)

The core solver is 10 lines of pure Python:

```python
def dcpf(B, Pbus, Va0, ref, pv, pq):
    pvpq = r_[pv, pq]
    Va = copy(Va0)
    pvpq_matrix = B[pvpq.T,:].tocsc()[:,pvpq]
    ref_matrix = transpose(Pbus[pvpq] - B[pvpq.T,:].tocsc()[:,ref] * Va0[ref])
    Va[pvpq] = real(spsolve(pvpq_matrix, ref_matrix))
    return Va
```

This constructs a reduced B-matrix (excluding the reference bus), forms the RHS injection vector, and solves the sparse linear system `B_reduced * Va = P_net` using `scipy.sparse.linalg.spsolve`.

## Module Inventory (in execution path)

| Module | File | Inspectable | Language |
|--------|------|-------------|----------|
| `pandapower.run` | run.py | Yes | Python |
| `pandapower.powerflow` | powerflow.py | Yes | Python |
| `pandapower.pd2ppc` | pd2ppc.py | Yes | Python |
| `pandapower.pf.run_dc_pf` | pf/run_dc_pf.py | Yes | Python |
| `pandapower.pf.ppci_variables` | pf/ppci_variables.py | Yes | Python |
| `pandapower.pypower.dcpf` | pypower/dcpf.py | Yes | Python |
| `pandapower.pypower.makeBdc` | pypower/makeBdc.py | Yes | Python |
| `pandapower.pypower.makeSbus` | pypower/makeSbus.py | Yes | Python |
| `scipy.sparse.linalg.spsolve` | (compiled) | Source available | C/Fortran |

## Opaque Binary Steps

**None.** The entire pandapower execution path from API to solver is pure Python. The only compiled code invoked is `scipy.sparse.linalg.spsolve` (SuperLU), which is a well-documented, open-source sparse direct solver with full source available.

For AC power flow (`runpp`), the path is similar but uses Newton-Raphson iteration (`pandapower.pf.run_newton_raphson_pf`), which is also pure Python/NumPy/SciPy. If LightSim2Grid is installed and selected, it provides an alternative C++ Newton-Raphson solver -- but this is optional, and the pure Python path is always available as fallback.

## Assessment

pandapower has excellent code inspectability. The entire power flow computation is implemented in readable Python modules tracing directly from PYPOWER heritage. The solver step delegates to scipy's sparse linear algebra, which itself is open-source. No opaque binary steps exist in the critical path. All intermediate data structures (ppc/ppci dicts with numpy arrays) are accessible for debugging and validation.
