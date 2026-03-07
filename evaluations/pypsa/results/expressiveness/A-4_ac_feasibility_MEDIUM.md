---
test_id: A-4
tool: pypsa
dimension: expressiveness
network: MEDIUM
protocol_version: "v4"
status: fail
workaround_class: null
wall_clock_seconds: 0.0
peak_memory_mb: null
loc: null
solver: highs
timestamp: 2026-03-06T00:00:00Z
---

# A-4: AC feasibility check (MEDIUM -- ACTIVSg10k)

## Result: FAIL

## Details

A-4 depends on A-3 (DC OPF) to produce a dispatch which is then checked for AC feasibility
via `n.pf()`. Since A-3 is infeasible on the MEDIUM network (2,462 branches with `s_nom == 0`
cause the LP to be infeasible during presolve), A-4 cannot proceed.

**Error:** `DC OPF did not converge: ('warning', 'infeasible')`

**Root cause:** Same as A-3 -- the ACTIVSg10k MATPOWER case has zero-capacity branches that
make the DC OPF infeasible. This is a data-preparation issue; the test would likely pass
if s_nom values were corrected before optimization.

**Workaround applied (inherited from A-3):**
- Manually set marginal_cost on 2,485 generators from gencost data
