---
test_id: A-1
tool: powermodels
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: pass
workaround_class: null
wall_clock_seconds: 1.85
peak_memory_mb: 121.3
loc: 103
solver: null
timestamp: 2026-03-07T00:00:00Z
---

# A-1: Solve DCPF on MEDIUM (ACTIVSg 10000-bus)

## Result: PASS

## Approach

Used PowerModels' native `compute_dc_pf(data)` function, which performs a direct linear solve (backslash operator on the susceptance matrix) without JuMP or any optimizer.

1. `PowerModels.parse_file("case_ACTIVSg10k.m")` -- parse time: 1.62s
2. `PowerModels.compute_dc_pf(data)` -- solve time: 0.234s (after JIT warm-up)
3. `PowerModels.update_data!(data, sol)` + `PowerModels.calc_branch_flow_dc(data)` for branch flows

## Output

- **Convergence:** true (direct solve, no iterations)
- **Network:** 10,000 buses, 12,706 branches, 2,485 generators
- **10,000 bus voltage angles** extracted from `sol["bus"][id]["va"]` (radians)
  - Sample: Bus 10001: 0.8197, Bus 10002: 0.8706, Bus 10003: 0.9269
- **12,706 branch flows** computed via `calc_branch_flow_dc`
- **Parse time:** 1.62s (MATPOWER .m file, 10k buses)
- **Solve time:** 0.234s (direct linear solve only, excludes JIT)

## Workarounds

None required. The `compute_dc_pf` API handled the 10,000-bus network without modification.

PowerModels emits thousands of Memento warnings about angle bounds being clamped to +/- 60 degrees (many branches in ACTIVSg10k have angmin/angmax = 0 or +/- 360). These are cosmetic and do not affect results.

## Timing

- Wall-clock: 1.85s (parse + solve, excludes JIT warm-up)
- Parse time: 1.62s
- Solve time: 0.234s
- Peak memory: 121.3 MB (total live bytes)
- Memory delta: 81.8 MB (incremental from DCPF)
- Iterations: N/A (direct solve)

## Test Script

Path: `evaluations/powermodels/tests/expressiveness/test_a1_dcpf_medium.jl`
Batch runner: `evaluations/powermodels/tests/test_medium_all.jl`
