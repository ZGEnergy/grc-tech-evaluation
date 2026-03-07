---
test_id: B-6
tool: pandapower
dimension: extensibility
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

# B-6: Qualitative assessment of DCPF solve path architecture

## Result: PASS

## Finding

pandapower's DCPF solve path traverses 4 clearly separated abstraction layers across well-defined module boundaries. Internal interfaces are partially documented (public API is well-documented; internal ppc structures follow MATPOWER conventions but are not formally documented by pandapower). The architecture demonstrates clean separation of network model, problem formulation, solver interface, and result extraction.

## Evidence

### Call Chain: `pp.rundcpp()` to solver

```
Layer 1: Public API (run.py)
  pp.rundcpp(net, **kwargs)
    -> _powerflow(net, **kwargs)

Layer 2: Problem Setup (powerflow.py)
  _powerflow(net, **kwargs)
    -> _pd2ppc(net)          # Convert pandas DataFrames -> MATPOWER ppc arrays
    -> _run_pf_algorithm()   # Dispatch to correct solver
    -> _ppci_to_net(result)  # Map results back to net.res_* DataFrames

Layer 3: Conversion Pipeline (pd2ppc.py)
  _pd2ppc(net)
    -> builds ppc dict with bus, gen, branch numpy arrays
    -> _ppc2ppci(ppc)        # Filter to in-service elements only
    -> stores in net._ppc, net._pd2ppc_lookups

Layer 4: Solver (pf/run_dc_pf.py)
  _run_dc_pf(ppci, recycle)
    -> _get_pf_variables_from_ppci()  # Extract ref, pv, pq bus sets
    -> makeBdc(bus, branch)           # Build B matrix
    -> dcpf(B, Pbus, Va0, ref, pv, pq)  # Solve Va = B\P
    -> Writes results back into ppci arrays
```

### Separation of Concerns

| Concern | Module(s) | Separated? |
|---------|-----------|------------|
| Network model | `pandapowerNet` (dict-of-DataFrames) | Yes - pure data, no solver logic |
| Model conversion | `pd2ppc.py` | Yes - dedicated module |
| Problem formulation | `pf/run_dc_pf.py` (B matrix construction) | Yes |
| Solver invocation | `pypower/dcpf.py` (sparse linear solve) | Yes - isolated function |
| Result extraction | `results.py`, `_ppci_to_net()` | Yes - dedicated functions |

### Abstraction Layer Count: 4

1. **Public API** (`run.py`): User-facing functions (`rundcpp`, `runpp`, `rundcopp`, `runopp`). Handles option validation and dispatching.
2. **Orchestration** (`powerflow.py`): Coordinates conversion, solving, and result extraction. The `_powerflow()` function is the central orchestrator.
3. **Data conversion** (`pd2ppc.py`): Transforms between pandapower's pandas DataFrames and MATPOWER-compatible numpy arrays. Bidirectional (pd->ppc for setup, ppc->pd for results).
4. **Solver** (`pf/run_dc_pf.py` + `pypower/dcpf.py`): Pure numerical computation on numpy arrays. No knowledge of pandapower data structures.

### Internal Interface Documentation

| Interface | Documented? | Notes |
|-----------|-------------|-------|
| Public API (`rundcpp`, `runpp`, etc.) | Yes | Full docstrings, RTD pages |
| `pandapowerNet` structure | Yes | Element tables documented per element type |
| `net._ppc` internal dict | Partially | Follows MATPOWER conventions; accessible but underscore-prefixed |
| `net._pd2ppc_lookups` | No | Internal index mapping, undocumented |
| `ppc`/`ppci` array layout | Inherited | MATPOWER column indices via `idx_bus`, `idx_gen`, `idx_brch` constants |
| PYPOWER solver functions | Minimal | Function signatures, sparse docstrings |

### Codebase Scale

| Metric | Value |
|--------|-------|
| Total `.py` files | 361 |
| Total LOC | ~89,300 |
| Subpackages | ~18 |
| Solver backends | 7+ (Newton-Raphson, BFSW, GS, FD, lightsim2grid, PGM, DC) |

### Architecture Quality Assessment

**Strengths:**
- Clean two-layer architecture (user-facing DataFrames / internal numpy arrays)
- Solver is fully isolated from data model
- Multiple solver backends share the same conversion pipeline
- Result extraction is centralized
- MATPOWER conventions for internal arrays enable interop with MATPOWER ecosystem

**Weaknesses:**
- No formal interface contracts between layers (no abstract base classes or protocols)
- Internal `_ppc` structure is accessible but not part of the public API contract
- `_pd2ppc()` is a large monolithic function (~900 lines) handling all element types
- No dependency injection for solver selection; algorithm selection is via string parameter and if/elif chain

## Implications

The architecture is well-structured for a tool of this maturity (10+ years, 89K LOC). The 4-layer separation enables solver swapping and extension through the controller framework. However, the lack of formal interfaces between layers means that extensions requiring deep integration (custom elements, custom formulations) must work with undocumented internals. This is consistent with the B-1/B-2 findings about custom constraint injection operating at the PYPOWER level rather than the pandapower level.
