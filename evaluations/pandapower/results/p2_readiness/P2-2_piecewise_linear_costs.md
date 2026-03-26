---
test_id: P2-2
tool: pandapower
dimension: p2_readiness
network: N/A
status: informational
workaround_class: null
timestamp: 2026-03-13T00:00:00Z
protocol_version: v11
skill_version: v2
test_hash: "c7801e67"
---

# P2-2: Piecewise-Linear Cost Curves

## Question

Can pandapower handle piecewise-linear cost curves in OPF?

## Finding

**Yes.** pandapower has a first-class `create_pwl_cost()` API that works with both
DC OPF (`rundcopp`) and AC OPF (`runopp`).

### API

```python
pp.create_pwl_cost(net, element, et, points, power_type="p")
```

- **`element`**: index of the element in its table
- **`et`**: element type — `"gen"`, `"sgen"`, `"ext_grid"`, `"load"`, `"dcline"`, `"storage"`
- **`points`**: list of `[p_start, p_end, marginal_cost]` segments, e.g.,
  `[[0, 40, 1.0], [40, 100, 3.0]]` for 1 EUR/MW over 0-40 MW, 3 EUR/MW over 40-100 MW
- **`power_type`**: `"p"` (active) or `"q"` (reactive)

Costs are stored in `net.pwl_cost` DataFrame. A companion `create_poly_cost()` handles
polynomial (quadratic) cost curves.

### Test performed

Two-bus system with two generators and a 50 MW load:

- **Gen 0**: PWL cost 1 EUR/MW for 0-40 MW, 3 EUR/MW for 40-100 MW
- **Gen 1**: PWL cost 2 EUR/MW for 0-80 MW

Expected dispatch: Gen 0 dispatches its cheap 40 MW tranche first, Gen 1 picks up the
remaining 10 MW at 2 EUR/MW (cheaper than Gen 0's 3 EUR/MW second tranche).

**DC OPF result**: Gen 0 = 40.0 MW, Gen 1 = 10.0 MW, cost = 60.0 EUR. Correct.

**AC OPF result**: Gen 0 = 40.0 MW, Gen 1 = 10.0 MW, cost = 60.0 EUR. Correct
(minor deviations from losses).

### Observations

- The PWL cost format uses marginal cost per segment (slope), not cumulative cost at
  breakpoints. This matches MATPOWER's `COST` format type 1.
- Segments must be continuous (end point of segment n = start point of segment n+1).
- Both `create_pwl_cost` and `create_pwl_costs` (batch version) are available.
- The optimizer correctly respects the kink in the cost curve, dispatching up to the
  breakpoint where marginal cost changes.
- No friction observed — the API is clean and well-documented.
