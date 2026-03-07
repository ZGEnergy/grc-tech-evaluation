---
test_id: B-6
tool: pypsa
dimension: extensibility
network: N/A
protocol_version: "v4"
status: informational
workaround_class: null
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: null
timestamp: 2026-03-06T00:00:00Z
---

# B-6: Code Architecture

## Result: INFORMATIONAL

## Approach

Traced the `n.lpf()` call path through the PyPSA v1.1.2 source code, starting
from the public API entry point down to the linear algebra solve. Source files
examined:

- `pypsa/networks.py` (2033 lines) -- Network and SubNetwork class definitions
- `pypsa/network/power_flow.py` (1862 lines) -- all power flow logic

## Architecture Trace: `n.lpf()` Call Path

### Layer 1: Network API (public interface)

`Network.lpf()` is defined in `NetworkPowerFlowMixin` (line 805 of
`network/power_flow.py`). The Network class inherits from 8 mixins:

```
Network(
    NetworkComponentsMixin,      # Component store, property accessors
    NetworkDescriptorsMixin,     # Computed properties
    NetworkTransformMixin,       # Add/remove/copy components
    NetworkIndexMixin,           # Snapshot/period index management
    NetworkConsistencyMixin,     # Data validation
    NetworkGraphMixin,           # NetworkX graph, adjacency/incidence matrices
    NetworkPowerFlowMixin,       # PF calculations (lpf, pf, lpf_contingency)
    NetworkIOMixin,              # Import/export
)
```

`n.lpf()` normalizes the snapshot index and delegates immediately:

```python
def lpf(n, snapshots=None, skip_pre=False):
    sns = as_index(n, snapshots, "snapshots")
    _network_prepare_and_run_pf(n, sns, skip_pre, linear=True)
```

### Layer 2: Orchestrator (module-level function)

`_network_prepare_and_run_pf()` (line 140) is the shared entry point for both
linear and nonlinear power flow. It:

1. Selects the sub-network preparation function (`calculate_B_H` for linear,
   `calculate_Y` for nonlinear) and the sub-network solve function
   (`SubNetworkPowerFlowMixin.lpf` vs `.pf`)
2. Calls `n.determine_network_topology()` to identify connected sub-networks
3. Calls `n.calculate_dependent_values()` to compute per-unit impedances
4. Calls `_allocate_pf_outputs()` to prepare result DataFrames
5. Handles Link power dispatch
6. Iterates over each sub-network, calling `find_bus_controls()`,
   `calculate_B_H()`, then `sub_network.lpf()`

### Layer 3: Sub-network Solve

`SubNetworkPowerFlowMixin.lpf()` (line 1746) performs the actual linear power
flow on a single connected sub-network:

1. Computes nodal power injections by aggregating all one-port components
   (generators, loads, storage units, shunt impedances) grouped by bus
2. Calls `calculate_B_H()` if not already done
3. Solves the linear system: `v_diff[:, 1:] = spsolve(B[1:, 1:], p[:, 1:].T).T`
4. Computes branch flows: `flows = v_diff * H.T + p_branch_shift`
5. Writes results back to the Network's dynamic DataFrames

### Layer 4: Matrix Construction

`SubNetworkPowerFlowMixin.calculate_B_H()` (line 1079) builds the B and H
matrices used by the linear solve:

1. Extracts branch impedances (x_pu_eff for AC, r_pu_eff for DC)
2. Computes susceptances: `b = 1/z`
3. Builds incidence matrix K via `self.incidence_matrix()`
4. Constructs: `H = diag(b) * K^T` and `B = K * H` (weighted Laplacian)
5. Handles transformer phase shifts

### Layer 5: Linear Algebra (solver invocation)

The actual solve is a single `scipy.sparse.linalg.spsolve()` call at line 1831:

```python
v_diff[:, 1:] = spsolve(self.B[1:, 1:], p[:, 1:].T).T
```

This is a direct sparse LU factorization (no iterative solver, no external
optimizer). The slack bus row/column is removed from B before solving.

## Abstraction Layers

| Layer | Responsibility | Location |
|-------|---------------|----------|
| 1. Public API | Entry point, snapshot normalization | `NetworkPowerFlowMixin.lpf()` |
| 2. Orchestrator | Topology, impedance calc, sub-network dispatch | `_network_prepare_and_run_pf()` |
| 3. Sub-network solve | Power injection, linear system solve, result write-back | `SubNetworkPowerFlowMixin.lpf()` |
| 4. Matrix construction | B, H, K matrices from impedances | `SubNetworkPowerFlowMixin.calculate_B_H()` |
| 5. Linear algebra | Sparse direct solve | `scipy.sparse.linalg.spsolve()` |

**Total abstraction layers: 5** (API -> orchestrator -> sub-network solve -> matrix build -> scipy)

## Separation of Concerns

| Concern | Separated? | Notes |
|---------|-----------|-------|
| Network model / data | Yes | Mixin composition separates components, I/O, graph, PF |
| Problem formulation | Partial | B/H matrix construction is in the same module as the solve |
| Solver interface | N/A | DCPF uses scipy.sparse directly (no optimizer abstraction) |
| Results storage | Yes | Results written back to Network's pandas DataFrames |
| Topology | Yes | `determine_network_topology()` handled by NetworkGraphMixin |

The network model is well-separated through mixin composition. However, the
power flow module (`network/power_flow.py`) mixes several concerns: matrix
construction, the solve itself, result allocation, and both linear and nonlinear
PF are in the same 1862-line file. The optimization path (`n.optimize()`) uses a
completely separate subsystem with Linopy, demonstrating good separation between
PF and OPF.

## Internal Documentation Quality

- **Docstrings:** 29 of 34 functions (85%) have docstrings
- **Parameter documentation:** Public methods have full NumPy-style docstrings
  with parameter descriptions and return types
- **Inline comments:** Key mathematical steps are commented (e.g., "following leans
  heavily on pypower.makeBdc", "weighted Laplacian")
- **Type hints:** Comprehensive throughout, using modern Python typing
- **Architecture docs:** The mixin pattern is documented in docstrings ("Class
  inherits to pypsa.Network. All attributes and methods can be used within any
  Network instance.")
- **Gap:** The `_network_prepare_and_run_pf` orchestrator function lacks a
  docstring and is complex (90+ lines). Its role in dispatching between linear
  and nonlinear PF is not documented.

**Internal documentation quality: Good.** Public APIs are well-documented.
Internal functions have reasonable coverage. The main gap is the orchestrator
function's lack of documentation.

## Implications

The architecture is clean for its intended use case. The mixin pattern provides
good horizontal separation of concerns (components, I/O, graph, PF, optimization
are independent). The vertical call depth for DCPF (5 layers from API to scipy)
is reasonable. The main architectural weakness is the monolithic power_flow.py
file that handles both linear and nonlinear PF in 1862 lines, mixing matrix
construction with solving.

For extensibility, the key observations are:
1. DCPF bypasses the optimizer entirely (direct scipy solve), so solver-swap
   concepts do not apply
2. The optimization path (n.optimize) uses Linopy with a clean solver abstraction
3. Mixin composition makes subclassing fragile but provides good separation
4. All internal data flows through pandas DataFrames, making inspection trivial
