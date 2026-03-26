---
test_id: F-5
tool: pandapower
dimension: supply_chain
network: N/A
status: informational
workaround_class: null
blocked_by: null
wall_clock_seconds: null
timing_source: estimated
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: null
solver: null
timestamp: "2026-03-24T00:00:00Z"
protocol_version: "v11"
skill_version: "v2"
test_hash: "708f9e05"
---

# F-5: Code Inspectability -- Execution Path Trace

## Result: INFORMATIONAL

## Finding

pandapower has excellent code inspectability. The entire power flow computation from API
call to solver is implemented in readable Python modules with PYPOWER heritage. The only
compiled code invoked is scipy's sparse linear algebra (SuperLU), which is open-source.
No opaque binary steps exist in the critical path.

## Evidence

### Entry Point: `pandapower.rundcpp(net)`

Traced the full execution path from user-facing API to numerical solver in the
devcontainer (2026-03-24).

### Call Chain

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

### Solver Detail: `dcpf()` (pandapower/pypower/dcpf.py)

The core solver is ~10 lines of pure Python:

```python
def dcpf(B, Pbus, Va0, ref, pv, pq):
    pvpq = r_[pv, pq]
    Va = copy(Va0)
    pvpq_matrix = B[pvpq.T,:].tocsc()[:,pvpq]
    ref_matrix = transpose(Pbus[pvpq] - B[pvpq.T,:].tocsc()[:,ref] * Va0[ref])
    Va[pvpq] = real(spsolve(pvpq_matrix, ref_matrix))
    return Va
```

This constructs a reduced B-matrix (excluding the reference bus), forms the RHS injection
vector, and solves `B_reduced * Va = P_net` via `scipy.sparse.linalg.spsolve`.

### AC Power Flow Path

For `runpp()` (AC power flow), the path is similar but uses Newton-Raphson iteration
(`pandapower.pf.run_newton_raphson_pf`), which is also pure Python/NumPy/SciPy. If
LightSim2Grid is installed and selected, it provides an alternative C++ Newton-Raphson
solver -- but this is optional, and the pure Python path is always available as fallback.

### Module Inventory (in Execution Path)

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

### Opaque Binary Steps

**None.** The entire pandapower execution path from API to solver is pure Python. The only
compiled code invoked is `scipy.sparse.linalg.spsolve` (SuperLU), a well-documented,
open-source sparse direct solver with full source available.

### Architecture Observations (from consumed observations)

Two architectural notes relevant to inspectability:

1. **Positive:** Clean 6-layer architecture (public API, orchestration, data model
   conversion, problem formulation, solver, result extraction) with well-separated
   concerns. [arch-quality, B-6]
2. **Negative:** The result extraction layer discards PYPOWER OPF duals/multipliers
   (`result['lin']['mu']`, `result['var']`), meaning shadow prices for custom constraints
   are lost. Users must access undocumented internals to retrieve them. [arch-quality, B-1]

## Implications

pandapower achieves the highest level of code inspectability among the tools under
evaluation. The entire power flow computation is implemented in readable Python modules
with PYPOWER heritage. All intermediate data structures (ppc/ppci dicts with numpy arrays)
are accessible for debugging and validation. The sole compiled dependency (scipy's
SuperLU) is a well-established open-source sparse solver. The optional LightSim2Grid
accelerator has full source available on GitHub.
