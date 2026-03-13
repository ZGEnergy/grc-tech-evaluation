---
tag: api-friction
dimension: expressiveness
test_id: A-7
observed: 2026-03-11
tool: powermodels
version: 0.21.5
---

# API Friction: No built-in N-x contingency solver; no graph library integration

## Observation

PowerModels.jl provides no dedicated N-1 or N-x contingency screening function. The `solve_opf_ptdf_branch_power_cuts` and `solve_opf_branch_power_cuts` functions are iterative OPF solvers that add flow-limit constraints dynamically — they are not classical N-k load-loss screening tools.

For classical contingency sweeps, users must:
1. Load the base case once
2. `deepcopy` the data dict per contingency
3. Set `branch["br_status"] = 0` to apply the outage
4. Call `compute_dc_pf` or solve OPF
5. Post-process results

This pattern works correctly and is expressed cleanly. The `deepcopy` approach avoids file reconstruction — the key pass condition for A-7.

## Graph API Gap

PowerModels has no native `Graphs.jl` integration and no topology traversal API beyond the raw `data["branch"]` dict. Graph-distance scoping (for pruning) requires manual BFS implementation (~20 lines from `f_bus`/`t_bus` fields).

`PowerModelsAnalytics.jl` (not installed in this evaluation) provides a `Graphs.jl` bridge, but it is a separate package not part of the core PowerModels.jl API.

## Performance Note

`compute_dc_pf` (Julia backslash, no JuMP) runs at approximately 0.7–2.4 ms per contingency after JIT warmup on case39. Full N-2 sweep (1,035 cases) completes in 0.725s. This is fast enough for operational screening on TINY networks.
