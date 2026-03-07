---
test_id: B-1
tool: gridcal
dimension: extensibility
network: TINY
protocol_version: "v4"
status: fail
workaround_class: blocking
wall_clock_seconds: 0.104
peak_memory_mb: null
loc: 230
solver: HiGHS
timestamp: 2026-03-06T02:30:00Z
---

# B-1: Custom Constraints

## Result: FAIL

## Approach

Attempted to add a flow gate limit to the DC OPF formulation on IEEE 39-bus and extract the dual value for the binding constraint. Investigated three approaches:

1. **Rate modification** -- tightened `branch.rate` on the most-loaded branch to 80% of baseline flow.
2. **API search** -- scanned all grid methods, VGE classes, and OPF option attributes for custom constraint support.
3. **Internal model access** -- checked whether the PuLP LP model is exposed via the results object.

## Findings

### Rate Modification (Partial Workaround)

Branch rate modification successfully forces a flow gate to bind:

| Metric | Baseline | Constrained |
|--------|----------|-------------|
| Target branch flow (MW) | -865.0 | -692.0 |
| Target branch loading (%) | 72.1 | 100.0 |
| Constraint binding | No | Yes |
| Total generation (MW) | 6254.23 | 6254.23 |
| LMP range ($/MWh) | 0.3 -- 0.3 | 0.3 -- 0.3 |

LMPs did not change because all generators have identical costs (0.3 $/MWh), so redispatch does not affect marginal cost. The constraint is binding (100% loading) but its economic impact is masked by uniform costs.

### API Search Results

| Search Target | Found |
|---------------|-------|
| Grid methods with "constraint"/"limit" | None |
| VGE classes with "constraint" | Contingency-related only (N-1 analysis, not custom LP constraints) |
| Flow gate / interface classes | BranchGroup exists but is not wired into OPF formulation |
| Per-constraint dual values | Not available -- only nodal LMPs (bus_shadow_prices) |
| PuLP model access | Not exposed via results or options objects |

### Why This Fails

The pass condition requires:
1. Custom constraints addable through a documented API -- **not met**. The OPF formulation is hardcoded in PuLP model-building code. No user-facing API to inject additional linear constraints.
2. No source patching -- **would be required**. Adding custom constraints requires modifying the internal LP formulation files.
3. Dual value extractable from binding constraint -- **not met**. Only nodal LMPs are returned. Per-branch or per-constraint shadow prices are not accessible.

### Rate Modification Limitations

- Only handles single-branch flow limits (already built into the formulation)
- Cannot express multi-branch interface limits (sum of flows across corridor)
- Cannot add generator group constraints
- Cannot add arbitrary linear constraints (e.g., ramp limits, reserve requirements)
- No dual/shadow price for the specific constraint

## Workaround Classification: BLOCKING

Rate modification is not a workaround for the general custom constraint requirement -- it only reuses the existing branch limit mechanism. True custom constraints would require source modification of the LP formulation code.

## Test Script

**Path:** `evaluations/gridcal/tests/extensibility/test_b1_custom_constraints.py`
