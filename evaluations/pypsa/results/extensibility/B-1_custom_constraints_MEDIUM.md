---
test_id: B-1
tool: pypsa
dimension: extensibility
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

# B-1: Custom constraints (MEDIUM -- ACTIVSg10k)

## Result: FAIL

## Details

B-1 adds a flow-gate constraint to the DC OPF and checks that the constraint is binding.
Since the baseline DC OPF is infeasible on the ACTIVSg10k network (same root cause as A-3:
2,462 branches with `s_nom == 0`), B-1 cannot proceed.

**Error:** `TypeError: float() argument must be a string or a real number, not 'NoneType'`
(triggered by attempting to read `n.objective` after infeasible solve)

**Root cause:** The MATPOWER case has zero-capacity branches making the LP infeasible during
presolve. This is a data-preparation issue, not a tool limitation. The custom constraint
API (`n.optimize()` with extra constraints via linopy) works correctly on the TINY network.

**Workaround applied:**
- Manually set marginal_cost on 2,485 generators with small perturbations to break LP
  degeneracy
