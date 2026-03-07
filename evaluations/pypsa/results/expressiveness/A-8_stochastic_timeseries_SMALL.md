---
test_id: A-8
tool: pypsa
dimension: expressiveness
network: SMALL
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: null
peak_memory_mb: null
loc: null
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# A-8: Stochastic Timeseries Optimization (SMALL)

## Result: FAIL

## Approach

Same finding as TINY: PyPSA v1.1.2 does not support native stochastic optimization.
The `n.scenarios` attribute exists but is not wired to the optimizer (Linopy). There
is no scenario-indexed formulation — no scenario tree, no two-stage stochastic program,
no chance constraints.

The only way to solve multiple scenarios is a deterministic loop (`n.copy()` +
`n.optimize()` per scenario), which does not meet the pass condition requiring the
stochastic structure to be part of the optimization formulation.

## Why FAIL

The pass condition requires: "Tool natively supports scenario-indexed timeseries...
the stochastic structure is part of the optimization formulation (e.g., scenario tree,
two-stage stochastic program), not just independent deterministic solves in a loop."

PyPSA does not satisfy this. The deterministic loop approach is tested under B-4
(stochastic wrapping) and C-6 (stochastic scale) instead.

## Workarounds

- **What:** No workaround available — native stochastic optimization is absent.
- **Why:** PyPSA's optimizer (Linopy) has no scenario dimension.
- **Durability:** blocking — would require fundamental changes to the optimization backend.
- **Grade impact:** Significant. A-8 is a core expressiveness test. This represents a
  fundamental modeling capability gap.
- **Version tested:** PyPSA 1.1.2

## Test Script

Not executed at SMALL tier. TINY result carries forward — the capability gap is
tool-level, not network-dependent.
