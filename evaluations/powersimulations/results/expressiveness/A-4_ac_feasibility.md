---
test_id: A-4
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v11"
skill_version: "v2"
test_hash: "8531c61c"
status: pass
workaround_class: null
blocked_by: null
wall_clock_seconds: 1.900
timing_source: measured
peak_memory_mb: 1407.7
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: binary_convergence_api
loc: 337
solver: HiGHS + Ipopt
timestamp: "2026-03-24T00:00:00Z"
---

# A-4: AC Feasibility Check on DC OPF Dispatch

## Result: PASS

## Approach

Ran DCOPF on the Modified Tiny case39 (differentiated costs + 70% branch derating, same
configuration as A-3), then fixed generator active power dispatch on the same `System` object
and ran ACPF using PowerFlows.jl. The entire workflow operates on a single in-memory
`PowerSystems.System` object -- no export to file and reimport.

**Step 1 -- DCOPF:** Built a `DecisionModel` with `DCPPowerModel` network formulation,
`ThermalDispatchNoMin` device model, and `StaticBranch` for all branch types. Solver: HiGHS
1.21.1 (single-threaded, presolve on). Extracted per-generator dispatch from
`read_variable(res, "ActivePowerVariable__ThermalStandard")`.

**Step 2 -- Fix dispatch:** Set each generator's `active_power` to the DCOPF dispatch value
(converted to per-unit) via `set_active_power!(gen, dispatch_mw / base_power)`. This modifies
the same `System` object in-place.

**Step 3 -- ACPF:** Ran `solve_powerflow(ACPowerFlow(), sys)` from PowerFlows.jl on the
same System. PowerFlows.jl uses Newton-Raphson AC power flow with the generators' active power
as fixed setpoints (PV bus mode). Convergence confirmed by non-null return value.

**Step 4 -- Violation identification:** Extracted bus voltages from `pf_result["bus_results"]`
and branch flows from `pf_result["flow_results"]`. Computed MVA flow magnitude
`sqrt(P^2 + Q^2)` and compared against derated branch ratings. Checked reactive power limits
for all generators.

## Output

**DCOPF Dispatch (MW):**

| Generator | Bus | Dispatch (MW) |
|-----------|-----|--------------|
| gen-1 | 30 | 275.64 |
| gen-2 | 31 | 646.00 |
| gen-3 | 32 | 630.00 |
| gen-4 | 33 | 592.00 |
| gen-5 | 34 | 508.00 |
| gen-6 | 35 | 630.00 |
| gen-7 | 36 | 580.00 |
| gen-8 | 37 | 564.00 |
| gen-9 | 38 | 840.00 |
| gen-10 | 39 | 988.59 |

**ACPF convergence:** Yes (Newton-Raphson converged). Evidence quality: `binary_convergence_api`
-- `solve_powerflow` returns `Dict` on success, `nothing` on failure.

**Voltage summary:**

| Metric | Value |
|--------|-------|
| Min Vm | 0.9820 p.u. |
| Max Vm | 1.0636 p.u. |
| Mean Vm | 1.0263 p.u. |
| Buses checked | 39 |

**Voltage violations (5 buses outside [0.95, 1.05] p.u.):**

| Bus | Voltage (p.u.) | Type | Deviation |
|-----|---------------|------|-----------|
| 19 | 1.0506 | over | 0.0006 |
| 22 | 1.0502 | over | 0.0002 |
| 25 | 1.0578 | over | 0.0078 |
| 26 | 1.0523 | over | 0.0023 |
| 36 | 1.0636 | over | 0.0136 |

All violations are minor overvoltages (max 1.36% above 1.05 p.u.). No undervoltage violations.

**Thermal violations (3 branches exceeding derated MVA rating):**

| Branch | Flow (MVA) | Rating (MVA) | Loading (%) | Overload (MVA) |
|--------|-----------|------------|-------------|---------------|
| bus-2-bus-3-i_3 | 358.37 | 350.0 | 102.4% | 8.37 |
| bus-10-bus-32-i_20 | 640.00 | 630.0 | 101.6% | 10.00 |
| bus-22-bus-35-i_37 | 647.87 | 630.0 | 102.8% | 17.87 |

Thermal violations are expected -- DC OPF dispatch satisfies DC (active-power-only) limits but
AC power flow includes reactive power, making MVA flows exceed the active-power ratings.

**Reactive power violations (1 generator):**

| Generator | Q (MVAr) | Q_min (MVAr) | Q_max (MVAr) |
|-----------|---------|-------------|-------------|
| gen-8 | -1.37 | 0.0 | 250.0 |

gen-8 absorbs 1.37 MVAr reactive power, slightly below its Qmin of 0.

## Workarounds

None required. PowerSimulations.jl (DCOPF via `DecisionModel`) and PowerFlows.jl (ACPF via
`solve_powerflow`) share the same `PowerSystems.System` object. Dispatch values are set in-place
on generators via `set_active_power!`, then ACPF runs directly. No export/reimport needed.
The workflow uses documented public API from three Sienna ecosystem packages.

## Timing

- **Wall-clock:** 1.900 s (second run, after JIT warm-up; includes DCOPF build+solve + ACPF solve)
- **Timing source:** measured
- **Peak memory:** 1407.7 MB (Julia process RSS, includes JIT compilation cache)
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a4_ac_feasibility.jl`

Key API pattern:
```julia
# Step 1: DCOPF
model = DecisionModel(template, sys; optimizer=solver)
build!(model; output_dir=mktempdir()); solve!(model)
dispatch_df = read_variable(res, "ActivePowerVariable__ThermalStandard")

# Step 2: Fix dispatch in-place (same System object)
set_active_power!(gen, dispatch_mw / base_power)

# Step 3: ACPF on same System
pf_result = solve_powerflow(ACPowerFlow(), sys)

# Step 4: Extract violations
bus_df = pf_result["bus_results"]   # voltage violations
flow_df = pf_result["flow_results"] # thermal violations
```
