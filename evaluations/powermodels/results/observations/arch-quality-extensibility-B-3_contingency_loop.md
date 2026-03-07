---
tag: arch-quality
dimension: extensibility
test_id: B-3
slug: contingency_loop
tool: powermodels
---

# arch-quality: Data-dict architecture enables efficient contingency loops

PowerModels' data model is a plain Julia Dict, which makes contingency analysis
straightforward:

1. `deepcopy(data)` clones the entire network in ~0.5ms for the 39-bus case.
2. `data["branch"][id]["br_status"] = 0` toggles a branch outage -- no model
   reconstruction needed.
3. `compute_dc_pf(data)` solves directly from the modified dict.
4. `calc_connected_components(data)` detects islands before solving.
5. `calc_branch_flow_dc(data)` computes flows from the PF solution.

This pattern ran 46 N-1 contingencies in 0.22s (median 0.95ms each, excluding JIT).
No file re-parsing. No model re-instantiation. The dict-based data model naturally
supports in-memory modification.

The first contingency took 177ms due to Julia's JIT compilation of `calc_connected_components`
and `calc_branch_flow_dc` on first call. Subsequent iterations ran at ~1ms each.
This is a Julia language characteristic, not a PowerModels issue.

For production use at scale (thousands of buses, thousands of contingencies), the
`deepcopy` cost would grow linearly with network size. A more sophisticated approach
would modify the admittance matrix directly (rank-1 update), but the dict-copy approach
is simple and sufficient for moderate networks.
