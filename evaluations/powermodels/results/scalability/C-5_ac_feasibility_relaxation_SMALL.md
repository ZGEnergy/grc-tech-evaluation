---
test_id: C-5
tool: powermodels
dimension: scalability
network: SMALL
protocol_version: v11
skill_version: v2
test_hash: 4b83d02b
status: informational
workaround_class: stable
blocked_by: null
wall_clock_seconds: 1.504
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
convergence_evidence_quality: binary_convergence_api
loc: 170
solver: NLsolve (Newton-Raphson via compute_ac_pf)
cpu_threads_used: 1
cpu_threads_available: 32
timestamp: 2026-03-24T16:30:00Z
---

# C-5: AC Feasibility — Progressive Relaxation on SMALL (ACTIVSg 2000-bus)

## Result: INFORMATIONAL

All C-5 outcomes are diagnostic (informational) per v11 protocol -- not scored pass/fail.

## Approach

Progressive AC feasibility relaxation on the ACTIVSg 2000-bus network following the convergence protocol:

1. **DCPF warm start:** Solved DC power flow using `compute_dc_pf` to extract bus voltage angles. All 1999 non-slack buses produced nonzero angles (0.117s).

2. **ACPF at 0% relaxation:** Initialized VM=1.0 pu on all buses, VA=DCPF solution angles. Solved ACPF using `compute_ac_pf` (NLsolve Newton-Raphson).

3. **Result:** Converged on the first attempt (0% relaxation) in 0.279s. No thermal limit relaxation was needed. Steps at 10% and 20% relaxation were not required.

Solver: NLsolve (Newton-Raphson, internal to `compute_ac_pf`). Single-threaded.

## Output

### DCPF Warm Start

| Metric | Value |
|--------|-------|
| DCPF converged | true |
| DCPF time | 0.117s |
| Non-zero angle buses | 1999 / 2000 |

### ACPF at 0% Relaxation

| Metric | Value |
|--------|-------|
| Converged | true (Bool) |
| ACPF solve time | 0.279s |
| Vm range | 0.93623 -- 1.01610 pu |
| Va range | -79.94 -- 0.0 deg |
| Buses with Vm != 1.0 | 1601 / 2000 (80.1%) |
| Non-slack buses with Va != 0 | 1999 / 1999 (100%) |
| Voltage violations ([0.95, 1.05] pu) | 58 buses |
| Thermal violations | 0 branches |
| Convergence evidence quality | binary_convergence_api (Bool status + voltage profile) |
| Relaxation level achieved | **0%** |

### Progressive Relaxation Summary

| Relaxation | Status | Wall-clock | Voltage Violations | Thermal Violations |
|------------|--------|-----------|--------------------|--------------------|
| 0% | **converged** | 0.279s | 58 | 0 |
| 10% | not attempted | -- | -- | -- |
| 20% | not attempted | -- | -- | -- |

### Voltage Violations

58 buses have voltage magnitudes below 0.95 pu (minimum 0.936 pu). These are voltage magnitude violations in the converged AC solution, not convergence failures. No thermal violations were detected. The 2000-bus ACPF converges cleanly at 0% relaxation with DCPF warm start.

## Workarounds

- **What:** `compute_ac_pf` returns a Bool for `termination_status` (true/false), not a JuMP/MOI status code. NR iteration count and convergence residual are not exposed.
- **Why:** `compute_ac_pf` uses NLsolve directly, bypassing JuMP diagnostic infrastructure.
- **Durability:** stable -- documented behavior, consistent with A-2 findings.
- **Grade impact:** Minor diagnostic limitation. Convergence verified via voltage profile quality (100% non-flat angles).

- **What:** Branch flows require post-processing via `calc_branch_flow_ac(data)` after `update_data!`.
- **Why:** `compute_ac_pf` does not populate `result["solution"]["branch"]`.
- **Durability:** stable -- documented public API function.
- **Grade impact:** Minor. Standard two-step pattern.

## Timing

- **Wall-clock (total):** 1.504s
- **DCPF solve:** 0.117s
- **ACPF solve (0% relaxation):** 0.279s
- **Timing source:** measured
- **Peak memory:** not measured (peak RSS reading unavailable in script)
- **Solver iterations:** not available (NLsolve internal, not exposed)
- **Convergence residual:** not available (NLsolve internal)
- **CPU threads used:** 1
- **CPU threads available:** 32

**Key finding:** The 2000-bus ACTIVSg network converges on the first attempt with 0% thermal relaxation and DCPF warm-start angles. This contrasts with MEDIUM (10k-bus), where both `compute_ac_pf` (NLsolve) and `solve_ac_pf` (Ipopt) diverge. The convergence boundary lies between 2,000 and 10,000 buses.

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

# Step 3: ACPF
ac_result = PowerModels.compute_ac_pf(ac_data)

# Step 4: Branch flows for thermal violation check
PowerModels.update_data!(ac_data, ac_result["solution"])
flow_data = PowerModels.calc_branch_flow_ac(ac_data)
```
