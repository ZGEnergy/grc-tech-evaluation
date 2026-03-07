---
test_id: C-2
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: 4.39
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T06:30:00Z"
---

# C-2: ACPF Scale — MEDIUM (ACTIVSg 10k)

## Result: FAIL

## Approach

ACPF on the 10,000-bus ACTIVSg network using `PowerFlows.solve_powerflow(ACPowerFlow(), sys)`.
Newton-Raphson solver with default settings (flat start).

## Output

| Metric | Value |
|--------|-------|
| Network | ACTIVSg 10k (10,000 buses, 12,706 branches, 2,485 generators) |
| Wall clock | 4.39s |
| Convergence | FAILED |
| Error | "The NewtonRaphsonACPowerFlow solver failed to converge" |

The Newton-Raphson ACPF solver did not converge on the 10,000-bus network. The
convergence protocol calls for a flat start → DC warm start fallback, but PowerFlows.jl
does not support DC warm start initialization — it only offers `ACPowerFlow()` with
the system's existing voltage setpoints.

## Root Cause

The ACTIVSg 10k case has complex topology with many generators requiring voltage magnitude
corrections during loading. The default Newton-Raphson implementation in PowerFlows.jl
(v0.9.0) may lack the robustness features (e.g., step-size limiting, Q-limit enforcement,
PV→PQ switching) needed for large-scale ACPF convergence.

## Implications

ACPF on MEDIUM networks is not achievable with the current PowerFlows.jl implementation.
This limits the DCOPF→ACPF feasibility check workflow (A-4) to TINY networks.

## Test Script

`evaluations/powersimulations/tests/scalability/test_scale_batch1.jl`
