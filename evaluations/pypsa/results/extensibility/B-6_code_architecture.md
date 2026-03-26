---
test_id: B-6
tool: pypsa
dimension: extensibility
network: N/A
protocol_version: v11
skill_version: v2
test_hash: 0f337d8d
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.09
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 349
solver: null
sced_mode: null
timestamp: 2026-03-24T00:00:00Z
---

# B-6: Qualitative assessment -- trace DCPF solve path from API call to solver invocation

## Result: PASS

## Approach

Used Python's `inspect` module to trace the call chain from `n.lpf()` down to
`scipy.sparse.linalg.spsolve`. Inspected source files, line counts, method resolution
order, module structure, and documented each layer's responsibility. Also assessed
the OPF path (`n.optimize()`) for comparison.

## Output

### Abstraction Layers: 4

| Layer | Name | LOC | Description |
|-------|------|-----|-------------|
| 1 | User API (`Network.lpf()`) | 19 | Single-call entry point. Iterates over SubNetworks and delegates. |
| 2 | Mixin Dispatch (`SubNetworkPowerFlowMixin.lpf()`) | 117 | Builds B-matrix, assembles injection vector P, calls spsolve(B, P), assigns results to DataFrames. |
| 2b | B-matrix construction (`calculate_B_H()`) | 57 | Constructs DC susceptance matrix and H-matrix from line/transformer parameters. Scipy sparse CSC format. Incorporates tap ratios. |
| 2c | PTDF computation (`calculate_PTDF()`) | 35 | Derives PTDF matrix from B and H. Optional -- not called by default lpf(). |
| 3 | Linear algebra backend (`scipy.sparse.linalg.spsolve`) | N/A | Direct sparse LU factorization (SuperLU). No external optimizer needed for DCPF. |

All layers reside in a single file: `pypsa/network/power_flow.py`.

### Network Class Inheritance Chain (12 classes)

```
Network -> NetworkComponentsMixin -> NetworkDescriptorsMixin ->
NetworkTransformMixin -> NetworkIndexMixin -> NetworkConsistencyMixin ->
NetworkGraphMixin -> NetworkPowerFlowMixin -> NetworkIOMixin ->
_NetworkABC -> ABC -> object
```

8 mixin classes compose the Network object. Each mixin owns a single concern
(components, graph, power flow, I/O, etc.).

### Module Structure

PyPSA v1.1.2 organizes into 15 top-level modules and 8 sub-packages:

- **Sub-packages:** clustering, components, data, definitions, network, optimization, plot, statistics
- **Key files:** `networks.py` (Network class), `network/power_flow.py` (PF/LPF), `optimization/` (OPF via linopy)

### Separation of Concerns

| Concern Pair | Separated? | Evidence |
|--------------|-----------|----------|
| Network model vs. formulation | Yes | Data in pandas DataFrames (`n.buses`, `n.lines`). Formulation in `power_flow.py` and `optimization/`. No mixing. |
| Formulation vs. solver | Yes (OPF) / Partial (PF) | OPF: solver selected via `solver_name` kwarg; linopy abstracts solver interface. DCPF: scipy.sparse is hardcoded -- no kwarg to swap. |
| Solver vs. results | Yes | Results assigned directly to `n.*_t` DataFrames. No solver-specific result objects. |
| Model build vs. solve | Yes (OPF) / No (PF) | OPF: `create_model()` and `solve_model()` are separate steps. PF: `lpf()` combines build and solve in one call. |

### Internal Interface Documentation

- **Public API:** Well documented at docs.pypsa.org with examples and tutorials.
- **SubNetwork-level methods:** Docstring-documented in source but not featured in the user guide. `calculate_B_H()`, `calculate_PTDF()`, `calculate_Y()` are discoverable but require source-reading.
- **Mixin architecture:** Not documented. Which mixin provides which method requires reading the class hierarchy in source code.

### Extension/Injection Points: 5

| Point | Scope | Access | Documented |
|-------|-------|--------|------------|
| `extra_functionality` callback | OPF | Public API | Yes |
| `n.model` (linopy.Model) | OPF | Public attribute | Yes |
| Component DataFrames (in-place mutation) | All | Public API | Yes |
| `n.graph()` (NetworkX export) | Topology | Public API | Yes |
| SubNetwork matrices (B, H, PTDF, Y) | PF internals | Public attributes | Partially |

### Architecture Quality Summary

**Strengths:**
- Clean separation of data model (DataFrames) from computation (power_flow.py, optimization/)
- OPF model build/solve separation is explicit and well-documented
- `extra_functionality` injection point is idiomatic and documented with examples
- All results as pandas DataFrames -- zero-friction interoperability
- NetworkX graph export via single API call
- PTDF accessible via public API after topology determination

**Weaknesses:**
- DCPF solver (scipy.sparse) is hardcoded -- not swappable via parameter
- PF build/solve not separated (no equivalent of create_model/solve_model for PF)
- SubNetwork access requires knowledge of internal structure (`n.sub_networks.at["0", "obj"]`)
- Mixin architecture creates non-obvious method resolution order; not documented

## Workarounds

None required.

## Timing

- **Wall-clock:** 1.09s
- **Timing source:** measured

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b6_code_architecture_tiny.py`
