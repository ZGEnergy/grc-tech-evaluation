---
test_id: B-1
tool: powermodels
dimension: extensibility
network: TINY
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.981
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 4
solver: HiGHS
protocol_version: v10
skill_version: v1
test_hash: 6d6b3cf6
timestamp: 2026-03-13T23:36:40Z
---

# B-1: Custom Constraints (TINY)

## Result: PASS

## Approach

Used PowerModels' documented two-level API:
1. `instantiate_model(data, DCPPowerModel, build_opf)` — builds the JuMP model without solving
2. `@constraint(pm.model, flow_var <= limit)` — appends constraint to the JuMP model
3. `optimize_model!(pm; optimizer=optimizer)` — solves the constrained model
4. `JuMP.dual(constraint_ref)` — extracts dual value

Two test cases were run to verify both binding and non-binding behavior per cross-tool-watchpoints.md:

**Non-binding case:** Branch 5 flow limit set at 150% of unconstrained flow (9.91 pu). Constraint did not bind. Both duals were exactly 0.0. Objective unchanged from base (41263.94).

**Binding case:** Branch 5 flow limit set at 50% of unconstrained flow (3.30 pu). Constraint bound (actual flow = −3.30 pu, at lower limit). Dual on lower bound = 900.96. Objective increased by 1428.07 (from 41263.94 to 42692.01).

The branch with the largest unconstrained flow was branch 5 (flow = 6.608 pu). Network: 39 buses, 46 branches, 10 generators.

## Output

| Case | Limit (pu) | Actual Flow (pu) | Dual Upper | Dual Lower | Objective |
|------|-----------|-----------------|-----------|-----------|-----------|
| Base (no gate) | — | −6.608 | — | — | 41,263.94 |
| Non-binding (1.5×) | 9.913 | −6.608 | 0.0 | 0.0 | 41,263.94 |
| Binding (0.5×) | 3.304 | −3.304 | 0.0 | 900.961 | 42,692.01 |

- Non-binding dual = 0: confirmed
- Binding dual ≠ 0: confirmed (dual_lower = 900.96)
- Objective increased under binding constraint: +1,428.07 (+3.5%)
- Source patching required: false
- Extension API: `instantiate_model` + `@constraint(pm.model, ...)` + `optimize_model!`

## Workarounds

None required. The two-level API is documented in the PowerModels quickguide and specifically designed for custom constraint injection. `JuMP.dual()` is standard JuMP API.

## Timing

- **Wall-clock:** 0.981 s (post-JIT; includes warm-up call before timing)
- **Timing source:** measured
- **Peak memory:** not measured
- **Solver iterations:** Simplex 33 + QP ASM 100 (binding case, HiGHS)
- **Convergence residual:** N/A (LP/QP)
- **CPU cores used:** 1 (threads=1)

## Test Script

**Path:** `evaluations/powermodels/tests/extensibility/test_b1_custom_constraints_tiny.jl`

Key pattern — 4 lines of custom constraint code beyond model instantiation:

```julia

pm = PowerModels.instantiate_model(data, DCPPowerModel, PowerModels.build_opf)
flow_var = PowerModels.var(pm, nw_id, :p)[(br_idx, f_bus, t_bus)]
gate_upper = @constraint(pm.model, flow_var <= limit)   # line 1
gate_lower = @constraint(pm.model, flow_var >= -limit)  # line 2
result = PowerModels.optimize_model!(pm; optimizer=optimizer)
dual_u = JuMP.dual(gate_upper)   # line 3
dual_l = JuMP.dual(gate_lower)   # line 4

```
