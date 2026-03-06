# Observation: workaround-needed — B-8 Reference Bus Config

## Tool
PowerModels.jl v0.21.5

## Finding
**Single reference bus** is configurable via `data["bus"]["X"]["bus_type"] = 3`. This works cleanly and produces correct results.

**Distributed slack** is NOT supported natively. A workaround requires writing a custom `build_*` function (~40 LOC including boilerplate, ~15 LOC net new) that replaces `constraint_theta_ref` with a sum-of-angles constraint. The workaround works correctly (produces OPTIMAL solution with identical LMPs), demonstrating that the architecture supports this kind of extension, but it requires understanding:
1. How `build_opf` assembles constraints
2. How to access JuMP variables via `PowerModels.var(pm, :va, i)`
3. The `solve_model()` API for passing custom build functions

**Dual/LMP extraction** requires passing `setting = Dict("output" => Dict("duals" => true))` to the solve call. This is not obvious from the API surface and easy to miss.

## Impact
- Single ref bus: No friction
- Distributed slack: Medium friction (requires internals knowledge)
- LMP extraction: Low friction but undiscoverable without reading source code

## Recommendation
Document the `duals` setting prominently. Consider adding a distributed slack option as a built-in configuration.
