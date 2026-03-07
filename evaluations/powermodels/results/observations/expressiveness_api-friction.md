---
tag: api-friction
dimension: expressiveness
tool: powermodels
tests: [A-1, A-2]
timestamp: "2026-03-06T00:00:00Z"
---

# API Friction: Native PF vs JuMP-based PF return different status types

PowerModels provides two parallel APIs for power flow:

1. **Native (no JuMP):** `compute_dc_pf(data)`, `compute_ac_pf(data)` -- returns `"termination_status" => true/false` (Boolean)
2. **JuMP-based:** `solve_dc_pf(data, optimizer)`, `solve_ac_pf(data, optimizer)` -- returns `"termination_status" => OPTIMAL` (MOI enum)

This inconsistency means code written for one API cannot be reused for the other without branching on the status type. The native API is faster (no JuMP overhead) but uses a different return convention.

Additionally, the native `compute_dc_pf` solution dict does not include a `"gen"` key -- generator outputs are only updated in the data dict after `update_data!(data, sol)`, requiring the user to read from the modified data dict rather than the solution. The JuMP-based `solve_dc_pf` returns generator outputs in `result["solution"]["gen"]`.

**Impact:** Low-moderate. Requires careful reading of source code to discover the Boolean vs MOI status difference. Not documented prominently.
