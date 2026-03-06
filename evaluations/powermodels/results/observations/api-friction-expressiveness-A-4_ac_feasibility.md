---
tag: api-friction
dimension: expressiveness
test_id: A-4
tool: powermodels
---

# API Friction: Inconsistent Return Types Between DC and AC Power Flow

PowerModels' native power flow functions have inconsistent return semantics:

- `compute_dc_pf(data)` returns a result Dict, does NOT modify `data`, requires `update_data!()` to propagate solution
- `compute_ac_pf!(data)` returns `Nothing`, modifies `data` in-place

While the `!` suffix follows Julia's mutating-function convention, the asymmetry means users must know which function mutates and which doesn't. The DC PF function name lacks `!` but also doesn't modify data, which is correct -- but the different patterns for the same conceptual operation (power flow) create a learning curve.

This inconsistency caused an initial test failure when the A-4 script assumed `compute_ac_pf!` returned a result dict (like `compute_dc_pf`).
