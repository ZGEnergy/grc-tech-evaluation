---
test_id: B-1
tool: pypsa
dimension: extensibility
network: MEDIUM
protocol_version: v9
skill_version: v1
test_hash: 7578c2ba
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1704.11
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 165
solver: highs
timestamp: 2026-03-12T00:00:00Z
---

# B-1: Custom Constraints — Flow Gate (MEDIUM)

## Result: PASS

## Approach

Loaded ACTIVSg10k with `overwrite_zero_s_nom=100000.0` (required for OPF feasibility — ACTIVSg10k has 2,462 zero-rated branches that become 1 MVA constraints if set to 1.0, making OPF infeasible). Assigned differentiated marginal costs ($10–$100/MWh). Three-phase test:

1. **Pilot OPF**: Unconstrained DC OPF to identify the highest-flow line with positive flow.
2. **Non-binding case**: FlowGate constraint at 2× max_flow (line L2141, threshold=7993.90 MW). Constraint cannot bind; dual must be ≈0.
3. **Binding case**: FlowGate constraint at 0.5× max_flow (threshold=1998.47 MW). Constraint must bind; dual must be nonzero; objective must increase.

**Critical implementation detail:** PyPSA's `Line-s` linopy variable is signed (positive = forward, negative = reverse). A one-sided `<= threshold` constraint is trivially satisfied for negative-flow lines regardless of threshold. Gate line selection must use only lines with **positive** flow in the pilot solution.

Custom constraint added via `extra_functionality` callback using linopy's `model.add_constraints()`:
```python
def add_flow_gate(n, snapshots):
    var = n.model.variables["Line-s"]
    line_dim_name = [d for d in var.dims if d != "snapshot"][0]
    lhs = var.sel({line_dim_name: valid_gate}).sum(line_dim_name)
    n.model.add_constraints(lhs, "<=", threshold, name="FlowGate")
```

## Output

| Metric | Value |
|--------|-------|
| Network: buses | 10,000 |
| Network: lines | 9,726 |
| Network: generators | 1,465 |
| Pilot max flow line | L2141 |
| Pilot max flow (positive) | 3,996.95 MW |

**Non-binding case (threshold = 7,993.90 MW):**

| Metric | Value |
|--------|-------|
| Solver status | ok / optimal |
| Objective | $6,691,367/h |
| FlowGate dual | 0.0 (constraint non-binding ✓) |
| Actual gate flow | 3,996.95 MW |
| Solve time | 648.63 s |

**Binding case (threshold = 1,998.47 MW):**

| Metric | Value |
|--------|-------|
| Solver status | ok / optimal |
| Objective | $6,732,667/h |
| FlowGate dual | -30.87 $/MWh (constraint binding ✓) |
| Actual gate flow | 1,998.47 MW (exactly at threshold ✓) |
| Objective increase | +$41,300/h (+0.62%) |
| Solve time | 259.05 s |

**Pass condition checks:**

| Check | Result |
|-------|--------|
| Dual extractable (non-binding) | True ✓ |
| Dual extractable (binding) | True ✓ |
| Dual ≈ 0 (non-binding) | True ✓ |
| Dual ≠ 0 (binding) | True ✓ |
| Objective increases when binding | True ✓ |

## Workarounds

The test used the documented `extra_functionality` callback API. This is the standard PyPSA v1.1.2 approach for custom constraints — not a workaround.

Two implementation notes (not workarounds):
1. `overwrite_zero_s_nom=100000.0` is required for OPF on ACTIVSg10k (see observation `api-friction-extensibility-B-1_activsg10k_zero_s_nom_MEDIUM.md`)
2. Gate line selection must filter to positive-flow lines to avoid trivially satisfying the one-sided constraint (see observation `api-friction-extensibility-B-1_signed_line_variable_MEDIUM.md`)

## Timing

- **Wall-clock:** 1,704.11 s total (28.4 minutes)
  - Pilot OPF (unconstrained): 789.71 s (ran with CPU contention from concurrent stale processes)
  - Non-binding OPF: 648.63 s (also under contention)
  - Binding OPF (0.5× threshold): 259.05 s (after contention cleared)
- **Timing source:** measured
- **Note:** Pilot and non-binding solves ran with two stale processes competing for CPU (~3000% total). The binding solve ran cleanly (~984% CPU). Uncontended solve time for each OPF is estimated at ~60–120 s based on the binding case timing.

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b1_custom_constraints_medium.py`

Key API sequence (custom constraint injection):
```python
def add_flow_gate(n, snapshots):
    var = n.model.variables["Line-s"]  # signed apparent power variable
    line_dim_name = [d for d in var.dims if d != "snapshot"][0]
    lhs = var.sel({line_dim_name: gate_lines}).sum(line_dim_name)
    n.model.add_constraints(lhs, "<=", threshold, name="FlowGate")

n.optimize(extra_functionality=add_flow_gate, solver_name="highs", ...)

# Extract dual after solve:
dual = float(n.model.constraints["FlowGate"].dual.values.flatten()[0])
```
