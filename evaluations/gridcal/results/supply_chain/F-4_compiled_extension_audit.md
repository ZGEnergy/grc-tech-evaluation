---
test_id: F-4
tool: gridcal
dimension: supply_chain
network: N/A
protocol_version: "v4"
status: pass
workaround_class: null
timestamp: 2026-03-06T05:00:00Z
---

# F-4: Code Inspectability

## Criteria

Verify that the complete execution path from user API call to numerical result can be
traced through readable source code with no opaque steps.

## Result: PASS

The full DC power flow execution path is traceable through pure Python source with no
opaque binary steps.

### Traced Execution Path

1. **User entry**: `vge.power_flow(grid, options)` -- public API function
2. **Driver dispatch**: `PowerFlowDriver.run()` -- selects solver based on options
3. **Circuit compilation**: `compile_numerical_circuit_at(t)` -- builds admittance
   matrices from grid model at time snapshot `t`
4. **Numerical circuit**: `NumericalCircuit` -- assembles `Ybus`, `Sbus`, `B'`, `B''`
   sparse matrices from component data
5. **DC solver**: Constructs `B' * theta = P` system, calls
   `scipy.sparse.linalg.spsolve()` for the linear solve
6. **Result assembly**: `PowerFlowResults` -- voltage angles, branch flows, losses

Every step is a Python function or method. Matrix construction uses numpy/scipy array
operations that are directly readable. The sparse linear solve delegates to scipy which
calls LAPACK/SuperLU internally, but these are standard, well-audited numerical libraries.

### OPF Path

The OPF path routes through PuLP or highspy for LP/MILP formulation. The constraint
construction is visible in Python source. The solver itself (HiGHS) is open-source C++
with public source.

### No Obfuscation

- No minified or obfuscated code
- No encrypted modules or license-key gating in the open-source variant
- No dynamic code loading from network sources
