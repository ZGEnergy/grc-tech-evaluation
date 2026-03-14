---
test_id: A-4
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v10"
skill_version: "v1"
test_hash: "8531c61c"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.493
timing_source: measured
peak_memory_mb: 1506.3
convergence_residual: null
convergence_iterations: null
loc: 326
solver: HiGHS + Ipopt
timestamp: "2026-03-14T00:00:00Z"
---

# A-4: AC Feasibility Check on DC OPF Dispatch

## Result: PASS

## Approach

Ran DCOPF on the Modified Tiny case39 (differentiated costs + 70% branch derating, same
configuration as A-3), then fixed generator active power dispatch on the same `System` object
and ran ACPF using PowerFlows.jl. The entire workflow operates on a single in-memory
`PowerSystems.System` object with no export/reimport.

**Step 1 — DCOPF:** `DecisionModel` with `DCPPowerModel`, `ThermalDispatchNoMin`,
HiGHS solver. Extracted dispatch via `read_variable(res, "ActivePowerVariable__ThermalStandard")`.

**Step 2 — Fix dispatch:** Called `set_active_power!(gen, dispatch_pu)` for each generator,
converting MW dispatch from the DCOPF result to per-unit (divide by `base_power`).

**Step 3 — ACPF:** Called `solve_powerflow(ACPowerFlow(), sys)` from PowerFlows.jl on the
same System object. PowerFlows uses Newton-Raphson by default.

**Step 4 — Violation analysis:** Checked bus voltage magnitudes against [0.95, 1.05] pu
limits, branch apparent power flows against derated thermal ratings, and generator reactive
power output against reactive limits.

## Output

**ACPF converged:** Yes

**Voltage violations (5 buses outside [0.95, 1.05] pu):**

| Bus | Voltage (pu) | Type | Deviation |
|-----|-------------|------|-----------|
| 19 | 1.0506 | over | 0.0006 |
| 22 | 1.0502 | over | 0.0002 |
| 25 | 1.0578 | over | 0.0078 |
| 26 | 1.0523 | over | 0.0023 |
| 36 | 1.0636 | over | 0.0136 |

Voltage range: 0.982 to 1.064 pu (mean 1.026 pu). All violations are over-voltage at
generator-adjacent buses, consistent with PV bus voltage setpoints slightly exceeding
the 1.05 pu upper limit.

**Thermal violations (3 branches):**

| Branch | Flow (MVA) | Rating (MVA) | Loading |
|--------|-----------|-------------|---------|
| bus-2-bus-3-i_3 | 358.4 | 350.0 | 102.4% |
| bus-10-bus-32-i_20 | 640.0 | 630.0 | 101.6% |
| bus-22-bus-35-i_37 | 647.9 | 630.0 | 102.8% |

The DCOPF only constrains active power flow, so reactive power flow causes some branches
to exceed their MVA ratings when the full AC power flow is computed.

**Reactive power violation (1 generator):**

| Generator | Q (MVAr) | Q_min (MVAr) | Q_max (MVAr) |
|-----------|---------|-------------|-------------|
| gen-8 | -1.37 | 0.0 | 250.0 |

Generator gen-8 absorbs a small amount of reactive power below its minimum limit.

## Workarounds

None required. The PowerSimulations DCOPF and PowerFlows ACPF share the same
`PowerSystems.System` object. DCOPF dispatch values are set in-place on generators via
`set_active_power!()`, then ACPF runs on the same System. No file export or reimport needed.
The workflow uses three public packages from the same ecosystem (PowerSystems, PowerSimulations,
PowerFlows) with a shared data model.

## Timing

- **Wall-clock:** 1.493 s (second run, after JIT warm-up; includes DCOPF build+solve + ACPF)
- **Timing source:** measured
- **Peak memory:** 1506.3 MB (Julia process RSS, includes JIT compilation cache)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a4_ac_feasibility.jl`

Key API pattern:
```julia
# Step 1: DCOPF (same as A-3)
model = DecisionModel(template, sys; optimizer=highs_solver)
build!(model; output_dir=mktempdir()); solve!(model)
dispatch_mw = read_variable(res, "ActivePowerVariable__ThermalStandard")

# Step 2: Fix generator dispatch in-place
set_active_power!(gen, dispatch_mw / base_power)

# Step 3: ACPF on same System
pf_result = solve_powerflow(ACPowerFlow(), sys)

# Step 4: Check violations from pf_result["bus_results"], pf_result["flow_results"]
```

## Observations

- **convergence-quality:** ACPF converges on first attempt with flat start. The DC dispatch
  produces a feasible (but slightly violated) AC operating point, as expected for a lossless
  DC approximation.
- **unit-mismatch:** `set_active_power!()` expects per-unit values but DCOPF dispatch from
  `read_variable()` is in MW. User must divide by `base_power` manually. This is consistent
  with A-3 findings.
- **api-friction:** The shared `System` data model across PowerSystems, PowerSimulations,
  and PowerFlows makes this workflow seamless. No serialization or format conversion needed.
