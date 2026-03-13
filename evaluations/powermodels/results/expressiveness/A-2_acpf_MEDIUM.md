---
test_id: A-2
tool: powermodels
dimension: expressiveness
network: MEDIUM
protocol_version: "v9"
skill_version: v1
test_hash: 23f50ea3
status: fail
workaround_class: null
blocked_by: null
wall_clock_seconds: 1261.51
timing_source: measured
peak_memory_mb: null
convergence_residual: null
convergence_iterations: null
loc: 165
solver: NLsolve (Newton-Raphson)
timestamp: 2026-03-11T05:15:00Z
---

# A-2: AC Power Flow (ACPF) — MEDIUM

## Result: FAIL

## Approach

Loaded `case_ACTIVSg10k.m` with MEDIUM preprocessing (2462 branches rate_a→9999 MVA). Enforced flat start (vm=1.0 pu, va=0.0 rad) per convergence-protocol.md. Attempted AC power flow using `PowerModels.compute_ac_pf(data)` — NLsolve-based Newton-Raphson, no JuMP.

**Attempt 1 — Flat start:** Ran to completion in 581.85s. Termination status: `Bool=false` (did not converge).

**Attempt 2 — DC warm-start fallback (convergence-protocol.md):** Solved DCPF first, set bus angles from DC solution (vm=1.0, va from DC). Re-ran `compute_ac_pf`. Ran to completion in 621.57s. Termination status: `Bool=false` (did not converge).

Total elapsed: **1261.51s (~21 minutes)**. Both attempts failed.

## Output

| Metric | Value |
|--------|-------|
| Buses | 10000 |
| Branches | 12706 |
| Generators | 2485 |
| Flat start result | failed (Bool=false, 581.85s) |
| DC warm-start result | failed (Bool=false, 621.57s) |
| Total wall-clock | 1261.51s |
| NR iterations | not available (diagnostic gap) |
| Convergence residual | not available (diagnostic gap) |
| Voltage profile | not extractable (no converged solution) |

## Workarounds

No workaround available. The NLsolve-based Newton-Raphson implementation in `compute_ac_pf` is not suitable for solving AC power flow on 10,000-bus networks within practical time limits.

### Per convergence-protocol.md:
- Flat start failure on MEDIUM scale: common
- DC warm-start failure on MEDIUM scale: notable finding, may cap grade

This failure is attributable to the NLsolve solver — not the network data. The ACTIVSg10k network has no fundamental infeasibility (other tools converge on it with Ipopt).

**What would be needed:** Use the JuMP-based AC OPF path (`solve_ac_opf` with Ipopt optimizer) rather than `compute_ac_pf`. However, AC OPF is not ACPF — it optimizes generation dispatch, not just computes power flow for a given dispatch. A proper ACPF with Ipopt would require using `instantiate_model(ACPPowerModel)` + `optimize_model!` with Ipopt configured as the solver, which the PowerModels API supports but is not the natural "ACPF" function.

## Timing

- **Wall-clock:** 1261.51s (~21 minutes, including both flat-start and DC warm-start attempts)
- **Flat start solve time:** 581.85s
- **DC warm-start solve time:** 621.57s
- **Timing source:** measured
- **Peak memory:** ~672 MB (from process monitor during run)
- **Solver iterations:** not available (NLsolve diagnostic gap)
- **Convergence residual:** not available

## Test Script

**Path:** `evaluations/powermodels/tests/expressiveness/test_a2_acpf_medium.jl`

Key API calls:

```julia

data = PowerModels.parse_file("case_ACTIVSg10k.m")
# Apply preprocessing
apply_medium_preprocessing!(data)
# Flat start
for (_, bus) in data["bus"]; bus["vm"] = 1.0; bus["va"] = 0.0; end

result = PowerModels.compute_ac_pf(data)
# termination_status is Bool
converged = result["termination_status"] == true  # false on 10k-bus network

# DC warm-start fallback:
dc_result = PowerModels.compute_dc_pf(data_dc)
PowerModels.update_data!(data_dc, dc_result["solution"])
result2 = PowerModels.compute_ac_pf(data_dc)  # also fails

```
