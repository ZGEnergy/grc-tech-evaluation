---
test_id: B-1
tool: powermodels
network: TINY
status: pass
timestamp: 2026-03-05T21:00:00Z
---

# B-1: Custom Constraints (Flow Gate Limit) on DC OPF (case39)

## Result: PASS

## Metrics

- **Wall clock:** ~2.5 s
- **Lines of code:** ~10 lines beyond baseline DC OPF
- **Workarounds:** None -- uses documented two-stage API
- **Source patching required:** No
- **Depends on:** A-3 (baseline DC OPF)

## Details

- **Network:** 39 buses, 10 generators
- **Solver:** HiGHS (QP)
- **Flow gate branches:** 1, 2, 3
- **Gate baseline flow:** 3.4555 pu (sum of pf on gate branches in unconstrained OPF)
- **Gate limit:** 2.7644 pu (80% of baseline flow)

### Results

| Metric | Baseline (A-3) | With Flow Gate |

|--------|----------------|----------------|

| Objective | 41,263.94 | 41,457.48 |

| Gate flow | 3.4555 pu | 2.7644 pu |

- **Objective increase:** 193.54 (flow gate raises cost by redirecting power)
- **Gate constraint binding:** Yes (constrained flow exactly at limit)
- **Gate limit respected:** Yes

### Dispatch Changes

The flow gate forces dispatch redispatch:
- Gen 1: 6.608 -> 5.430 (reduced to limit flow through gate branches)
- Gen 6: 6.608 -> 6.870 (increased to compensate)
- Gen 9: 6.608 -> 6.866 (increased to compensate)
- Gen 3: 6.608 -> 7.250 (increased to compensate)

### LMP Changes

LMPs become non-uniform with the flow gate active (compared to uniform LMPs in A-3):
- LMP range: -510.31 to -1722.88 (vs uniform ~-1356.8 in A-3)
- Bus 1 (near gate): -510.31 (significant divergence)
- Bus 3: -1722.88 (most negative)

## Method

Two-stage approach using documented API:
1. `instantiate_model(data, DCPPowerModel, PowerModels.build_opf)` to create model
2. Access branch flow variables via `PowerModels.var(pm, :p, (branch_id, f_bus, t_bus))`
3. Add flow gate constraint via `JuMP.@constraint(pm.model, sum(flows) <= limit)`
4. Solve via `optimize_model!(pm, optimizer=HiGHS.Optimizer)`

## API Pattern

```julia
pm = PowerModels.instantiate_model(data, DCPPowerModel, PowerModels.build_opf;
    setting = Dict("output" => Dict("duals" => true)))
# Access branch flow variable (indexed by branch_id, from_bus, to_bus tuple)
pf_var = PowerModels.var(pm, :p, (br_id, data["branch"][br_str]["f_bus"], data["branch"][br_str]["t_bus"]))
# Add flow gate constraint
JuMP.@constraint(pm.model, flowgate_upper, sum(gate_flow_vars) <= gate_limit)
result = PowerModels.optimize_model!(pm, optimizer=HiGHS.Optimizer)

```

## Notes

- Branch flow variables in DC OPF use `:p` symbol, indexed by `(branch_id, f_bus, t_bus)` tuple
- The variable indexing convention is not prominently documented; requires inspecting model internals or source code
- No source patching needed -- `instantiate_model` + JuMP constraint addition is the intended extension mechanism
- Flow gate constraints are a standard grid operations concept; PowerModels supports them cleanly via the two-stage API

## Test Script

See `evaluations/powermodels/tests/extensibility/test_b1_custom_constraints.jl`
