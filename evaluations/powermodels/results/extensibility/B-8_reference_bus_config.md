# B-8: Reference Bus Configuration (TINY — case39)

## Tool
PowerModels.jl v0.21.5

## Status: PASS

## Summary
Three slack configurations tested via DC OPF: (1) default ref bus, (2) alternative single ref bus, (3) distributed slack via custom build function. All three produce identical objectives (41,263.94) and identical LMPs, confirming that in lossless DC OPF the ref bus choice only sets the angle origin. Ref bus is configurable via `bus_type` field. Distributed slack is NOT native and requires a custom build function (~15 LOC workaround).

## Approach

### Config 1: Default reference bus (bus 31)
- Parse network; bus 31 has `bus_type=3` (ref) by default
- `solve_dc_opf(data, HiGHS.Optimizer; setting=Dict("output"=>Dict("duals"=>true)))`

### Config 2: Alternative reference bus (bus 30)
- Set bus 31 to `bus_type=2` (PV), bus 30 to `bus_type=3` (ref)
- Same solve call

### Config 3: Distributed slack (custom workaround)
- Write custom `build_distributed_slack_opf` function that:
  - Calls all standard variable/constraint/objective functions
  - Replaces `constraint_theta_ref` with `@constraint(model, sum(va[i] for i in buses) == 0)`
  - Uses `PowerModels.var(pm, :va, i)` to access angle variables
- Pass custom build function to `solve_model()`

## Results

| Config | Ref Bus | Objective | LMP Bus 1 | Status |

|--------|---------|-----------|-----------|--------|

| 1 (default) | 31 | 41,263.94 | -1351.692 | OPTIMAL |

| 2 (alt single) | 30 | 41,263.94 | -1351.692 | OPTIMAL |

| 3 (distributed) | sum(va)=0 | 41,263.94 | -1351.692 | OPTIMAL |

- Max LMP diff config 1 vs 2: 0.0
- Max LMP diff config 1 vs 3: 0.0
- All 39 buses report LMPs in all configs

## Ref Bus Configuration Mechanism
- **Single ref bus**: Set `data["bus"]["X"]["bus_type"] = 3` for desired bus, ensure only one bus has type 3
- **Limitation**: Only single reference bus is officially supported. Multiple type-3 buses produce a warning about potential infeasibility.
- **Distributed slack**: Not native. Requires writing a custom `build_*` function (approximately 40 lines including all standard boilerplate, 15 lines net new).

## Dual/LMP Extraction
- Requires passing `setting = Dict("output" => Dict("duals" => true))` to the solve call
- LMPs appear in `result["solution"]["bus"][i]["lam_kcl_r"]`
- This setting requirement is not prominently documented; easy to miss.

## Workarounds
- Distributed slack requires custom build function replacing `constraint_theta_ref` with a sum-of-angles constraint.
- Dual reporting requires explicit `setting` parameter (not enabled by default).

## Script
`tests/extensibility/test_b8_reference_bus_config.jl`
