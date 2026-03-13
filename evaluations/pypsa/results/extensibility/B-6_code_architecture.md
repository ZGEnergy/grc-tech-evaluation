---
test_id: B-6
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: v9
skill_version: v1
test_hash: 3468b28b
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.099
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 345
solver: null
timestamp: 2026-03-11T00:00:00Z
---

# B-6: Code Architecture Assessment

## Result: PASS

## Approach

Traced the DCPF call path from `n.lpf()` to matrix solve using `inspect.getsourcefile()` and `inspect.getsource()`. Assessed abstraction layers, separability of concerns, and injection points via static analysis of the PyPSA 1.1.2 source.

## Output

### Abstraction Layers (4)

| Layer | Name | Description |
|-------|------|-------------|
| 1 | User API | `n.lpf()`, `n.pf()`, `n.optimize()` — single-call entry points. Results written to `n.*_t` DataFrame attributes. |
| 2 | Network Mixin Dispatch | `Network` is composed of 8 mixins: `NetworkComponentsMixin`, `NetworkDescriptorsMixin`, `NetworkTransformMixin`, `NetworkIndexMixin`, `NetworkConsistencyMixin`, `NetworkGraphMixin`, `NetworkPowerFlowMixin`, `NetworkIOMixin`. `n.lpf()` delegates to `SubNetwork.lpf()`. |
| 3 | SubNetwork Computation | `SubNetwork` owns B-matrix, PTDF, BODF, and linear algebra. Builds admittance matrices from component DataFrames; solves Bθ=P via `scipy.sparse.linalg`. |
| 4 | Linear Algebra Backend | `scipy.sparse` + `numpy` for DCPF/ACPF. `linopy` + `HiGHS` for OPF. No external solver for DC power flow — direct sparse LU factorization. |

**Network MRO:**
```
Network → NetworkComponentsMixin → NetworkDescriptorsMixin → NetworkTransformMixin
→ NetworkIndexMixin → NetworkConsistencyMixin → NetworkGraphMixin
→ NetworkPowerFlowMixin → NetworkIOMixin → _NetworkABC → ABC → object
```

### Separability of Concerns

| Concern | Verdict | Detail |
|---------|---------|--------|
| Model build vs. solve | Clean for OPF; implicit for PF | `n.optimize.create_model()` and `n.optimize.solve_model()` are explicit separate steps for OPF. For DCPF, B-matrix construction and solve are fused in `sub_network_lpf()` — not externally separable, but PTDF extraction works independently. |
| Data model vs. formulation | Well separated | Network data in static DataFrames (`n.buses`, `n.lines`, `n.generators`), time-series in `n.*_t`. Formulation logic in `network/power_flow.py` and `optimization/`. No mixing. |
| Solver interface | Abstracted for OPF; hard-coded for PF | OPF: `solver_name=` kwarg routes through `linopy` to HiGHS/GLPK. DCPF: `scipy.sparse` is hard-coded — not configurable or swappable via public API. |
| Results extraction | Zero-friction DataFrames | All results in `n.*_t` accessor attributes (already pandas DataFrames). `n.lines_t.p0`, `n.buses_t.v_ang`, `n.buses_t.marginal_price`, etc. No unwrapping needed. |

### Injection Points (5 stable)

| Injection Point | Type | Durability |
|----------------|------|-----------|
| `extra_functionality(n, snapshots)` kwarg to `n.optimize()` | Add custom constraints/vars to linopy model before solve | stable |
| `n.optimize.create_model()` + `n.model` | Direct linopy model access for modification before `solve_model()` | stable |
| `sub_network.calculate_PTDF()` | Exposes `sub_network.PTDF` numpy array for sensitivity analyses | stable |
| `n.graph()` | Returns full-featured `networkx.OrderedGraph` | stable |
| Component DataFrames (`n.buses`, `n.lines`, etc.) | In-place parameter modification; `n.add()` / `n.remove()` for components | stable |

### Quality Summary

**Strengths:**
- Clean separation of data model (DataFrames) from computation (`pf.py`, `optimization/`)
- OPF model build/solve separation is explicit and well-documented with examples
- `extra_functionality` injection is idiomatic and documented (used in official examples)
- All results as pandas DataFrames — zero-friction interoperability with the scientific Python stack
- NetworkX graph export requires a single API call
- Native PTDF and BODF computation available via public API

**Weaknesses:**
- DCPF solver (`scipy.sparse`) is hard-coded — not swappable via kwarg (contrast with OPF)
- `n.lpf_contingency()` is broken on Python 3.12+ — a regression in a public API method
- `SubNetwork` access pattern (`n.sub_networks.at['0', 'obj']`) requires knowledge of the internal data structure and is not documented in examples
- Mixin architecture (8 mixins) creates a non-obvious method resolution order; finding where a method is defined requires tracing the MRO

## Workarounds

None required. This test is a qualitative assessment.

## Timing

- **Wall-clock:** 0.099 s
- **Timing source:** measured
- **Peak memory:** not measured

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b6_code_architecture_tiny.py`

The script uses `inspect.getsourcefile()`, `inspect.getsource()`, and `type.__mro__` to locate and characterize key functions.
