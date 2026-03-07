---
test_id: B-1
tool: powermodels
dimension: extensibility
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.850
peak_memory_mb: null
loc: 210
solver: HiGHS
timestamp: "2026-03-06T00:00:00Z"
---

# B-1: Add a flow gate limit to DC OPF with dual extraction

## Result: PASS

## Approach

Used PowerModels' two-level API to add a custom flow gate constraint to DC OPF:

1. `PowerModels.solve_dc_opf(data, optimizer)` to solve base case and identify the highest-flow branch (branch 5, bus 2->30, base flow = 6.608 p.u.).
2. `PowerModels.instantiate_model(data, DCPPowerModel, PowerModels.build_opf)` to build JuMP model without solving.
3. Accessed the branch flow variable via `PowerModels.var(pm, nw_id, :p)[(br_idx, f_bus, t_bus)]`.
4. Added custom constraints directly to the JuMP model: `@constraint(jump_model, flow_var <= gate_limit)` and `@constraint(jump_model, flow_var >= -gate_limit)`.
5. `PowerModels.optimize_model!(pm, optimizer=optimizer)` to solve the constrained model.
6. Extracted dual values via `JuMP.dual(constraint_ref)`.

Flow gate was set to 80% of the base case flow on the most loaded branch, forcing the constraint to bind.

This approach uses no source patching -- it is the documented two-level API pattern. The `instantiate_model` + `optimize_model!` pair is explicitly designed for this use case.

## Output

- **Base case objective:** 41,263.94 $/hr
- **Constrained objective:** 41,482.93 $/hr
- **Cost of flow gate constraint:** 218.99 $/hr
- **Flow gate definition:** Branch 5 (bus 2 -> bus 30), limit = 5.287 p.u. (80% of 6.608)
- **Constrained flow on gate branch:** -5.287 p.u. (binding at lower bound)
- **Dual value (lower bound):** 335.02 (non-zero, correctly reflects binding status)
- **Dual value (upper bound):** 0.0 (non-binding, correctly zero)
- **Constraint binding:** true
- **Objective increased:** true (higher cost due to constrained dispatch)

The dual value of 335.02 on the lower bound constraint correctly indicates:
- The constraint is binding (flow equals the limit)
- Each unit of relaxation in the gate limit would reduce cost by ~335 $/hr
- The upper bound is non-binding (dual = 0), consistent with negative flow direction

## Workarounds

None required. The two-level API (`instantiate_model` + JuMP model access + `optimize_model!`) is a clean, documented extension mechanism. Custom constraints and dual extraction work exactly as expected through standard JuMP interfaces.

## Timing

- Wall-clock: 1.850s (includes base case solve, model build, constrained solve)
- Constrained solve time: 0.003s (HiGHS QP)
- Peak memory: not measured

## Test Script

Path: `evaluations/powermodels/tests/extensibility/test_b1_custom_constraints.jl`
