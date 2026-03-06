---
test_id: B-1
tool: powermodels
dimension: extensibility
network: MEDIUM
status: pass
wall_clock_seconds: 9.175
timestamp: 2026-03-05
---

# B-1: Custom Flow Gate Constraint on DC OPF [MEDIUM]

## Result: PASS

## Approach
Same as TINY: `instantiate_model()` + `JuMP.@constraint` on `pm.model` to add flow gate limit. Top-3 highest-flow branches selected as gate group, limit set to 80% of baseline flow.

## Data Preprocessing
- Standard preprocessing (costs, rate_a)

## Output
- Baseline DC OPF solved (Ipopt)
- Flow gate constraint added via JuMP (2 constraints: upper and lower bound)
- Gated DC OPF solved (Ipopt)
- Objective increase recorded (gate constraint binding)
- No source patching required

## Timing
- Wall-clock: 9.2s (both baseline and gated solves)
- Fast even at 10k-bus scale

## API Pattern

```julia
pm = PowerModels.instantiate_model(data, DCPPowerModel, PowerModels.build_opf)
pf_var = PowerModels.var(pm, :p, (br_id, f_bus, t_bus))
JuMP.@constraint(pm.model, sum(gate_vars) <= limit)
PowerModels.optimize_model!(pm, optimizer=Ipopt.Optimizer)

```
