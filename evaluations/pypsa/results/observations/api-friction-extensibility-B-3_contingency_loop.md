---
tag: api-friction
source_dimension: extensibility
source_test: B-3
tool: pypsa
severity: medium
timestamp: 2026-03-11T00:00:00Z
---

# Observation: SubNetwork access requires undocumented data structure knowledge

## Finding

Accessing a `SubNetwork` object — required for PTDF, BODF, and contingency analysis — requires `n.sub_networks.at['0', 'obj']`. The key `'obj'` is an undocumented column name in the internal `sub_networks` DataFrame, and the index `'0'` is the auto-assigned name for the single sub-network. Neither is documented in user-facing examples.

## Context

Multiple extensibility tests (B-3, B-9) require accessing the `SubNetwork` object to call `calculate_PTDF()` or `calculate_BODF()`. The pattern `n.sub_networks.at['0', 'obj']` works but is only discoverable by reading source code. There is no documented method like `n.get_sub_network()` or equivalent. Users who don't know to look in `n.sub_networks` will not find the PTDF/BODF API.

The `sub_networks` DataFrame has an `'obj'` column containing Python objects — a pattern that is not consistent with PyPSA's general DataFrame-based data model where columns contain numeric or string values.

## Implications

This API friction affects any user attempting to use PyPSA's sensitivity analysis capabilities. The Accessibility audit (D-tests) should verify whether the PTDF/BODF access pattern is documented in any official guide, tutorial, or docstring. The Maturity audit should note this as a discoverability gap — the capability exists but is hidden behind an internal data structure convention.
