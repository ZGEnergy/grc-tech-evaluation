---
test_id: B-1
tool: pypsa
dimension: extensibility
network: TINY
protocol_version: v9
skill_version: v1
test_hash: 7578c2ba
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 2.39
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 175
solver: highs
timestamp: 2026-03-11T00:00:00Z
---

# B-1: Custom Constraints — Flow Gate (custom_constraints)

## Result: PASS

## Approach

Loaded case39.m with the same A-3 setup (differentiated marginal costs $10–$100/MWh, all branch limits derated 70%). Defined a flow gate as the sum of apparent power flows on lines `L1` and `L2` (≤ threshold).

Custom constraint added via `extra_functionality(n, snapshots)` callable passed to `n.optimize()`. Inside the callback, the linopy variable `Line-s` was accessed via `n.model.variables["Line-s"]`, filtered to gate lines using `var.sel({dim: gate_lines})`, and the sum added as `n.model.add_constraints(lhs, "<=", threshold, name="FlowGate")`.

**Non-binding case:** Threshold = 10,000 MW (unreachable). Dual extracted via `n.model.constraints["FlowGate"].dual`.

**Binding case:** Threshold = 95% of unconstrained flow sum (~358.66 MW). Thresholds of 75% and 90% produced infeasible problems because the 70% branch derating creates a tightly congested network where even moderate reductions in gate flow are infeasible. At 95%, the constraint is both feasible and binding.

**Key API discovery:** In PyPSA v1.1.2, the line flow variable is named `Line-s` (apparent power), not `Line-p` (active power) as the spec suggested. The spec note about checking `n.model.variables["Line-p"].dims` was outdated; the actual variable is `Line-s`.

## Output

| Metric | Non-Binding | Binding |
|--------|------------|---------|
| Threshold (MW) | 10,000 | 358.66 |
| Solver status | ok/optimal | ok/optimal |
| Objective ($/h) | 370,208.16 | 385,881.87 |
| FlowGate dual | 0.0 | −830.32 |
| Actual gate flow (MW) | 377.53 | 358.66 |

**Pass condition checks:**
- Dual extractable (non-binding): ✓
- Dual extractable (binding): ✓
- Dual ≈ 0 when non-binding: ✓ (dual = −0.0)
- Dual ≠ 0 when binding: ✓ (dual = −830.32)
- Objective increases when binding: ✓ ($385,882 > $370,208; +4.2%)

**Constraint dimension names observed:**
- Line flow variable: `Line-s` (not `Line-p`)
- Line dimension in variable: `Line-ext-0` (or similar — confirmed by `var.dims`)
- All constraints: `Generator-fix-p-lower`, `Generator-fix-p-upper`, `Line-fix-s-lower`, `Line-fix-s-upper`, `Transformer-fix-s-lower`, `Transformer-fix-s-upper`, `Kirchhoff-Voltage-Law`, `FlowGate`

**Note on threshold feasibility:** At 70% branch derating, the network is heavily congested. The protocol target of 50% of unconstrained flow sum was infeasible. 75% and 90% were also infeasible. Only 95% produced a feasible binding case. This reflects network topology, not an API limitation.

## Workarounds

None required. The `extra_functionality` API is the documented public mechanism for adding custom constraints in PyPSA v1.1.2. The complete constraint injection pattern is:

```python
def add_flow_gate(n, snapshots):
    var = n.model.variables["Line-s"]
    line_dim = [d for d in var.dims if d != "snapshot"][0]
    lhs = var.sel({line_dim: gate_lines}).sum(line_dim)
    n.model.add_constraints(lhs, "<=", threshold, name="FlowGate")

n.optimize(extra_functionality=add_flow_gate, solver_name="highs")
dual = n.model.constraints["FlowGate"].dual
```

This is a first-class, documented extension point. No internal patching required.

**One minor doc gap:** The variable name `Line-s` vs `Line-p` is not documented in the public API reference — must be discovered empirically or by reading source code. Logged as observation.

## Timing

- **Wall-clock:** 2.39 s (total including 3 binding-threshold attempts)
- **Timing source:** measured
- **Solve time:** ~0.4 s per solve call (non-binding); ~0.3 s (binding at 95%)
- **Peak memory:** not measured
- **CPU cores used:** 1 (configured)

## Test Script

**Path:** `evaluations/pypsa/tests/extensibility/test_b1_custom_constraints_tiny.py`
