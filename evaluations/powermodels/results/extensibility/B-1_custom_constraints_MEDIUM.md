---
test_id: B-1
tool: powermodels
dimension: extensibility
network: MEDIUM
protocol_version: "v9"
skill_version: v1
test_hash: 224f17c2
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 286.48
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 125
solver: HiGHS
timestamp: 2026-03-11T09:30:00Z
---

# B-1: Custom Constraints — MEDIUM

## Result: PASS

## Approach

Loaded `case_ACTIVSg10k.m` and applied MEDIUM preprocessing (0 zero-reactance branches fixed; 2462/12706 rate_a values set to 9999 MVA). Linearized 1130 quadratic cost generators (QP→LP) to allow HiGHS to solve as LP.

Used the two-level API (same approach as TINY):

1. Solved base-case DC OPF via `solve_dc_opf` to identify the highest-flow branch (branch 2181, 13580→13631, base flow = 2064.17 MW).
2. `instantiate_model(data, DCPPowerModel, build_opf)` — builds JuMP model without solving.
3. Accessed the branch flow variable: `var(pm, nw_id, :p)[(br_idx, f_bus, t_bus)]`.
4. Added custom gate constraints: `@constraint(pm.model, flow_var <= gate_limit)` and `@constraint(pm.model, flow_var >= -gate_limit)`.
5. `optimize_model!(pm; optimizer=optimizer)` — solved the constrained model.
6. Extracted duals via `JuMP.dual(gate_con)`.

**Binding case:** Gate limit set to 80% of base flow (1651.34 MW).
**Non-binding case:** Gate limit set to 200% of base flow (4128.35 MW).

JIT warm-up performed on case39 before timing. Wall-clock of 286.5s includes:
- Parse + preprocessing: ~22s
- Base case DC OPF: 95.4s
- Binding case DC OPF: 87.1s
- Non-binding case DC OPF: 68.4s
- JIT warm-up: ~14s (excluded from above)

## Output

### Binding Case (gate = 80% of base flow = 1651.34 MW)

| Metric | Value |
|--------|-------|
| Status | OPTIMAL |
| Solve time | 87.1s |
| Objective | $2,403,861/h |
| Base objective | $2,401,337/h |
| Objective increase | $2,524/h |
| Flow on gate branch | −1651.34 MW (exactly at lower bound) |
| Constraint binding | true |
| Dual (UB) | 0.0 |
| Dual (LB) | 1429.32 |
| Dual nonzero | **true** ✓ |

### Non-Binding Case (gate = 200% of base flow = 4128.35 MW)

| Metric | Value |
|--------|-------|
| Status | OPTIMAL |
| Solve time | 68.4s |
| Objective | $2,401,337/h (matches base — constraint inactive) |
| Flow on gate branch | −2064.17 MW (well within ±4128.35 MW gate) |
| Dual (UB) | 0.0 |
| Dual (LB) | 0.0 |
| Dual zero | **true** ✓ |

### Extension API Used

```julia

pm = PowerModels.instantiate_model(data, DCPPowerModel, PowerModels.build_opf)
nw_id  = PowerModels.nw_id_default
p_vars = PowerModels.var(pm, nw_id, :p)
flow_var = p_vars[(br_idx, f_bus, t_bus)]
gate_con_ub = @constraint(pm.model, flow_var <=  gate_limit)
gate_con_lb = @constraint(pm.model, flow_var >= -gate_limit)
result = PowerModels.optimize_model!(pm; optimizer=optimizer)
dual_ub = JuMP.dual(gate_con_ub)   # 0.0 (upper not binding)
dual_lb = JuMP.dual(gate_con_lb)   # 1429.32 (lower binding)

```

## Workarounds

None required. The `instantiate_model` → `@constraint(pm.model, ...)` → `optimize_model!` → `JuMP.dual()` path works cleanly at MEDIUM scale. No source patching needed.

## Timing

- **Wall-clock:** 286.5s total (includes 3 OPF solves: base + binding + non-binding)
- **Timing source:** measured
- **Per-solve timing:** base=95.4s, binding=87.1s, non-binding=68.4s
- **Peak memory:** not measured
- **Solver:** HiGHS v1.13.1 (LP, costs linearized from QP→LP)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powermodels/tests/extensibility/test_b1_custom_constraints_medium.jl`

Key extension API calls:

```julia

# Step 1: solve base case to find high-flow branch
base_result = PowerModels.solve_dc_opf(data, optimizer; setting=Dict("output" => Dict("duals" => true)))
# ... find max-flow branch from base_result["solution"]["branch"] ...

# Step 2: two-level API with custom constraint
pm_bind = PowerModels.instantiate_model(data, DCPPowerModel, PowerModels.build_opf)
p_vars  = PowerModels.var(pm_bind, PowerModels.nw_id_default, :p)
flow_var = p_vars[(br_idx, f_bus, t_bus)]
gate_con_lb = @constraint(pm_bind.model, flow_var >= -gate_limit)
gate_con_ub = @constraint(pm_bind.model, flow_var <=  gate_limit)
bind_result = PowerModels.optimize_model!(pm_bind; optimizer=optimizer)
dual_lb = JuMP.dual(gate_con_lb)   # nonzero: 1429.32

```
