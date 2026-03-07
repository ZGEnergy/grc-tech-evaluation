---
test_id: B-1
tool: powermodels
dimension: extensibility
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 54.44
peak_memory_mb: null
loc: 210
solver: Ipopt
timestamp: "2026-03-07T00:00:00Z"
---

# B-1: Custom Flow Gate Constraint with Dual Extraction (MEDIUM, ACTIVSg 10k-bus)

## Result: PASS

## Approach

Same two-level API as TINY, applied to the ACTIVSg 10,000-bus network:

1. `PowerModels.solve_dc_opf(data, Ipopt)` to solve base case and identify the
   highest-flow branch (branch 2181, base flow = 19.524 p.u.)
2. `PowerModels.instantiate_model(data, DCPPowerModel, build_opf)` to build JuMP model
3. Accessed branch flow variable via `PowerModels.var(pm, nw_id, :p)[(br_idx, f_bus, t_bus)]`
4. Added custom constraints: `@constraint(jump_model, flow_var <= gate_limit)` and lower bound
5. `PowerModels.optimize_model!(pm, optimizer=Ipopt)` to solve constrained model
6. Extracted duals via `JuMP.dual(constraint_ref)`

Flow gate set to 80% of base flow on the most loaded branch.

## Output

- **Base case objective:** 2,436,631.22
- **Base case solve time:** 21.09s (Ipopt)
- **Constrained objective:** 2,440,666.42
- **Constrained solve time:** 7.05s (Ipopt)
- **Cost of flow gate constraint:** 4,035.20
- **Flow gate definition:** Branch 2181, limit = 15.6192 p.u. (80% of 19.524)
- **Constrained flow:** -15.6192 p.u. (binding at lower bound)
- **Dual value (lower bound):** 1,666.82 (non-zero, correctly reflects binding status)
- **Dual value (upper bound):** -0.0 (non-binding, correctly zero)
- **Constraint binding:** true

## Scaling Analysis

| Metric | TINY (39-bus) | MEDIUM (10k-bus) | Ratio |
|--------|--------------|------------------|-------|
| Base solve time | ~0.003s | 21.09s | ~7,000x |
| Constrained solve | ~0.003s | 7.05s | ~2,350x |
| Total wall-clock | 1.85s | 54.44s | 29x |

The large solve time increase is driven by the Ipopt QP formulation on 10k buses.
The two-level API (`instantiate_model` + JuMP constraint + `optimize_model!`) works
identically at both scales.

## Workarounds

None. The two-level API is a clean, documented extension mechanism.

## Test Script

Path: `evaluations/powermodels/tests/test_medium_batch3.jl`
