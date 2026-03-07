---
test_id: A-2
tool: powersimulations
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.43
peak_memory_mb: null
loc: 178
solver: "PowerFlows.jl internal Newton-Raphson"
timestamp: "2026-03-07T01:30:00Z"
---

# A-2: Solve AC Power Flow (Newton-Raphson)

## Result: PASS

## Approach

AC Power Flow was solved using `PowerFlows.jl` (v0.9.0) via
`solve_powerflow(ACPowerFlow(), sys)`. PowerFlows uses its own internal Newton-Raphson
solver -- Ipopt is NOT used for power flow. The solver converged in 4 iterations.

Flat start was attempted first (PQ buses set to Vm=1.0, Va=0.0). The flat start
**converged successfully** on case39, so no DC warm start fallback was needed.

Results are returned as a `Dict` with `"bus_results"` and `"flow_results"` DataFrames,
identical in structure to the DCPF results but with non-zero reactive power and loss
values.

## Output

**Bus results** (39 rows, 9 columns): Same columns as A-1 but with non-trivial Vm, Q values.

**Voltage statistics:**

| Metric | Value |
|--------|-------|
| Min Vm | 0.982 pu |
| Max Vm | 1.064 pu |
| Mean Vm | 1.026 pu |
| Min Va | -0.2537 rad |
| Max Va | 0.0780 rad |

**Active power balance:**

| Metric | Value (MW) |
|--------|-----------|
| Total generation P | 6297.87 |
| Total load P | 6254.23 |
| Gen-load balance (losses) | 43.64 |

**Reactive power:**

| Metric | Value (MVAr) |
|--------|-------------|
| Total generation Q | 1274.94 |
| Total load Q | 1387.10 |

**Line losses:**

| Metric | Value |
|--------|-------|
| Total P losses (from flow_results) | -68.97 (net flow direction losses) |
| Max single line P loss | 4.34 MW |
| Total Q losses | -4243.48 MVAr |

**Flat start convergence:** Yes (4 iterations)
**DC warm start needed:** No

**Output format:** DataFrames with bus_results (Vm, theta, P/Q gen/load/net) and flow_results (P/Q from/to, losses).

## Workarounds

None required.

## Timing

- **Wall-clock (total):** 1.43s (packages already compiled from A-1 in same session)
- **Solve time only:** 1.33s
- **Solver iterations:** 4 (Newton-Raphson)
- **Peak memory:** not measured
- **CPU cores used:** 1

## Test Script

**Path:** `evaluations/powersimulations/tests/expressiveness/test_a2_acpf.jl`
