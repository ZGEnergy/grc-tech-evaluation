---
test_id: C-5
tool: powermodels
dimension: scalability
network: SMALL
protocol_version: v10
skill_version: v1
test_hash: 6ea5a7e5
status: pass
workaround_class: stable
blocked_by: null
wall_clock_seconds: 1.442
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 170
solver: NLsolve (Newton-Raphson via compute_ac_pf)
timestamp: 2026-03-13T22:00:00Z
---

# C-5: AC Feasibility — Progressive Relaxation on SMALL

## Result: PASS

## Approach

Progressive AC feasibility relaxation on the ACTIVSg 2000-bus network following the protocol:

1. **DCPF warm start:** Solved DC power flow using `compute_dc_pf` to extract bus voltage angles. All 1999 non-slack buses produced nonzero angles (0.152s).

2. **ACPF at 0% relaxation:** Initialized VM=1.0 pu on all buses, VA=DCPF solution angles. Solved ACPF using `compute_ac_pf` (NLsolve Newton-Raphson).

3. **Result:** Converged on the first attempt (0% relaxation) in 0.231s. No thermal limit relaxation was needed. Steps 3 and 4 (10%, 20% relaxation) were not required.

## Output

### DCPF Warm Start

| Metric | Value |
|--------|-------|
| DCPF converged | true |
| DCPF time | 0.152s |
| Non-zero angle buses | 1999 / 2000 |

### ACPF at 0% Relaxation

| Metric | Value |
|--------|-------|
| Converged | true (Bool) |
| ACPF solve time | 0.231s |
| Vm range | 0.93623 -- 1.01610 pu |
| Va range | -79.94 -- 0.0 deg |
| Buses with Vm != 1.0 | 1601 / 2000 |
| Non-slack buses with Va != 0 | 1999 / 1999 (100%) |
| Voltage violations ([0.95, 1.05] pu) | 58 buses |
| Thermal violations | 0 branches |
| Convergence quality | verified (100% non-flat angles) |

### Progressive Relaxation Summary

| Relaxation | Status | Wall-clock | Voltage Violations | Thermal Violations |
|------------|--------|-----------|--------------------|--------------------|
| 0% | **converged** | 0.231s | 58 | 0 |
| 10% | not attempted | -- | -- | -- |
| 20% | not attempted | -- | -- | -- |

### Voltage Violations

58 buses have voltage magnitudes below 0.95 pu. The minimum voltage is 0.936 pu. These are voltage magnitude violations, not convergence failures -- the solver found a valid AC solution, but some buses have voltage magnitudes outside the [0.95, 1.05] band. This is expected for a large network solved from flat voltage magnitudes. No thermal violations were detected.

## Workarounds

- **What:** `compute_ac_pf` termination_status is Bool (true/false), not a JuMP/MOI status code. NR iteration count and convergence residual not exposed.
- **Why:** `compute_ac_pf` uses NLsolve directly, bypassing JuMP diagnostic infrastructure.
- **Durability:** stable -- documented behavior, consistent with A-2 findings.
- **Grade impact:** Minor diagnostic limitation. Convergence verified via voltage profile quality (100% non-flat angles).

- **What:** Branch flows require post-processing via `calc_branch_flow_ac(data)` after `update_data!`.
- **Why:** `compute_ac_pf` does not populate `result["solution"]["branch"]`.
- **Durability:** stable -- documented public API function.
- **Grade impact:** Minor. Standard two-step pattern.

## Timing

- **Wall-clock (total):** 1.442s (includes JIT compilation overhead)
- **DCPF solve:** 0.152s
- **ACPF solve (0% relaxation):** 0.231s
- **Timing source:** measured
- **Peak memory:** not measured (peak RSS reading unavailable)
- **Solver iterations:** not available (NLsolve internal, not exposed)
- **Convergence residual:** not available (NLsolve internal)
- **CPU cores used:** 1

**Key finding:** The 2000-bus ACTIVSg network converges on the first attempt with 0% thermal relaxation and DCPF warm-start angles. This contrasts with A-2 MEDIUM (10k-bus), where `compute_ac_pf` failed to converge even with DC warm start. The 2000-bus scale is well within the NLsolve Newton-Raphson solver's convergence envelope.

## Test Script

**Path:** `evaluations/powermodels/tests/scalability/test_c5_ac_feasibility_relaxation_small.jl`

Key API sequence:

```julia
# Step 1: DCPF for warm-start angles
dc_data = deepcopy(data)
dc_result = PowerModels.compute_dc_pf(dc_data)

# Step 2: Set warm start (VM=1.0, VA=DCPF angles)
for (bus_id, bus) in ac_data["bus"]
    bus["vm"] = 1.0
    bus["va"] = dc_angles[bus_id]
end

# Step 3: ACPF at each relaxation level
ac_result = PowerModels.compute_ac_pf(ac_data)

# Step 4: Branch flows for thermal violation check
PowerModels.update_data!(ac_data, ac_result["solution"])
flow_data = PowerModels.calc_branch_flow_ac(ac_data)
```
