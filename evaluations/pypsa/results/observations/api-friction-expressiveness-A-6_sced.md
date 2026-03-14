---
tag: api-friction
source_dimension: expressiveness
source_test: A-6
tool: pypsa
severity: medium
timestamp: 2026-03-13T00:00:00Z
---

# Observation: No fix_commitment() API for two-stage UC/ED workflow

## Finding

PyPSA has no dedicated API to fix a UC commitment schedule and re-solve as pure LP economic dispatch. The two-stage UC-then-ED workflow requires manually setting `committable=False` and constructing time-varying `p_min_pu`/`p_max_pu` DataFrames to encode the commitment schedule as generator bounds.

## Context

Test A-6 (SCED) demonstrated the two-stage workflow by: (1) solving UC with `committable=True`, (2) extracting `generators_t.status`, (3) reloading the network with `committable=False`, (4) building per-hour bounds where committed=1 maps to [0.3, 1.0] and committed=0 maps to [0.0, 0.0]. The approach works and uses only documented public API, but requires ~20 lines of boilerplate that could be a single method call.

## Implications

This affects the Accessibility assessment (D-dimension): a common power systems workflow (fix commitment, re-solve dispatch) requires non-obvious manual steps. Users must understand the relationship between `committable`, `generators_t.p_min_pu`, and `generators_t.p_max_pu` to implement the two-stage pattern. A `fix_commitment()` or `freeze_uc()` convenience method would significantly reduce friction.
