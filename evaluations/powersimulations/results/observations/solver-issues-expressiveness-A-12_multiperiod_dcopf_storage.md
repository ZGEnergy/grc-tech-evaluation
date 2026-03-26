---
tag: solver-issues
source_dimension: expressiveness
source_test: A-12
tool: powersimulations
severity: medium
timestamp: "2026-03-24T00:00:00Z"
---

# Observation: HiGHS fails on multi-period QP models

## Finding

HiGHS returns `OTHER_ERROR` when solving 24-period QP models (quadratic costs with
`c2 = c1 * 0.001`). The same QP formulation succeeds on single-period models (A-3).
This limits multi-period OPF to linear costs when using HiGHS.

## Context

A-12 specifies quadratic costs (`c2 = c1 * 0.001`) per the Modified Tiny recipe. HiGHS
handles single-period QP correctly (A-3 passes) but fails on the 24x larger multi-period
model. Ipopt solves the same QP without issue, confirming this is a HiGHS limitation rather
than a model formulation error.

## Implications

This is relevant to the Scalability audit (C-7 solver swap). The HiGHS QP failure at
multi-period scale means tools using HiGHS for QP-based OPF may need to fall back to
linear costs or switch solvers at scale. This is a solver-specific limitation, not a
tool-specific one.
