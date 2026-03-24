---
tag: doc-gaps
source_dimension: expressiveness
source_test: A-3
tool: gridcal
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: OPF options naming inconsistency, undocumented soft constraints

## Finding

Two documentation gaps discovered during A-3 DCOPF testing:

1. **Parameter naming inconsistency:** `OptimalPowerFlowOptions` uses `solver=` while
   `PowerFlowOptions` uses `solver_type=`. This caused an initial `TypeError` and required
   runtime introspection to resolve.

2. **Undocumented soft branch constraints:** The `linear_opf` formulation uses soft branch
   flow constraints (LP slack variables with penalty costs). Branch 2_3_1 shows 112.24%
   loading in the optimal solution -- exceeding the derated thermal limit. The `overloads`
   result attribute reports -42.85 MW but the penalty coefficient is not documented and the
   relationship between `overloads`, `loading`, and branch shadow prices is unclear.

## Context

The ReadTheDocs documentation covers up to version 5.0.2 with the old `GridCalEngine` naming.
The installed version is 5.6.28. Source code inspection was required to determine correct API
patterns. The soft constraint behavior was confirmed via cross-tool-watchpoints.md (probe-005)
and independently verified by checking max branch loading in the DCOPF solution.

## Implications

For accessibility assessment: Documentation lag is a significant barrier. The soft constraint
behavior is particularly important because it means GridCal's DCOPF results have different
semantics than hard-constraint tools -- LMPs reflect penalty costs rather than true congestion
relief costs. Users may not realize this without reading the source code.

For maturity assessment: The documentation gap between published docs (v5.0.2) and installed
version (v5.6.28) suggests rapid development outpacing documentation updates.
