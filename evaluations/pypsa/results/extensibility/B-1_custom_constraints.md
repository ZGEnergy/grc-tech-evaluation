---
test_id: B-1
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: v10
skill_version: v1
test_hash: fececf15
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.87
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 354
solver: HiGHS
timestamp: 2026-03-13T00:00:00Z
---

# B-1: Add a flow gate limit to the DC OPF formulation from A-3

## Result: PASS

## Approach

Used PyPSA's documented `extra_functionality` callback mechanism to inject a custom flow gate constraint into the DC OPF formulation. The callback receives `(n, snapshots)` where `n.model` is the linopy `Model` object, providing full access to add variables, constraints, and modify the objective.

The flow gate FG_01 spans two branches: line L2 (bus 2 -> bus 3) and transformer T0 (bus 2 -> bus 30). The callback accesses the `Line-s` and `Transformer-s` linopy variables, selects the gate branches, sums their flows, and constrains the sum to be <= threshold via `n.model.add_constraints()`.

Two cases were tested per the guardrail specification:

1. **Non-binding case**: Threshold = 10,000 MW (unreachable). Verifies that the dual value is ~0.
2. **Binding case**: Threshold = 50% of unconstrained flow (~57.2 MW). Verifies that the dual is nonzero and objective increases.

Solver: HiGHS with single-thread, 300s time limit, presolve on.

Network setup mirrors A-3: differentiated generator costs from Modified Tiny `gen_temporal_params.csv` (hydro $5, nuclear $10, coal $25, gas $40) and 70% branch derating for congestion.

## Output

| Case | Threshold (MW) | Objective ($) | FlowGate Dual | Gate Flow (MW) |
|------|----------------|---------------|---------------|----------------|
| Non-binding | 10,000 | 126,125.17 | -0.0 | 114.46 |
| Binding | 57.23 | 126,371.94 | -4.31 | 57.23 |

**Pass condition checks:**

| Check | Result |
|-------|--------|
| Dual extractable (non-binding) | Yes |
| Dual extractable (binding) | Yes |
| Dual ~0 when non-binding | Yes (|-0.0| < 1e-4) |
| Dual nonzero when binding | Yes (|-4.31| > 1e-6) |
| Objective increases when binding | Yes (126,372 > 126,125) |

The binding flow gate constraint forces the optimizer to reroute power away from the 2->3/2->30 corridor, increasing total generation cost by $247 (0.2% increase). The negative dual (-4.31 $/MWh) correctly reflects the shadow price of the constraint: each additional MW of flow gate capacity would reduce cost by $4.31.

## Workarounds

None required. The `extra_functionality` callback is the documented public API for custom constraint injection in PyPSA v1.1.2. The linopy `Model` provides `add_constraints()`, `add_variables()`, and full access to constraint duals after solve. No source patching, forking, or undocumented internals were needed.

## Timing

- **Wall-clock:** 1.87s (both solves combined)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** not reported (LP, direct solve)

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b1_custom_constraints.py`

Key API pattern for constraint injection:

```python
def add_flow_gate(n, snapshots):
    line_var = n.model.variables["Line-s"]
    xfmr_var = n.model.variables["Transformer-s"]
    lhs = line_var.sel({"Line": ["L2"]}).sum("Line") + \
          xfmr_var.sel({"Transformer": ["T0"]}).sum("Transformer")
    n.model.add_constraints(lhs, "<=", threshold, name="FlowGate")

n.optimize(extra_functionality=add_flow_gate, solver_name="highs")

# Extract dual after solve:
dual = n.model.constraints["FlowGate"].dual
```
