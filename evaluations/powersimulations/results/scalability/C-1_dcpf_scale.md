---
test_id: C-1
tool: powersimulations
dimension: scalability
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 9.4
peak_memory_mb: null
loc: null
solver: null
timestamp: "2026-03-07T06:30:00Z"
---

# C-1: DCPF Scale — MEDIUM (ACTIVSg 10k)

## Result: PASS

## Approach

DCPF on the 10,000-bus ACTIVSg network using `PowerFlows.solve_powerflow(DCPowerFlow(), sys)`.
System loaded from `case_ACTIVSg10k.m` via PowerSystems.jl.

## Output

| Metric | Value |
|--------|-------|
| Network | ACTIVSg 10k (10,000 buses, 12,706 branches, 2,485 generators) |
| System load time | 107.1s (includes JIT; subsequent loads ~3s) |
| DCPF solve time | 9.4s |
| Result format | Dict of DataFrames (bus_results, flow_results) |
| Flow results | 12,706 rows × 9 columns |
| Convergence | Direct solve (no iterations) |

DCPF scales well to 10,000 buses. The solve time of 9.4s is dominated by the PTDF
matrix factorization (direct linear solve). No solver required — this is a matrix operation.

## Timing

- System load: 107.1s (first run with JIT compilation)
- DCPF solve: 9.4s
- Total: ~116.5s

## Test Script

`evaluations/powersimulations/tests/scalability/test_scale_batch1.jl`
