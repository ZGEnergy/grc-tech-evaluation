---
tag: workaround-needed
source_dimension: expressiveness
source_test: A-12
tool: pypsa
severity: medium
timestamp: 2026-03-11T00:00:00Z
---

# Observation: Shadow prices empty after multi-period optimize() — same fragile workaround as A-3 applies at scale

## Finding

In multi-period OPF (24 snapshots), `n.lines_t.mu_upper` remains empty after `n.optimize()`. Shadow prices for congestion analysis must be extracted from `n.model.constraints["Line-fix-s-upper"].dual` — the same fragile workaround identified in A-3. At multi-period scale, the dual array has an additional snapshot dimension that requires careful indexing.

## Context

Discovered during A-12 multi-period DCOPF with BESS and renewables. The shadow price extraction loop must handle the `(snapshot, name)` dimensions of the dual DataArray. The constraint naming convention (`Line-fix-s-upper`, `Line-fix-s-lower`) persists across single-period and multi-period solves.

## Implications

The fragile shadow price workaround (from A-3) propagates to all multi-period applications. Any extensibility test (B-tests) or scalability test (C-tests) that needs shadow prices will encounter the same issue. The `assign_all_duals=True` parameter exists on `n.optimize()` but the shadow prices are still not assigned to `n.lines_t.mu_upper` — the behavior appears to assign them back to a different attribute. The consuming dimensions should check whether `assign_all_duals=True` resolves this in their evaluation context.

Also note: the BESS sign convention (positive = discharge, negative = charge) is consistent with PyPSA documentation but opposite to some other tools (pandapower uses positive = generation/discharge). Cross-tool BESS comparisons should account for this.
