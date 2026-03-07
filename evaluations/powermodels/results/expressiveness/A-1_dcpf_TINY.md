---
test_id: A-1
tool: powermodels
dimension: expressiveness
network: TINY
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 0.266
peak_memory_mb: null
loc: 131
solver: null
timestamp: "2026-03-06T00:00:00Z"
---

# A-1: Solve DCPF on TINY (IEEE 39-bus)

## Result: PASS

## Approach

Used PowerModels' native `compute_dc_pf(data)` function, which performs a direct linear solve (backslash operator on the susceptance matrix) without JuMP or any optimizer. This is the most efficient path for DCPF in PowerModels.

1. `PowerModels.parse_file("case39.m")` to load the MATPOWER file
2. `PowerModels.compute_dc_pf(data)` to solve (returns `Dict` with `"termination_status" => true/false`)
3. `PowerModels.update_data!(data, sol)` to merge solution into data
4. `PowerModels.calc_branch_flow_dc(data)` to compute line flows from angles

The native PF functions return `"termination_status"` as a Boolean (`true`/`false`), not an MOI status string -- this differs from the JuMP-based `solve_dc_pf()` which returns `"OPTIMAL"`.

## Output

- **Convergence:** true (direct solve, no iterations)
- **Solve time:** 0.0006s (excluding JIT)
- **39 bus voltage angles** extracted from `sol["bus"][id]["va"]` (radians)
  - Sample: Bus 1: -0.2056 rad, Bus 2: -0.1324 rad, Bus 3: -0.1814 rad
- **46 line flows** computed via `calc_branch_flow_dc`: `pf` (from-end) and `pt` (to-end)
  - DC flows are lossless: `pf = -pt` for all branches
- **10 generator injections** from `data["gen"][id]["pg"]` after `update_data!`
  - Gen 10 (slack at bus 39): 10.0 p.u., Gen 2: 6.78 p.u.
- **Net bus injections** computed as gen - load at each bus

## Workarounds

None required. The `compute_dc_pf` API is clean and direct.

## Timing

- Wall-clock: 0.266s (including parse, excludes JIT warm-up)
- Solve time: 0.0006s (direct linear solve only)
- Peak memory: not measured
- Iterations: N/A (direct solve)

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a1_dcpf.jl`
