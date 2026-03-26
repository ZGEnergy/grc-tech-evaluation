---
test_id: B-1
tool: powersimulations
dimension: extensibility
network: TINY
protocol_version: v11
skill_version: v2
test_hash: "fececf15"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 0.30
timing_source: measured
peak_memory_mb: 1263.9
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: null
loc: 372
solver: HiGHS
cpu_threads_used: null
cpu_threads_available: null
ingestion_path: null
sced_mode: null
test_category: null
timestamp: 2026-03-24T00:00:00Z
---

# B-1: Custom Constraints (flow gate limit + dual extraction)

## Result: PASS

## Approach

Built a DCOPF model via PowerSimulations.jl's `DecisionModel` with `DCPPowerModel`,
then accessed the underlying JuMP model via `PSI.get_optimization_container(model)` and
`PSI.get_jump_model(oc)`. Added a flow gate constraint using JuMP's `@constraint` macro
on flow variables found across multiple PSI variable containers (Lines and TapTransformers).

Tested two scenarios:

1. **Non-binding constraint** (limit = 10,000 MW, far above actual flow of 74.4 MW)
2. **Binding constraint** (limit = 50% of unconstrained flow = 37.18 MW)

Flow gate FG_01 from Modified Tiny data spans two branches: bus-2-bus-3 (Line) and
bus-2-bus-30 (TapTransformer). Both branch types have flow variables in PSI's internal
containers, accessed via `PSI.get_variables(oc)`.

Duals extracted directly from JuMP constraint references using `JuMP.dual()`.

### Solver settings (HiGHS)
- `time_limit`: 300s, `presolve`: on, `threads`: 1, `output_flag`: false

## Output

### Non-binding case (limit = 10,000 MW)

| Metric | Value |
|--------|-------|
| Termination status | OPTIMAL |
| Objective value | $215,211.33 |
| Flowgate flow | 74.36 MW |
| Dual (upper) | 0.0 |
| Dual (lower) | 0.0 |

### Binding case (limit = 37.18 MW)

| Metric | Value |
|--------|-------|
| Termination status | OPTIMAL |
| Objective value | $216,865.30 |
| Flowgate flow | 37.18 MW |
| Dual (upper) | -4,609.07 |
| Dual (lower) | 0.0 |

### Cost comparison

| Metric | Value |
|--------|-------|
| Unconstrained objective | $215,211.33 |
| Constrained objective | $216,865.30 |
| Cost increase | $1,653.97 |

### Dual behavior verification

- Non-binding dual = 0: **confirmed** (both upper and lower duals exactly zero)
- Binding dual != 0: **confirmed** (upper dual = -4,609.07, indicating binding constraint)
- Objective increases: **confirmed** ($1,653.97 increase)

The negative sign on the upper constraint dual is consistent with a binding upper bound
in a minimization problem (shadow price for relaxing the constraint). [tool-specific]

## Workarounds

None required for the core constraint addition and dual extraction. JuMP model access
via `PSI.get_optimization_container` + `PSI.get_jump_model` is the documented approach.

Minor operational note: PowerSimulations.jl requires deterministic time series data
even for single-snapshot DCOPF. Added 1-step forecast with multiplier=1.0 for all loads.
This is the same requirement noted in A-3. This is not classified as a workaround because
it is the standard API usage pattern for PowerSimulations.jl.

## Timing

- **Wall-clock:** 0.30s (second invocation, post-JIT)
- **Timing source:** measured
- **Peak memory:** 1,264 MB (includes JIT artifacts from warm-up)

## Test Script

**Path:** `evaluations/powersimulations/tests/extensibility/test_b1_custom_constraints.jl`

Key API pattern for adding custom constraints to a PSI model:

```julia
# Access JuMP model after build!
oc = PSI.get_optimization_container(model)
jm = PSI.get_jump_model(oc)

# Find flow variables across all branch types
psi_vars = PSI.get_variables(oc)
for k in keys(psi_vars)
    if occursin("FlowActivePowerVariable", string(k))
        arr = psi_vars[k]
        # arr[branch_name, timestep] gives JuMP variable reference
    end
end

# Add constraint and solve
con = @constraint(jm, flow_expr <= limit)
JuMP.optimize!(jm)

# Extract dual
dual_value = JuMP.dual(con)
```
