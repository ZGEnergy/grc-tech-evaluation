---
tag: solver-issues
source_dimension: expressiveness
source_test: A-3
tool: gridcal
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: GridCal linear_opf uses soft branch flow constraints

## Finding

GridCal's `linear_opf` formulation uses soft branch flow constraints (LP slack variables)
rather than hard inequality constraints. In the A-3 DCOPF test with 70% branch derating,
branch 2_3_1 showed 112.24% loading in the optimal solution -- exceeding the derated thermal
limit by 12.24 percentage points. The `overloads` result attribute reports -42.85 MW for this
branch. [tool-specific: soft constraint formulation in linear_opf]

## Context

This was tested on the IEEE 39-bus (TINY) network with differentiated generator costs and
70% branch derating. Six other branches showed exactly 100.00% loading, indicating the
soft constraint penalty is high enough to keep most branches at their limits but not high
enough to prevent violations on the most congested branch.

The soft constraint behavior is consistent with the cross-tool watchpoint documentation
(probe-005, v10-to-v11 sweep) which confirmed this as a known characteristic of GridCal's
linear_opf formulation.

## Implications

For scalability assessment: The soft constraint formulation may mask congestion severity at
larger scales. If the penalty coefficient is not scaled with network size, violations could
be more pronounced on larger networks.

For extensibility assessment: Users cannot configure hard branch constraints through the
public API. There is no documented option to switch between soft and hard constraint modes
in the linear_opf formulation.
